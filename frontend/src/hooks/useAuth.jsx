import { useState, useEffect, useCallback } from "react";
import { getMe, logout as apiLogout } from "../services/api";
import { AuthCtx } from "./authContext";
// Export only the provider component so Fast Refresh keeps consumers coherent.

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
      localStorage.removeItem("verify_access");
      localStorage.removeItem("verify_refresh");
      localStorage.removeItem("verifai_access");
      localStorage.removeItem("verifai_refresh");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const signIn = (me) => {
    setUser(me);
  };

  const signOut = () => {
    localStorage.removeItem("verify_access");
    localStorage.removeItem("verify_refresh");
    localStorage.removeItem("verifai_access");
    localStorage.removeItem("verifai_refresh");
    setUser(null);
    apiLogout("/");
  };

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signOut, reload: loadUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
