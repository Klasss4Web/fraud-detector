import { useState } from "react";
import Card from "./Card";
import "./DetectionScoreDashboard.css";

const ATTACK_TYPE_LABELS = {
  velocity_attack: "Velocity Attack",
  card_testing: "Card Testing",
  address_mismatch: "Address Mismatch",
  high_amount: "High Amount",
  device_spoofing: "Device Spoofing",
  synthetic_identity: "Synthetic Identity",
};

const MetricCard = ({ title, value, subtitle, color = "default" }) => (
  <div className={`metric-card metric-card-${color}`}>
    <div className="metric-card-value">{value}</div>
    <div className="metric-card-title">{title}</div>
    {subtitle && <div className="metric-card-subtitle">{subtitle}</div>}
  </div>
);

const ProgressBar = ({ value, max = 100, color = "blue" }) => (
  <div className="progress-bar-container">
    <div
      className={`progress-bar progress-bar-${color}`}
      style={{ width: `${Math.min((value / max) * 100, 100)}%` }}
    />
  </div>
);

const AttackTypeRow = ({ attackType, metrics, isExpanded, onToggle }) => {
  const label = ATTACK_TYPE_LABELS[attackType] || attackType;
  const detectionColor =
    metrics.detection_rate >= 80
      ? "green"
      : metrics.detection_rate >= 50
        ? "yellow"
        : "red";

  return (
    <div className="attack-type-row">
      <div className="attack-type-header" onClick={onToggle}>
        <div className="attack-type-name">
          <span className="expand-icon">{isExpanded ? "−" : "+"}</span>
          {label}
        </div>
        <div className="attack-type-metrics">
          <div className="metric-inline">
            <span className="metric-label">Detection:</span>
            <span className={`metric-value text-${detectionColor}`}>
              {metrics.detection_rate.toFixed(1)}%
            </span>
          </div>
          <div className="metric-inline">
            <span className="metric-label">False Negative:</span>
            <span className="metric-value text-red">
              {metrics.false_negative_rate.toFixed(1)}%
            </span>
          </div>
          <div className="metric-inline">
            <span className="metric-label">Avg Score:</span>
            <span className="metric-value">{metrics.average_confidence_score.toFixed(1)}</span>
          </div>
        </div>
        <ProgressBar value={metrics.detection_rate} color={detectionColor} />
      </div>

      {isExpanded && (
        <div className="attack-type-details">
          <div className="detail-stats">
            <div className="detail-stat">
              <span className="stat-label">Total Transactions:</span>
              <span className="stat-value">{metrics.total_transactions}</span>
            </div>
            <div className="detail-stat">
              <span className="stat-label">Attacks Caught:</span>
              <span className="stat-value text-green">{metrics.caught_count}</span>
            </div>
            <div className="detail-stat">
              <span className="stat-label">Attacks Missed:</span>
              <span className="stat-value text-red">{metrics.missed_count}</span>
            </div>
          </div>

          {metrics.simulations && metrics.simulations.length > 0 && (
            <div className="simulations-list">
              <h5>Simulation Details</h5>
              {metrics.simulations.map((sim, idx) => (
                <div key={idx} className="simulation-item">
                  <div className="simulation-header">
                    <span className="simulation-number">Simulation #{sim.simulation_number}</span>
                    <span className="simulation-description">{sim.description}</span>
                  </div>
                  <div className="transaction-list">
                    {sim.transactions.map((tx, txIdx) => (
                      <div
                        key={txIdx}
                        className={`transaction-item ${tx.was_caught ? "caught" : "missed"}`}
                      >
                        <span className="tx-id">{tx.transaction_id}</span>
                        <span className="tx-score">Score: {tx.risk_score.toFixed(1)}</span>
                        <span className="tx-level">{tx.risk_level}</span>
                        <span className={`tx-status ${tx.was_caught ? "caught" : "missed"}`}>
                          {tx.was_caught ? "CAUGHT" : "MISSED"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const DetectionScoreDashboard = ({ data }) => {
  const [expandedTypes, setExpandedTypes] = useState({});

  if (!data) {
    return null;
  }

  const { metrics_by_attack_type, overall_metrics } = data;

  const toggleExpanded = (attackType) => {
    setExpandedTypes((prev) => ({
      ...prev,
      [attackType]: !prev[attackType],
    }));
  };

  const overallDetectionColor =
    overall_metrics.overall_detection_rate >= 80
      ? "green"
      : overall_metrics.overall_detection_rate >= 50
        ? "yellow"
        : "red";

  return (
    <div className="detection-score-dashboard">
      {/* Overall Metrics Section */}
      <section className="overall-metrics-section">
        <h2>Overall Detection Performance</h2>
        <div className="metrics-grid">
          <MetricCard
            title="Overall Detection Rate"
            value={`${overall_metrics.overall_detection_rate.toFixed(1)}%`}
            subtitle="Attacks successfully caught"
            color={overallDetectionColor}
          />
          <MetricCard
            title="False Negative Rate"
            value={`${overall_metrics.overall_false_negative_rate.toFixed(1)}%`}
            subtitle="Attacks that slipped through"
            color="red"
          />
          <MetricCard
            title="Avg Confidence Score"
            value={overall_metrics.overall_average_confidence.toFixed(1)}
            subtitle="Average risk score assigned"
            color="blue"
          />
          <MetricCard
            title="Detection Threshold"
            value={overall_metrics.detection_threshold_used.toFixed(0)}
            subtitle="Score needed to flag attack"
            color="default"
          />
        </div>

        <div className="summary-stats">
          <Card>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">Attack Types Tested</span>
                <span className="summary-value">{overall_metrics.total_attack_types_tested}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Total Simulations</span>
                <span className="summary-value">{overall_metrics.total_simulations_run}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Transactions Analyzed</span>
                <span className="summary-value">{overall_metrics.total_transactions_analyzed}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Attacks Caught</span>
                <span className="summary-value text-green">
                  {overall_metrics.total_attacks_caught}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Attacks Missed</span>
                <span className="summary-value text-red">
                  {overall_metrics.total_attacks_missed}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Per Attack Type Section */}
      <section className="attack-type-section">
        <h2>Detection by Attack Type</h2>
        <Card>
          <div className="attack-type-list">
            {Object.entries(metrics_by_attack_type).map(([attackType, metrics]) => (
              <AttackTypeRow
                key={attackType}
                attackType={attackType}
                metrics={metrics}
                isExpanded={expandedTypes[attackType]}
                onToggle={() => toggleExpanded(attackType)}
              />
            ))}
          </div>
        </Card>
      </section>

      {/* Detection Rate Chart (Visual Bar Chart) */}
      <section className="chart-section">
        <h2>Detection Rate Comparison</h2>
        <Card>
          <div className="bar-chart">
            {Object.entries(metrics_by_attack_type).map(([attackType, metrics]) => {
              const label = ATTACK_TYPE_LABELS[attackType] || attackType;
              const detectionColor =
                metrics.detection_rate >= 80
                  ? "green"
                  : metrics.detection_rate >= 50
                    ? "yellow"
                    : "red";
              return (
                <div key={attackType} className="bar-chart-row">
                  <div className="bar-label">{label}</div>
                  <div className="bar-container">
                    <div
                      className={`bar bar-${detectionColor}`}
                      style={{ width: `${metrics.detection_rate}%` }}
                    >
                      <span className="bar-value">{metrics.detection_rate.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </section>
    </div>
  );
};

export default DetectionScoreDashboard;
