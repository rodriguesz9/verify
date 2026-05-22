import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

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

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public pages */}
        <Route path="/"         element={<LandingPage />} />
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected pages */}
        <Route path="/app"       element={<ProtectedRoute><><Navbar/><Home/></></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><><Navbar/><Dashboard/></></ProtectedRoute>} />
        <Route path="/history"   element={<ProtectedRoute><><Navbar/><HistoryPage/></></ProtectedRoute>} />
        <Route path="/report"    element={<ProtectedRoute><><Navbar/><ReportPage/></></ProtectedRoute>} />
        <Route path="/report/:id" element={<ProtectedRoute><><Navbar/><ReportPage/></></ProtectedRoute>} />
        <Route path="/plans"     element={<ProtectedRoute><><Navbar/><PricingPage/></></ProtectedRoute>} />
        <Route path="/mission"   element={<ProtectedRoute><><Navbar/><Missao/></></ProtectedRoute>} />
        <Route path="/suggestions" element={<ProtectedRoute><><Navbar/><Sugestoes/></></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  );
}
