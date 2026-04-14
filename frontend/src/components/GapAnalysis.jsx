export default function GapAnalysis({ gaps = [], recommendations = [] }) {
  return (
    <section className="metric-card full-span">
      <div className="results-split">
        <div>
          <p className="panel-label">Gap Analysis</p>
          <h3>Priority gaps</h3>
          <div className="gap-list">
            {gaps.length ? (
              gaps.map((gap) => (
                <article className="gap-item" key={`${gap.skill}-${gap.priority}`}>
                  <div className="gap-row">
                    <strong>{gap.skill}</strong>
                    <span className={`priority-badge ${String(gap.priority).toLowerCase()}`}>{gap.priority}</span>
                  </div>
                  <p>{gap.reason}</p>
                </article>
              ))
            ) : (
              <p className="status-copy">No major gaps were returned by the model.</p>
            )}
          </div>
        </div>

        <div>
          <p className="panel-label">Recommendations</p>
          <h3>What to change next</h3>
          <div className="recommendation-list">
            {recommendations.length ? (
              recommendations.map((item) => (
                <article className="recommendation-item" key={item.title}>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  <span>{item.action}</span>
                </article>
              ))
            ) : (
              <p className="status-copy">No recommendations available.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
