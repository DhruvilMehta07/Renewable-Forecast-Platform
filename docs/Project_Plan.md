# Project Plan — AI-Powered Renewable Generation Forecasting Platform

**Team:** The Final Commit | **Event:** HackOut 2026 (Synapse) | **College:** Dhirubhai Ambani University
**Build mode:** solo (Ayush) + AI pair (Claude), sequential sprints, ~1.5–2 days total.

## Objective
Forecast 24–72hr solar/wind generation per site and recommend grid actions (curtail / dispatch storage / activate backup) via a three-layer system: forecasting → decision engine → dashboard. Full original concept: `docs/Ideation_Report_TheFinalCommit.pdf`.

## Scope
**In:** 1 validated solar site plus an approximate What-if site mode · Kaggle historical data + Open-Meteo live forecast · linear regression baseline → XGBoost and Optuna-tuned LightGBM · rule-based decision engine · React dashboard · deployed live link.
**Out (documented, not built):** multi-site generalization, Prophet/LSTM comparisons, market-price signals, satellite nowcasting, scheduled retraining, learned policy. See `docs/DECISIONS.md`.

## Tech Stack
| Layer | Tech |
|---|---|
| Data / Modeling | Python, Pandas, scikit-learn, XGBoost, LightGBM, Optuna, pvlib |
| Weather | Open-Meteo API |
| Backend | FastAPI, SQLite |
| Frontend | React, Recharts |
| Deploy | Vercel/Netlify (frontend), Render/Railway (backend) |

## Sprint status

| Sprint | Focus | Status | Key output |
|---|---|---|---|
| 0 | Repo setup | ✅ Done | Repo, folders, LICENSE, initial docs |
| 1 | Data + features | ✅ Done | `ml/build_forecast_dataset.py` → `data/plant1_forecast_dataset.csv` (210,340 rows, 72 horizons). Two real bugs found and fixed — see `docs/DECISIONS.md` |
| 1.5 | EDA + validation | ✅ Done | `ml/eda.py`, `docs/EDA.md`, `docs/eda/*.png`. Confirmed zero-inflation is physical, no feature exceeds VIF 10, found + documented residual NaNs in 3 columns |
| 2 | Modeling | ✅ Done | `ml/train_models.py`. Reduced-feature, Optuna-tuned LightGBM beats the matching reduced-feature XGBoost and linear baseline (MAE 291.7 kW, daytime MAPE 5.8%). Full writeup: `docs/MODELING.md` |
| 3 | Backend | ✅ Done | FastAPI (`backend/`): `/forecast`, `/feature-importance`, `/history`. 2 real bugs caught by tests before reaching the API — see `docs/BACKEND.md` |
| 4 | Frontend | ✅ Done | React dashboard (`frontend/`): Plant 1 and What-if modes, forecast chart w/ band + night shading, alerts panel, feature importance panel. Build and live visual rendering verified — see `docs/FRONTEND.md` |
| 5 | 2nd site (stretch) | ⬜ Next | Repeat pipeline for a 2nd site if ahead of schedule |
| 6 | Deploy | ⬜ | Live public link, weather-API fallback caching |
| 7 | Docs + pitch | ⬜ | Full README rewrite, screenshots, architecture diagram, pitch deck, rehearsal, backup video |
| 8 | Buffer | ⬜ | Bug bash on deployed link, early submit |

## Definition of Done
- [ ] At least 1 site: live weather → forecast w/ confidence band → decision flag → shown on the deployed dashboard
- [ ] README with architecture diagram, setup steps, screenshots, limitations, future scope
- [ ] Backup demo video recorded
- [ ] Pitch deck ready

## Reference docs
- `docs/DECISIONS.md` — assumptions, bugs found + fixed, unit-conversion notes
- `docs/EDA.md` — distributions, multicollinearity, missing-value findings, decisions made from them
- `docs/MODELING.md` — baseline vs XGBoost results, feature importance, prediction intervals
- `docs/BACKEND.md` — API design, decision engine logic, bugs found by the test suite
- `docs/FRONTEND.md` — design choices, architecture, what still needs a visual check
