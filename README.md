# Renewable Forecast Platform

AI-powered platform forecasting 24–72hr solar/wind generation and recommending grid actions (curtailment, storage dispatch, backup activation). Built for **HackOut 2026** (Synapse) by team **The Final Commit**, Dhirubhai Ambani University.

Full original concept: [`docs/Ideation_Report_TheFinalCommit.pdf`](docs/Ideation_Report_TheFinalCommit.pdf)

## Status

**Sprint 3 of 8 complete.** Data pipeline, EDA, modeling, and the FastAPI backend are done. Frontend dashboard (Sprint 4) is next. Full sprint-by-sprint status: [`docs/Project_Plan.md`](docs/Project_Plan.md).

## Model performance

| Model | MAE | MAPE (daytime) |
|---|---|---|
| Linear regression baseline | 422.8 | 20.5% |
| **XGBoost** | **320.6** | **6.5%** |

Full results, feature importance, and prediction interval calibration: [`docs/MODELING.md`](docs/MODELING.md).

## How it works

1. **Offline, once:** historical solar generation + weather data → feature engineering → a horizon-aware training set → trains an XGBoost model.
2. **Live, on every request:** current + 72hr forecast weather (Open-Meteo) + computed solar position (pvlib) → assembled into the same feature shape the model was trained on → 72-hour prediction with a confidence band.
3. **Then:** a rule-based decision engine flags curtailment/dispatch/backup periods from the prediction, and a dashboard displays the forecast, alerts, and feature importance.

Full breakdown of what's used at each step: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Data

Kaggle ["Solar Power Generation Data"](https://www.kaggle.com/datasets/anikannal/solar-power-generation-data) (anikannal) — Plant 1, 15-minute intervals, 34 days. Two files: per-inverter generation, plant-level weather sensors.

## Repo structure

```
data/       raw source CSVs (generated dataset is gitignored — regenerate with the script below)
ml/         data pipeline, EDA, model training, and trained model artifacts
backend/    FastAPI service — forecast, feature importance, and history endpoints
frontend/   React dashboard (Sprint 4)
docs/       ideation report, project plan, decisions log, EDA + modeling + backend findings and figures
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 ml/build_forecast_dataset.py   # builds data/plant1_forecast_dataset.csv
python3 ml/eda.py                       # regenerates docs/eda/*.png and stats
python3 ml/train_models.py              # trains both models, saves ml/models/*.joblib

cd backend
uvicorn main:app --reload               # serves the API at http://localhost:8000
pytest tests/                           # runs the backend test suite (mocked weather, no network needed)
```

## Key decisions and limitations

Two real bugs were found and fixed during data pipeline development (timeline gaps breaking lag features, and an initial nowcast/forecast mismatch) — full writeup in [`docs/DECISIONS.md`](docs/DECISIONS.md). EDA findings (zero-inflation, multicollinearity, residual missing values) are in [`docs/EDA.md`](docs/EDA.md). Modeling results and the resolved "current state anchor" question are in [`docs/MODELING.md`](docs/MODELING.md).

Known limitations: both models show similar RMSE despite XGBoost's clear MAE/MAPE advantage — rare, sudden-weather-transition cases remain harder to predict than the average-case numbers suggest. The decision engine's capacity/demand thresholds are a practical proxy (no real grid-demand data available for this dataset), documented in [`docs/BACKEND.md`](docs/BACKEND.md).

## Future scope

Multi-site generalization, real market-price signals in the decision engine, satellite-based sub-hour nowcasting, scheduled retraining, and a learned policy replacing the rule-based decision thresholds. See `docs/Project_Plan.md` for the full in/out-of-scope list.

## License

MIT — see [`LICENSE`](LICENSE).
