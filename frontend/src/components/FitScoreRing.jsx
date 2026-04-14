export default function FitScoreRing({ fitScore = 0, grade = "D", roleDetected = "Unknown" }) {
  const radius = 66;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, fitScore)) / 100) * circumference;

  return (
    <section className="metric-card hero-card">
      <p className="panel-label">Fit Score</p>
      <div className="score-ring-wrap">
        <svg className="score-ring" viewBox="0 0 180 180" aria-hidden="true">
          <circle className="score-ring-track" cx="90" cy="90" r={radius} />
          <circle
            className="score-ring-progress"
            cx="90"
            cy="90"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="score-ring-center">
          <strong>{fitScore}</strong>
          <span>{grade}</span>
        </div>
      </div>
      <p className="status-copy">Best aligned role: {roleDetected}</p>
    </section>
  );
}
