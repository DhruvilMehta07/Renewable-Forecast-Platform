// Base URL is overridable via env var so Sprint 6's deployed frontend can
// point at a deployed backend instead of localhost without a code change.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getJSON(path, token) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${path} failed (${res.status}): ${body || res.statusText}`);
  }
  return res.json();
}

export function getForecast(token) {
  return getJSON("/forecast", token);
}

export function getWhatIfForecast({ latitude, longitude, capacityKw, timezone = "auto" }, token) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    capacity_kw: String(capacityKw),
    timezone,
  });
  return getJSON(`/forecast/what-if?${params}`, token);
}

export function getGeocodeResults(query, token) {
  return getJSON(`/geocode?query=${encodeURIComponent(query)}`, token);
}

export function getFeatureImportance(token) {
  return getJSON("/feature-importance", token);
}

export function getHistory(limit = 10, token) {
  return getJSON(`/history?limit=${limit}`, token);
}

async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || `${path} failed (${res.status})`);
  }
  return res.json();
}

export function loginUser(credentials) {
  return postJSON("/auth/login", credentials);
}

export function signupUser(details) {
  return postJSON("/auth/signup", details);
}

export function getCurrentUser(token) {
  return getJSON("/auth/me", token);
}
