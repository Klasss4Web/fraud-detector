import { useState, useEffect, useRef } from "react";
import { runDetectionScoreAnalysis } from "../services/api";
import DetectionScoreDashboard from "../components/DetectionScoreDashboard";
import SimulationProgress from "../components/SimulationProgress";
import Card from "../components/Card";
import "./DetectionScorePage.css";

const ATTACK_TYPES = [
  { value: "velocity_attack", label: "Velocity Attack" },
  { value: "card_testing", label: "Card Testing" },
  { value: "address_mismatch", label: "Address Mismatch" },
  { value: "high_amount", label: "High Amount" },
  { value: "device_spoofing", label: "Device Spoofing" },
  { value: "synthetic_identity", label: "Synthetic Identity" },
];

const DetectionScorePage = () => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Configuration state
  const [selectedAttackTypes, setSelectedAttackTypes] = useState([]);
  const [simulationsPerType, setSimulationsPerType] = useState(1);
  const [detectionThreshold, setDetectionThreshold] = useState("");

  // Progress state - simple index based
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const progressInterval = useRef(null);

  const getStages = () => {
    const attackTypes = selectedAttackTypes.length > 0 
      ? selectedAttackTypes 
      : ATTACK_TYPES.map(t => t.value);
    
    return [
      {
        id: "init",
        title: "Initializing Simulation",
        description: "Setting up the fraud simulation environment",
      },
      {
        id: "generating",
        title: "Generating Attack Payloads",
        description: `Creating synthetic fraud transactions for ${attackTypes.length} attack type(s)`,
      },
      {
        id: "analyzing",
        title: "Analyzing Transactions",
        description: "Running fraud detection on generated transactions",
        detail: "Evaluating risk scores and signals",
      },
      {
        id: "scoring",
        title: "Calculating Detection Metrics",
        description: "Computing detection rates and false negative rates",
      },
      {
        id: "complete",
        title: "Analysis Complete",
        description: "Generating final report",
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
    }, 1200); // Move to next stage every 1.2 seconds
  };

  const handleAttackTypeToggle = (value) => {
    setSelectedAttackTypes((prev) =>
      prev.includes(value)
        ? prev.filter((t) => t !== value)
        : [...prev, value]
    );
  };

  const handleSelectAll = () => {
    if (selectedAttackTypes.length === ATTACK_TYPES.length) {
      setSelectedAttackTypes([]);
    } else {
      setSelectedAttackTypes(ATTACK_TYPES.map((t) => t.value));
    }
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError("");
    setResults(null);

    // Start progress simulation
    simulateProgress();

    try {
      const options = {
        attackTypes: selectedAttackTypes.length > 0 ? selectedAttackTypes : null,
        simulationsPerType: simulationsPerType,
        detectionThreshold: detectionThreshold ? parseFloat(detectionThreshold) : null,
      };

      const data = await runDetectionScoreAnalysis(options);
      
      // Complete all stages
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
      setCurrentStageIndex(stages.length - 1);
      setIsComplete(true);
      
      // Small delay to show completion before showing results
      setTimeout(() => {
        setResults(data);
        setLoading(false);
      }, 600);
    } catch (err) {
      console.error("Detection score analysis failed:", err);
      setError("Failed to run detection score analysis. Please ensure the backend is running.");
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
      setLoading(false);
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

  return (
    <div className="detection-score-page">
      <div className="page-header">
        <h1>Detection Score Dashboard</h1>
        <p className="page-subtitle">
          Measure your fraud detection system's effectiveness across different attack types
        </p>
      </div>

      {/* Configuration Panel */}
      {!loading && (
        <section className="config-section">
          <Card title="Analysis Configuration">
            <div className="config-grid">
              {/* Attack Types Selection */}
              <div className="config-group">
                <label className="config-label">
                  Attack Types to Test
                  <button
                    type="button"
                    className="select-all-btn"
                    onClick={handleSelectAll}
                  >
                    {selectedAttackTypes.length === ATTACK_TYPES.length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                </label>
                <div className="attack-type-checkboxes">
                  {ATTACK_TYPES.map((type) => (
                    <label key={type.value} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={selectedAttackTypes.includes(type.value)}
                        onChange={() => handleAttackTypeToggle(type.value)}
                      />
                      <span>{type.label}</span>
                    </label>
                  ))}
                </div>
                <span className="config-hint">
                  {selectedAttackTypes.length === 0
                    ? "Leave empty to test all attack types"
                    : `${selectedAttackTypes.length} type(s) selected`}
                </span>
              </div>

              {/* Simulations Per Type */}
              <div className="config-group">
                <label className="config-label" htmlFor="simulationsPerType">
                  Simulations Per Type
                </label>
                <input
                  type="number"
                  id="simulationsPerType"
                  min="1"
                  max="10"
                  value={simulationsPerType}
                  onChange={(e) =>
                    setSimulationsPerType(
                      Math.max(1, Math.min(10, parseInt(e.target.value) || 1))
                    )
                  }
                  className="config-input"
                />
                <span className="config-hint">
                  More simulations = better accuracy but longer wait (1-10)
                </span>
              </div>

              {/* Detection Threshold */}
              <div className="config-group">
                <label className="config-label" htmlFor="detectionThreshold">
                  Detection Threshold (Optional)
                </label>
                <input
                  type="number"
                  id="detectionThreshold"
                  min="0"
                  max="100"
                  step="1"
                  placeholder="Default: System threshold"
                  value={detectionThreshold}
                  onChange={(e) => setDetectionThreshold(e.target.value)}
                  className="config-input"
                />
                <span className="config-hint">
                  Risk score threshold to consider an attack "caught" (0-100)
                </span>
              </div>
            </div>

            {/* Run Button */}
            <div className="run-section">
              <button
                onClick={handleRunAnalysis}
                disabled={loading}
                className="run-button"
              >
                Run Detection Score Analysis
              </button>
            </div>
          </Card>
        </section>
      )}

      {/* Progress Display */}
      {loading && (
        <SimulationProgress
          stages={stages}
          currentStageIndex={currentStageIndex}
        />
      )}

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">!</span>
          {error}
        </div>
      )}

      {/* Results */}
      {results && <DetectionScoreDashboard data={results} />}
    </div>
  );
};

export default DetectionScorePage;
