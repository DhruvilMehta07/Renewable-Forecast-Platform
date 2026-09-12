# EDA — Plant 1 forecast dataset

Standard-procedure checks run on `data/plant1_forecast_dataset.csv` (210,340 rows,
72 horizons) before modeling. Script: `ml/eda.py`. Figures: `docs/eda/*.png`.
Raw numbers: `docs/eda/summary_stats.csv`, `docs/eda/vif_table.csv`.

## 1. Shape and missing values

Full horizon-stacked dataset: 210,340 rows x 15 columns.
De-duplicated per-issue-time view (horizon = 1): 3,126 rows.

**Finding not caught earlier:** the original build script only dropped rows missing
`issue_ac_power`, `target_ac_power`, `target_ambient_temp`, or `target_irradiation`.
Three other columns still carry real NaNs in the saved file:

| Column | Missing | Why |
|---|---|---|
| `issue_clearsky_index` | 97,502 (46%) | Undefined at night by construction (no clear-sky expectation to compare against) |
| `issue_ac_power_roll_1hr` | 953 | Edge effect - first hour of the dataset has no prior window |
| `issue_ac_power_roll_1day` | 1,662 | Edge effect - first day of the dataset has no prior window |
| `issue_ambient_temp` | 72 | Rare sensor gaps in the weather file |

**Decision:** leave these as native NaN for XGBoost - it handles missing values
natively via sparsity-aware split-finding, so no imputation needed there. The
linear regression baseline (Sprint 2) cannot handle NaN and will need its own
handling (row-drop or explicit imputation, e.g. fill night `clearsky_index` with 0)
- separate from the XGBoost data path, not a shared preprocessing step.

## 2. Summary statistics

**Known-at-issue features** (de-duplicated view, n=3,126 unless noted):

| Feature | mean | std | min | median | max |
|---|---|---|---|---|---|
| issue_ac_power | 6,713.1 | 8,584.6 | 0 | 888.4 | 29,150.2 |
| issue_ac_power_roll_1hr (n=3,112) | 6,719.4 | 8,387.3 | 0 | 1,090.1 | 27,573.5 |
| issue_ac_power_roll_1day (n=3,102) | 6,752.2 | **1,336.2** | 0 | 6,686.6 | 11,551.1 |
| issue_ambient_temp (n=3,125) | 25.57°C | 3.35 | 20.40 | 24.70 | 35.25 |
| issue_clearsky_index (n=1,685) | 0.632 | 0.242 | 0.007 | 0.631 | 1.5 (clipped) |

**Target-time features + target** (full dataset, n=210,340):

| Feature | mean | std | min | median | max |
|---|---|---|---|---|---|
| target_ambient_temp | 25.47°C | 3.29 | 20.40 | 24.51 | 35.25 |
| target_irradiation | 0.230 | 0.302 | 0 | 0.028 | 1.222 |
| target_solar_elevation | 8.82° | 43.57 | -56.17 | 6.15 | 85.51 |
| target_ac_power | 6,709.5 | 8,629.4 | 0 | 796.7 | 29,150.2 |

**Notable finding:** `issue_ac_power_roll_1day`'s std (1,336) is roughly 6x smaller
than `issue_ac_power` or `roll_1hr` (~8,400-8,600). A 24-hour rolling average always
blends a full day-and-night cycle together, so it converges toward a similar value
almost regardless of what time it currently is - it's capturing "overall recent
generation strength" (a slow-moving weather/seasonal signal), not "what's happening
right now." This is exactly why it came out with the lowest VIF (1.12, see section
4) despite being derived from the same underlying column as `issue_ac_power` -
it genuinely carries different information, not redundant information.

Both `target_irradiation` (mean 0.230, median 0.028) and `target_ac_power` (mean
6,709, median 797) have mean >> median - confirms the heavy right-skew visible in
the histograms (section 4), consistent with the zero-inflation from nighttime.

## 3. Discrete / categorical-like variables

- `target_is_daytime`: 113,764 daytime rows (54.1%) vs 96,576 night rows (45.9%).
  Close to, but not identical to, the 46.6% zero-generation share - the small gap
  is sunrise/sunset rows where the sun is technically up but output hasn't ramped
  up yet.
- `horizon_hours`: 72 distinct values (1-72h ahead), row counts range from 2,776
  (h=72) to 3,126 (h=1) - expected, not a bug: longer horizons lose more rows near
  the end of the 34-day window, since there's no data left to forecast 72h past a
  point that's only 71h from the dataset's end.

## 4. Distributions

![distributions](eda/distributions.png)

`target_ac_power`, `issue_ac_power`, and `target_irradiation` are all heavily
zero-inflated / right-skewed - a large spike at 0 (nighttime) with a fairly even
spread across positive daytime values. This is real physics, not a data quality
issue: 46.6% of `target_ac_power` rows are exactly 0, which matches the 46%
nighttime share from `is_daytime` almost exactly (cross-check passed).

**Decision:** no target transform (e.g. log) and no separate day/night model.
XGBoost learns the zero-generation-at-night pattern directly from
`solar_elevation` / `is_daytime`, and a log transform would need an arbitrary
offset to handle the exact zeros anyway. Single model, as planned.

## 5. Time series

![timeseries](eda/timeseries.png)

34 clean daily humps, as expected - and visibly uneven peak heights (e.g. several
days mid-June peak around 15-20k instead of the usual 25-29k). That's cloud cover
suppressing output on those days - good confirmation that weather features carry
real signal beyond a pure time-of-day baseline, which is the whole premise of
using weather forecasts rather than a naive seasonal-average forecast.

## 6. Correlation and multicollinearity (VIF)

![correlation](eda/correlation_heatmap.png)

| Feature | VIF |
|---|---|
| target_solar_elevation | 9.21 |
| issue_ac_power | 8.20 |
| issue_ac_power_roll_1hr | 8.13 |
| issue_ambient_temp | 5.20 |
| target_irradiation | 4.56 |
| target_is_daytime | 4.34 |
| hour | 2.69 |
| target_ambient_temp | 2.68 |
| issue_clearsky_index | 2.11 |
| day_of_year | 1.53 |
| issue_ac_power_roll_1day | 1.12 |
| horizon_hours | 1.03 |

Nothing crosses the VIF > 10 hard-concern threshold. Two moderate clusters, both
expected from how the features were built:
- `issue_ac_power` <-> `issue_ac_power_roll_1hr` (near-identical VIF, ~8.2) - both
  describing "recent output," and the heatmap confirms a strong pairwise correlation.
- `target_solar_elevation` <-> `target_is_daytime` <-> `target_irradiation` <-> `hour`
  - all describing where the sun is at the target time, so overlap is expected.

`horizon_hours` is essentially uncorrelated with everything (VIF 1.03) - confirms
it's a clean, orthogonal engineered feature, which is what we want from it.

**Decision:** keep every feature for XGBoost - tree ensembles aren't destabilized
by moderate collinearity the way OLS coefficients are. For the linear regression
baseline, the `issue_ac_power` / `issue_ac_power_roll_1hr` pair is the first place
to look if coefficients come out unstable or sign-flipped; drop `roll_1hr` there
first if needed. No pre-emptive drops before seeing Sprint 2's actual feature
importance output.
