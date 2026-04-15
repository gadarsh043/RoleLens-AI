const SESSION_STORAGE_KEY = "rolelens:session-id";

export function getSessionId() {
  if (typeof window === "undefined") {
    return "server-render";
  }

  const existingId = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existingId) {
    return existingId;
  }

  const nextId = buildSessionId();
  window.localStorage.setItem(SESSION_STORAGE_KEY, nextId);
  return nextId;
}

function buildSessionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `sess_${crypto.randomUUID()}`;
  }

  return `sess_${Math.random().toString(36).slice(2, 14)}`;
}
