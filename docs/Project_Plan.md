# Project Plan — AI-Powered Renewable Generation Forecasting Platform

**Team:** The Final Commit | **Event:** HackOut 2026 (Synapse) | **College:** Dhirubhai Ambani University
**Build mode:** solo (Ayush) + AI pair (Claude), sequential sprints, ~1.5–2 days total.

## Objective
Forecast 24–72hr solar/wind generation per site and recommend grid actions (curtail / dispatch storage / activate backup) via a three-layer system: forecasting → decision engine → dashboard. Full original concept: `docs/Ideation_Report_TheFinalCommit.pdf`.

## Scope
**In:** 1 solar site (2nd site only if time remains) · Kaggle historical data + Open-Meteo live forecast · linear regression baseline → XGBoost · rule-based decision engine · React dashboard · deployed live link.
**Out (documented, not built):** multi-site generalization, LightGBM/Prophet/LSTM comparisons, market-price signals, satellite nowcasting, scheduled retraining, learned policy. See `docs/DECISIONS.md`.

## Tech Stack
| Layer | Tech |
|---|---|
| Data / Modeling | Python, Pandas, scikit-learn, XGBoost, pvlib |
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
| 2 | Modeling | ✅ Done | `ml/train_models.py`. XGBoost beats linear baseline on every metric (MAPE 7.9% vs 20.5%). Feature importance shows target-time weather/astronomy drives ~99% of predictions. Full writeup: `docs/MODELING.md` |
| 3 | Backend | ⬜ Next | FastAPI endpoints, rule-based decision engine, SQLite persistence, Open-Meteo integration (unit-conversion note in DECISIONS.md) |
| 4 | Frontend | ⬜ | React dashboard: forecast chart w/ band, alerts panel, feature importance panel |
| 5 | 2nd site (stretch) | ⬜ | Repeat pipeline for a 2nd site if ahead of schedule |
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
