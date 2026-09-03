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
| Oktav | Continuous `difficulty_numeric` | `ridge_regression` | `yan2023_observed` | `r2 = 0.5204`, `pearson = 0.7345`, `spearman = 0.6342`, `mae = 6.61` | Best completed Oktav regression run currently present in the checkout. |
| Oktav | Continuous `difficulty_numeric` | `dummy_regression` | `yan2023_observed` | `r2 = -0.0020` | Baseline for the same feature set. |
| Oktav | 3-bin quantiles | `random_forest_classifier` | `runtime_all` | `balanced_accuracy = 0.5607` | Broad runtime family with classification target. |
| Oktav | 3-bin quantiles | `logistic_regression` | `runtime_all` | `balanced_accuracy = 0.5427` | Same target, linear classifier. |
| Oktav | 3-bin quantiles | `dummy_classifier` | `runtime_all` | `balanced_accuracy = 0.3333` | Chance baseline for three bins. |
| CIPI | Continuous Henle-linked rating | `random_forest_regression` | Yan-style feature set | `r2 = 0.6627` | Strongest currently visible CIPI regression result. |
| CIPI | Continuous Henle-linked rating | `ridge_regression` | Yan-style feature set | `r2 = 0.6407` | Linear baseline is also strong. |
| CIPI | 3-bin target | `random_forest_classifier` | Yan-style feature set | `balanced_accuracy = 0.6229` | Strong multiclass result. |
| CIPI | 3-bin target | `logistic_regression` | Yan-style feature set | `balanced_accuracy = 0.6213` | Nearly identical to the random forest classifier. |
| CIPI | 3-bin target | `dummy_classifier` | Yan-style feature set | `balanced_accuracy = 0.3333` | Chance baseline. |
| Oktav | 3-bin target | `random_forest_classifier` | Yan-style feature set | `balanced_accuracy = 0.5607` | Stronger than linear classifier on the same general task family. |

## Feature Set Coverage

| Feature set | Regression runs observed | Classification runs observed | Best current signal | Still missing |
| --- | --- | --- | --- | --- |
| `yan2023_observed` | Yes | Yes | Oktav ridge regression `r2 = 0.5204`; CIPI random forest regression `r2 = 0.6627` | More direct comparisons across the same target scheme |
| `runtime_all` | Yes | Yes | Oktav random forest classifier `balanced_accuracy = 0.5607` | Clean comparison against `runtime_no_expression` and family-specific subsets |
| `og_php` | Yes | No clear completed result in the current artifact set | Supportive as a legacy baseline, but not enough evidence here for a best model claim | More documented completed runs |
| `sebastien_clustering` | Yes | Yes | CIPI / Oktav comparisons show it is competitive on binned tasks | Need a tighter comparison against runtime families on the same matrix |
| `rhythm_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `leaps_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `texture_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `coordination_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `notation_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `expression_only` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Complete at least one regression and one classification run |
| `runtime_no_expression` | Not yet documented in a completed artifact | Not yet documented in a completed artifact | Unknown | Compare against `runtime_all` to isolate expression contribution |
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
| `runtime_no_expression` vs `runtime_all` on Oktav | isolates whether expression features contribute beyond the rest of the runtime families | Not yet run here |
| `rhythm_only` on Oktav regression | checks how far rhythm alone gets you | Not yet run here |
| `leaps_only` on Oktav regression | checks the strength of movement-related features alone | Not yet run here |
| `texture_only` on Oktav regression | checks the strength of simultaneity / vertical-density features alone | Not yet run here |
| `coordination_only` on Oktav regression | checks whether hand-independence features matter on their own | Not yet run here |
| `notation_only` on Oktav regression | tests whether reading complexity carries independent signal | Not yet run here |
| `expression_only` on Oktav regression | tests whether articulation and dynamics matter independently | Not yet run here |
| `og_plus_runtime` on Oktav and CIPI | tests whether legacy aggregate features add anything beyond the runtime families | Not yet run here |
| `runtime_all` with `ridge_classifier` | gives a linear classification comparison to logistic regression | Not yet run here |
| `runtime_all` with `elasticnet` | tests sparse regression on the broad feature set | Not yet run here |
| `runtime_all` with `gradient_boosting_regression` | tests a stronger nonlinear regressor | Not yet run here |
| `yan2023_observed` on Henle 9-bin Oktav | fills the currently missing main summary gap | Placeholder only |

## Working Interpretation

- The current evidence says broad score-feature bundles are predictive.
- Ridge regression is already strong on Oktav.
- Random forests are strong on both regression and classification tasks.
- The dummy baselines behave as expected, so the current gains are not trivial.
- The most important missing work is family-level ablation, especially for the
  runtime family and the Yan-observed bundle.

## Where This Should Live

Keep this under `docs/` so it stays alongside:

- `docs/difficulty_theory_matrix.md`
- `docs/core_feature_registry.md`
- `docs/yan2023_feature_inventory.md`
- `docs/analysis_lanes.md`

That keeps the theory, the feature definitions, and the supervised evidence in
one place without mixing them into runtime or artifact directories.
