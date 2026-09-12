function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
}

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

export default function ComparisonPanel({ forecast, previousRun }) {
  if (!previousRun?.forecast?.length) {
    return (
      <div className="panel comparison-panel">
        <div className="section-heading"><div><div className="eyebrow">Forecast history</div><h2>Compare forecast updates</h2></div></div>
        <p className="empty-state">A second saved forecast is needed before changes can be compared. Refresh the forecast to create another run.</p>
      </div>
    );
  }

  const previousByHorizon = new Map(previousRun.forecast.map((row) => [row.horizon_hours, row]));
  const differences = forecast.map((row) => row.predicted_ac_power - (previousByHorizon.get(row.horizon_hours)?.predicted_ac_power || row.predicted_ac_power));
  const changed = differences.filter((value) => Math.abs(value) >= 250);
  const averageChange = average(differences);
  const largestChange = differences.reduce((largest, value) => Math.abs(value) > Math.abs(largest) ? value : largest, 0);

  return (
    <div className="panel comparison-panel">
      <div className="section-heading">
        <div><div className="eyebrow">Forecast history</div><h2>What changed since the last run?</h2></div>
        <span className="comparison-time">Previous: {formatTime(previousRun.created_at)}</span>
      </div>
      <p className="panel-note">This compares expected output at the same forecast horizons. Differences can reflect new weather data or a later forecast issue time.</p>
      <div className="comparison-grid">
        <div><span className="comparison-label">Average change</span><strong className={averageChange >= 0 ? "positive" : "negative"}>{averageChange >= 0 ? "+" : ""}{Math.round(averageChange).toLocaleString()} kW</strong></div>
        <div><span className="comparison-label">Largest change</span><strong>{largestChange >= 0 ? "+" : ""}{Math.round(largestChange).toLocaleString()} kW</strong></div>
        <div><span className="comparison-label">Meaningful changes</span><strong>{changed.length} hours</strong></div>
      </div>
    </div>
  );
}
