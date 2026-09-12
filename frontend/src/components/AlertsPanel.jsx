function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

const LABELS = {
  curtail: "Curtailment recommended",
  backup_dispatch: "Backup dispatch recommended",
};

export default function AlertsPanel({ forecast, capacity }) {
  const alerts = forecast.filter((row) => row.decision !== "normal");

  return (
    <div className="panel">
      <div className="section-heading">
        <div><div className="eyebrow">Decision support</div><h2>Recommended actions</h2></div>
        <span className="help-tip" title="Alerts appear only during daylight when expected output crosses an operating threshold." aria-label="About alerts">?</span>
      </div>
      <p className="panel-note">Review these daylight hours where expected generation may need attention.</p>
      {alerts.length === 0 ? (
        <p className="empty-state">No alerts in the next 72 hours.</p>
      ) : (
        <ul className="alerts-list">
          {alerts.map((row) => (
            <li key={row.target_time} className={`alert-row ${row.decision}`}>
              <span className="time">{formatTime(row.target_time)}</span>
              <span className="alert-reading"><strong>{Math.round(row.predicted_ac_power).toLocaleString()} kW</strong><span className="type">{LABELS[row.decision]}</span><span className="alert-explanation">{capacity ? (row.decision === "curtail" ? `Above ${Math.round(capacity * 0.9).toLocaleString()} kW operating threshold` : `Below ${Math.round(capacity * 0.1).toLocaleString()} kW daylight threshold`) : "Crossed a daytime operating threshold"}</span></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
