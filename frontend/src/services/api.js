import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api` : "/api";
const api = axios.create({ baseURL, timeout: 60000, withCredentials: true });

// Attach JWT from localStorage on every request as fallback
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("verify_access") || localStorage.getItem("verifai_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    const skipRefresh = ["/auth/login", "/auth/register", "/auth/google", "/auth/refresh", "/auth/logout"].includes(orig?.url);
    if (err.response?.status === 401 && !orig._retry && !orig._skipAuthRefresh && !skipRefresh) {
      orig._retry = true;
      try {
        const refresh = localStorage.getItem("verify_refresh") || localStorage.getItem("verifai_refresh");
        if (refresh) {
          const { data } = await axios.post(`${baseURL}/auth/refresh`, { refresh_token: refresh }, { withCredentials: true });
          localStorage.setItem("verify_access",  data.access_token);
          localStorage.setItem("verify_refresh", data.refresh_token);
          orig.headers.Authorization = `Bearer ${data.access_token}`;
          return api(orig);
        } else {
          await api.post("/auth/refresh", {}, { _skipAuthRefresh: true });
          return api(orig);
        }
      } catch {
        if (!orig._skipLogoutRedirect) logout();
      }
    }
    return Promise.reject(err);
  }
);

export const logout = (redirect = "/login") => {
  localStorage.removeItem("verify_access");
  localStorage.removeItem("verify_refresh");
  localStorage.removeItem("verifai_access");
  localStorage.removeItem("verifai_refresh");
  api.post("/auth/logout", {}, { _skipAuthRefresh: true })
    .catch(() => {})
    .finally(() => { window.location.href = redirect; });
};

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register   = (b) => api.post("/auth/register",   b).then(r => r.data);
export const login      = (b) => api.post("/auth/login",      b).then(r => r.data);
export const googleAuth = (b) => api.post("/auth/google",     b).then(r => r.data);
export const refreshTokens = () => api.post("/auth/refresh", {}).then(r => r.data);
export const getMe      = ()  => api.get ("/auth/me", { _skipLogoutRedirect: true }).then(r => r.data);

// ── Analysis ──────────────────────────────────────────────────────────────────
export const analyzeText   = (text) => api.post("/check-text", { text }    ).then(r => r.data);
export const analyzeUrl    = (url)  => api.post("/check-url",  { url }     ).then(r => r.data);
export const analyzeUpload = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/upload", form, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
};

// ── WhatsApp ──────────────────────────────────────────────────────────────────
export const simulateWhatsApp = (message) => api.post("/whatsapp/simulate", { message }).then(r => r.data);

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory = (page = 1) => api.get(`/history?page=${page}&limit=20`).then(r => r.data);
export const getStats   = ()         => api.get("/history/stats"                 ).then(r => r.data);
export const getLog     = (id)       => api.get(`/history/${id}`                 ).then(r => r.data);
