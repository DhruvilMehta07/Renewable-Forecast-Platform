import { useEffect, useState, useCallback } from "react";
import { getForecast, getFeatureImportance, getWhatIfForecast, getGeocodeResults } from "./api";
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
  const [site, setSite] = useState({ capacityKw: "5000" });
  const [locationQuery, setLocationQuery] = useState("");
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [searching, setSearching] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [approximate, setApproximate] = useState(false);

  const load = useCallback(async (selectedMode = mode) => {
    setLoading(true);
    setError(null);
    try {
      if (selectedMode === "whatif" && !selectedLocation) return;
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
      setImportance(importanceRes.feature_importance);
    } catch (e) {
      setError(e.message);
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
    } catch (error) {
      setLocationError(error.message);
    } finally {
      setSearching(false);
    }
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
            <label className="location-search">Location
              <span className="inline-input">
                <input type="search" placeholder="City, landmark, or country" value={locationQuery} onChange={(e) => setLocationQuery(e.target.value)} />
                <button className="search-btn" type="button" onClick={searchLocations} disabled={searching}>{searching ? "Searching..." : "Search"}</button>
              </span>
            </label>
            <label>Capacity (kW)<input type="number" min="1" max="1000000" step="any" value={site.capacityKw} onChange={(e) => setSite({ ...site, capacityKw: e.target.value })} required /></label>
            <button className="refresh-btn" type="submit" disabled={loading}>Estimate site</button>
          </form>
        )}
        {mode === "whatif" && locations.length > 0 && (
          <div className="location-results" role="listbox" aria-label="Location results">
            {locations.map((location) => (
              <button type="button" key={`${location.latitude}-${location.longitude}`} className="location-result" onClick={() => { setSelectedLocation(location); setLocations([]); setLocationError(null); }}>
                <strong>{location.name}</strong>
                <span>{[location.admin1, location.country].filter(Boolean).join(", ")} · {location.timezone}</span>
              </button>
            ))}
          </div>
        )}
        {mode === "whatif" && selectedLocation && (
          <div className="selected-location">Selected: <strong>{selectedLocation.name}</strong> · {selectedLocation.latitude.toFixed(3)}, {selectedLocation.longitude.toFixed(3)} · {selectedLocation.timezone}</div>
        )}
        {mode === "whatif" && locationError && <div className="form-error">{locationError}</div>}
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
