import { CheckCircle, Circle, Loader2 } from "lucide-react";
import "./SimulationProgress.css";

const SimulationProgress = ({ stages, currentStageIndex = 0, isComplete = false }) => {
  const getStageStatus = (index) => {
    if (isComplete) return "completed";
    if (index < currentStageIndex) return "completed";
    if (index === currentStageIndex) return "active";
    return "pending";
  };

  // Calculate progress: completed stages / total stages
  // Only count fully completed stages (not the active one)
  const completedCount = isComplete ? stages.length : currentStageIndex;
  const progressPercent = Math.round((completedCount / stages.length) * 100);

  return (
    <div className="simulation-progress">
      <div className="progress-header">
        <Loader2 className="spin" size={20} />
        <span>Simulation in Progress</span>
      </div>
      
      <div className="progress-stages">
        {stages.map((stage, index) => {
          const status = getStageStatus(index);
          return (
            <div key={stage.id} className={`progress-stage stage-${status}`}>
              <div className="stage-indicator">
                {status === "completed" ? (
                  <CheckCircle size={28} />
                ) : status === "active" ? (
                  <div className="stage-spinner">
                    <Loader2 size={28} className="spin" />
                  </div>
                ) : (
                  <Circle size={28} />
                )}
                {index < stages.length - 1 && (
                  <div className={`stage-connector ${status === "completed" ? "completed" : ""}`} />
                )}
              </div>
              <div className="stage-content">
                <h4>{stage.title}</h4>
                <p>{stage.description}</p>
                {status === "active" && stage.detail && (
                  <span className="stage-detail">{stage.detail}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
      <div className="progress-percentage">
        {progressPercent}% Complete
      </div>
    </div>
  );
};

export default SimulationProgress;
