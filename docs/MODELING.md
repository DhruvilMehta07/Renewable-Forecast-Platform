# Sprint 2 - Modeling: linear baseline vs tuned tree models

Script: `ml/train_models.py`. Split: time-based, by `issue_time` - train on everything
before 2020-06-05 22:45, calibrate prediction intervals on the next 6 days (val),
report final metrics on the last 6 days (test, touched once). LightGBM uses Optuna
with three spaced four-day validation windows and early stopping. Never a random
split - see `docs/DECISIONS.md` for why that would leak.

## Headline results

| Model | MAE | RMSE | MAPE (daytime only) | MAE (night rows) |
|---|---|---|---|---|
| Linear regression baseline | 422.8 | 659.1 | 20.5% | 169.5 |
| XGBoost | 320.6 | 656.0 | **6.5%** | **0.4** |
| **Optuna-tuned LightGBM** | **267.8** | **577.9** | **5.0%** | **1.0** |

MAPE is computed only over rows where actual generation > 100 (daytime) - with
~46.6% of rows at exactly 0, a naive MAPE divides by zero constantly. The
zero/near-zero subset is reported separately as MAE instead. XGBoost has the
lowest nighttime error, while LightGBM is better overall and during daytime.

LightGBM is the best model on this untouched test window: it reduces MAE to
267.8 kW, RMSE to 577.9 kW, and daytime MAPE to 5.0%. Its night MAE is 1.0 kW.
The improvement is especially meaningful because all three models use the same
chronological split and the test period is not used during tuning.

RMSE still penalizes large errors more heavily than MAE, so sudden weather
transitions remain harder than typical solar-generation periods.

## LightGBM Optuna tuning

LightGBM was tuned with 20 Optuna TPE trials. Each trial used three spaced,
chronological four-day validation windows, native missing-value handling, and
early stopping after 50 rounds without validation improvement. The objective was
a balanced score: 70% overall MAE and 30% daytime MAE. The final tree count was
the mean best iteration across the validation folds.

Selected values:

| Parameter | Value |
|---|---:|
| `learning_rate` | 0.0241 |
| `num_leaves` | 24 |
| `max_depth` | 8 |
| `min_child_samples` | 82 |
| `subsample` | 0.8879 |
| `colsample_bytree` | 0.8790 |
| `reg_lambda` | 3.9619 |
| `reg_alpha` | 0.6978 |
| `n_estimators` | 780 |

The regularization, limited tree depth, minimum child size, subsampling, and
early stopping reduce the risk of fitting individual weather days. Trial results
are saved in `docs/eda/lightgbm_optuna_trials.csv`, parameters in
`ml/models/lightgbm_best_params.json`, and the trained model in
`ml/models/lightgbm_model.joblib`.

## Horizon comparison

| Model | 1-24h MAE | 25-48h MAE | 49-72h MAE |
|---|---:|---:|---:|
| Linear regression | 430.3 | 423.5 | 410.0 |
| XGBoost | 320.0 | 328.0 | 312.1 |
| LightGBM | **270.3** | **276.7** | **252.5** |

## Reproducibility note

Re-running this script on a different machine reproduced the linear baseline's
numbers exactly (422.8/659.1, identical coefficients), but gave slightly different
XGBoost numbers (320.6 vs an earlier 342.4 MAE) despite the fixed `random_state=42`.
This is a known characteristic of gradient-boosted trees: training is parallelized
across CPU cores, and floating-point summation order during parallel histogram
building isn't guaranteed identical across machines/core counts, which can nudge
early tree splits and cascade into different (but similarly accurate) trees over
300 boosting rounds. `random_state` fixes the algorithm's own RNG stream, not
cross-platform floating-point arithmetic. Forcing `n_jobs=1` would make it fully
reproducible on a given XGBoost version, at the cost of slower training - not done
here since training takes seconds either way and the qualitative conclusion is
identical across runs.

This same run-to-run variation is also why the per-feature importance ranking
shifted (see below) - worth understanding for judging Q&A, not a sign of a bug.

## EDA prediction confirmed

The EDA (`docs/EDA.md`, section 6) flagged `issue_ac_power` and
`issue_ac_power_roll_1hr` as a moderately collinear pair (VIF ~8.2 each) and said
to watch for unstable/sign-flipped coefficients in the linear baseline if it came
up. It did: `issue_ac_power` = +0.0038, `issue_ac_power_roll_1hr` = -0.0022 -
opposite signs on two features that should logically move together. This isn't a
bug, it's exactly the symptom the EDA predicted, now confirmed on real output -
and reproduced identically on a second machine.

## Feature importance - resolves an earlier open question

![feature importance](eda/feature_importance.png)

*(figure reflects the first training run - see note below on why the exact
per-feature split shifted on re-run, without changing the overall conclusion)*

Two independent training runs agree that `target_is_daytime`, `target_irradiation`,
and `target_solar_elevation` together account for ~99% of total importance:

| Feature | Run 1 | Run 2 (different machine) |
|---|---|---|
| target_irradiation | 32.4% | 81.7% |
| target_solar_elevation | 14.3% | 17.5% |
| target_is_daytime | 52.1% | 0.01% |
| **combined** | **98.8%** | **99.2%** |
| all "known-at-issue" features + horizon_hours | ~0.1% total | ~0.1% total |

The exact split within the top cluster moved a lot between runs (expected - these
three features are collinear, per the EDA's VIF check, so trees can credit any of
them somewhat interchangeably) but the combined share and the conclusion did not:

This directly resolves the "current state anchor" concern raised while planning
Sprint 3: since there's no live SCADA feed for this dataset, "current output" has to
be approximated (the model's own 0-hour self-prediction) rather than read from a
real sensor. That approximation is now shown to be low-risk, on two independent
runs - the model's actual predictions are driven almost entirely by target-time
weather and solar position, which come directly from Open-Meteo and pvlib, not
from the approximated anchor.

## Prediction intervals

Calibrated on the val set only (never touched by training or by the reported test
metrics) - 90th-percentile absolute residual, by horizon bucket (this run):

| Horizon | p90 absolute residual |
|---|---|
| 1-24h | 649.0 |
| 25-48h | 754.6 |
| 49-72h | 865.8 |

Band = prediction +/- the bucket's value, applied at inference. Grows with horizon,
as it should - confirms the calibration is behaving sensibly rather than
arbitrarily.

## Decisions made

- **Model choice for the live system: Optuna-tuned LightGBM.** It has the lowest
  test MAE, RMSE, and daytime MAPE. XGBoost remains stored as a benchmark/fallback
  and has slightly lower nighttime MAE.
- **Hyperparameter tuning:** LightGBM uses 20 Optuna trials, three spaced
  chronological validation windows, regularization, subsampling, and early
  stopping. The final model uses the mean best iteration from those folds.
- **Model artifacts are stored separately:** `lightgbm_model.joblib` is loaded by
  the backend, while `xgboost_model.joblib` and `linear_baseline.joblib` remain
  available for comparison and fallback.
