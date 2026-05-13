import RiskBadge from "./RiskBadge";
import Card from "./Card";
import {
  AlertTriangle,
  CheckCircle,
  Shield,
  TrendingUp,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import "./AnalysisResult.css";
import MarkdownToText from "./markdown/MarkdownToText";
import { useEffect, useRef, useState } from "react";

const AnalysisResult = ({ result }) => {
  if (!result) return null;

  const {
    entity_id,
    entity_type,
    risk_score,
    risk_level,
    requires_action,
    recommendation,
    signals,
    agent_results,
    investigation_report,
  } = result;

  // Animated risk score
  const [displayedRiskScore, setDisplayedRiskScore] = useState(0);
  useEffect(() => {
    if (typeof risk_score === "number") {
      let raf;
      let start = displayedRiskScore;
      let end = Math.round(risk_score);
      if (start === end) return;
      let step = end > start ? 1 : -1;
      const animate = () => {
        setDisplayedRiskScore((prev) => {
          if (prev === end) return prev;
          const next = prev + step;
          if ((step > 0 && next > end) || (step < 0 && next < end)) return end;
          raf = requestAnimationFrame(animate);
          return next;
        });
      };
      raf = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(raf);
    } else {
      setDisplayedRiskScore(0);
    }
    // eslint-disable-next-line
  }, [risk_score]);

  // Animated progress bars for signals
  const [signalWidths, setSignalWidths] = useState([]);
  useEffect(() => {
    if (signals && signals.length > 0) {
      setSignalWidths(Array(signals.length).fill(0));
      const timeouts = signals.map((signal, i) =>
        setTimeout(
          () => {
            setSignalWidths((w) => {
              const copy = [...w];
              copy[i] = signal.weight * 100;
              return copy;
            });
          },
          100 + i * 120,
        ),
      );
      return () => timeouts.forEach(clearTimeout);
    }
  }, [signals]);

  // Animated progress bars for agent scores
  const [agentWidths, setAgentWidths] = useState({});
  useEffect(() => {
    if (agent_results && Object.keys(agent_results).length > 0) {
      setAgentWidths({});
      const entries = Object.entries(agent_results);
      const timeouts = entries.map(([agent, score], i) =>
        setTimeout(
          () => {
            setAgentWidths((w) => ({ ...w, [agent]: score }));
          },
          100 + i * 120,
        ),
      );
      return () => timeouts.forEach(clearTimeout);
    }
  }, [agent_results]);

  // Animated dropdown for investigation report
  const [reportOpen, setReportOpen] = useState(false);
  const reportRef = useRef(null);
  useEffect(() => {
    if (investigation_report) {
      setReportOpen(true);
    } else {
      setReportOpen(false);
    }
  }, [investigation_report]);

  console.log({ investigation_report });

  const getActionIcon = () => {
    if (risk_level === "critical" || risk_level === "high") {
      return (
        <AlertTriangle className="result-action-icon result-action-icon-warning" />
      );
    }
    return (
      <CheckCircle className="result-action-icon result-action-icon-success" />
    );
  };

  return (
    <div className="analysis-result">
      <div className="result-header">
        <div className="result-header-info">
          <h2 className="result-title">Analysis Result</h2>
          <p className="result-entity">
            {entity_type.toUpperCase()}: {entity_id}
          </p>
        </div>
        <RiskBadge level={risk_level} score={displayedRiskScore} />
      </div>

      <div className="result-grid">
        <Card className="result-score-card">
          <div className="result-score">
            <div className="result-score-circle" data-level={risk_level}>
              <span className="result-score-value">{displayedRiskScore}</span>
              <span className="result-score-label">Risk Score</span>
            </div>
          </div>
        </Card>

        <Card
          title="Recommendation"
          className={requires_action ? "card-warning" : "card-success"}
        >
          <div className="result-recommendation">
            {getActionIcon()}
            <div className="result-recommendation-content">
              <p className="result-recommendation-action">
                {requires_action ? "Action Required" : "No Action Required"}
              </p>
              <p className="result-recommendation-text">{recommendation}</p>
            </div>
          </div>
        </Card>
      </div>

      {signals && signals.length > 0 && (
        <Card title="Detected Signals" className="result-signals-card">
          <div className="result-signals">
            {signals.map((signal, index) => (
              <div key={index} className="result-signal">
                <div className="result-signal-header">
                  <Shield className="result-signal-icon" />
                  <span className="result-signal-name">{signal.name}</span>
                  <span className="result-signal-category">
                    {signal.category}
                  </span>
                </div>
                <p className="result-signal-description">
                  {signal.description}
                </p>
                <div className="result-signal-weight">
                  <div
                    className="result-signal-weight-bar"
                    style={{ width: `${signalWidths[index] || 0}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {agent_results && Object.keys(agent_results).length > 0 && (
        <Card title="Agent Scores" className="result-agents-card">
          <div className="result-agents">
            {Object.entries(agent_results).map(([agent, score]) => (
              <div key={agent} className="result-agent">
                <div className="result-agent-info">
                  <TrendingUp className="result-agent-icon" />
                  <span className="result-agent-name">{agent}</span>
                </div>
                <div className="result-agent-score">
                  <div className="result-agent-bar-bg">
                    <div
                      className="result-agent-bar"
                      style={{ width: `${agentWidths[agent] || 0}%` }}
                      data-score={
                        score >= 60 ? "high" : score >= 40 ? "medium" : "low"
                      }
                    ></div>
                  </div>
                  <span className="result-agent-value">{score.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Investigation Report" className="card-highlight">
        <div className="result-investigation-dropdown">
          {investigation_report && (
            <>
              <button
                className="result-investigation-toggle"
                onClick={(e) => {
                  e.preventDefault();
                  setReportOpen((v) => !v);
                }}
                aria-expanded={reportOpen}
                style={{
                  background: "none",
                  border: 0,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontWeight: 600,
                  color: "#1e293b",
                  marginBottom: 8,
                  fontSize: 16,
                }}
              >
                {reportOpen ? (
                  <ChevronUp size={18} />
                ) : (
                  <ChevronDown size={18} />
                )}
                {reportOpen ? "Hide" : "Show"} Report
              </button>
              <div
                className="result-investigation-animated"
                ref={reportRef}
                style={{
                  maxHeight:
                    reportOpen && reportRef.current
                      ? reportRef.current.scrollHeight
                      : 0,
                  opacity: reportOpen ? 1 : 0,
                  overflow: "hidden",
                  transition:
                    "max-height 0.5s cubic-bezier(0.4,0,0.2,1), opacity 0.4s",
                }}
              >
                <MarkdownToText
                  reportText={investigation_report?.llm_analysis}
                />
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default AnalysisResult;
