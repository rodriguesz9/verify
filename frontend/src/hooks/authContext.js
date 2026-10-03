import {createContext, useContext} from "react";

// Keep context identity outside the Fast Refresh component boundary.
export const AuthCtx = createContext(null);

export function useAuth() {
  const context = useContext(AuthCtx);
  if (!context) throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  return context;
}
