export default function ModelGuide({ approximate }) {
  return (
    <div className="panel model-guide">
      <div className="section-heading"><div><div className="eyebrow">How to read this dashboard</div><h2>Forecast guide</h2></div></div>
      <div className="guide-grid">
        <div><strong>Expected output</strong><p>The model's best estimate of renewable power generation for that hour.</p></div>
        <div><strong>Possible range</strong><p>The calibrated uncertainty band around the estimate. A wider band means more uncertainty.</p></div>
        <div><strong>Recommended action</strong><p>Daylight thresholds flag unusually high output for curtailment or low output for backup dispatch.</p></div>
        <div><strong>{approximate ? "What-if estimate" : "Validated Plant 1"}</strong><p>{approximate ? "This view scales the Plant 1 model to the selected location and capacity, so use it for exploration." : "This is the validated reference site forecast using the live model and weather data."}</p></div>
      </div>
    </div>
  );
}
