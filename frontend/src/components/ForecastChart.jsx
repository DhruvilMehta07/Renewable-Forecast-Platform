import {
  ComposedChart, Area, Line, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceArea, ResponsiveContainer,
} from "recharts";

function getNightSegments(data) {
  const segments = [];
  let start = null;
  data.forEach((row, i) => {
    if (!row.is_daytime && start === null) start = i;
    if (row.is_daytime && start !== null) {
      segments.push({ x1: start, x2: i - 1 });
      start = null;
    }
  });
  if (start !== null) segments.push({ x1: start, x2: data.length - 1 });
  return segments;
}

function formatTick(iso) {
  const d = new Date(iso);
  return {
    date: d.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric" }),
    time: d.toLocaleString(undefined, { hour: "numeric", minute: "2-digit" }),
  };
}

function formatPowerTick(value) {
  return Math.round(value).toLocaleString();
}

function ForecastXAxisTick({ x, y, payload, data }) {
  const row = data[Number(payload.value)];
  if (!row) return null;
  const label = formatTick(row.target_time);
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fill="#94a5af" fontSize={10}>
        <tspan x="0" dy="12">{label.date}</tspan>
        <tspan x="0" dy="13" fill="#d7dee8">{label.time}</tspan>
      </text>
    </g>
  );
}

function formatTooltipDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{
      background: "#1a2436", border: "1px solid #253247", borderRadius: 6,
      padding: "10px 14px", fontSize: 13, fontFamily: "IBM Plex Sans, sans-serif",
    }}>
      <div style={{ color: "#d7dee8", marginBottom: 8, fontWeight: 500 }}>{formatTooltipDate(row.target_time)}</div>
      <div style={{ color: "#7c8798", marginBottom: 4 }}>Forecast at +{row.horizon_hours} hours</div>
      <div className="mono" style={{ color: "#e8a33d", fontSize: 16 }}>{Math.round(row.predicted_ac_power).toLocaleString()} kW</div>
      <div className="mono" style={{ color: "#7c8798", fontSize: 11 }}>
        Expected range: {Math.round(row.lower_bound).toLocaleString()}{"\u2013"}{Math.round(row.upper_bound).toLocaleString()} kW
      </div>
      {row.decision !== "normal" && (
        <div style={{ color: row.decision === "curtail" ? "#e8a33d" : "#e85d4c", marginTop: 4, fontWeight: 500 }}>
          {row.decision === "curtail" ? "Curtailment recommended" : "Backup dispatch recommended"}
        </div>
      )}
    </div>
  );
}

export default function ForecastChart({ forecast }) {
  // alertMarker/alertDecision live on the SAME shared array as every other
  // series (rather than a separately-filtered, shorter array) - Recharts
  // synchronizes tooltip hover position across all series' data by shared
  // index, so a differently-sized child series desyncs that index and the
  // tooltip locks onto the wrong row. This was a real bug, not cosmetic.
  const data = forecast.map((row, i) => ({
    ...row,
    index: i,
    alertMarker: row.decision !== "normal" ? row.predicted_ac_power : null,
  }));
  const nightSegments = getNightSegments(data);

  return (
    <div className="panel">
      <div className="section-heading">
        <div><div className="eyebrow">Primary signal</div><h2>Solar generation forecast</h2></div>
        <span className="chart-horizon">Next 72 hours</span>
      </div>
      <p className="panel-note">The amber line is expected output. The shaded band is the model's possible range; darker areas indicate nighttime.</p>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#253247" strokeDasharray="3 3" vertical={false} />
          {nightSegments.map((seg, i) => (
            <ReferenceArea key={i} x1={seg.x1} x2={seg.x2} fill="#0d1420" fillOpacity={0.6} strokeWidth={0} />
          ))}
          <XAxis
            dataKey="index"
            type="category"
            ticks={data.filter((_, i) => i % 12 === 0).map((r) => r.index)}
            tick={<ForecastXAxisTick data={data} />}
            stroke="#7c8798"
            height={44}
          />
          <YAxis
            stroke="#7c8798"
            fontSize={11}
            width={78}
            tickFormatter={formatPowerTick}
            label={{ value: "Power (kW)", angle: -90, position: "insideLeft", fill: "#94a5af", fontSize: 11, dy: 38 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area dataKey="upper_bound" stroke="none" fill="#3fbfad" fillOpacity={0.08} isAnimationActive={false} />
          <Area dataKey="lower_bound" stroke="none" fill="#0d1420" fillOpacity={1} isAnimationActive={false} />
          <Line dataKey="predicted_ac_power" stroke="#e8a33d" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Scatter
            dataKey="alertMarker"
            shape={(props) => {
              if (props.payload.alertMarker == null) return null;
              const color = props.payload.decision === "curtail" ? "#e8a33d" : "#e85d4c";
              return <circle cx={props.cx} cy={props.cy} r={4} fill={color} stroke="#0d1420" strokeWidth={1.5} />;
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="legend-row">
        <span><span className="legend-dot" style={{ background: "#e8a33d" }} />Expected output</span>
        <span><span className="legend-dot" style={{ background: "#3fbfad", opacity: 0.5 }} />Possible range</span>
        <span><span className="legend-dot" style={{ background: "#e85d4c" }} />Action recommended</span>
      </div>
    </div>
  );
}
