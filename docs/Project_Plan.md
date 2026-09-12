# Project Plan — AI-Powered Renewable Generation Forecasting Platform

**Team:** The Final Commit | **Event:** HackOut 2026 (Synapse) | **College:** Dhirubhai Ambani University

## Objective
Forecast 24–72hr solar/wind generation per site and recommend grid actions (curtail / dispatch storage / activate backup) via a three-layer system: forecasting → decision engine → dashboard. Full original concept: see `docs/Ideation_Report.pdf`.

## Build constraints
Built solo (Ayush) with an AI pair (Claude) in ~1.5–2 days. Scope is deliberately smaller than the original ideation report — the goal is one fully working, deployed slice rather than a partially-built full system.

## In scope
- 1 solar site + 1 wind site (2nd site only once the 1st is fully working end-to-end)
- Historical data: Kaggle solar/wind generation datasets
- Live weather: Open-Meteo API (free, no key required, gives 24–72hr forecast variables)
- Models: linear regression baseline → XGBoost (single model choice, no LightGBM/Prophet bake-off)
- Uncertainty: residual-based prediction intervals
- Decision engine: rule-based thresholds (forecast vs. capacity/demand)
- Dashboard: forecast chart with confidence band, alert panel, feature importance panel
- Deployment: frontend (Vercel/Netlify) + backend (Render/Railway) + SQLite

## Out of scope → Future Scope (documented, not built this round)
- Multi-region / multi-site generalization
- LightGBM/Prophet comparison, LSTM/Transformer stretch model
- Real market price signals feeding the decision engine
- Satellite-imagery sub-hour nowcasting
- Airflow/cron scheduled retraining
- Learned policy replacing rule-based thresholds

## Tech Stack
| Layer | Tech |
|---|---|
| Data / Modeling | Python, Pandas, scikit-learn, XGBoost |
| Weather | Open-Meteo API |
| Backend | FastAPI, SQLite |
| Frontend | React, Recharts |
| Deploy | Vercel/Netlify (frontend), Render/Railway (backend) |

## Sprint Plan (sequential — solo + Claude)
| Sprint | Focus | Tasks | Deliverable | Est. hrs |
|---|---|---|---|---|
| 0 | Setup | Repo, folders, docs skeleton | Skeleton pushed | 1 |
| 1 | Data + Features | Clean/align Kaggle data; engineer features (solar elevation angle, cloud cover trend, wind shear, lag features, rolling averages) for 1 site | Feature-ready dataset | 3–4 |
| 2 | Modeling | Linear regression baseline → XGBoost; log MAPE/RMSE/MAE; feature importance; prediction intervals | Trained model + metrics | 3–4 |
| 3 | Backend | FastAPI endpoints; rule-based decision engine; SQLite persistence; wire to model | Working API returning forecast + decision | 3–4 |
| 4 | Frontend | React dashboard: forecast chart w/ band, alert panel, feature importance panel | Working local dashboard hitting real API | 4–5 |
| 5 | 2nd site (stretch) | Repeat pipeline for the wind site if ahead of schedule | 2-site demo | 2–3 |
| 6 | Deploy | Push frontend + backend live; cache fallback for weather API calls | Live public link | 2 |
| 7 | Docs + Pitch | Full README rewrite, screenshots, architecture diagram, pitch deck, demo rehearsal, backup video | Submission-ready repo + deck | 3–4 |
| 8 | Buffer | Bug bash on the deployed link (fresh browser), early submit | Clean submission | 2 |

**Total: ~23–29 hrs** — fits 1.5–2 days accounting for sleep.

## Definition of Done
- [ ] At least 1 site: live weather → forecast w/ confidence band → decision flag → shown on the deployed dashboard
- [ ] README with architecture diagram, setup steps, screenshots, limitations, future scope
- [ ] Backup demo video recorded
- [ ] Pitch deck ready