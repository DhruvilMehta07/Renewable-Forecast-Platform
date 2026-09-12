# GreenCast — Renewable Energy Forecasting Platform

GreenCast forecasts 24–72 hour solar generation and recommends grid actions
such as curtailment and backup dispatch. It combines live weather, a trained
LightGBM model, uncertainty ranges, and an explainable dashboard. Built for
**HackOut 2026** (Synapse) by team **The Final Commit**, Dhirubhai Ambani
University.

Full original concept: [`docs/Ideation_Report_TheFinalCommit.pdf`](docs/Ideation_Report_TheFinalCommit.pdf)

## Status

**Current status:** data pipeline, EDA, modeling, authenticated backend, and
the full dashboard are implemented. The live backend uses the Optuna-tuned
LightGBM model; XGBoost remains stored as a benchmark/fallback. Full sprint
status: [`docs/Project_Plan.md`](docs/Project_Plan.md).

## Model performance

| Model | MAE | MAPE (daytime) |
|---|---|---|
| Linear regression baseline | 424.3 | 19.8% |
| XGBoost | 353.9 | 8.7% |
| **Optuna-tuned LightGBM** | **291.7** | **5.8%** |

Full results, LightGBM tuning details, feature importance, and prediction interval calibration: [`docs/MODELING.md`](docs/MODELING.md).

## How it works

1. **Offline, once:** historical solar generation + weather data → feature engineering → a horizon-aware training set with nine live-consistent features → compares linear regression, XGBoost, and Optuna-tuned LightGBM.
2. **Live, on every request:** current + 72hr forecast weather (Open-Meteo) + computed solar position (pvlib) → assembled into the same feature shape the model was trained on → 72-hour prediction with a confidence band.
3. **Then:** a rule-based decision engine flags curtailment/dispatch/backup periods from the prediction, and a dashboard displays the forecast, alerts, and feature importance.

Full breakdown of what's used at each step: [`docs/DECISIONS.md`](docs/DECISIONS.md).

The GreenCast dashboard provides chart and table views, 24/48/72-hour focus
controls, CSV export, capacity utilization, alert explanations, timezone and
freshness context, saved-run comparison, and plain-language model guidance.
Access to the dashboard is protected by an administrator approval workflow,
username/password authentication, hashed passwords, expiring bearer tokens,
and user-scoped forecast history. Anyone can submit an access request, but only
approved users can sign in and see forecast data.

## User workflow

1. Open GreenCast. The public welcome screen offers **User login**, **Admin
	login**, and **Create account**.
2. Create an account with a display name, unique username, six-digit employee
	ID, and password of at least eight characters. The request is stored as
	`pending`; no dashboard token is issued.
3. An administrator signs in through **Admin login**, reviews the employee ID
	and account request, then chooses **Approve** or **Reject**.
4. After approval, the employee signs in through **User login** and the
	dashboard loads the validated Plant 1 forecast.
5. Use the dashboard controls to choose a time window, switch between chart and
	table views, inspect alerts, export CSV, and review model guidance.
5. Use **What-if site** to search for a location, select a result, enter site
	capacity, and run an approximate capacity-scaled estimate.
6. Refresh the forecast to save a new run. Matching runs can then be compared
	in the forecast history panel.
7. Use **Sign out** to clear the local session token.

The default local administrator is created automatically on first startup:

```text
Username: admin
Password: GreenCastAdmin123!
```

Change these values before shared or deployed use with
`GREENCAST_ADMIN_USERNAME` and `GREENCAST_ADMIN_PASSWORD`. Also set a strong
`GREENCAST_AUTH_SECRET`; never use the development defaults in production.

## Dashboard feature guide

