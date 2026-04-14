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

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/resume/upload`, {
    method: "POST",
    body: formData,
  });

  return parseResponse(response, "Failed to upload resume.");
}

export async function fetchResumeStatus() {
  const response = await fetch(`${API_BASE_URL}/api/resume/status`);
  return parseResponse(response, "Failed to fetch resume status.");
}

export async function analyzeJobDescription(jobDescription) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_description: jobDescription }),
  });
  return parseResponse(response, "Failed to analyze resume.");
}

export async function chatWithResume(prompt, history = []) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt, history }),
  });

  return parseResponse(response, "Failed to query resume chat.");
}
