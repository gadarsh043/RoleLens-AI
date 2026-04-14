export default function JobDescInput({
  jobDescription,
  onJobDescriptionChange,
  onAnalyze,
  isAnalyzing,
  canAnalyze,
  roleHint,
  progressStep,
  errorMessage,
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="panel-label">Job Description</p>
          <h2>Paste the target role</h2>
        </div>
        {roleHint ? <span className="role-badge">{roleHint}</span> : null}
      </div>

      <textarea
        className="job-textarea"
        placeholder="Paste the job description here."
        rows={12}
        value={jobDescription}
        onChange={onJobDescriptionChange}
      />

      <div className="action-row">
        <button className="primary-button" type="button" onClick={onAnalyze} disabled={!canAnalyze}>
          {isAnalyzing ? progressStep : "Analyze"}
        </button>
        <p className="helper-copy">
          {isAnalyzing
            ? "The app uploads if needed, retrieves the best chunks, then requests a grounded analysis."
            : "Minimum input: indexed resume plus a meaningful job description."}
        </p>
      </div>

      {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
    </section>
  );
}
