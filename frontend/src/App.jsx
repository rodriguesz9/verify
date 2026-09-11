import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import SplashScreen from "./components/SplashScreen";

import LandingPage  from "./pages/LandingPage";
import Home         from "./pages/Home";
import Dashboard    from "./pages/Dashboard";
import ReportPage   from "./pages/ReportPage";
import HistoryPage  from "./pages/HistoryPage";
import PricingPage  from "./pages/PricingPage";
import LoginPage    from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import Missao       from "./pages/Missao";
import Sugestoes    from "./pages/Sugestoes";
import Termos       from "./pages/Termos";
import Privacidade  from "./pages/Privacidade";
import LimitacoesIA from "./pages/LimitacoesIA";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 2500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AuthProvider>
      {showSplash && <SplashScreen />}
      <Routes>
        <Route path="/"            element={<LandingPage />} />
        <Route path="/login"       element={<LoginPage />} />
        <Route path="/register"    element={<RegisterPage />} />
        <Route path="/terms"       element={<><Navbar/><Termos/></>} />
        <Route path="/privacy"     element={<><Navbar/><Privacidade/></>} />
        <Route path="/limitations" element={<><Navbar/><LimitacoesIA/></>} />

        <Route path="/app"        element={<><Navbar/><Home/></>} />
        <Route path="/report"     element={<><Navbar/><ReportPage/></>} />
        <Route path="/report/:id" element={<><Navbar/><ReportPage/></>} />
        <Route path="/plans"      element={<><Navbar/><PricingPage/></>} />
        <Route path="/mission"    element={<><Navbar/><Missao/></>} />
        <Route path="/suggestions" element={<><Navbar/><Sugestoes/></>} />
        <Route path="/dashboard"  element={<ProtectedRoute><><Navbar/><Dashboard/></></ProtectedRoute>} />
        <Route path="/history"    element={<ProtectedRoute><><Navbar/><HistoryPage/></></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  );
}
