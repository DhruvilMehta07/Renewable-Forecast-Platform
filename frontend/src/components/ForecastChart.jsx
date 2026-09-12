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
  return d.toLocaleString(undefined, { weekday: "short", hour: "numeric" });
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{
      background: "#1a2436", border: "1px solid #253247", borderRadius: 6,
      padding: "10px 14px", fontSize: 13, fontFamily: "IBM Plex Sans, sans-serif",
    }}>
      <div style={{ color: "#7c8798", marginBottom: 4 }}>{formatTick(row.target_time)} (+{row.horizon_hours}h)</div>
      <div className="mono" style={{ color: "#e8a33d" }}>{Math.round(row.predicted_ac_power).toLocaleString()} kW</div>
      <div className="mono" style={{ color: "#7c8798", fontSize: 11 }}>
        range {Math.round(row.lower_bound).toLocaleString()}{"\u2013"}{Math.round(row.upper_bound).toLocaleString()}
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
      <h2>72-hour generation forecast</h2>
      <p className="panel-note">Shaded band is the model's calibrated prediction interval. Darker regions are nighttime.</p>
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
            tickFormatter={(idx) => formatTick(data[idx].target_time)}
            stroke="#7c8798"
            fontSize={11}
          />
          <YAxis stroke="#7c8798" fontSize={11} width={50} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
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
        <span><span className="legend-dot" style={{ background: "#e8a33d" }} />Predicted generation</span>
        <span><span className="legend-dot" style={{ background: "#e85d4c" }} />Backup dispatch flag</span>
        <span><span className="legend-dot" style={{ background: "#e8a33d", opacity: 0.6 }} />Curtail flag</span>
      </div>
    </div>
  );
}
