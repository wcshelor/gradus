# Difficulty Prediction Matrix

This document summarizes the supervised experiments we have actually run and
leaves explicit room for the experiments we have not run yet.

## Read This First

- Rows are model families or run families.
- Columns are feature sets or target schemes.
- Values record the best observed evidence currently present in this checkout.
- Empty cells mean the run has not been completed here yet.

## Observed Results

| Dataset | Target scheme | Model family | Feature set | Observed result | Notes |
| --- | --- | --- | --- | --- | --- |
| Oktav | Continuous `difficulty_numeric` | `ridge_regression` | `yan2023_observed` | `r2 = 0.5204`, `pearson = 0.7345`, `spearman = 0.6342`, `mae = 6.61` | Yan bundle still the strongest Oktav regression; retained for reference. |
| Oktav | Continuous `difficulty_numeric` | `dummy_regression` | `yan2023_observed` | `r2 = -0.0020` | Baseline for Yan feature set. |
| Oktav | Continuous `difficulty_numeric` | `ridge_regression` | `runtime_all` | `r2 = -0.3656`, `pearson = 0.4946`, `spearman = 0.5863`, `mae = 8.65`, `rmse = 15.85` | Repo-native runtime_all underfits with full 99-feature bundle (see no_expression). Run `oktav/20260916T204038Z__oktav-runtime-ridge-regression`. |
| Oktav | Continuous `difficulty_numeric` | `ridge_regression` | `runtime_no_expression` | `r2 = 0.3945`, `pearson = 0.6847`, `spearman = 0.6158`, `mae = 7.41`, `rmse = 10.55` | Removing 24 expression features restores signal; best repo-native Oktav regression here. Run `oktav/20260916T204058Z__oktav-runtime-no-expression-ridge-regression`. |
| Oktav | Continuous `difficulty_numeric` | `dummy_regression` | `runtime_all` | `r2 = -0.0053` | Baseline for repo-native Oktav. |
| Oktav | 3-bin quantiles | `random_forest_classifier` | `runtime_all` | `balanced_accuracy = 0.5927`, `macro_f1 = 0.5886` | Repo-native best 3-bin Oktav. Run `oktav/20260916T204048Z__oktav-runtime-rf-3bin`. |
| Oktav | 3-bin quantiles | `logistic_regression` | `runtime_all` | `balanced_accuracy = 0.5362`, `macro_f1 = 0.5338` | Linear classifier lift +0.20 over dummy. Run `oktav/20260916T204047Z__oktav-runtime-logreg-3bin`. |
| Oktav | 3-bin quantiles | `dummy_classifier` | `runtime_all` | `balanced_accuracy = 0.3333` | Chance baseline. |
| Oktav | 3-bin quantiles | `logistic_regression` | `leaps_only` | `balanced_accuracy = 0.5264` | Family ablation best signal (tie texture). |
| Oktav | 3-bin quantiles | `logistic_regression` | `texture_only` | `balanced_accuracy = 0.5263` | Vertical-density signal. |
| Oktav | 3-bin quantiles | `logistic_regression` | `coordination_only` | `balanced_accuracy = 0.5208` | Hand-independence signal. |
| Oktav | 3-bin quantiles | `logistic_regression` | `rhythm_only` | `balanced_accuracy = 0.4907` | Rhythm alone weaker than full bundle. |
| Oktav | 3-bin quantiles | `logistic_regression` | `notation_only` | `balanced_accuracy = 0.4494` | Reading complexity weakest alone. |
| CIPI | Continuous Henle (1–9) | `ridge_regression` | `runtime_all` | `r2 = -2.7630`, `pearson = 0.2980`, `spearman = 0.7319`, `mae = 1.20`, `rmse = 3.63` | Good rank correlation, poor calibration; outliers inflate RMSE. Run `cipi/20260916T204039Z__cipi-runtime-ridge-regression`. |
| CIPI | Continuous Henle | `ridge_regression` | `runtime_no_expression` | `r2 = -3.7117`, `pearson = 0.2545`, `spearman = 0.7260` | Expression removal worsens fit slightly. |
| CIPI | Continuous Henle | `dummy_regression` | `runtime_all` | `r2 = -0.0037` | Baseline. |
| CIPI | 3-bin quantiles | `logistic_regression` | `runtime_all` | `balanced_accuracy = 0.5967`, `macro_f1 = 0.5958` | Strong repo-native 3-bin CIPI (+0.263 over dummy). Run `cipi/20260916T204050Z__cipi-runtime-logreg-3bin`. |
| CIPI | 3-bin quantiles | `dummy_classifier` | `runtime_all` | `balanced_accuracy = 0.3333` | Chance baseline. |
| CIPI | 9-bin Henle (`custom_bins:9`) | `logistic_regression` | `runtime_all` | `balanced_accuracy = 0.2893`, `macro_f1 = 0.2884`, `off_by_one = 0.773` | 9-bin lift +0.178 over dummy 0.111. Run `cipi/20260916T204050Z__cipi-runtime-logreg-9bin`. |
| CIPI | 9-bin Henle | `dummy_classifier` | `runtime_all` | `balanced_accuracy = 0.1111` | Chance 1/9. |
| CIPI (reference) | Continuous Henle | `random_forest_regression` | `yan2023_observed` | `r2 = 0.6627` | Yan bundle reference (not repo-native). |
| CIPI (reference) | Continuous Henle | `ridge_regression` | `yan2023_observed` | `r2 = 0.6407` | Yan linear baseline. |

