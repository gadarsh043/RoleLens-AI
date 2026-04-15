import { useEffect, useState, startTransition } from "react";
import { useNavigate } from "react-router-dom";
import {
  analyzeJobDescription,
  fetchAnalysisContext,
  fetchResumeStatus,
  uploadResume,
} from "../api/client";
import JobDescInput from "../components/JobDescInput";
import ResumeUpload from "../components/ResumeUpload";

export default function Home() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [resumeStatus, setResumeStatus] = useState({ indexed: false });
  const [progressStep, setProgressStep] = useState("Analyze");
  const [uploadError, setUploadError] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    let ignore = false;

    fetchResumeStatus()
      .then((status) => {
        if (!ignore) {
          setResumeStatus(status);
        }
      })
      .catch(() => {
        if (!ignore) {
          setResumeStatus({ indexed: false });
        }
      });

    fetchAnalysisContext()
      .then((context) => {
        if (!ignore && context?.job_description?.text) {
          setJobDescription(context.job_description.text);
        }
      })
      .catch(() => {});

    return () => {
      ignore = true;
    };
  }, []);

  const roleHint = detectRole(jobDescription);
  const canAnalyze = Boolean(jobDescription.trim()) && !isUploading && !isAnalyzing;

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    setUploadError("");
    setAnalysisError("");

    if (!file) {
      return;
    }

    if (file.type && file.type !== "application/pdf") {
      setUploadError("Please upload a PDF resume.");
      return;
    }

    setSelectedFile(file);
    setIsUploading(true);
    setProgressStep("Indexing...");

    try {
      const indexedResume = await uploadResume(file);
      setResumeStatus({ indexed: true, resume: indexedResume, chunks_indexed: indexedResume.chunks_indexed });
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
      setProgressStep("Analyze");
    }
  }

  async function handleAnalyze() {
    setUploadError("");
    setAnalysisError("");

    const trimmedJobDescription = jobDescription.trim();
    if (!trimmedJobDescription) {
      setAnalysisError("Paste a job description before running analysis.");
      return;
    }

    setIsAnalyzing(true);

    try {
      let currentResume = resumeStatus.resume;

      if (!resumeStatus.indexed && selectedFile) {
        setProgressStep("Indexing...");
        currentResume = await uploadResume(selectedFile);
        setResumeStatus({ indexed: true, resume: currentResume, chunks_indexed: currentResume.chunks_indexed });
      }

      if (!currentResume && !resumeStatus.indexed) {
        throw new Error("Upload a resume PDF before running analysis.");
      }

      setProgressStep("Retrieving...");
      setProgressStep("Analyzing...");
      const analysis = await analyzeJobDescription(trimmedJobDescription);

      const payload = {
        analysis,
        jobDescription: trimmedJobDescription,
        resume: currentResume ?? resumeStatus.resume ?? null,
        generatedAt: new Date().toISOString(),
      };

      sessionStorage.setItem("rolelens:last-analysis", JSON.stringify(payload));
      startTransition(() => {
        navigate("/results", { state: payload });
      });
    } catch (error) {
      setAnalysisError(error.message);
    } finally {
      setProgressStep("Analyze");
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">RoleLens AI</p>
        <h1>Resume and job-fit analysis grounded in your actual documents.</h1>
        <p className="lede">
          Upload a PDF, paste a job description, and compare your profile against the role with
          retrieval-backed analysis and grounded follow-up chat.
        </p>
      </section>

      <section className="two-panel">
        <ResumeUpload
          file={selectedFile}
          indexedResume={resumeStatus.resume}
          chunksIndexed={resumeStatus.chunks_indexed}
          isUploading={isUploading}
          onFileChange={handleFileChange}
          errorMessage={uploadError}
        />
        <JobDescInput
          jobDescription={jobDescription}
          onJobDescriptionChange={(event) => setJobDescription(event.target.value)}
          onAnalyze={handleAnalyze}
          isAnalyzing={isAnalyzing}
          canAnalyze={canAnalyze}
          roleHint={roleHint}
          progressStep={progressStep}
          errorMessage={analysisError}
        />
      </section>
    </main>
  );
}

function detectRole(jobDescription) {
  const normalized = jobDescription.toLowerCase();

  if (!normalized) {
    return "";
  }

  const roles = [
    "frontend engineer",
    "backend engineer",
    "full stack engineer",
    "machine learning engineer",
    "data scientist",
    "product manager",
    "software engineer",
    "developer advocate",
    "devops engineer",
  ];

  return roles.find((role) => normalized.includes(role)) ?? "Role detected";
}
