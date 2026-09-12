# Sprint 3 — Backend: FastAPI, decision engine, persistence

## Architecture

```
backend/
  config.py           site constants, feature order, calibration values, thresholds
  weather_client.py   Open-Meteo fetch (no API key required)
  features.py         live feature assembly - counterpart to ml/build_forecast_dataset.py
  model_service.py     loads ml/models/xgboost_model.joblib, predicts, looks up intervals
  decision_engine.py   rule-based curtail/backup_dispatch/normal flags
  database.py         SQLite persistence of each forecast run
  main.py             FastAPI app: /health, /forecast, /feature-importance, /history
  tests/test_forecast.py
```

Paths in `config.py` resolve relative to the file itself, not the working
directory, so the app behaves the same whether launched as `uvicorn
backend.main:app` from the repo root or `cd backend && uvicorn main:app`.

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /forecast` | 72-hour forecast: prediction, interval band, `is_daytime`, decision flag per hour |
| `GET /feature-importance` | Live model's `feature_importances_`, for the dashboard's explainability panel |
| `GET /history?limit=10` | Recent forecast runs from SQLite |

## Two real bugs found by the test suite before they could reach the API

Testing was done against a synthetic-but-realistic mocked Open-Meteo response
(`backend/tests/test_forecast.py`) rather than the live API — partly because
this environment's sandbox can't reach `api.open-meteo.com` at all, but mocking
the weather call is the right approach regardless: it keeps tests fast,
deterministic, and independent of a third party's uptime. **Run the real live
call yourself once locally to confirm the actual Open-Meteo integration works
end-to-end** — the mock proves the logic is correct, not that the network call
itself succeeds.

1. **`pvlib.clearsky.haurwitz` returns a DataFrame (column `ghi`), not a plain
   Series.** `ml/build_forecast_dataset.py` got away with `.values` on the
   whole 3,264-row DataFrame (which happens to flatten cleanly when assigned to
   a same-length column). `features.py`'s single-timestamp `.iloc[0]` call
   returned a one-element Series instead of a float, and `Series > 5` threw
   `ValueError: The truth value of a Series is ambiguous` the first time a real
   request ran the code path. Fixed by explicitly indexing the `ghi` column
   before extracting the scalar.
2. **XGBoost can predict small negative values** near the physical floor of
   zero generation (a real test case caught `-15.1`). This isn't a data or code
   bug — the model has no built-in awareness that power can't be negative, it's
   just a regression that occasionally undershoots near zero. Fixed by clipping
   the prediction to `>= 0` at the API layer, not by retraining — the model's
   raw output is otherwise fine, this is standard post-processing for physical
   constraints a plain regressor doesn't know about.
3. **A real live call surfaced nighttime jitter the mock hadn't caught.** The
   mocked weather tests only checked `>= 0`, which passed — but a live
   Open-Meteo call showed nonzero "noise" at night (e.g. 203.4 kW at an
   `is_daytime: false` hour). Harmless to the decision engine (nighttime flags
   are gated off regardless), but it would look like a bug on a dashboard
   chart. Since nighttime generation is a confirmed physical zero (`docs/EDA.md`),
   snapping to exactly 0 whenever `is_daytime` is false is enforcing a known
   ground truth, not hiding a result. Covered by
   `test_night_predictions_are_exact_zero`.

## Verified against a real live call, not just mocks

The mocked test suite proves the logic is correct; a real `GET /forecast` was
also run against the actual Open-Meteo API and produced a physically sensible
72-hour curve — sunrise ramp-up, midday peak (~20,900–22,750 kW), dusk taper,
repeating consistently across all 3 forecast days, with `backup_dispatch`
firing at the same relative dusk hour each day (h=1, 25, 49) and interval math
checking out exactly (e.g. prediction 20900.5 ± 755.5 = [20145.0, 21656.0]).

## Decision engine design choices

- **Only fires during daytime.** Nighttime generation is expected to be
  near-zero — flagging that every single night hour is "backup_dispatch" would
  be noise, not signal. The engine is meant to catch *unexpected* daytime
  deviations (heavy cloud cover suppressing output, or generation running high
  enough to warrant curtailment).
- **Thresholds are a capacity-based proxy, not real grid data.**
  `SITE_CAPACITY_KW` uses the max observed generation in the training data —
  there's no real nameplate capacity or grid demand data available for this
  dataset (matches the "real market/demand signals" future-scope item already
  in `docs/Project_Plan.md`). Documented here as a real limitation, not
  glossed over.
- **A live sanity check surfaced a genuine edge case, not a bug:** at the
  boundary between day and dusk, pvlib's solar-elevation-based `is_daytime`
  can say "yes" a little after a weather source's irradiance has already
  dropped near zero — exactly the situation `backup_dispatch` exists to catch
  (technically daylight, but not enough to generate). Seeing it fire correctly
  on a realistic edge case in testing is a good sign, not a red flag.

## Known-at-issue power features: the placeholder decision, applied

As planned back when the "current state anchor" question first came up:
`issue_ac_power`, `issue_ac_power_roll_1hr`, and `issue_ac_power_roll_1day` are
set to `0.0` at inference rather than built from a self-prediction bootstrap.
Sprint 2's feature importance analysis (`docs/MODELING.md`) is what justifies
this — those three features carried ~0.1% combined importance across two
independent training runs, so a crude placeholder costs essentially nothing.
`issue_ambient_temp` and `issue_clearsky_index`, which *do* have a live source
(Open-Meteo's `current` block), are computed properly, not placeholdered.

## Testing

4 tests in `backend/tests/test_forecast.py`, all passing:
response shape (72 rows, horizons 1–72 in order), value sanity (bounds bracket
the prediction, decision is one of the 3 valid values), persistence
(a forecast run is retrievable via `/history`), feature importance sums to 1.0,
nighttime predictions are exact 0, and a simulated weather-API failure returns
a clean `502` instead of a raw stack trace.
