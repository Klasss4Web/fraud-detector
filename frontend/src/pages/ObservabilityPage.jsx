import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Users,
  Shield,
  Clock,
  BarChart3,
  RefreshCw,
  Zap,
  Target,
  AlertOctagon,
  ThumbsUp,
  PieChart,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  Cpu,
  DollarSign,
  Hash,
  Timer,
} from "lucide-react";
import Card from "../components/Card";
import {
  getMetrics,
  getFraudMetrics,
  getEvaluationSummary,
  getConfusionMatrix,
  getAgentPerformance,
  getImprovementSuggestions,
  getLLMUsage,
  getLLMUsageByOperation,
} from "../services/api";
import "./ObservabilityPage.css";

const MetricCard = ({ title, value, subtitle, icon: Icon, color = "blue", trend = null, trendLabel = "" }) => (
  <div className={`obs-metric-card obs-metric-${color}`}>
    <div className="obs-metric-header">
      <div className={`obs-metric-icon obs-icon-${color}`}>
        <Icon size={20} />
      </div>
      {trend !== null && (
        <div className={`obs-metric-trend ${trend >= 0 ? "positive" : "negative"}`}>
          {trend >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          <span>{Math.abs(trend)}%</span>
        </div>
      )}
    </div>
    <div className="obs-metric-body">
      <span className="obs-metric-value">{typeof value === 'number' ? value.toLocaleString() : value}</span>
      <span className="obs-metric-title">{title}</span>
      {subtitle && <span className="obs-metric-subtitle">{subtitle}</span>}
    </div>
  </div>
);

const StatCard = ({ label, value, color = "default", icon: Icon }) => (
  <div className={`stat-card stat-${color}`}>
    {Icon && <Icon size={16} className="stat-icon" />}
    <div className="stat-content">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  </div>
);

const ConfusionMatrixDisplay = ({ matrix }) => {
  if (!matrix) return null;

  const total = (matrix.true_positives || 0) + (matrix.true_negatives || 0) + 
                (matrix.false_positives || 0) + (matrix.false_negatives || 0);

  return (
    <div className="confusion-matrix-container">
      <div className="matrix-visual">
        <div className="matrix-labels-top">
          <div className="matrix-corner"></div>
          <div className="matrix-label-header">
            <span>Predicted</span>
          </div>
        </div>
        <div className="matrix-labels-col">
          <span className="label-fraud">Fraud</span>
          <span className="label-legit">Legit</span>
        </div>
        <div className="matrix-grid-new">
          <div className="matrix-cell-new tp">
            <div className="cell-inner">
              <span className="cell-count">{matrix.true_positives || 0}</span>
              <span className="cell-name">True Positive</span>
              <span className="cell-desc">Correctly caught</span>
            </div>
          </div>
          <div className="matrix-cell-new fn">
            <div className="cell-inner">
              <span className="cell-count">{matrix.false_negatives || 0}</span>
              <span className="cell-name">False Negative</span>
              <span className="cell-desc">Missed fraud</span>
            </div>
          </div>
          <div className="matrix-cell-new fp">
            <div className="cell-inner">
              <span className="cell-count">{matrix.false_positives || 0}</span>
              <span className="cell-name">False Positive</span>
              <span className="cell-desc">Wrong block</span>
            </div>
          </div>
          <div className="matrix-cell-new tn">
            <div className="cell-inner">
              <span className="cell-count">{matrix.true_negatives || 0}</span>
              <span className="cell-name">True Negative</span>
              <span className="cell-desc">Correctly allowed</span>
            </div>
          </div>
        </div>
        <div className="matrix-labels-row">
          <span className="label-fraud">Fraud</span>
          <span className="label-legit">Legit</span>
        </div>
        <div className="matrix-label-side">
          <span>Actual</span>
        </div>
      </div>

      <div className="matrix-stats">
        <div className="matrix-stat-card">
          <div className="stat-ring green">
            <svg viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#10b981"
                strokeWidth="3"
                strokeDasharray={`${(matrix.precision || 0) * 100}, 100`}
              />
            </svg>
            <span className="ring-value">{((matrix.precision || 0) * 100).toFixed(0)}%</span>
          </div>
          <span className="stat-name">Precision</span>
        </div>
        <div className="matrix-stat-card">
          <div className="stat-ring blue">
            <svg viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="3"
                strokeDasharray={`${(matrix.recall || 0) * 100}, 100`}
              />
            </svg>
            <span className="ring-value">{((matrix.recall || 0) * 100).toFixed(0)}%</span>
          </div>
          <span className="stat-name">Recall</span>
        </div>
        <div className="matrix-stat-card">
          <div className="stat-ring purple">
            <svg viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#8b5cf6"
                strokeWidth="3"
                strokeDasharray={`${(matrix.f1_score || 0) * 100}, 100`}
              />
            </svg>
            <span className="ring-value">{((matrix.f1_score || 0) * 100).toFixed(0)}%</span>
          </div>
          <span className="stat-name">F1 Score</span>
        </div>
        <div className="matrix-stat-card">
          <div className="stat-ring orange">
            <svg viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#f97316"
                strokeWidth="3"
                strokeDasharray={`${(matrix.accuracy || 0) * 100}, 100`}
              />
            </svg>
            <span className="ring-value">{((matrix.accuracy || 0) * 100).toFixed(0)}%</span>
          </div>
          <span className="stat-name">Accuracy</span>
        </div>
      </div>
      
      {total === 0 && (
        <div className="matrix-empty-notice">
          <Info size={16} />
          <span>No evaluation data yet. Analyze transactions and record outcomes to see metrics.</span>
        </div>
      )}
    </div>
  );
};

const AgentPerformanceCard = ({ name, metrics }) => {
  // Handle both old format (accuracy, total_decisions) and new format (success_rate, total_executions)
  const accuracy = metrics?.accuracy || metrics?.success_rate || 0;
  const totalExecutions = metrics?.total_decisions || metrics?.total_executions || 0;
  const avgTime = metrics?.avg_execution_time_ms || 0;
  const confidence = metrics?.avg_confidence || accuracy;
  
  const accuracyColor = accuracy >= 0.8 ? "green" : accuracy >= 0.6 ? "yellow" : "red";
  const displayName = name.replace(/Agent$/, "").replace(/([A-Z])/g, " $1").trim();

  return (
    <div className="agent-card-new">
      <div className="agent-header-new">
        <div className={`agent-icon agent-icon-${accuracyColor}`}>
          <Shield size={18} />
        </div>
        <div className="agent-info">
          <h4>{displayName}</h4>
          <span className="agent-type">Detection Agent</span>
        </div>
        <div className={`agent-badge badge-${accuracyColor}`}>
          {(accuracy * 100).toFixed(0)}%
        </div>
      </div>
      
      <div className="agent-metrics">
        <div className="agent-metric">
          <span className="metric-num">{totalExecutions}</span>
          <span className="metric-label">Executions</span>
        </div>
        <div className="agent-metric">
          <span className="metric-num">{(confidence * 100).toFixed(0)}%</span>
          <span className="metric-label">Success Rate</span>
        </div>
        <div className="agent-metric">
          <span className="metric-num">{avgTime > 0 ? avgTime.toFixed(0) : "< 1"}ms</span>
          <span className="metric-label">Avg Time</span>
        </div>
      </div>

      <div className="agent-progress">
        <div className="progress-bar">
          <div 
            className={`progress-fill progress-${accuracyColor}`}
            style={{ width: `${accuracy * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

const SuggestionCard = ({ suggestion, index }) => {
  const typeColors = {
    threshold_adjustment: { bg: "#dbeafe", color: "#2563eb", label: "Threshold" },
    sensitivity_adjustment: { bg: "#fef3c7", color: "#d97706", label: "Sensitivity" },
    confidence_calibration: { bg: "#f3e8ff", color: "#7c3aed", label: "Calibration" },
    rule_update: { bg: "#ecfdf5", color: "#059669", label: "Rules" },
  };

  const typeStyle = typeColors[suggestion.type] || typeColors.rule_update;

  return (
    <div className="suggestion-card-new">
      <div className="suggestion-number">{index + 1}</div>
      <div className="suggestion-content">
        <div className="suggestion-header-new">
          <span 
            className="suggestion-badge"
            style={{ background: typeStyle.bg, color: typeStyle.color }}
          >
            {typeStyle.label}
          </span>
          <h4>{suggestion.issue}</h4>
        </div>
        <p className="suggestion-details-new">{suggestion.details}</p>
        <div className="suggestion-action-new">
          <ThumbsUp size={14} />
          <span>{suggestion.suggestion}</span>
        </div>
      </div>
    </div>
  );
};

// LLM Usage Components
const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num?.toLocaleString() || '0';
};

const formatCost = (cost) => {
  if (cost === undefined || cost === null) return '$0.0000';
  return '$' + cost.toFixed(4);
};

const LLMUsageCard = ({ llmUsage }) => {
  if (!llmUsage) return null;

  return (
    <div className="llm-usage-summary">
      <div className="llm-stats-row">
        <div className="llm-stat-item">
          <div className="llm-stat-icon blue">
            <Hash size={18} />
          </div>
          <div className="llm-stat-content">
            <span className="llm-stat-value">{formatNumber(llmUsage.total_calls)}</span>
            <span className="llm-stat-label">Total Calls</span>
          </div>
        </div>
        <div className="llm-stat-item">
          <div className="llm-stat-icon purple">
            <Cpu size={18} />
          </div>
          <div className="llm-stat-content">
            <span className="llm-stat-value">{formatNumber(llmUsage.tokens?.total || 0)}</span>
            <span className="llm-stat-label">Total Tokens</span>
          </div>
        </div>
        <div className="llm-stat-item">
          <div className="llm-stat-icon green">
            <DollarSign size={18} />
          </div>
          <div className="llm-stat-content">
            <span className="llm-stat-value">{formatCost(llmUsage.cost?.total_usd)}</span>
            <span className="llm-stat-label">Total Cost</span>
          </div>
        </div>
        <div className="llm-stat-item">
          <div className="llm-stat-icon orange">
            <Timer size={18} />
          </div>
          <div className="llm-stat-content">
            <span className="llm-stat-value">{Math.round(llmUsage.latency?.avg_ms || 0)}ms</span>
            <span className="llm-stat-label">Avg Latency</span>
          </div>
        </div>
      </div>

      <div className="llm-token-breakdown">
        <div className="token-breakdown-header">
          <span>Token Breakdown</span>
          <span className="success-rate">
            {((llmUsage.success_rate || 0) * 100).toFixed(1)}% success rate
          </span>
        </div>
        <div className="token-bar-container">
          <div className="token-bar-visual">
            <div 
              className="token-bar-input" 
              style={{ 
                width: `${(llmUsage.tokens?.input || 0) / (llmUsage.tokens?.total || 1) * 100}%` 
              }}
            />
            <div 
              className="token-bar-output" 
              style={{ 
                width: `${(llmUsage.tokens?.output || 0) / (llmUsage.tokens?.total || 1) * 100}%` 
              }}
            />
          </div>
          <div className="token-bar-labels">
            <span className="input-label">
              <span className="dot input"></span>
              Input: {formatNumber(llmUsage.tokens?.input || 0)}
            </span>
            <span className="output-label">
              <span className="dot output"></span>
              Output: {formatNumber(llmUsage.tokens?.output || 0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

const LLMOperationsTable = ({ operations }) => {
  if (!operations || operations.length === 0) {
    return (
      <div className="llm-empty">
        <Info size={18} />
        <span>No LLM operations recorded yet</span>
      </div>
    );
  }

  const maxTokens = Math.max(...operations.map(op => op.total_tokens || 0));

  return (
    <div className="llm-operations-table">
      <table>
        <thead>
          <tr>
            <th>Operation</th>
            <th>Calls</th>
            <th>Input Tokens</th>
            <th>Output Tokens</th>
            <th>Total Tokens</th>
            <th>Cost</th>
            <th>Avg Latency</th>
          </tr>
        </thead>
        <tbody>
          {operations.map((op, idx) => (
            <tr key={idx}>
              <td className="op-name">{op.operation}</td>
              <td>{formatNumber(op.total_calls)}</td>
              <td>
                <div className="token-cell">
                  {formatNumber(op.total_input_tokens)}
                  <div className="mini-bar">
                    <div 
                      className="mini-bar-fill input" 
                      style={{ width: `${(op.total_input_tokens || 0) / maxTokens * 100}%` }}
                    />
                  </div>
                </div>
              </td>
              <td>
                <div className="token-cell">
                  {formatNumber(op.total_output_tokens)}
                  <div className="mini-bar">
                    <div 
                      className="mini-bar-fill output" 
                      style={{ width: `${(op.total_output_tokens || 0) / maxTokens * 100}%` }}
                    />
                  </div>
                </div>
              </td>
              <td className="total-tokens">{formatNumber(op.total_tokens)}</td>
              <td className="cost">{formatCost(op.total_cost)}</td>
              <td>
                <span className={`latency-badge ${op.avg_latency_ms < 500 ? 'fast' : op.avg_latency_ms < 2000 ? 'medium' : 'slow'}`}>
                  {Math.round(op.avg_latency_ms || 0)}ms
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ObservabilityPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const [metrics, setMetrics] = useState(null);
  const [fraudMetrics, setFraudMetrics] = useState(null);
  const [evaluationSummary, setEvaluationSummary] = useState(null);
  const [confusionMatrix, setConfusionMatrix] = useState(null);
  const [agentPerformance, setAgentPerformance] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [llmUsage, setLLMUsage] = useState(null);
  const [llmOperations, setLLMOperations] = useState([]);

  const fetchAllData = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const results = await Promise.allSettled([
        getMetrics(),
        getFraudMetrics(),
        getEvaluationSummary(),
        getConfusionMatrix(),
        getAgentPerformance(),
        getImprovementSuggestions(),
        getLLMUsage(24),
        getLLMUsageByOperation(24),
      ]);

      if (results[0].status === "fulfilled") setMetrics(results[0].value);
      if (results[1].status === "fulfilled") setFraudMetrics(results[1].value);
      if (results[2].status === "fulfilled") setEvaluationSummary(results[2].value);
      if (results[3].status === "fulfilled") setConfusionMatrix(results[3].value);
      if (results[4].status === "fulfilled") {
        console.log("Agent performance data:", results[4].value);
        setAgentPerformance(results[4].value);
      }
      if (results[5].status === "fulfilled") setSuggestions(results[5].value?.suggestions || []);
      if (results[6].status === "fulfilled") setLLMUsage(results[6].value);
      if (results[7].status === "fulfilled") setLLMOperations(results[7].value || []);

      setLastUpdated(new Date());

      const allFailed = results.every((r) => r.status === "rejected");
      if (allFailed) {
        setError("Failed to connect to the backend. Make sure the API server is running.");
      }
    } catch (err) {
      setError("Failed to fetch observability data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => fetchAllData(true), 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchAllData(true);
  };

  if (loading) {
    return (
      <div className="obs-page">
        <div className="obs-loading">
          <div className="loading-spinner">
            <RefreshCw size={32} />
          </div>
          <p>Loading observability data...</p>
        </div>
      </div>
    );
  }

  const totalAlerts = (fraudMetrics?.alerts?.received || 0);
  const totalDecisions = (fraudMetrics?.decisions?.total || 0);

  return (
    <div className="obs-page">
      {/* Header */}
      <div className="obs-header-new">
        <div className="obs-header-left">
          <div className="obs-title">
            <Activity size={28} className="obs-title-icon" />
            <div>
              <h1>Observability Dashboard</h1>
              <p>Real-time monitoring and performance analytics</p>
            </div>
          </div>
        </div>
        <div className="obs-header-right">
          {lastUpdated && (
            <span className="last-updated">
              <Clock size={14} />
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            className={`refresh-btn-new ${refreshing ? "refreshing" : ""}`}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={18} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="obs-error-new">
          <AlertOctagon size={20} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Quick Stats */}
      <section className="obs-section">
        <div className="section-header">
          <Zap size={20} />
          <h2>System Overview</h2>
        </div>
        <div className="obs-metrics-grid-new">
          <MetricCard
            title="Alerts Received"
            value={fraudMetrics?.alerts?.received || 0}
            icon={AlertTriangle}
            color="yellow"
          />
          <MetricCard
            title="Alerts Processed"
            value={fraudMetrics?.alerts?.processed || 0}
            icon={CheckCircle}
            color="green"
          />
          <MetricCard
            title="Total Decisions"
            value={fraudMetrics?.decisions?.total || 0}
            icon={Target}
            color="blue"
          />
          <MetricCard
            title="Actions Executed"
            value={fraudMetrics?.actions?.executed || 0}
            icon={Zap}
            color="purple"
          />
          <MetricCard
            title="Pending Escalations"
            value={fraudMetrics?.escalations?.pending || 0}
            subtitle={`${fraudMetrics?.escalations?.total || 0} total`}
            icon={Users}
            color="orange"
          />
          <MetricCard
            title="Rate Limited"
            value={fraudMetrics?.actions?.rate_limited || 0}
            icon={Clock}
            color="red"
          />
        </div>
      </section>

      {/* Two Column Layout */}
      <div className="obs-two-col">
        {/* Confusion Matrix */}
        <section className="obs-section">
          <div className="section-header">
            <PieChart size={20} />
            <h2>Model Performance</h2>
          </div>
          <Card className="matrix-card">
            <ConfusionMatrixDisplay matrix={confusionMatrix} />
          </Card>
        </section>

        {/* Evaluation Summary */}
        <section className="obs-section">
          <div className="section-header">
            <BarChart3 size={20} />
            <h2>Evaluation Summary</h2>
          </div>
          <Card className="eval-card-new">
            <div className="eval-stats-grid">
              <StatCard
                label="Total Evaluated"
                value={evaluationSummary?.total_evaluated || 0}
                color="blue"
                icon={Layers}
              />
              <StatCard
                label="Negative Exemplars"
                value={evaluationSummary?.negative_exemplar_count || 0}
                color="red"
                icon={XCircle}
              />
            </div>
            
            {evaluationSummary?.overall_metrics && (
              <div className="eval-metrics-row">
                <div className="eval-metric">
                  <span className="eval-metric-value green">
                    {((evaluationSummary.overall_metrics.metrics?.precision || 0) * 100).toFixed(1)}%
                  </span>
                  <span className="eval-metric-label">Precision</span>
                </div>
                <div className="eval-metric">
                  <span className="eval-metric-value blue">
                    {((evaluationSummary.overall_metrics.metrics?.recall || 0) * 100).toFixed(1)}%
                  </span>
                  <span className="eval-metric-label">Recall</span>
                </div>
                <div className="eval-metric">
                  <span className="eval-metric-value purple">
                    {((evaluationSummary.overall_metrics.metrics?.f1_score || 0) * 100).toFixed(1)}%
                  </span>
                  <span className="eval-metric-label">F1 Score</span>
                </div>
              </div>
            )}

            {(!evaluationSummary || evaluationSummary.total_evaluated === 0) && (
              <div className="eval-empty">
                <Info size={18} />
                <p>No evaluations yet. Record outcomes via webhooks or manual feedback to see metrics.</p>
              </div>
            )}
          </Card>
        </section>
      </div>

      {/* Agent Performance */}
      <section className="obs-section">
        <div className="section-header">
          <Shield size={20} />
          <h2>Agent Performance</h2>
        </div>
        {agentPerformance && Object.keys(agentPerformance).length > 0 ? (
          <div className="agents-grid-new">
            {Object.entries(agentPerformance).map(([name, metrics]) => (
              <AgentPerformanceCard key={name} name={name} metrics={metrics} />
            ))}
          </div>
        ) : (
          <Card className="empty-card">
            <Shield size={32} strokeWidth={1.5} />
            <h3>No Agent Data</h3>
            <p>Analyze some transactions to see agent performance metrics.</p>
          </Card>
        )}
      </section>

      {/* LLM Token Usage */}
      <section className="obs-section">
        <div className="section-header">
          <Cpu size={20} />
          <h2>LLM Token Usage</h2>
          <span className="section-badge">Last 24 hours</span>
        </div>
        {llmUsage && llmUsage.total_calls > 0 ? (
          <>
            <Card className="llm-card">
              <LLMUsageCard llmUsage={llmUsage} />
            </Card>
            
            {llmOperations && llmOperations.length > 0 && (
              <Card className="llm-operations-card">
                <div className="card-header-inner">
                  <h3>Token Usage by Operation</h3>
                  <span className="ops-count">{llmOperations.length} operations</span>
                </div>
                <LLMOperationsTable operations={llmOperations} />
              </Card>
            )}
          </>
        ) : (
          <Card className="empty-card">
            <Cpu size={32} strokeWidth={1.5} />
            <h3>No LLM Usage Data</h3>
            <p>LLM token usage will appear here once the system makes API calls to language models.</p>
          </Card>
        )}
      </section>

      {/* Improvement Suggestions */}
      {suggestions.length > 0 && (
        <section className="obs-section">
          <div className="section-header">
            <TrendingUp size={20} />
            <h2>Improvement Suggestions</h2>
            <span className="suggestion-count">{suggestions.length}</span>
          </div>
          <div className="suggestions-grid">
            {suggestions.map((suggestion, idx) => (
              <SuggestionCard key={idx} suggestion={suggestion} index={idx} />
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {!fraudMetrics && !evaluationSummary && !confusionMatrix && !agentPerformance && !error && (
        <div className="obs-empty-new">
          <div className="empty-icon">
            <BarChart3 size={48} strokeWidth={1.5} />
          </div>
          <h3>No Data Available</h3>
          <p>Start analyzing transactions to see metrics and performance data.</p>
          <button className="empty-action" onClick={handleRefresh}>
            <RefreshCw size={16} />
            Refresh Data
          </button>
        </div>
      )}
    </div>
  );
};

export default ObservabilityPage;
