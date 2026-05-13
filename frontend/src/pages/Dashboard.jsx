import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Shield,
  CreditCard,
  FileText,
  User,
  ShoppingCart,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
} from "lucide-react";
import Card from "../components/Card";
import { checkHealth } from "../services/api";
import "./Dashboard.css";

const Dashboard = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
      } catch (err) {
        console.error("Failed to fetch health:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHealth();
  }, []);

  const analysisTypes = [
    {
      to: "/transaction",
      icon: CreditCard,
      title: "Transaction Analysis",
      description:
        "Detect fraud in financial transactions including velocity attacks, amount anomalies, and geographic risks.",
      color: "blue",
    },
    {
      to: "/insurance",
      icon: FileText,
      title: "Insurance Claims",
      description:
        "Identify fraudulent insurance claims including staged incidents, exaggerated claims, and serial claimants.",
      color: "purple",
    },
    {
      to: "/identity",
      icon: User,
      title: "Identity Verification",
      description:
        "Detect identity fraud including synthetic identity, account takeover, and new account fraud.",
      color: "green",
    },
    {
      to: "/ecommerce",
      icon: ShoppingCart,
      title: "E-Commerce Orders",
      description:
        "Analyze e-commerce orders for reseller fraud, stolen cards, friendly fraud, and address mismatches.",
      color: "orange",
    },
  ];

  const riskLevels = [
    {
      level: "Critical",
      range: "80-100",
      action: "Block/Deny immediately",
      color: "critical",
    },
    {
      level: "High",
      range: "60-79",
      action: "Require verification",
      color: "high",
    },
    {
      level: "Medium",
      range: "40-59",
      action: "Enhanced monitoring",
      color: "medium",
    },
    {
      level: "Low",
      range: "0-39",
      action: "Standard processing",
      color: "low",
    },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-header-content">
          <h1 className="dashboard-title">Fraud Detection Dashboard</h1>
          <p className="dashboard-subtitle">
            Multi-agent AI system for comprehensive fraud detection
          </p>
        </div>
        <div className="dashboard-status">
          {loading ? (
            <span className="status-loading">Checking status...</span>
          ) : health ? (
            <span className="status-online">
              <CheckCircle size={16} /> System Online
            </span>
          ) : (
            <span className="status-offline">
              <AlertTriangle size={16} /> System Offline
            </span>
          )}
        </div>
      </div>

      <section className="dashboard-section">
        <h2 className="section-title">Analysis Types</h2>
        <div className="analysis-grid">
          {analysisTypes.map(
            ({ to, icon: Icon, title, description, color }) => (
              <Link
                key={to}
                to={to}
                className={`analysis-card analysis-card-${color}`}
              >
                <div className="analysis-card-icon">
                  <Icon size={32} />
                </div>
                <h3 className="analysis-card-title">{title}</h3>
                <p className="analysis-card-description">{description}</p>
                <span className="analysis-card-link">
                  Start Analysis <TrendingUp size={16} />
                </span>
              </Link>
            ),
          )}
        </div>
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Risk Level Guide</h2>
        <Card>
          <div className="risk-guide">
            {riskLevels.map(({ level, range, action, color }) => (
              <div
                key={level}
                className={`risk-guide-item risk-guide-${color}`}
              >
                <div className="risk-guide-level">
                  <span className="risk-guide-name">{level}</span>
                  <span className="risk-guide-range">{range}</span>
                </div>
                <p className="risk-guide-action">{action}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Red Team Tools</h2>
        <div className="red-team-grid">
          <Link to="/simulate-attack" className="red-team-card">
            <h3>Simulate Attack</h3>
            <p>Generate synthetic fraud attacks to test system responses in real-time.</p>
          </Link>
          <Link to="/detection-score" className="red-team-card red-team-card-highlight">
            <h3>Detection Score Dashboard</h3>
            <p>Measure detection effectiveness across attack types with detailed metrics.</p>
          </Link>
        </div>
      </section>

      {health && (
        <section className="dashboard-section">
          <h2 className="section-title">System Information</h2>
          <Card>
            <div className="system-info">
              <div className="system-info-item">
                <span className="system-info-label">Version</span>
                <span className="system-info-value">{health.version}</span>
              </div>
              <div className="system-info-item">
                <span className="system-info-label">Status</span>
                <span className="system-info-value system-info-status">
                  {health.status}
                </span>
              </div>
              <div className="system-info-item">
                <span className="system-info-label">Active Agents</span>
                <span className="system-info-value">
                  {health.agents_loaded?.length || 0}
                </span>
              </div>
            </div>
            <div className="agents-list">
              <h4 className="agents-list-title">Loaded Agents:</h4>
              <div className="agents-tags">
                {health.agents_loaded?.map((agent) => (
                  <span key={agent} className="agent-tag">
                    <Shield size={12} /> {agent}
                  </span>
                ))}
              </div>
            </div>
          </Card>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