See `tests/artifacts/difficulty_prediction/label_validation_summary.csv:1` for machine-readable summary (19 runs) and `docs/difficulty_label_validation.md:1` for full validation narrative.

## Feature Set Coverage

| Feature set | Regression runs observed | Classification runs observed | Best current signal | Still missing |
| --- | --- | --- | --- | --- |
| `yan2023_observed` | Yes | Yes | Oktav ridge regression `r2 = 0.5204`; CIPI random forest regression `r2 = 0.6627` | More direct comparisons across the same target scheme |
| `runtime_all` | Yes (2026-09-16) | Yes (2026-09-16) | Oktav `r2 = -0.37` (all) / `0.39` (no_expr) and `bal_acc = 0.593` (RF 3-bin); CIPI `r2 = -2.76` but spearman 0.73 and `bal_acc 0.597` (3-bin), `0.289` (9-bin) | Calibrated regression and non-linear regressor |
| `og_php` | Yes | No clear completed result in the current artifact set | Supportive as a legacy baseline, but not enough evidence here for a best model claim | Document repo-native vs og on same matrix |
| `sebastien_clustering` | Yes | Yes | CIPI / Oktav comparisons show it is competitive on binned tasks | Need a tighter comparison against runtime families on the same matrix |
| `rhythm_only` | Not yet on regression | Yes (`bal_acc 0.4907` logreg 3-bin) | Rhythm alone mid signal | Regression run |
| `leaps_only` | Not yet on regression | Yes (`bal_acc 0.5264` logreg 3-bin) | Strong movement signal alone | Regression run |
| `texture_only` | Not yet on regression | Yes (`bal_acc 0.5263` logreg 3-bin) | Strong simultaneity signal | Regression run |
| `coordination_only` | Not yet on regression | Yes (`bal_acc 0.5208` logreg 3-bin) | Strong hand-independence | Regression run |
| `notation_only` | Not yet on regression | Yes (`bal_acc 0.4494` logreg 3-bin) | Weakest alone | Regression run |
| `expression_only` | Yes (`r2=-0.14` ridge) | Not yet | Weak alone on Oktav | Classification run |
| `runtime_no_expression` | Yes (`r2 0.39` Oktav, `-3.71` CIPI) | Not yet on classification | Isolates expression noise/helpfulness | Classification runs |
| `og_plus_runtime` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Test whether joining legacy and runtime features helps or just adds noise |

## Model Family Coverage

