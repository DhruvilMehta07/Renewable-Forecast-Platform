function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short", hour: "numeric", minute: "2-digit",
  });
}

const LABELS = {
  curtail: "Curtailment recommended",
  backup_dispatch: "Backup dispatch recommended",
};

export default function AlertsPanel({ forecast }) {
  const alerts = forecast.filter((row) => row.decision !== "normal");

  return (
    <div className="panel">
      <h2>Alerts</h2>
      <p className="panel-note">Hours where forecast generation crosses a capacity threshold during daylight.</p>
      {alerts.length === 0 ? (
        <p className="empty-state">No alerts in the next 72 hours.</p>
      ) : (
        <ul className="alerts-list">
          {alerts.map((row) => (
            <li key={row.target_time} className={`alert-row ${row.decision}`}>
              <span className="time">{formatTime(row.target_time)}</span>
              <span className="type">{LABELS[row.decision]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
