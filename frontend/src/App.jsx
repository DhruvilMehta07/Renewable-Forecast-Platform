import { useCallback, useEffect, useState } from "react";
import { getFeatureImportance, getForecast, getGeocodeResults, getHistory, getWhatIfForecast } from "./api";
import AlertsPanel from "./components/AlertsPanel";
import ComparisonPanel from "./components/ComparisonPanel";
import ForecastChart from "./components/ForecastChart";
import ForecastTable from "./components/ForecastTable";
import ImportancePanel from "./components/ImportancePanel";
import ModelGuide from "./components/ModelGuide";
import StatusStrip from "./components/StatusStrip";
import UtilizationChart from "./components/UtilizationChart";
import "./index.css";

function formatIssueTime(iso, timezone) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: timezone || undefined,
  });
}

function csvValue(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadForecast(forecast, timezone) {
  const headers = ["target_time", "horizon_hours", "predicted_ac_power_kw", "lower_bound_kw", "upper_bound_kw", "is_daytime", "decision"];
  const rows = forecast.map((row) => [
    new Date(row.target_time).toLocaleString(undefined, { timeZone: timezone || undefined }),
    row.horizon_hours,
    row.predicted_ac_power,
    row.lower_bound,
    row.upper_bound,
    row.is_daytime,
    row.decision,
  ]);
  const csv = [headers, ...rows].map((row) => row.map(csvValue).join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = "greencast-forecast.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

export default function App() {
  const [forecast, setForecast] = useState(null);
  const [importance, setImportance] = useState(null);
  const [history, setHistory] = useState([]);
  const [issueTime, setIssueTime] = useState(null);
  const [loadedAt, setLoadedAt] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("plant");
  const [site, setSite] = useState({ capacityKw: "5000" });
  const [locationQuery, setLocationQuery] = useState("");
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [searching, setSearching] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [approximate, setApproximate] = useState(false);
  const [siteDetails, setSiteDetails] = useState(null);
  const [horizon, setHorizon] = useState(72);
  const [view, setView] = useState("chart");

  const load = useCallback(async (selectedMode = mode) => {
    setLoading(true);
    setError(null);
    try {
      if (selectedMode === "whatif" && !selectedLocation) {
        setLoading(false);
        return;
      }
      const forecastRequest = selectedMode === "plant"
        ? getForecast()
        : getWhatIfForecast({ ...site, ...selectedLocation });
      const [forecastRes, importanceRes] = await Promise.all([
        forecastRequest,
        getFeatureImportance(),
      ]);
      setForecast(forecastRes.forecast);
      setIssueTime(forecastRes.issue_time);
      setApproximate(Boolean(forecastRes.approximate));
      setSiteDetails(forecastRes.site);
      setImportance(importanceRes.feature_importance);
      setLoadedAt(new Date().toISOString());
      try {
        const historyRes = await getHistory(3);
        setHistory(historyRes.runs || []);
      } catch {
        setHistory([]);
      }
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [mode, site, selectedLocation]);

  useEffect(() => { load(); }, [load]);

  function submitWhatIf(event) {
    event.preventDefault();
    if (!selectedLocation) {
      setLocationError("Search for and select a location first.");
      return;
    }
    setMode("whatif");
    load("whatif");
  }

  async function searchLocations(event) {
    event.preventDefault();
    const query = locationQuery.trim();
    if (query.length < 2) {
      setLocationError("Enter at least 2 characters.");
      return;
    }
    setSearching(true);
    setLocationError(null);
    setLocations([]);
    try {
      const response = await getGeocodeResults(query);
      setLocations(response.results);
      if (!response.results.length) setLocationError("No matching location found.");
    } catch (searchError) {
      setLocationError(searchError.message);
    } finally {
      setSearching(false);
    }
  }

  const visibleForecast = forecast?.filter((row) => row.horizon_hours <= horizon) || [];
  const timezone = siteDetails?.timezone || undefined;
  const currentMode = approximate ? "what_if" : "plant_1";
  const previousRun = history.slice(1).find((run) => {
    if (run.mode !== currentMode) return false;
    if (currentMode === "plant_1") return true;
    return run.site && siteDetails
      && Math.abs(run.site.lat - siteDetails.lat) < 0.0001
      && Math.abs(run.site.lon - siteDetails.lon) < 0.0001
      && Number(run.site.capacity_kw) === Number(siteDetails.capacity_kw);
  }) || null;
  const freshness = loadedAt ? Math.max(0, Math.round((Date.now() - new Date(loadedAt).getTime()) / 60000)) : null;

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">GC</div>
          <div>
            <div className="eyebrow">Renewable energy intelligence</div>
            <h1>GreenCast</h1>
            <p className="subtitle">Clear, actionable solar generation forecasts for the next 72 hours.</p>
          </div>
        </div>
        <div className="meta">
          <div className="status-badge"><span className="status-dot" />{approximate ? "Exploratory estimate" : "Live forecast"}</div>
          {issueTime && <div className="issued">Issued <span className="issue-time">{formatIssueTime(issueTime, timezone)}</span></div>}
          <div className="data-context">Timezone: {siteDetails?.timezone || "browser local time"} {freshness !== null && `· refreshed ${freshness}m ago`}</div>
          <button className="refresh-btn primary-action" onClick={load} disabled={loading}>{loading ? "Refreshing..." : "Refresh forecast"}</button>
        </div>
      </header>

      <section className="intro-block" aria-labelledby="intro-title">
        <div><div className="eyebrow">Forecast workspace</div><h2 id="intro-title">Know what your energy site may produce next.</h2></div>
        <p>Use the forecast to plan around expected solar output. The shaded range shows uncertainty, while action markers highlight hours that may need grid attention.</p>
      </section>

      <section className="panel mode-panel">
        <div className="section-heading compact-heading">
          <div><div className="eyebrow">Forecast source</div><h2>Choose a site view</h2></div>
          <span className="help-tip" title="Plant 1 uses the validated site model. What-if estimates scale that model to another location and capacity." aria-label="About forecast modes">?</span>
        </div>
        <div className="mode-tabs" role="tablist" aria-label="Forecast mode">
          <button className={mode === "plant" ? "mode-tab active" : "mode-tab"} onClick={() => { setMode("plant"); load("plant"); }}><span className="tab-title">Plant 1</span><span className="tab-note">Validated site</span></button>
          <button className={mode === "whatif" ? "mode-tab active" : "mode-tab"} onClick={() => setMode("whatif")}><span className="tab-title">What-if site</span><span className="tab-note">Explore a location</span></button>
        </div>
        {mode === "whatif" && (
          <form className="what-if-form" onSubmit={submitWhatIf}>
            <label className="location-search">Search location<span className="inline-input"><input type="search" placeholder="City, landmark, or country" value={locationQuery} onChange={(event) => setLocationQuery(event.target.value)} /><button className="search-btn" type="button" onClick={searchLocations} disabled={searching}>{searching ? "Searching..." : "Search"}</button></span></label>
            <label>Site capacity (kW)<input type="number" min="1" max="1000000" step="any" value={site.capacityKw} onChange={(event) => setSite({ ...site, capacityKw: event.target.value })} required /></label>
            <button className="refresh-btn primary-action" type="submit" disabled={loading}>Run estimate</button>
          </form>
        )}
        {mode === "whatif" && locations.length > 0 && <div className="location-results" role="listbox" aria-label="Location results">{locations.map((location) => <button type="button" key={`${location.latitude}-${location.longitude}`} className="location-result" onClick={() => { setSelectedLocation(location); setLocations([]); setLocationError(null); }}><strong>{location.name}</strong><span>{[location.admin1, location.country].filter(Boolean).join(", ")} · {location.timezone}</span></button>)}</div>}
        {mode === "whatif" && selectedLocation && <div className="selected-location">Selected: <strong>{selectedLocation.name}</strong> · {selectedLocation.latitude.toFixed(3)}, {selectedLocation.longitude.toFixed(3)} · {selectedLocation.timezone}</div>}
        {mode === "whatif" && locationError && <div className="form-error">{locationError}</div>}
      </section>

      {loading && !forecast && <div className="loading">Fetching forecast...</div>}
      {error && <div className="error-state"><div className="message">Couldn't load the forecast: {error}</div><button className="refresh-btn" onClick={load}>Try again</button></div>}

      {forecast && !error && (
        <>
          <StatusStrip forecast={visibleForecast} siteDetails={siteDetails} />
          <section className="panel forecast-controls" aria-label="Forecast display controls">
            <div><div className="eyebrow">Explore the forecast</div><h2>Choose a time window and view</h2><p className="panel-note">Use a shorter window on small screens, or switch to a table when you need exact hourly values.</p></div>
            <div className="control-row"><div className="segmented-control" aria-label="Forecast period"><span className="control-label">Window</span>{[24, 48, 72].map((hours) => <button key={hours} className={horizon === hours ? "selected" : ""} onClick={() => setHorizon(hours)}>{hours}h</button>)}</div><div className="segmented-control" aria-label="Forecast display"><span className="control-label">View</span><button className={view === "chart" ? "selected" : ""} onClick={() => setView("chart")}>Chart</button><button className={view === "table" ? "selected" : ""} onClick={() => setView("table")}>Table</button></div><button className="export-button" onClick={() => downloadForecast(visibleForecast, timezone)}>Download CSV</button></div>
          </section>
          {view === "chart" ? <ForecastChart forecast={visibleForecast} /> : <section className="panel"><div className="section-heading"><div><div className="eyebrow">Exact values</div><h2>Hourly forecast table</h2></div></div><ForecastTable forecast={visibleForecast} timezone={timezone} capacity={siteDetails?.capacity_kw} /></section>}
          <UtilizationChart forecast={visibleForecast} capacity={siteDetails?.capacity_kw || 1} />
          <AlertsPanel forecast={visibleForecast} capacity={siteDetails?.capacity_kw} />
          <ComparisonPanel forecast={forecast} previousRun={previousRun} />
          {importance && <ImportancePanel importance={importance} />}
          <ModelGuide approximate={approximate} />
        </>
      )}
    </div>
  );
}
