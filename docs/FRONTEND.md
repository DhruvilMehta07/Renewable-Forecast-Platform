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
   App.jsx                    auth gate, dashboard layout, data loading, states
   components/AuthScreen.jsx  login and account creation experience
  index.css                  design tokens (CSS variables) + base styles
  components/
    StatusStrip.jsx          next-hour / peak / window / alert summary readouts
    ForecastChart.jsx        band + line chart, night shading, readable time ticks
    ForecastTable.jsx        exact hourly values, ranges, utilization, and actions
    UtilizationChart.jsx     expected output as a percentage of site capacity
    ComparisonPanel.jsx      changes from the previous saved forecast run
    ModelGuide.jsx           plain-language interpretation guide
    AlertsPanel.jsx          flagged hours with threshold explanations
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
  location-specific weather, and displays a capacity-scaled estimate. In the
  actual UI, users search for a city, landmark, area, or country; they select a
  geocoded result rather than entering coordinates manually. The UI labels the
  result as approximate because the model was trained on Plant 1, not arbitrary
  sites.

## Dashboard capabilities

The dashboard includes these user-facing workflows:

1. **Forecast summary:** next-hour output, 72-hour peak, forecast window, and
   active alert count, with capacity use where available.
2. **Chart and table views:** the chart shows trends and uncertainty; the table
   provides exact hourly output, range, capacity use, and recommended action.
3. **Time-window controls:** focus on the next 24, 48, or 72 hours for readable
   mobile views and short-term planning.
4. **CSV export:** download the selected window with local-time timestamps,
   power bounds, daylight state, and decision flags.
5. **Capacity utilization:** see expected generation as a percentage of the
   selected site's capacity.
6. **Action explanations:** alerts explain the 90% curtailment and 10% daytime
   backup-dispatch thresholds in plain language.
7. **Timezone and freshness context:** the header shows forecast mode, issue
   time, site timezone, and time since the dashboard refreshed.
8. **Forecast comparison:** after two saved runs, compare same-horizon output
   changes, largest change, and materially changed hours.
9. **Interpretation help:** legends, help controls, feature-importance wording,
   and a forecast guide explain the dashboard without requiring ML knowledge.

The browser locale controls display formatting, while the selected site's
timezone is applied to forecast timestamps and CSV export when available.

## First-time user workflow

The public screen introduces GreenCast before asking for credentials. A user can
create an account with a display name, unique username, and password of at
least eight characters. After signup or login, the frontend stores the returned
bearer session locally, validates it with `/auth/me` on reload, and sends the
token with every protected dashboard request. Sign out removes the stored
session and returns to the public screen.

The dashboard is intentionally organized in reading order: forecast status,
site mode, display controls, primary chart or exact-value table, capacity
utilization, recommended actions, saved-run comparison, feature importance,
and the forecast guide. This lets a first-time user move from "what is
happening" to "what should I do" to "why did the model decide that".

## Feature usage

- **Chart/table:** use `Chart` for trends and uncertainty; use `Table` for
   exact hourly values, possible ranges, capacity use, and actions.
- **24/48/72-hour controls:** shorten the window to focus on immediate planning
   or keep all 72 hours for broader scheduling.
- **CSV export:** downloads the currently selected window with site-local
   timestamps and the same forecast fields shown in the table.
- **Capacity utilization:** divides predicted output by the selected capacity;
   it is an operating-context metric, not an additional model prediction.
- **Alert explanations:** connect each `curtail` or `backup_dispatch` marker to
   the threshold that triggered it. Alerts are only generated during daytime.
- **Timezone/freshness:** timestamps use the selected site's timezone when the
   API provides one, and the header reports when the current browser session
   refreshed its data.
- **Forecast comparison:** compares same-horizon rows only. Plant 1 runs are
   compared with Plant 1; What-if runs must match location and capacity.
- **Model guide and importance:** explain the uncertainty band, action flags,
   and relative feature influence without presenting feature importance as
   physical causation.

## Authentication experience

The application opens on a public GreenCast welcome screen. Users can submit an
access request with a display name, unique username, six-digit employee ID, and
password of at least eight characters. Signup returns a pending confirmation,
not a session. An administrator uses the separate Admin login to approve or
reject requests. Only approved employees can use User login.

After login, the API returns an expiring bearer token; the frontend stores the
session locally, validates it on reload, sends it with dashboard requests, and
clears it on sign out. Admin sessions open the request console rather than the
forecast dashboard.

The forecast dashboard and all saved-run data are unavailable until approved
user login.
What-if site settings, forecast tables, CSV export, utilization, alerts,
comparison, and model guidance remain available after authentication exactly as
before. The frontend does not store or inspect the password after submission.

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
