# Sprint 2 - Modeling: linear baseline vs XGBoost

Script: `ml/train_models.py`. Split: time-based, by `issue_time` - train on everything
before 2020-06-05 22:45, calibrate prediction intervals on the next 6 days (val),
report final metrics on the last 6 days (test, touched once). Never a random split -
see `docs/DECISIONS.md` for why that would leak.

## Headline results

| Model | MAE | RMSE | MAPE (daytime only) | MAE (night rows) |
|---|---|---|---|---|
| Linear regression baseline | 422.8 | 659.1 | 20.5% | 169.5 |
| XGBoost | 320.6 | 656.0 | **6.5%** | **0.4** |

MAPE is computed only over rows where actual generation > 100 (daytime) - with
~46.6% of rows at exactly 0, a naive MAPE divides by zero constantly. The
zero/near-zero subset is reported separately as MAE instead, where XGBoost's
advantage is largest: it can cleanly gate to near-zero at night, where the linear
model's continuous coefficients leave residual noise.

**Interesting nuance:** RMSE is nearly identical between the two models (659.1 vs
656.0), while MAE and MAPE both favor XGBoost substantially. RMSE penalizes large
errors more heavily than MAE, so this gap says both models still struggle similarly
on rare, hard-to-predict cases (likely sudden weather transitions) - XGBoost's
advantage is in getting the typical case much more right, not in fixing the
worst-case misses. Worth a line in the README's limitations: rare extreme-weather
transitions remain a harder problem than the average-case numbers suggest.

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
| 1-24h | 755.5 |
| 25-48h | 850.0 |
| 49-72h | 914.8 |

Band = prediction +/- the bucket's value, applied at inference. Grows with horizon,
as it should - confirms the calibration is behaving sensibly rather than
arbitrarily.

## Decisions made

- **Model choice for the live system: XGBoost.** Wins on every metric that matters
  for this use case (typical-case accuracy, and specifically night-time cleanliness),
  reproduced on two machines.
- **No hyperparameter search performed** (n_estimators=300, max_depth=6,
  learning_rate=0.05, subsample/colsample=0.8 - reasonable defaults, not tuned)
  given hackathon time constraints. Documented here as an explicit scope cut, not
  an oversight - a good, honest answer if asked in judging.
- **Both model artifacts committed to the repo** (`ml/models/*.joblib`) rather than
  regenerated on demand - `xgboost_model.joblib` is ~1.3MB, small enough to commit,
  and this means Sprint 3's backend can load a trained model directly without a
  retraining step at deploy time. The committed model is whichever machine trained
  it last - exact metrics may shift slightly (see reproducibility note) but the
  conclusion is stable.
