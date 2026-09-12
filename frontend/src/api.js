// Base URL is overridable via env var so Sprint 6's deployed frontend can
// point at a deployed backend instead of localhost without a code change.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${path} failed (${res.status}): ${body || res.statusText}`);
  }
  return res.json();
}

export function getForecast() {
  return getJSON("/forecast");
}

export function getFeatureImportance() {
  return getJSON("/feature-importance");
}

export function getHistory(limit = 10) {
  return getJSON(`/history?limit=${limit}`);
}
