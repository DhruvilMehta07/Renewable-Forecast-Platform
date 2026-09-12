import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "numeric" });
}

export default function UtilizationChart({ forecast, capacity }) {
  const data = forecast.map((row) => ({
    ...row,
    utilization: capacity ? Math.round((row.predicted_ac_power / capacity) * 100) : 0,
  }));

  return (
    <div className="panel utilization-panel">
      <div className="section-heading">
        <div><div className="eyebrow">Site capacity</div><h2>Capacity utilization</h2></div>
        <span className="help-tip" title="Utilization is expected generation divided by the selected site capacity." aria-label="About capacity utilization">?</span>
      </div>
      <p className="panel-note">See how much of the selected site capacity the forecast uses at each hour. This is useful for planning storage, dispatch, or curtailment.</p>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="utilizationFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#52c8b2" stopOpacity={0.32} />
              <stop offset="100%" stopColor="#52c8b2" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#263847" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="target_time" tickFormatter={formatTime} ticks={data.filter((_, i) => i % 12 === 0).map((row) => row.target_time)} stroke="#94a5af" fontSize={10} />
          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} stroke="#94a5af" fontSize={10} width={42} />
          <Tooltip
            labelFormatter={(value) => formatTime(value)}
            formatter={(value) => [`${value}%`, "Capacity use"]}
            contentStyle={{ background: "#192631", border: "1px solid #385263", borderRadius: 7, fontSize: 12 }}
          />
          <Area type="monotone" dataKey="utilization" stroke="#52c8b2" fill="url(#utilizationFill)" strokeWidth={2} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
      <div className="chart-footnote">Selected capacity: <strong>{Math.round(capacity).toLocaleString()} kW</strong></div>
    </div>
  );
}
