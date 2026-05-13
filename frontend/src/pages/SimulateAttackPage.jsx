import { useState, useEffect, useRef } from "react";
import { Zap, Shield, AlertTriangle, Target } from "lucide-react";
import { simulateFraudAttack } from "../services/api";
import AnalysisResult from "../components/AnalysisResult";
import SimulationProgress from "../components/SimulationProgress";
import Card from "../components/Card";
import "./SimulateAttackPage.css";

const ATTACK_TYPES = [
  { value: "velocity_attack", label: "Velocity Attack", description: "Rapid burst of transactions" },
  { value: "card_testing", label: "Card Testing", description: "Small amounts, many cards" },
  { value: "address_mismatch", label: "Address Mismatch", description: "Shipping/billing differ" },
  { value: "high_amount", label: "High Amount", description: "Unusually large transactions" },
  { value: "device_spoofing", label: "Device Spoofing", description: "Multiple devices, same user" },
  { value: "synthetic_identity", label: "Synthetic Identity", description: "Fabricated identity info" },
];

const SimulateAttackPage = () => {
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState("");
  const [attackType, setAttackType] = useState("");

  // Progress state - simple index based
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const progressInterval = useRef(null);

  const getStages = () => {
    const selectedType = attackType 
      ? ATTACK_TYPES.find(t => t.value === attackType)?.label 
      : "Random";
    
    return [
      {
        id: "init",
        title: "Initializing Attack Simulation",
        description: "Setting up the red team environment",
      },
      {
        id: "generating",
        title: "Generating Attack Payload",
        description: `Creating ${selectedType} fraud transactions using AI`,
        detail: "Calling LLM to generate realistic fraud patterns",
      },
      {
        id: "validating",
        title: "Validating Payload",
        description: "Ensuring generated transactions match expected schema",
      },
      {
        id: "analyzing",
        title: "Running Fraud Detection",
        description: "Analyzing each transaction through the detection pipeline",
        detail: "Evaluating risk scores and fraud signals",
      },
      {
        id: "complete",
        title: "Simulation Complete",
        description: "Attack simulation finished, generating report",
      },
    ];
  };

  const stages = getStages();

  const simulateProgress = () => {
    // Clear any existing interval
    if (progressInterval.current) {
      clearInterval(progressInterval.current);
    }

    setCurrentStageIndex(0);
    setIsComplete(false);

    progressInterval.current = setInterval(() => {
      setCurrentStageIndex(prev => {
        if (prev < stages.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 1500); // Move to next stage every 1.5 seconds
  };

  const handleSimulateAttack = async () => {
    setSimLoading(true);
    setSimError("");
    setSimResult(null);

    // Start progress simulation
    simulateProgress();

    try {
      const data = await simulateFraudAttack(attackType || null);
      
      // Complete all stages
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
      setCurrentStageIndex(stages.length - 1);
      setIsComplete(true);
      
      // Small delay to show completion
      setTimeout(() => {
        setSimResult(data);
        setSimLoading(false);
      }, 600);
    } catch (err) {
      console.error("Simulation failed:", err);
      setSimError("Simulation failed. Please ensure the backend is running.");
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
      setSimLoading(false);
    }
  };

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, []);

  // Calculate stats from results
  const getResultStats = () => {
    if (!simResult?.analysis_results) return null;
    
    const results = simResult.analysis_results;
    const total = results.length;
    const highRisk = results.filter(r => r.risk_level === "high" || r.risk_level === "critical").length;
    const avgScore = results.reduce((sum, r) => sum + (r.risk_score || 0), 0) / total;
    
    return { total, highRisk, avgScore, detectionRate: (highRisk / total) * 100 };
  };

  const stats = getResultStats();

  return (
    <div className="simulate-attack-page">
      {/* Header */}
      <div className="sim-header">
        <div className="sim-header-content">
          <h1>
            <Zap size={28} />
            Red Team: Attack Simulation
          </h1>
          <p>Generate synthetic fraud attacks to test your detection system</p>
        </div>
      </div>

      {/* Attack Type Selection */}
      {!simLoading && !simResult && (
        <section className="attack-selection">
          <Card>
            <h3>Select Attack Type</h3>
            <div className="attack-grid">
              <div
                className={`attack-option ${attackType === "" ? "selected" : ""}`}
                onClick={() => setAttackType("")}
              >
                <div className="attack-icon random">
                  <Target size={24} />
                </div>
                <div className="attack-info">
                  <h4>Random</h4>
                  <p>Let the system choose an attack type</p>
                </div>
              </div>
              {ATTACK_TYPES.map((type) => (
                <div
                  key={type.value}
                  className={`attack-option ${attackType === type.value ? "selected" : ""}`}
                  onClick={() => setAttackType(type.value)}
                >
                  <div className="attack-icon">
                    <AlertTriangle size={24} />
                  </div>
                  <div className="attack-info">
                    <h4>{type.label}</h4>
                    <p>{type.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="sim-actions">
              <button
                onClick={handleSimulateAttack}
                disabled={simLoading}
                className="simulate-btn"
              >
                <Zap size={18} />
                Launch Attack Simulation
              </button>
            </div>
          </Card>
        </section>
      )}

      {/* Progress Display */}
      {simLoading && (
        <SimulationProgress
          stages={stages}
          currentStageIndex={currentStageIndex}
          isComplete={isComplete}
        />
      )}

      {/* Error Display */}
      {simError && (
        <div className="sim-error">
          <AlertTriangle size={20} />
          {simError}
        </div>
      )}

      {/* Results */}
      {simResult && (
        <div className="sim-results">
          {/* Stats Overview */}
          {stats && (
            <div className="sim-stats">
              <div className="stat-card">
                <span className="stat-value">{stats.total}</span>
                <span className="stat-label">Transactions Generated</span>
              </div>
              <div className="stat-card">
                <span className="stat-value text-red">{stats.highRisk}</span>
                <span className="stat-label">Flagged as High Risk</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.avgScore.toFixed(1)}</span>
                <span className="stat-label">Average Risk Score</span>
              </div>
              <div className="stat-card">
                <span className={`stat-value ${stats.detectionRate >= 50 ? "text-green" : "text-red"}`}>
                  {stats.detectionRate.toFixed(0)}%
                </span>
                <span className="stat-label">Detection Rate</span>
              </div>
            </div>
          )}

          {/* Attack Info */}
          <Card className="attack-info-card">
            <div className="attack-header">
              <div className="attack-badge">
                <Zap size={16} />
                {simResult.attack_type?.replace(/_/g, " ").toUpperCase()}
              </div>
              <Shield size={20} className="text-blue" />
            </div>
            <p className="attack-description">{simResult.description}</p>
            
            <details className="payload-details">
              <summary>View Attack Payload ({simResult.attack_payload?.length || 0} transactions)</summary>
              <pre className="payload-code">
                {JSON.stringify(simResult.attack_payload, null, 2)}
              </pre>
            </details>
          </Card>

          {/* Analysis Results */}
          <div className="analysis-section">
            <h3>
              <Shield size={20} />
              Detection Analysis
            </h3>
            <div className="analysis-results">
              {simResult.analysis_results.map((res, idx) => (
                <AnalysisResult key={idx} result={res} />
              ))}
            </div>
          </div>

          {/* Run Again Button */}
          <div className="sim-actions" style={{ marginTop: "2rem" }}>
            <button
              onClick={() => setSimResult(null)}
              className="simulate-btn"
              style={{ background: "linear-gradient(135deg, #3b82f6, #2563eb)" }}
            >
              <Zap size={18} />
              Run Another Simulation
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SimulateAttackPage;
