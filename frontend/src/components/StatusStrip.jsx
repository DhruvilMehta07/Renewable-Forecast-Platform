function fmt(n) {
  return Math.round(n).toLocaleString();
}

export default function StatusStrip({ forecast }) {
  const nextHour = forecast[0];
  const peak = forecast.reduce((max, row) => (row.predicted_ac_power > max.predicted_ac_power ? row : max), forecast[0]);
  const activeAlerts = forecast.filter((row) => row.decision !== "normal").length;

  return (
    <div className="status-strip">
      <div className="status-card solar">
        <div className="label">Next hour</div>
        <div className="value">
          {fmt(nextHour.predicted_ac_power)}
          <span className="unit">kW</span>
        </div>
      </div>
      <div className="status-card solar">
        <div className="label">Peak in next 72h</div>
        <div className="value">
          {fmt(peak.predicted_ac_power)}
          <span className="unit">kW</span>
        </div>
      </div>
      <div className={`status-card${activeAlerts > 0 ? " alert" : ""}`}>
        <div className="label">Active alerts (72h)</div>
        <div className="value">{activeAlerts}</div>
      </div>
    </div>
  );
}
