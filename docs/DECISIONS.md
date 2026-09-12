# Sprint 1 — Data & Feature Engineering: Decisions and Bugs Found

## Dataset
- Source: Kaggle "Solar Power Generation Data" (anikannal) — https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
- Site used: Plant 1, 15-minute intervals, 34 days (2020-05-15 to 2020-06-17)
- Direct CSV mirror used for scripted download: https://github.com/kaivalpanchal/Solar-Panel-Power-Generation

## Assumptions
- Approximate site location used for solar-position/clear-sky calculations: 14.5°N, 78.0°E (exact plant GPS coordinates are not published in the dataset).
- `MODULE_TEMPERATURE` is a sensor-only reading. Kept for training/feature-importance, but not usable at live inference since Open-Meteo can't forecast it.
- "Perfect prog" backtesting assumption: target-time weather features use the actual historical reading as a stand-in for "what a forecast would have said." Reported backtest accuracy will be somewhat optimistic versus live performance, since Open-Meteo's real forecast carries its own error this backtest doesn't see.

## Bugs found and fixed
1. **Timeline gaps.** 107 missing 15-minute timestamps out of 3,264 expected across 34 days. The first version of the pipeline used `.shift(N)` assuming fixed row-to-row spacing — any gap silently turned "N steps ago" into "more than N steps ago" in actual wall-clock time, with no visible symptom in the output. Fixed by reindexing to a continuous 15-min timeline (`asfreq`) before computing any shift-based feature.
2. **Nowcast vs. forecast mismatch.** The first version computed lag features and the target from the same timestamp — effectively a "what's happening right now" model, not a "what will happen 24–72h from now" model. Fixed by splitting every feature into known-at-issue-time (available the moment the forecast is issued) vs. target-time (the future point being forecast), with `horizon_hours` (1–72) as an explicit input feature, so one model handles every horizon directly.

## Verification performed
- Continuous timeline: 3,264 expected rows, 106 confirmed gap rows in `AC_POWER`.
- Horizon-aware dataset: 210,340 rows after dropping edge/gap rows, spanning 72 distinct hourly horizons.
- Alignment check: `target_time − issue_time` exactly equals `horizon_hours` — 0 mismatch across all 210k rows.
- Physics sanity check: correlation between "now" and "target" power is high at +1h (persistence), collapses at +6h (different time of day), and recovers to ~0.88–0.90 at +24h/+48h/+72h — matching the expected daily solar cycle.

## Carry-forward note for Sprint 3 (backend)
Open-Meteo's `shortwave_radiation` is in W/m²; the training data's `IRRADIATION` column is in kW/m². Divide Open-Meteo's value by 1000 before passing it to the model, or every prediction will be built on a value 1000x too large.
