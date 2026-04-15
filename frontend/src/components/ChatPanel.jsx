export default function ChatPanel({
  messages,
  inputValue,
  onInputChange,
  onInputKeyDown,
  onAsk,
  onReanalyze,
  isLoading,
  errorMessage,
  isCollapsed,
  onToggleCollapse,
}) {
  return (
    <aside className={`chat-sidebar ${isCollapsed ? "is-collapsed" : ""}`}>
      {isCollapsed ? (
        <div className="chat-collapsed">
          <button className="ghost-button icon-button" type="button" onClick={onToggleCollapse}>
            <span aria-hidden="true">‹</span>
            <span className="sr-only">Expand chat</span>
          </button>
          <span className="chat-collapsed-label">Chat</span>
        </div>
      ) : (
        <div className="chat-header">
          <div className="chat-heading">
            <p className="panel-label">Grounded Q&A</p>
            <h3>Ask follow-up questions or run a new analysis</h3>
          </div>
          <button className="ghost-button" type="button" onClick={onToggleCollapse}>
            Collapse
          </button>
        </div>
      )}

      {!isCollapsed ? (
        <>
          <p className="helper-copy">
            `Ask` can answer from your resume, the active job description, or both. `Reanalyze JD`
            replaces the dashboard with a new job-description analysis.
          </p>

          <div className="chat-thread">
            {messages.map((message, index) => (
              <article
                className={`chat-message ${message.role === "user" ? "user" : "assistant"}`}
                key={`${message.role}-${index}`}
              >
                <p className="chat-role">{message.role === "user" ? "You" : "RoleLens"}</p>
                <p>{message.content}</p>
                {message.role === "assistant" && (message.scope || message.sourceTypes?.length) ? (
                  <div className="source-row">
                    {message.scope ? (
                      <span className="source-chip primary">{formatScopeLabel(message.scope)}</span>
                    ) : null}
                    {message.sourceTypes?.map((sourceType) => (
                      <span className="source-chip" key={sourceType}>
                        {formatSourceTypeLabel(sourceType)}
                      </span>
                    ))}
                  </div>
                ) : null}
                {message.followUpSuggestions?.length ? (
                  <div className="suggestion-row">
                    {message.followUpSuggestions.map((suggestion) => (
                      <span className="suggestion-chip" key={suggestion}>
                        {suggestion}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
            {isLoading ? (
              <article className="chat-message assistant is-loading">
                <p className="chat-role">RoleLens</p>
                <div className="typing-loader" aria-label="RoleLens is responding" role="status">
                  <span />
                  <span />
                  <span />
                </div>
              </article>
            ) : null}
          </div>

          <div className="chat-compose">
            <textarea
              className="job-textarea compact"
              rows={4}
              value={inputValue}
              onChange={onInputChange}
              onKeyDown={onInputKeyDown}
              placeholder="Ask about your resume, the current job description, or your fit. Paste a new JD and click Reanalyze JD."
            />
            <div className="chat-actions">
              <button className="ghost-button" type="button" onClick={onReanalyze} disabled={isLoading}>
                {isLoading ? "Working..." : "Reanalyze JD"}
              </button>
              <button className="primary-button" type="button" onClick={onAsk} disabled={isLoading}>
                {isLoading ? "Thinking..." : "Ask"}
              </button>
            </div>
          </div>

          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
        </>
      ) : null}
    </aside>
  );
}

function formatScopeLabel(scope) {
  if (scope === "comparison") {
    return "Comparison Answer";
  }
  if (scope === "job") {
    return "Job Facts";
  }
  return "Resume Facts";
}

function formatSourceTypeLabel(sourceType) {
  if (sourceType === "job_description") {
    return "JD Evidence";
  }
  if (sourceType === "resume") {
    return "Resume Evidence";
  }
  return "Evidence";
}
