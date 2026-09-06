import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000, withCredentials: true });

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    const skipRefresh = ["/auth/login", "/auth/register", "/auth/google", "/auth/refresh", "/auth/logout"].includes(orig?.url);
    if (err.response?.status === 401 && !orig._retry && !orig._skipAuthRefresh && !skipRefresh) {
      orig._retry = true;
      try {
        await api.post("/auth/refresh", {}, { _skipAuthRefresh: true });
        return api(orig);
      } catch {
        // Startup session checks are expected to fail for signed-out visitors.
        // Redirecting them here reloads /login indefinitely.
        if (!orig._skipLogoutRedirect) logout();
      }
    }
    return Promise.reject(err);
  }
);

export const logout = (redirect = "/login") => {
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

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory = (page = 1) => api.get(`/history?page=${page}&limit=20`).then(r => r.data);
export const getStats   = ()         => api.get("/history/stats"                 ).then(r => r.data);
export const getLog     = (id)       => api.get(`/history/${id}`                 ).then(r => r.data);
