import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import SplashScreen from "./components/SplashScreen";

import LandingPage  from "./pages/LandingPage";
import Home         from "./pages/Home";
import Dashboard    from "./pages/Dashboard";
import ReportPage   from "./pages/ReportPage";
import LoginPage    from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import Missao       from "./pages/Missao";
import Sugestoes    from "./pages/Sugestoes";
import Termos       from "./pages/Termos";
import Privacidade  from "./pages/Privacidade";
import LimitacoesIA from "./pages/LimitacoesIA";
import DemonstracaoPage from "./pages/DemonstracaoPage";

function PageWrapper({ children }) {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return (
    <div key={location.pathname} className="page-transition">
      {children}
    </div>
  );
}

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
        <Route path="/"            element={<PageWrapper><LandingPage /></PageWrapper>} />
        <Route path="/login"       element={<PageWrapper><LoginPage /></PageWrapper>} />
        <Route path="/register"    element={<PageWrapper><RegisterPage /></PageWrapper>} />
        <Route path="/terms"       element={<PageWrapper><><Navbar/><Termos/></></PageWrapper>} />
        <Route path="/privacy"     element={<PageWrapper><><Navbar/><Privacidade/></></PageWrapper>} />
        <Route path="/limitacoes"  element={<PageWrapper><><Navbar/><LimitacoesIA/></></PageWrapper>} />

        <Route path="/app"         element={<PageWrapper><><Navbar/><Home/></></PageWrapper>} />
        <Route path="/report"      element={<PageWrapper><><Navbar/><ReportPage/></></PageWrapper>} />
        <Route path="/report/:id"  element={<PageWrapper><><Navbar/><ReportPage/></></PageWrapper>} />
        <Route path="/mission"     element={<PageWrapper><><Navbar/><Missao/></></PageWrapper>} />
        <Route path="/suggestions" element={<PageWrapper><><Navbar/><Sugestoes/></></PageWrapper>} />
        <Route path="/demo"        element={<PageWrapper><DemonstracaoPage /></PageWrapper>} />
        <Route path="/demonstracao" element={<PageWrapper><DemonstracaoPage /></PageWrapper>} />
        <Route path="/dashboard"   element={<PageWrapper><ProtectedRoute><><Navbar/><Dashboard/></></ProtectedRoute></PageWrapper>} />
        <Route path="/history"     element={<PageWrapper><ProtectedRoute><><Navbar/><Dashboard/></></ProtectedRoute></PageWrapper>} />
      </Routes>
    </AuthProvider>
  );
}
