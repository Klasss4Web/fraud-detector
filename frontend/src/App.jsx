import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import TransactionPage from "./pages/TransactionPage";
import InsurancePage from "./pages/InsurancePage";
import IdentityPage from "./pages/IdentityPage";
import EcommercePage from "./pages/EcommercePage";
import ObservabilityPage from "./pages/ObservabilityPage";
import StorePage from "./pages/StorePage";
import CheckoutPage from "./pages/CheckoutPage";
import SimulateAttackPage from "./pages/SimulateAttackPage";
import DetectionScorePage from "./pages/DetectionScorePage";
import MixedDetectionPage from "./pages/MixedDetectionPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import "./App.css";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Auth routes (no layout) */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Main app routes (with layout) */}
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/transaction" element={<Layout><TransactionPage /></Layout>} />
          <Route path="/insurance" element={<Layout><InsurancePage /></Layout>} />
          <Route path="/identity" element={<Layout><IdentityPage /></Layout>} />
          <Route path="/ecommerce" element={<Layout><EcommercePage /></Layout>} />
          <Route path="/observability" element={<Layout><ObservabilityPage /></Layout>} />
          <Route path="/store" element={<Layout><StorePage /></Layout>} />
          <Route path="/checkout" element={<Layout><CheckoutPage /></Layout>} />
          <Route path="/simulate-attack" element={<Layout><SimulateAttackPage /></Layout>} />
          <Route path="/detection-score" element={<Layout><DetectionScorePage /></Layout>} />
          <Route path="/mixed-detection" element={<Layout><MixedDetectionPage /></Layout>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
