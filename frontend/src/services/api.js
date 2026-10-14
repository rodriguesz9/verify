import axios from "axios";
import { captureAnalysisScope, clearSensitiveBrowserData } from "./privacyStorage.js";
import { transcriptionScopeHeaders } from "./transcriptionScope.js";

const apiOrigin = import.meta.env?.VITE_API_URL;
const baseURL = apiOrigin ? `${apiOrigin.replace(/\/$/, '')}/api` : "/api";
export const api = axios.create({ baseURL, timeout: 60000, withCredentials: true });
// These budgets cover the server's bounded provider deadlines, including
// extraction + retrieval + grounded document comparison. This is a bounded
// wait, not a retry; authentication, media uploads and PDF keep shorter limits.
const ANALYSIS_TIMEOUT = 240000;
const MEDIA_TIMEOUT = 180000;

// Compare epochs even before getMe initializes the account. The report storage
// guard intentionally requires initialization, whereas this transport guard
// must permit startup /auth/me and detect A -> B -> A transitions.
const isRequestScopeCurrent = (config) => {
  const current = captureAnalysisScope();
  return !!config?._privacyScope && config._privacyScope.owner === current.owner
    && config._privacyScope.epoch === current.epoch;
};
// Synchronous capture closes the gap before an asynchronous interceptor runs.
api.interceptors.request.use((config) => {
  config._privacyScope ??= captureAnalysisScope();
  if (!isRequestScopeCurrent(config)) {
    throw new axios.CanceledError("A sessão mudou. Faça um novo pedido.", config);
  }
  return config;
}, (error) => { throw error; }, { synchronous: true });

// Authentication remains in HTTP-only cookies; JavaScript never receives a JWT.
// Only read-only requests may be replayed, in the same owner/epoch. This does
// not undo server writes or a late Set-Cookie from an already sent request.
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    // A client error without an original request must not enter refresh/retry.
    const skipRefresh = ["/auth/login", "/auth/register", "/auth/google", "/auth/refresh", "/auth/logout"].includes(orig?.url);
    if (orig && err.response?.status === 401 && !orig._retry && !orig._skipAuthRefresh && !skipRefresh
      && isRequestScopeCurrent(orig)) {
      orig._retry = true;
      try {
        await api.post("/auth/refresh", {}, { _skipAuthRefresh: true, _privacyScope: orig._privacyScope });
      } catch {
        // An old failure must not log out an account opened while refresh ran.
        if (isRequestScopeCurrent(orig) && !orig._skipLogoutRedirect) logout();
        return Promise.reject(err);
      }
      if (!isRequestScopeCurrent(orig)) return Promise.reject(err);
      if (["get", "head", "options"].includes(String(orig.method).toLowerCase())) return api(orig);
      // Uploads, analyses, PDF snapshots and other writes require a deliberate
      // new request: never replay their body/FormData under renewed cookies.
      err.message = "Seu pedido não foi reenviado automaticamente. Envie novamente se desejar.";
      err.code = "ERR_REQUEST_REQUIRES_RESUBMISSION";
      err.response = { ...err.response, data: { detail: err.message } };
    }
    return Promise.reject(err);
  }
);

export const logout = (redirect = "/login") => {
  clearSensitiveBrowserData({ broadcast: true, reason: "logout" });
  const scope = captureAnalysisScope();
  return api.post("/auth/logout", {}, { _skipAuthRefresh: true, _privacyScope: scope })
    .catch(() => {})
    .finally(() => {
      if (isRequestScopeCurrent({ _privacyScope: scope })) window.location.href = redirect;
    });
};

// ── Auth ──────────────────────────────────────────────────────────────────────
const authenticate = (endpoint, body) => {
  // Invalidate pending private work and notify other tabs before cookies can
  // change, not only after LoginPage receives the new account.
  clearSensitiveBrowserData({ broadcast: true, reason: "account-change" });
  return api.post(endpoint, body).then(r => r.data);
};
export const register   = (b) => authenticate("/auth/register", b);
export const login      = (b) => authenticate("/auth/login", b);
export const googleAuth = (b) => authenticate("/auth/google", b);
export const refreshTokens = () => api.post("/auth/refresh", {}).then(r => r.data);
export const getMe      = ()  => api.get ("/auth/me", { _skipLogoutRedirect: true }).then(r => r.data);

// ── Analysis ──────────────────────────────────────────────────────────────────
export const analyzeText   = (text) => api.post("/check-text", { text }, { timeout: ANALYSIS_TIMEOUT }).then(r => r.data);
export const analyzeTextBatch = (texts) => api.post("/check-text-batch", { texts }, { timeout: ANALYSIS_TIMEOUT }).then(r => r.data);
export const analyzeUrl    = (url)  => api.post("/check-url", { url }, { timeout: ANALYSIS_TIMEOUT }).then(r => r.data);
export const analyzeUpload = (file, { reviewText = false } = {}) => {
  const form = new FormData();
  form.append("file", file);
  if (reviewText) form.append("review_text", "true");
  return api.post("/upload", form, { timeout: MEDIA_TIMEOUT, headers: { "Content-Type": "multipart/form-data", ...transcriptionScopeHeaders() } }).then(r => r.data);
};
export const analyzeReviewedText = (text, reviewToken) => api.post("/check-extracted-text", {
  text, review_token: reviewToken,
}, { timeout: ANALYSIS_TIMEOUT }).then(r => r.data);

// ── Verification & interactive demonstration ───────────────────────────────
export const verifyAudioQuick = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/verificar/audio-rapido", form, { timeout: MEDIA_TIMEOUT, headers: { "Content-Type": "multipart/form-data", ...transcriptionScopeHeaders() } }).then(r => r.data);
};

export const captureSeal = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/capturar/selo", form, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
};

export const verifySeal = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/verificar/selo", form, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
};

export const verifyComplete = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/verificar/completo", form, { timeout: MEDIA_TIMEOUT, headers: { "Content-Type": "multipart/form-data", ...transcriptionScopeHeaders() } }).then(r => r.data);
};

export const downloadPdfReport = async (snapshotToken) => {
  if (typeof snapshotToken !== "string" || !snapshotToken.startsWith("vpdf1.") || snapshotToken.length > 512 * 1024) {
    throw new Error("Esta análise não tem uma exportação de PDF disponível.");
  }
  const resp = await api.post("/verificar/relatorio-pdf", { snapshot_token: snapshotToken }, {
    responseType: "blob",
    timeout: 30000,
    _skipLogoutRedirect: true,
  });
  return resp.data;
};

// ── WhatsApp ──────────────────────────────────────────────────────────────────
export const simulateWhatsApp = (message) => api.post("/whatsapp/simulate", { message }, { timeout: ANALYSIS_TIMEOUT, headers: transcriptionScopeHeaders() }).then(r => r.data);

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory = (page = 1, { search = "", contentType = "all", verdict = "all", signal } = {}) => api.get("/history", { params: { page, limit: 20, search, content_type: contentType, verdict }, signal }).then(r => r.data);
export const getStats   = ()         => api.get("/history/stats"                 ).then(r => r.data);
export const getLog     = (id)       => api.get(`/history/${id}`                 ).then(r => r.data);