| Model family | Regression | Classification | Notes |
| --- | --- | --- | --- |
| `dummy_regression` | Completed | N/A | Baseline only. |
| `ridge_regression` | Completed | N/A | Best linear regression baseline so far. |
| `random_forest_regression` | Completed | N/A | Strong nonlinear regression baseline. |
| `dummy_classifier` | N/A | Completed | Chance baseline. |
| `logistic_regression` | N/A | Completed | Strong simple classifier baseline. |
| `random_forest_classifier` | N/A | Completed | Strong nonlinear classifier baseline. |
| `gradient_boosting_regression` | Not yet run here | Not yet run here | Add once we want a more expressive tree baseline. |
| `gradient_boosting_classifier` | Not yet run here | Not yet run here | Add once we want a more expressive tree classifier. |
| `elasticnet` | Not yet run here | Not yet run here | Add if we want a sparse linear regression comparison. |
| `ridge_classifier` | Not yet run here | Not yet run here | Add if we want a linear classification comparison against logistic regression. |

## Open Experiment Slots

The following are the next most useful gaps to fill:

| Planned test | Why it matters | Status |
| --- | --- | --- |
| `runtime_no_expression` vs `runtime_all` on Oktav | isolates whether expression features contribute beyond the rest of the runtime families | **Done 2026-09-16** (`r2 0.39` vs `-0.37`) — expression adds noise for ridge on this slice |
| `rhythm_only` on Oktav regression | checks how far rhythm alone gets you | Not yet run here (classification done `0.4907`) |
| `leaps_only` on Oktav regression | checks the strength of movement-related features alone | Not yet run here (classification done `0.5264`) |
| `texture_only` on Oktav regression | checks the strength of simultaneity / vertical-density features alone | Not yet run here (classification done `0.5263`) |
| `coordination_only` on Oktav regression | checks whether hand-independence features matter on their own | Not yet run here (classification done `0.5208`) |
| `notation_only` on Oktav regression | tests whether reading complexity carries independent signal | Not yet run here (classification done `0.4494`) |
| `expression_only` on Oktav regression | tests whether articulation and dynamics matter independently | **Done** (`r2=-0.14`) — weak alone |
| `og_plus_runtime` on Oktav and CIPI | tests whether legacy aggregate features add anything beyond the runtime families | Not yet run here |
| `runtime_all` with `ridge_classifier` | gives a linear classification comparison to logistic regression | Not yet run here |
| `runtime_all` with `elasticnet` | tests sparse regression on the broad feature set | Not yet run here (would likely help calibration) |
| `runtime_all` with `gradient_boosting_regression` | tests a stronger nonlinear regressor | Not yet run here (likely to fix negative R2) |
| `runtime_no_expression` vs `runtime_all` on CIPI | same isolation on CIPI | **Done 2026-09-16** (`-3.71` vs `-2.76`) — expression slightly helps |
| `CIPI runtime_all 9-bin logreg` | tests 9-point Henle classification | **Done 2026-09-16** (`bal_acc 0.289` vs `0.111`) |
| `yan2023_observed` on Henle 9-bin Oktav | fills the currently missing main summary gap | Placeholder only |

## Working Interpretation (2026-09-16 update, see `docs/difficulty_label_validation.md:7`)

- Repo-native extracted score features show alignment with external difficulty labels on both Oktav and CIPI when evaluated as ordinal classifiers (3-bin lift +0.20–0.26, 9-bin lift +0.18 over dummy). This supports the extraction layer as difficulty-relevant.
- Continuous regression is more fragile: Oktav `runtime_all` ridge is negative R2 but becomes `r2=0.39` after removing expression features; CIPI ridge is negative R2 yet `spearman ~0.73`, indicating ranking signal but poor calibration due to sparse high-cardinality rhythm features and outliers. No hyperparameter tuning was done.
- Family ablations on Oktav 3-bin show leaps/texture/coordination each ~0.52 balanced_accuracy, rhythm 0.49, notation weakest 0.45 — no single family beats the full bundle, but several carry strong independent signal.
- Dummy baselines behave as expected, so gains are not trivial.
- This does not validate the 9-point taxonomy or any specific weighting; taxonomy weighting and learner-facing interpretation still need separate validation.

## Where This Should Live

Keep this under `docs/` so it stays alongside:

- `docs/difficulty_theory_matrix.md`
- `docs/core_feature_registry.md`
- `docs/yan2023_feature_inventory.md`
- `docs/analysis_lanes.md`

That keeps the theory, the feature definitions, and the supervised evidence in
one place without mixing them into runtime or artifact directories.
