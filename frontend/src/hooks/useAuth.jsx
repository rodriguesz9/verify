import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getMe, logout as apiLogout } from "../services/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem("verifai_access");
    if (!token) { setLoading(false); return; }
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      localStorage.removeItem("verifai_access");
      localStorage.removeItem("verifai_refresh");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const signIn = (tokens, me) => {
    localStorage.setItem("verifai_access",  tokens.access_token);
    localStorage.setItem("verifai_refresh", tokens.refresh_token);
    setUser(me);
  };

  const signOut = () => {
    localStorage.removeItem("verifai_access");
    localStorage.removeItem("verifai_refresh");
    setUser(null);
    window.location.href = "/";
  };

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signOut, reload: loadUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
