export default function ResumeUpload({
  file,
  indexedResume,
  chunksIndexed,
  isUploading,
  onFileChange,
  errorMessage,
}) {
  return (
    <section className="panel">
      <p className="panel-label">Resume Upload</p>
      <h2>Upload your resume PDF</h2>
      <p className="panel-copy">
        Index your resume once, then compare it against multiple job descriptions.
      </p>

      <label className={`upload-dropzone ${isUploading ? "is-busy" : ""}`} htmlFor="resume-upload">
        <input
          id="resume-upload"
          className="sr-only"
          type="file"
          accept="application/pdf"
          onChange={onFileChange}
          disabled={isUploading}
        />
        <span className="upload-title">{isUploading ? "Indexing resume..." : "Choose PDF"}</span>
        <span className="upload-subtitle">
          {file?.name ?? indexedResume?.filename ?? "Drag-and-drop styling can come later. File selection works now."}
        </span>
      </label>

      {indexedResume ? (
        <div className="status-card success">
          <p className="status-title">Indexed resume</p>
          <p className="status-copy">
            {indexedResume.filename} · {chunksIndexed ?? indexedResume.chunks_indexed ?? "?"} chunks
          </p>
          {indexedResume.sections?.length ? (
            <p className="status-meta">Sections: {indexedResume.sections.join(", ")}</p>
          ) : null}
        </div>
      ) : (
        <div className="status-card">
          <p className="status-title">No resume indexed yet</p>
          <p className="status-copy">Upload a PDF before running analysis.</p>
        </div>
      )}

      {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
    </section>
  );
}
