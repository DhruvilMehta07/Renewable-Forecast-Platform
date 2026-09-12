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

## What was and wasn't verified in this environment

`npm run build` succeeds (594 modules, no errors) — that catches syntax and
import errors, but this sandbox has no headless browser available, so the
actual rendered output was never visually confirmed here. **This is the one
piece of Sprint 4 that still needs your eyes** — run it locally (steps below)
against the real backend and confirm the chart, band, night shading, and
alert markers actually look right, the same way you confirmed the backend
against a real Open-Meteo call in Sprint 3.

## Running it

```bash
cd backend && uvicorn main:app --reload      # terminal 1
cd frontend && npm install && npm run dev    # terminal 2
```

Then open the printed local URL (typically `http://localhost:5173`).
