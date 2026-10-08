import { useState, useEffect, useCallback, useRef } from "react";
import { getMe, logout as apiLogout } from "../services/api";
import { syncAnalysisAccount, subscribeAnalysisReset } from "../services/privacyStorage.js";
import { AuthCtx } from "./authContext";
// Export only the provider component so Fast Refresh keeps consumers coherent.

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);
  const authRequest = useRef(0);

  const loadUser = useCallback(async () => {
    const request = ++authRequest.current;
    try {
      const me = await getMe();
      if (request !== authRequest.current) return;
      syncAnalysisAccount(me);
      setUser(me);
    } catch {
      if (request !== authRequest.current) return;
      syncAnalysisAccount(null);
      setUser(null);
    } finally {
      if (request === authRequest.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
    const unsubscribe = subscribeAnalysisReset(({ reason, remote }) => {
      if (reason === "logout") {
        authRequest.current += 1;
        syncAnalysisAccount(null);
        setUser(null);
        setLoading(false);
      } else if (remote) {
        setLoading(true);
        loadUser();
      }
    });
    return () => { unsubscribe(); authRequest.current += 1; };
  }, [loadUser]);

  const signIn = (me) => {
    authRequest.current += 1;
    syncAnalysisAccount(me, { broadcast: true });
    setUser(me);
    setLoading(false);
  };

  const signOut = () => {
    authRequest.current += 1;
    setUser(null);
    setLoading(false);
    apiLogout("/");
  };

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signOut, reload: loadUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
