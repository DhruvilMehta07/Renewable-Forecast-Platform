function formatTime(iso, timezone) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: timezone || undefined,
  });
}

function power(value) {
  return `${Math.round(value).toLocaleString()} kW`;
}

const ACTIONS = {
  curtail: "Curtailment",
  backup_dispatch: "Backup dispatch",
  normal: "Normal",
};

export default function ForecastTable({ forecast, timezone, capacity }) {
  return (
    <div className="forecast-table-wrap">
      <table className="forecast-table">
        <caption>Hourly renewable generation forecast</caption>
        <thead>
          <tr>
            <th scope="col">Target time</th>
            <th scope="col">Expected output</th>
            <th scope="col">Possible range</th>
            <th scope="col">Capacity use</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {forecast.map((row) => {
            const utilization = capacity ? Math.round((row.predicted_ac_power / capacity) * 100) : null;
            return (
              <tr key={row.target_time}>
                <td>{formatTime(row.target_time, timezone)}</td>
                <td className="table-number">{power(row.predicted_ac_power)}</td>
                <td>{power(row.lower_bound)} - {power(row.upper_bound)}</td>
                <td>{utilization === null ? "-" : `${utilization}%`}</td>
                <td><span className={`action-tag ${row.decision}`}>{ACTIONS[row.decision]}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
