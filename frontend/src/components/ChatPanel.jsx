export default function ChatPanel({
  messages,
  inputValue,
  onInputChange,
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
            <p className="panel-label">Resume Q&A</p>
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
            `Ask` keeps the current fit score. `Reanalyze JD` intentionally replaces the dashboard with a
            new job-description analysis.
          </p>

          <div className="chat-thread">
            {messages.map((message, index) => (
              <article
                className={`chat-message ${message.role === "user" ? "user" : "assistant"}`}
                key={`${message.role}-${index}`}
              >
                <p className="chat-role">{message.role === "user" ? "You" : "RoleLens"}</p>
                <p>{message.content}</p>
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
          </div>

          <div className="chat-compose">
            <textarea
              className="job-textarea compact"
              rows={4}
              value={inputValue}
              onChange={onInputChange}
              placeholder="Ask about the current analysis, or paste a new job description and click Reanalyze JD."
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
