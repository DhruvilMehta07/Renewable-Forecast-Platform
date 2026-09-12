import { useEffect, useState, useCallback } from "react";
import { getForecast, getFeatureImportance, getWhatIfForecast } from "./api";
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
  const [mode, setMode] = useState("plant");
  const [site, setSite] = useState({ latitude: "14.5", longitude: "78.0", capacityKw: "29150" });
  const [approximate, setApproximate] = useState(false);

  const load = useCallback(async (selectedMode = mode) => {
    setLoading(true);
    setError(null);
    try {
      const forecastRequest = selectedMode === "plant"
        ? getForecast()
        : getWhatIfForecast(site);
      const [forecastRes, importanceRes] = await Promise.all([
        forecastRequest,
        getFeatureImportance(),
      ]);
      setForecast(forecastRes.forecast);
      setIssueTime(forecastRes.issue_time);
      setApproximate(Boolean(forecastRes.approximate));
      setImportance(importanceRes.feature_importance);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [mode, site]);

  useEffect(() => { load(); }, [load]);

  function submitWhatIf(event) {
    event.preventDefault();
    setMode("whatif");
    load("whatif");
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Renewable Forecast Platform</h1>
          <p className="subtitle">
            {approximate ? "Capacity-scaled exploratory estimate" : "Validated Plant 1 forecast"}
            {" "}&middot; 72-hour solar generation forecast
          </p>
        </div>
        <div className="meta">
          {issueTime && <div>Issued <span className="issue-time">{formatIssueTime(issueTime)}</span></div>}
          <button className="refresh-btn" onClick={load} disabled={loading}>
            {loading ? "Refreshing\u2026" : "Refresh forecast"}
          </button>
        </div>
      </header>

      <section className="panel mode-panel">
        <div className="mode-tabs" role="tablist" aria-label="Forecast mode">
          <button className={mode === "plant" ? "mode-tab active" : "mode-tab"} onClick={() => { setMode("plant"); load("plant"); }}>
            Plant 1
          </button>
          <button className={mode === "whatif" ? "mode-tab active" : "mode-tab"} onClick={() => setMode("whatif")}>
            What-if site
          </button>
        </div>
        {mode === "whatif" && (
          <form className="what-if-form" onSubmit={submitWhatIf}>
            <label>Latitude<input type="number" min="-90" max="90" step="any" value={site.latitude} onChange={(e) => setSite({ ...site, latitude: e.target.value })} required /></label>
            <label>Longitude<input type="number" min="-180" max="180" step="any" value={site.longitude} onChange={(e) => setSite({ ...site, longitude: e.target.value })} required /></label>
            <label>Capacity (kW)<input type="number" min="1" max="1000000" step="any" value={site.capacityKw} onChange={(e) => setSite({ ...site, capacityKw: e.target.value })} required /></label>
            <button className="refresh-btn" type="submit" disabled={loading}>Estimate site</button>
          </form>
        )}
      </section>

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
