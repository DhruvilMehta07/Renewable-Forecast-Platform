# Sprint 4 — Frontend: React dashboard

## Design choices, not defaults

Built for a grid-operator monitoring tool, not a generic SaaS product — the
frontend-design skill's guidance was to ground choices in the actual subject
matter rather than reach for defaults. Concretely:

- **Dark, control-room palette** (`#0d1420` base) rather than a light SaaS
  theme — this is meant for extended monitoring, not a marketing page.
- **Night shading on the chart is real signal, not decoration** — it's drawn
  directly from `is_daytime`, the same field the decision engine uses, so a
  viewer can visually correlate "why is there a flag here" with "it's dusk."
- **IBM Plex Mono is used only for numeric readouts** (predicted values,
  timestamps), not as a decorative label style — digit alignment genuinely
  helps when scanning many numbers fast, which is the actual task here.
- **No generic gradient stat cards.** The status strip is plain
  bordered panels with a large mono number — closer to an instrument readout
  than a marketing metric card.

## Architecture

```
frontend/src/
  api.js                     fetch wrappers for /forecast, /feature-importance, /history
  App.jsx                    top-level layout, data loading, error/loading states
  index.css                  design tokens (CSS variables) + base styles
  components/
    StatusStrip.jsx          next-hour / 72h-peak / active-alert-count readouts
    ForecastChart.jsx        band + line chart, night shading, decision-flag markers
    AlertsPanel.jsx          list of flagged hours
    ImportancePanel.jsx      feature importance bar chart, from the live model
```

`VITE_API_BASE_URL` (see `.env.example`) points at the backend — defaults to
`http://localhost:8000`, overridable without a code change once Sprint 6
deploys the backend somewhere else.

The live `/forecast` and `/feature-importance` responses are produced by the
Optuna-tuned LightGBM model. The XGBoost artifact remains stored as a
benchmark/fallback and does not change the frontend response contract.

The dashboard provides two modes:

- **Plant 1:** the default validated mode using fixed Plant 1 coordinates,
  calibrated intervals, and the live LightGBM model.
- **What-if site:** accepts latitude, longitude, and capacity in kW, fetches
  location-specific weather, and displays a capacity-scaled estimate. The UI
  labels this result as approximate because the model was trained on Plant 1,
  not arbitrary sites.

## Verified live, and real bugs found + fixed

The dashboard was verified rendering correctly against the real backend
(status strip, chart, alerts, importance panel all populated with values
matching the API directly). That surfaced one genuine bug, not just polish:

**Tooltip desync.** The alert-marker `Scatter` series used its own separately
filtered `data` array (`alertPoints`, ~4 rows) instead of sharing the same
array as the other series. Recharts synchronizes tooltip hover position
across all series in a chart by matching index into each series' `data` —
a differently-sized child array desyncs that shared index, so the tooltip
locked onto the wrong row regardless of actual cursor position ("shows 0 at
every point" was this, not a data problem). Fixed by moving the alert flag
onto the same shared array as everything else (`alertMarker: decision !==
"normal" ? predicted_ac_power : null`), which is also the standard Recharts
pattern for exactly this kind of multi-series chart. Switched the x-axis to
`type="category"` at the same time — more reliable per-index hover tracking
than `type="number"` for a chart mixing dense and sparse series.

A second, smaller bug in the same component: `\u2013` (en dash) was written
directly in JSX text, where escape sequences are never interpreted — it
printed as the literal 6 characters instead of a dash. Fixed by wrapping it
in a JS expression (`{"\u2013"}`), which JSX does evaluate.

## Running it

```bash
cd backend && uvicorn main:app --reload      # terminal 1
cd frontend && npm install && npm run dev    # terminal 2
```

Then open the printed local URL (typically `http://localhost:5173`).
