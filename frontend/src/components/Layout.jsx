import { NavLink, useNavigate } from "react-router-dom";
import {
  Shield,
  BarChart3,
  FileText,
  User,
  ShoppingCart,
  CreditCard,
  Menu,
  X,
  Target,
  Zap,
  FlaskConical,
  LogOut,
  LogIn,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import "./Layout.css";

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { to: "/", icon: BarChart3, label: "Dashboard" },
    { to: "/transaction", icon: CreditCard, label: "Transaction" },
    { to: "/insurance", icon: FileText, label: "Insurance" },
    { to: "/identity", icon: User, label: "Identity" },
    { to: "/ecommerce", icon: ShoppingCart, label: "E-Commerce" },
    { to: "/store", icon: ShoppingCart, label: "Storefront" },
    { to: "/simulate-attack", icon: Zap, label: "Simulate Attack" },
    { to: "/detection-score", icon: Target, label: "Detection Score" },
    { to: "/mixed-detection", icon: FlaskConical, label: "Mixed Analysis" },
    { to: "/observability", icon: BarChart3, label: "Observability" },
  ];

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="layout">
      <header className="header">
        <button
          className="menu-toggle"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
        <div className="header-brand">
          <Shield className="header-icon" />
          <h1>Fraud Detection System</h1>
        </div>
        <div className="header-actions">
          {isAuthenticated ? (
            <div className="user-menu">
              <span className="user-name">{user?.full_name || user?.email}</span>
              <button className="auth-btn logout-btn" onClick={handleLogout} title="Logout">
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <NavLink to="/login" className="auth-btn login-btn">
              <LogIn size={18} />
              <span>Sign In</span>
            </NavLink>
          )}
        </div>
      </header>

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <nav className="sidebar-nav">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
              onClick={() => setSidebarOpen(false)}
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
};

export default Layout;
