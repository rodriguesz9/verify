import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="fixed inset-0 bg-bg flex items-center justify-center">
        <div style={{ position: "relative", width: 48, height: 48 }}>
          <div className="anim-spin-cw" style={{
            position: "absolute", inset: 0, borderRadius: "50%",
            border: "2px solid transparent", borderTopColor: "#00D4FF", borderRightColor: "rgba(0,212,255,.4)"
          }}/>
          <svg width="48" height="48" viewBox="0 0 28 28" style={{ position:"absolute", inset:0 }}>
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00D4FF" strokeWidth="1" opacity=".3"/>
            <circle cx="14" cy="14" r="3" fill="#00D4FF" opacity=".7"/>
          </svg>
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return children;
}
