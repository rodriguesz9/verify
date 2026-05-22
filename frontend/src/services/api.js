import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000 });

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("verifai_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true;
      const refresh = localStorage.getItem("verifai_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post("/api/auth/refresh", { refresh_token: refresh });
          localStorage.setItem("verifai_access",  data.access_token);
          localStorage.setItem("verifai_refresh", data.refresh_token);
          orig.headers.Authorization = `Bearer ${data.access_token}`;
          return api(orig);
        } catch { logout(); }
      }
    }
    return Promise.reject(err);
  }
);

export const logout = () => {
  localStorage.removeItem("verifai_access");
  localStorage.removeItem("verifai_refresh");
  window.location.href = "/login";
};

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register   = (b) => api.post("/auth/register",   b).then(r => r.data);
export const login      = (b) => api.post("/auth/login",      b).then(r => r.data);
export const googleAuth = (b) => api.post("/auth/google",     b).then(r => r.data);
export const refreshTokens=(b)=> api.post("/auth/refresh",    b).then(r => r.data);
export const getMe      = ()  => api.get ("/auth/me"           ).then(r => r.data);

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