| Feature | What it shows | How to use it |
|---|---|---|
| Forecast summary | Next-hour output, 72-hour peak, forecast window, and alert count | Scan the summary after loading a forecast |
| Chart view | Expected output, uncertainty band, nighttime shading, and action markers | Hover over the chart for date, time, values, and decision context |
| Table view | Exact hourly forecast values, range, capacity use, and action | Select `Table` when exact values matter |
| Time window | Next 24, 48, or 72 hours | Select `24h`, `48h`, or `72h` above the visualization |
| CSV export | Downloadable forecast data for the selected window | Select `Download CSV` |
| Capacity utilization | Expected generation as a percentage of site capacity | Review the utilization chart or table column |
| Action explanations | Why curtailment or backup dispatch was flagged | Read the explanation under each alert |
| Timezone and freshness | Site timezone, issue time, and refresh age | Check the dashboard header before interpreting timestamps |
| Forecast comparison | Change between matching saved forecast runs | Refresh at least twice in the same mode/site/capacity after approval |
| Forecast guide | Plain-language explanations of output, range, and actions | Read the guide below the model panels |

The Plant 1 view is the validated reference forecast. What-if mode is an
exploratory estimate because the model was trained on Plant 1 rather than on
every possible site.

## Data

Kaggle ["Solar Power Generation Data"](https://www.kaggle.com/datasets/anikannal/solar-power-generation-data) (anikannal) — Plant 1, 15-minute intervals, 34 days. Two files: per-inverter generation, plant-level weather sensors.

## Repo structure

```
data/       raw source CSVs (generated dataset is gitignored — regenerate with the script below)
ml/         data pipeline, EDA, model training, and trained model artifacts
backend/    FastAPI service — forecast, feature importance, and history endpoints
frontend/   React dashboard — authentication, forecast views, alerts, export, and explanations
docs/       ideation report, project plan, decisions log, and every sprint's findings/figures
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Use a long random value outside local development:
export GREENCAST_AUTH_SECRET="replace-with-a-long-random-secret"
python3 ml/build_forecast_dataset.py   # builds data/plant1_forecast_dataset.csv
python3 ml/eda.py                       # regenerates docs/eda/*.png and stats
python3 ml/train_models.py              # trains baseline, XGBoost, and tuned LightGBM

cd backend
uvicorn main:app --reload               # serves the API at http://localhost:8000
pytest tests/                           # runs the backend test suite (mocked weather, no network needed)

cd ../frontend
npm install && npm run dev              # serves the dashboard, defaults to http://localhost:5173
```

### Windows PowerShell

```powershell
cd "C:\Users\ajudi\OneDrive\Desktop\Hackout\Renewable-Forecast-Platform"
\.\venv\Scripts\Activate.ps1
$env:GREENCAST_AUTH_SECRET = "replace-with-a-long-random-secret"

# Terminal 1
cd backend
python -m uvicorn main:app --reload

# Terminal 2
cd ..\frontend
npm install
npm run dev
```

Open the frontend URL printed by Vite, usually `http://localhost:5173`.
The API documentation is available at `http://localhost:8000/docs`.

## Key decisions and limitations

Two real bugs were found and fixed during data pipeline development (timeline gaps breaking lag features, and an initial nowcast/forecast mismatch) — full writeup in [`docs/DECISIONS.md`](docs/DECISIONS.md). EDA findings (zero-inflation, multicollinearity, residual missing values) are in [`docs/EDA.md`](docs/EDA.md). Modeling results and the resolved "current state anchor" question are in [`docs/MODELING.md`](docs/MODELING.md).

Known limitations: the evaluation uses one short historical period and assumes perfect target-time weather during backtesting; rare, sudden-weather-transition cases remain harder to predict than average-case numbers suggest. The three zero-placeholder current-power features were removed from the live-consistent model; adding real SCADA later may improve performance. LightGBM is the current live model, while XGBoost remains a benchmark/fallback. What-if forecasts are approximate and do not model panel tilt, azimuth, efficiency, terrain, or technology. The decision engine's capacity/demand thresholds are a practical proxy (no real grid-demand data available for this dataset), documented in [`docs/BACKEND.md`](docs/BACKEND.md). For production deployment, replace the local SQLite setup with managed persistence, configure a strong `GREENCAST_AUTH_SECRET`, and serve the API over HTTPS.

## Future scope

Multi-site generalization, real market-price signals in the decision engine, satellite-based sub-hour nowcasting, scheduled retraining, and a learned policy replacing the rule-based decision thresholds. See `docs/Project_Plan.md` for the full in/out-of-scope list.

## License

MIT — see [`LICENSE`](LICENSE).
