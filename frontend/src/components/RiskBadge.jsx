import './RiskBadge.css';

const RiskBadge = ({ level, score }) => {
  const levelClass = `risk-badge risk-badge-${level}`;
  
  return (
    <div className={levelClass}>
      <span className="risk-badge-level">{level.toUpperCase()}</span>
      {score !== undefined && (
        <span className="risk-badge-score">{score.toFixed(1)}</span>
      )}
    </div>
  );
};

export default RiskBadge;
