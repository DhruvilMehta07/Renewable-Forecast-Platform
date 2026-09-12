function fmt(n) {
  return Math.round(n).toLocaleString();
}

function timeLabel(iso) {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
}

export default function StatusStrip({ forecast, siteDetails }) {
  const nextHour = forecast[0];
  const peak = forecast.reduce((max, row) => (row.predicted_ac_power > max.predicted_ac_power ? row : max), forecast[0]);
  const activeAlerts = forecast.filter((row) => row.decision !== "normal").length;
  const capacity = siteDetails?.capacity_kw;
  const utilization = capacity ? Math.round((peak.predicted_ac_power / capacity) * 100) : null;

  return (
    <section className="status-section" aria-labelledby="summary-title">
      <div className="section-heading">
        <div><div className="eyebrow">At a glance</div><h2 id="summary-title">Forecast summary</h2></div>
        <span className="units-note">All output values in kW</span>
      </div>
      <div className="status-strip">
      <div className="status-card solar">
        <div className="label">Next hour <span title="Predicted generation in the first forecast hour">?</span></div>
        <div className="value">
          {fmt(nextHour.predicted_ac_power)}
          <span className="unit">kW</span>
        </div>
      </div>
      <div className="status-card solar">
        <div className="label">72-hour peak</div>
        <div className="value">
          {fmt(peak.predicted_ac_power)}
          <span className="unit">kW</span>
        </div>
        <div className="card-detail">{timeLabel(peak.target_time)}{utilization !== null ? ` · ${utilization}% of capacity` : ""}</div>
      </div>
      <div className="status-card">
        <div className="label">Forecast window</div>
        <div className="value">72<span className="unit">h</span></div>
        <div className="card-detail">Through {timeLabel(forecast[forecast.length - 1].target_time)}</div>
      </div>
      <div className={`status-card${activeAlerts > 0 ? " alert" : ""}`}>
        <div className="label">Active alerts (72h)</div>
        <div className="value">{activeAlerts}</div>
        <div className="card-detail">{activeAlerts ? "Review recommended actions" : "No action needed"}</div>
      </div>
      </div>
    </section>
  );
}
