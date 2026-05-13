import { useState } from 'react';
import Card from '../components/Card';
import Button from '../components/Button';
import { Input } from '../components/Input';
import { runMixedDetectionAnalysis } from '../services/api';
import useApi from '../hooks/useApi';
import './MixedDetectionPage.css';

const MixedDetectionPage = () => {
  const [config, setConfig] = useState({
    numLegitimate: 10,
    numFraudulent: 10,
    detectionThreshold: 60,
  });

  const { data: results, loading, error, execute } = useApi(runMixedDetectionAnalysis);

  const handleRun = async () => {
    await execute({
      numLegitimate: config.numLegitimate,
      numFraudulent: config.numFraudulent,
      detectionThreshold: config.detectionThreshold,
      useLlm: false,
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: parseInt(value) || 0 }));
  };

  return (
    <div className="mixed-detection-page">
      <div className="page-header">
        <h1 className="page-title">Mixed Detection Analysis</h1>
        <p className="page-subtitle">
          Test the system's ability to distinguish legitimate from fraudulent transactions
        </p>
      </div>

      <div className="mixed-detection-layout">
        {/* Configuration Panel */}
        <Card title="Test Configuration" className="config-card">
          <div className="config-form">
            <Input
              label="Legitimate Transactions"
              type="number"
              name="numLegitimate"
              value={config.numLegitimate}
              onChange={handleChange}
              min={1}
              max={50}
            />
            <Input
              label="Fraudulent Transactions"
              type="number"
              name="numFraudulent"
              value={config.numFraudulent}
              onChange={handleChange}
              min={1}
              max={50}
            />
            <Input
              label="Detection Threshold"
              type="number"
              name="detectionThreshold"
              value={config.detectionThreshold}
              onChange={handleChange}
              min={0}
              max={100}
            />
            <p className="config-note">
              Total: {config.numLegitimate + config.numFraudulent} transactions
            </p>
            <Button
              variant="primary"
              onClick={handleRun}
              loading={loading}
              fullWidth
            >
              Run Analysis
            </Button>
          </div>
        </Card>

        {/* Results Panel */}
        <div className="results-panel">
          {error && (
            <Card className="error-card">
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                <span>{error.message || 'Analysis failed'}</span>
              </div>
            </Card>
          )}

          {results && (
            <>
              {/* Confusion Matrix */}
              <Card title="Confusion Matrix" className="matrix-card">
                <div className="confusion-matrix">
                  <div className="matrix-header">
                    <div className="matrix-spacer"></div>
                    <div className="matrix-label predicted">Predicted</div>
                  </div>
                  <div className="matrix-body">
                    <div className="matrix-row-label">
                      <span className="actual-label">Actual</span>
                    </div>
                    <div className="matrix-grid">
                      <div className="matrix-corner"></div>
                      <div className="matrix-col-header">Fraud</div>
                      <div className="matrix-col-header">Legit</div>
                      
                      <div className="matrix-row-header">Fraud</div>
                      <div className="matrix-cell tp">
                        <span className="cell-value">{results.confusion_matrix.true_positives}</span>
                        <span className="cell-label">TP</span>
                      </div>
                      <div className="matrix-cell fn">
                        <span className="cell-value">{results.confusion_matrix.false_negatives}</span>
                        <span className="cell-label">FN</span>
                      </div>
                      
                      <div className="matrix-row-header">Legit</div>
                      <div className="matrix-cell fp">
                        <span className="cell-value">{results.confusion_matrix.false_positives}</span>
                        <span className="cell-label">FP</span>
                      </div>
                      <div className="matrix-cell tn">
                        <span className="cell-value">{results.confusion_matrix.true_negatives}</span>
                        <span className="cell-label">TN</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Metrics */}
              <Card title="Performance Metrics" className="metrics-card">
                <div className="metrics-grid">
                  <div className="metric-item">
                    <span className="metric-value">{(results.metrics.accuracy * 100).toFixed(1)}%</span>
                    <span className="metric-label">Accuracy</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{(results.metrics.precision * 100).toFixed(1)}%</span>
                    <span className="metric-label">Precision</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{(results.metrics.recall * 100).toFixed(1)}%</span>
                    <span className="metric-label">Recall</span>
                  </div>
                  <div className="metric-item highlight">
                    <span className="metric-value">{results.metrics.f1_score.toFixed(3)}</span>
                    <span className="metric-label">F1 Score</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{(results.metrics.specificity * 100).toFixed(1)}%</span>
                    <span className="metric-label">Specificity</span>
                  </div>
                  <div className="metric-item warning">
                    <span className="metric-value">{(results.metrics.false_positive_rate * 100).toFixed(1)}%</span>
                    <span className="metric-label">False Positive Rate</span>
                  </div>
                  <div className="metric-item danger">
                    <span className="metric-value">{(results.metrics.false_negative_rate * 100).toFixed(1)}%</span>
                    <span className="metric-label">False Negative Rate</span>
                  </div>
                </div>
              </Card>

              {/* Interpretation */}
              <Card title="Interpretation" className="interpretation-card">
                <div className="interpretation-list">
                  <div className="interpretation-item">
                    <span className="interp-icon">🎯</span>
                    <span>{results.interpretation.accuracy_meaning}</span>
                  </div>
                  <div className="interpretation-item">
                    <span className="interp-icon">✅</span>
                    <span>{results.interpretation.precision_meaning}</span>
                  </div>
                  <div className="interpretation-item">
                    <span className="interp-icon">🔍</span>
                    <span>{results.interpretation.recall_meaning}</span>
                  </div>
                  <div className="interpretation-item">
                    <span className="interp-icon">⚠️</span>
                    <span>{results.interpretation.fpr_meaning}</span>
                  </div>
                  <div className="interpretation-item">
                    <span className="interp-icon">🚨</span>
                    <span>{results.interpretation.fnr_meaning}</span>
                  </div>
                </div>
              </Card>

              {/* Summary Stats */}
              <Card title="Summary" className="summary-card">
                <div className="summary-stats">
                  <div className="summary-row">
                    <span>Total Transactions:</span>
                    <strong>{results.summary.total_transactions}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Legitimate:</span>
                    <strong>{results.summary.total_legitimate}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Fraudulent:</span>
                    <strong>{results.summary.total_fraudulent}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Detection Threshold:</span>
                    <strong>{results.summary.detection_threshold}</strong>
                  </div>
                  <div className="summary-row highlight">
                    <span>Avg Fraud Score:</span>
                    <strong>{results.summary.average_fraud_score.toFixed(1)}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Avg Legitimate Score:</span>
                    <strong>{results.summary.average_legitimate_score.toFixed(1)}</strong>
                  </div>
                  <div className="summary-row success">
                    <span>Score Separation:</span>
                    <strong>{results.summary.score_separation.toFixed(1)} pts</strong>
                  </div>
                </div>
              </Card>

              {/* Detailed Results */}
              <Card title="Detailed Results" className="details-card">
                <div className="results-table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Expected</th>
                        <th>Predicted</th>
                        <th>Score</th>
                        <th>Outcome</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.detailed_results.slice(0, 20).map((tx, idx) => (
                        <tr key={idx} className={`outcome-${tx.outcome}`}>
                          <td className="tx-id">{tx.transaction_id}</td>
                          <td>
                            <span className={`badge ${tx.expected_fraud ? 'fraud' : 'legit'}`}>
                              {tx.expected_fraud ? 'FRAUD' : 'LEGIT'}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${tx.predicted_fraud ? 'fraud' : 'legit'}`}>
                              {tx.predicted_fraud ? 'FRAUD' : 'LEGIT'}
                            </span>
                          </td>
                          <td className="score">{tx.risk_score.toFixed(1)}</td>
                          <td>
                            <span className={`outcome-badge ${tx.outcome}`}>
                              {tx.outcome.replace('_', ' ')}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          )}

          {!results && !loading && !error && (
            <Card className="placeholder-card">
              <div className="placeholder">
                <div className="placeholder-icon">📊</div>
                <h3>Ready to Test</h3>
                <p>Configure the test parameters and click "Run Analysis" to evaluate the fraud detection system.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default MixedDetectionPage;
