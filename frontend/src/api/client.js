import { getSessionId } from "../lib/session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse(response, fallbackMessage) {
  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(payload?.detail ?? fallbackMessage);
  }

  return payload;
}

function buildHeaders(headers = {}) {
  return {
    ...headers,
    "X-Session-Id": getSessionId(),
  };
}

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/resume/upload`, {
    method: "POST",
    headers: buildHeaders(),
    body: formData,
  });

  return parseResponse(response, "Failed to upload resume.");
}

export async function fetchResumeStatus() {
  const response = await fetch(`${API_BASE_URL}/api/resume/status`, {
    headers: buildHeaders(),
  });
  return parseResponse(response, "Failed to fetch resume status.");
}

export async function analyzeJobDescription(jobDescription) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/analyze`, {
    method: "POST",
    headers: buildHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ job_description: jobDescription }),
  });
  return parseResponse(response, "Failed to analyze resume.");
}

export async function fetchAnalysisContext() {
  const response = await fetch(`${API_BASE_URL}/api/analysis/context`, {
    headers: buildHeaders(),
  });
  return parseResponse(response, "Failed to fetch analysis context.");
}

export async function chatWithResume(prompt, history = []) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/chat`, {
    method: "POST",
    headers: buildHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ prompt, history }),
  });

  return parseResponse(response, "Failed to query grounded chat.");
}
