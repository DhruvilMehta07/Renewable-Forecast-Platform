import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const LABELS = {
  target_is_daytime: "Is it daytime",
  target_irradiation: "Forecast sunlight",
  target_solar_elevation: "Sun angle",
  target_ambient_temp: "Forecast temperature",
  day_of_year: "Day of year",
  issue_ac_power_roll_1day: "Recent daily average output",
  horizon_hours: "How far ahead",
  issue_ambient_temp: "Current temperature",
  issue_ac_power: "Current output",
  issue_clearsky_index: "Current cloud cover",
  hour: "Hour issued",
  issue_ac_power_roll_1hr: "Recent hourly average output",
};

export default function ImportancePanel({ importance }) {
  const data = Object.entries(importance)
    .map(([key, value]) => ({ name: LABELS[key] || key, value: value * 100 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  return (
    <div className="panel">
      <div className="section-heading">
        <div><div className="eyebrow">Model transparency</div><h2>What drives the forecast</h2></div>
        <span className="help-tip" title="These percentages show relative model influence, not causation or importance in the physical system." aria-label="About feature importance">?</span>
      </div>
      <p className="panel-note">Relative influence of each input on the model's predictions. Higher bars mean the model relied on that input more often.</p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 16 }}>
          <CartesianGrid stroke="#253247" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" stroke="#7c8798" fontSize={11} tickFormatter={(v) => `${v.toFixed(0)}%`} />
          <YAxis type="category" dataKey="name" stroke="#7c8798" fontSize={12} width={160} />
          <Tooltip
            formatter={(v) => `${v.toFixed(1)}%`}
            contentStyle={{ background: "#1a2436", border: "1px solid #253247", borderRadius: 6, fontSize: 13 }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={i < 3 ? "#e8a33d" : "#3fbfad"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
