import { useEffect, useState, useCallback } from "react";
import { getForecast, getFeatureImportance } from "./api";
import StatusStrip from "./components/StatusStrip";
import ForecastChart from "./components/ForecastChart";
import AlertsPanel from "./components/AlertsPanel";
import ImportancePanel from "./components/ImportancePanel";
import "./index.css";

function formatIssueTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "long", hour: "numeric", minute: "2-digit",
  });
}

export default function App() {
  const [forecast, setForecast] = useState(null);
  const [importance, setImportance] = useState(null);
  const [issueTime, setIssueTime] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [forecastRes, importanceRes] = await Promise.all([
        getForecast(),
        getFeatureImportance(),
      ]);
      setForecast(forecastRes.forecast);
      setIssueTime(forecastRes.issue_time);
      setImportance(importanceRes.feature_importance);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Renewable Forecast Platform</h1>
          <p className="subtitle">Plant 1 &middot; 14.5&deg;N, 78.0&deg;E &middot; 72-hour solar generation forecast</p>
        </div>
        <div className="meta">
          {issueTime && <div>Issued <span className="issue-time">{formatIssueTime(issueTime)}</span></div>}
          <button className="refresh-btn" onClick={load} disabled={loading}>
            {loading ? "Refreshing\u2026" : "Refresh forecast"}
          </button>
        </div>
      </header>

      {loading && !forecast && <div className="loading">Fetching forecast\u2026</div>}

      {error && (
        <div className="error-state">
          <div className="message">Couldn't load the forecast: {error}</div>
          <button className="refresh-btn" onClick={load}>Try again</button>
        </div>
      )}

      {forecast && !error && (
        <>
          <StatusStrip forecast={forecast} />
          <ForecastChart forecast={forecast} />
          <AlertsPanel forecast={forecast} />
          {importance && <ImportancePanel importance={importance} />}
        </>
      )}
    </div>
  );
}
