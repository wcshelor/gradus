# Difficulty Label Validation — Repo-Native Extraction vs External Labels

Date: 2026-09-16
Matrices:
- `tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv`
- `tests/artifacts/cipi_dataset/python_analysis/full_run/cipi_labeled_feature_matrix.csv`

This report evaluates how well repo-native extracted score features align with external difficulty labels. Runtime extraction formulas were not changed. Experiments use the reusable harness at `tests/harness/difficulty_prediction/` with 5-fold CV (`shuffle=true`, `random_state=42`) and generated evidence under `tests/artifacts/difficulty_prediction/`.

## 1. Preflight Dataset Audits

| Dataset | Matrix path | Rows | Success / Failure | Target column | Labeled | Missing | Dup `piece_uid` | Dup `dataset_relative_path` | Feature cols (runtime prefixes) | Ready |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oktav | `tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv` | 405 | 405 / 0 | `difficulty_numeric` | 370 | 35 | 0 | 0 | 99 | Ready for supervised (370 labeled) |
| CIPI | `tests/artifacts/cipi_dataset/python_analysis/full_run/cipi_labeled_feature_matrix.csv` | 744 | 744 / 0 | `henle` | 744 | 0 | 0 | 0 | 165 | Ready |

CIPI audit `tests/artifacts/cipi_dataset/python_analysis/full_run/label_pairing_audit.json`:
- `missing_file_count=0`
- `ready_for_henle_validation=true`
- `henle_distribution: 1:15, 2:42, 3:54, 4:98, 5:137, 6:164, 7:134, 8:61, 9:39`

Oktav `difficulty_numeric` distribution (370 labeled): mean 45.78, std 13.58, range 11–76, mode 50 (48), 55 (43), 35 missing.

Feature-set handling: runner now drops columns where all entries are NaN before CV (e.g., sparse `rhythm_duration_value_ratio_*` with zero observed values) to avoid `SimpleImputer` shape mismatch; this touched 3 sparse rhythm columns on both datasets. No extraction formulas were changed.

## 2. Core Continuous-Regression (runtime_all)

| Dataset | Model | r2 | pearson | spearman | mae | rmse | lift vs dummy (r2) | Run dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oktav (`difficulty_numeric`, n=370) | `ridge_regression` (`alpha=1.0`) | -0.3656 | 0.4946 | 0.5863 | 8.65 | 15.85 | -0.36 | `tests/artifacts/difficulty_prediction/oktav/20260916T204038Z__oktav-runtime-ridge-regression` |
| Oktav | `dummy_regression` (mean) | -0.0053 | -0.097 | -0.079 | 10.81 | 13.60 | — | `.../oktav/20260916T204039Z__oktav-runtime-dummy-regression` |
| Oktav (`runtime_no_expression`) | `ridge_regression` | **0.3945** | 0.6847 | 0.6158 | 7.41 | 10.55 | +0.40 | `.../oktav/20260916T204058Z__oktav-runtime-no-expression-ridge-regression` |
| CIPI (`henle`, n=744) | `ridge_regression` | -2.7630 | 0.2980 | **0.7319** | 1.20 | 3.63 | -2.76 | `.../cipi/20260916T204039Z__cipi-runtime-ridge-regression` |
| CIPI | `dummy_regression` | -0.0037 | -0.081 | -0.083 | 1.53 | 1.88 | — | `.../cipi/20260916T204039Z__cipi-runtime-dummy-regression` |
| CIPI (`runtime_no_expression`) | `ridge_regression` | -3.7117 | 0.2545 | 0.7260 | 1.27 | 4.07 | -3.71 | `.../cipi/20260916T204059Z__cipi-runtime-no-expression-ridge-regression` |

Interpretation: On Oktav, `runtime_all` ridge with the full 99-feature bundle underperforms the dummy on R2/RMSE but retains moderate rank correlation (pearson 0.49, spearman 0.59). Removing the 24 expression-family features restores linear signal to `r2=0.39`, suggesting expression features add noise for this Oktav ridge setup rather than help. This supports the extraction layer as difficulty-relevant — the signal sharpens when the feature subset is constrained — and motivates family-level ablation. On CIPI, both ridge variants show strongly negative R2 yet high spearman (~0.73), indicating good ranking but poor absolute calibration (likely high-dimensional sparse rhythm features causing large coefficient variance without additional regularization).

All metrics are 5-fold CV aggregates; no hyperparameter tuning was performed.

## 3. Ordinal / Classification (3-bin and 9-bin)

Target schemes: `quantile_bins:3` (equal-frequency tertiles) and `custom_bins:9` with edges `[0.5,1.5,...,9.5]` and labels `1–9` for Henle (see `tests/harness/difficulty_prediction/targets.py:58`). Stratified 5-fold CV.

| Dataset | Target scheme | Model | balanced_accuracy | macro_f1 | accuracy | mean_abs_class_error | off_by_one_acc | lift vs dummy | Run dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oktav | `quantile_bins:3` | `dummy_classifier` | 0.3333 | 0.1886 | 0.3946 | 0.927 | 0.678 | — | `.../oktav/20260916T204047Z__oktav-runtime-dummy-3bin` |
| Oktav | `quantile_bins:3` | `logistic_regression` | 0.5362 | 0.5338 | 0.5541 | 0.530 | 0.916 | +0.203 | `.../oktav/20260916T204047Z__oktav-runtime-logreg-3bin` |
| Oktav | `quantile_bins:3` | `random_forest_classifier` | **0.5927** | 0.5886 | 0.6081 | 0.495 | 0.897 | +0.259 | `.../oktav/20260916T204048Z__oktav-runtime-rf-3bin` |
| CIPI | `quantile_bins:3` | `dummy_classifier` | 0.3333 | 0.2116 | 0.4651 | 0.849 | 0.685 | — | `.../cipi/20260916T204049Z__cipi-runtime-dummy-3bin` |
| CIPI | `quantile_bins:3` | `logistic_regression` | **0.5967** | 0.5958 | 0.6546 | 0.418 | 0.927 | +0.263 | `.../cipi/20260916T204050Z__cipi-runtime-logreg-3bin` |
| CIPI | `custom_bins:9` | `dummy_classifier` | 0.1111 | 0.0401 | 0.2204 | 1.493 | 0.585 | — | `.../cipi/20260916T204050Z__cipi-runtime-dummy-9bin` |
| CIPI | `custom_bins:9` | `logistic_regression` | **0.2893** | 0.2884 | 0.3387 | 0.997 | 0.773 | +0.178 | `.../cipi/20260916T204050Z__cipi-runtime-logreg-9bin` |

All classifiers produce confusion matrices at `confusion_matrix.csv` in their run dirs.

Interpretation: Repo-native extracted score features show alignment with external difficulty labels across both corpora on binned tasks. The lift over dummy is +0.20–0.26 on 3-bin and +0.18 on 9-bin, consistent across Oktav and CIPI. This supports the extraction layer as difficulty-relevant for ordinal grouping. For the 9-point Henle case, the evidence is that features rank and coarsely classify Henle levels, not that the 9-point taxonomy itself is validated.

## 4. Focused Feature-Set Comparisons

Priority `runtime_all` vs `runtime_no_expression` and Oktav family ablations (`quantile_bins:3` + `logistic_regression` unless noted):

- `runtime_no_expression` vs `runtime_all` on Oktav continuous: 0.3945 vs -0.3656 (Δ +0.76 R2). Expression family appears to add noise for ridge on this Oktav slice.
- On CIPI continuous: -3.71 vs -2.76 (both negative, but `runtime_all` slightly better — expression helps rank slightly).
- `expression_only` ridge on Oktav: `r2=-0.14, pearson=0.24` — weak alone.
- Family `logistic_regression` 3-bin on Oktav:
  - `leaps_only`: 0.5264
  - `texture_only`: 0.5263
  - `coordination_only`: 0.5208
  - `rhythm_only`: 0.4907
  - `notation_only`: 0.4494 (weakest)
  - `runtime_all` (all families): 0.5362

No single family beats the full bundle, but leaps/texture/coordination each carry substantial signal. Notation carries the least independent signal in this setup. CIPI family ablations were not run beyond `runtime_no_expression` to avoid rabbit-holing.

## 5. Comparison Tables

- Machine-readable summary: `tests/artifacts/difficulty_prediction/label_validation_summary.csv` — 19 runs, columns: dataset, target, target_scheme, feature_set, model_family, run_dir, primary_metric, r2, pearson, spearman, mae, rmse, balanced_accuracy, macro_f1, baseline_run_dir, lift_vs_baseline, etc. Generated by `tests/scripts/generate_label_validation_summary.py`.
- Error analysis: `tests/artifacts/difficulty_prediction/label_validation_errors.csv` — top overpredicted / underpredicted / largest absolute error examples for the main ridge runs (60 rows). Generated by `tests/scripts/generate_label_validation_errors.py`.

## 6. Error Analysis (Main Ridge Runs)

**Oktav `runtime_all` ridge** (`difficulty_numeric`):
- Largest absolute error: `Astronomia (Coffin Dance) - P-int MSMT OK00130` true 56 → pred -150.3 (error -206.3) — extreme underprediction.
- Top overpredicted: `Back To The Future - piano MSMT OK00072` true 57 → 142.1 (+85.1), `Vogel im Käfig - P-int` true 18 → 54.7 (+36.7). Many overpredicted cases are low-difficulty pieces (true 18–26) predicted high, suggesting the high-dimensional rhythm tail pushes predictions upward.
- Top underpredicted: `Sail - P-int` true 53 → 11.2 (-41.8), `Vogel im Käfig - beginner` true 58 → 18.8 (-39.2). Pattern: paired “beginner” vs “advanced” arrangements of same piece diverge in opposite directions, hinting arrangement effects.

**CIPI `runtime_all` ridge** (`henle`):
- Largest absolute error: `debussy brouillards` true 7 → -64.38 (error -71.38), `ravel une-barque-sur-locéan` true 8 → -32.77 (-40.77). Severe underpredictions dominated by impressionistic textures (Debussy/Ravel) with high Henle but unusual notational density.
- Top overpredicted: `schubert impromptu c-minor op90-1` true 6 → 29.92 (+23.92) — clear scale outlier (prediction outside 1–9 range), indicating unregularized ridge extrapolates beyond label range when sparse rhythm features fire.
- Median MAE is 1.20 (vs dummy 1.53) but RMSE 3.63 > dummy 1.88, confirming good typical error but catastrophic outliers inflate squared error and drive R2 negative despite spearman 0.73.

All error rows include `filename`, `dataset_relative_path`, `true label`, `predicted label`, `error`, `absolute_error`, `fold` at `label_validation_errors.csv:1`. Confusion matrices for classifiers show off-by-one accuracy >0.77–0.92, so most classification errors are adjacent bins.

## 7. Best Evidence Statement

Repo-native extracted score features show alignment with external difficulty labels on both Oktav (`difficulty_numeric`) and CIPI (`henle`). The strongest controlled evidence is ordinal: `runtime_all` logistic regression exceeds dummy by >0.20 balanced_accuracy on 3-bin tasks for both datasets (Oktav 0.536 vs 0.333, CIPI 0.597 vs 0.333) and by 0.178 on CIPI 9-bin Henle (0.289 vs 0.111). This supports the extraction layer as difficulty-relevant. For continuous targets, the signal is clearest after constraining the feature set: Oktav `runtime_no_expression` ridge achieves `r2=0.39, pearson=0.68`, while CIPI ridge achieves high rank correlation (`spearman~0.73`) despite negative R2, indicating ranking signal with calibration issues. The evidence does not validate the 9-point taxonomy as a whole, nor any weighting of its families.

## 8. Predictive Gap Experiment (2026-09-16 targeted grid)

This section closes the gap between the repo-native runtime feature matrix and the stronger old Yan-style results without rewriting core extraction (harness-first work under `tests/harness/difficulty_prediction/` and `tests/harness/yan2023/`).

**New harness capabilities:**
- Curated feature sets in `tests/harness/shared/matrix_features.py:29`: `runtime_core_no_expression`, `runtime_core_no_sparse`, `runtime_motor_texture`, `runtime_yan_overlap`, `yan2023_observed_no_blocked` (config-level selection only).
- Runtime feature hygiene flags in `tests/harness/difficulty_prediction/core.py:28` and `tests/harness/difficulty_prediction/runner.py:1`: `drop_sparse_duration_ratio` (prefix `rhythm_duration_value_ratio_`), `drop_near_zero_variance`, `max_missing_fraction`, `winsorize` (quantile capping). Defaults remain conservative; existing runs are unchanged. Hygiene is opt-in via `preprocessing:` in YAML (explicit configs like `runtime_clean_*`).
- Regularized models already supported in `tests/harness/difficulty_prediction/models.py:1`: `ridge_regression` (alpha sweep), `elasticnet`, `random_forest_regression`, `gradient_boosting_regression`.

**Yan-runtime gap diagnostic:** `tests/artifacts/difficulty_prediction/yan_runtime_feature_gap.csv` (31 rows, generated by `tests/harness/difficulty_prediction/yan_runtime_gap.py:1`) compares every `yan2023_observed` base feature to runtime analogues. Summary:
- `available` (direct analogue): `note_density` → `rhythm_note_density`, `staccato_rate` → `expression_staccato_note_ratio` (2/26).
- `partial` (proxy exists): `pitch_range`, `length`, `tempo`, `key_signature`, `playing_speed`, `polyphony_rate`, `triad/seventh/ninth`, `irregular_rhythm`, `hand_stretch/displacement` (14/26 via `metadata_*`, `pitch_geometry_*`, `texture_*`, `leaps_*`, `coordination_*`).
- `missing` (no runtime column): `pitch_mean`, `deviation_of_pitch` (std), `pitch_entropy`, `deviation_of_pitch_from_C4`, `mean/deviation_of_note_duration`, `pitch_variability`, `note_duration_variability`, `black_key_rate`, `dotted_note_rate`, `playing_speed_variation`, `distinct_stroke_rate` (11/26 high-priority per brief).
- `blocked` (needs performance/MIDI or expectancy model): `pressing_velocity_*`, `melodic_*` (5/26, deferred).
- `runtime_only` extra (no Yan counterpart): `rhythm_duration_value_ratio_*` (100+ columns on CIPI), `notation_accidental/ledger/clef`, `expression` beyond staccato, `coordination` extras, `pitch_geometry` details. These sparse/high-cardinality columns dominate variance and are the hygiene target.

**Targeted comparison grid:** 70 runs under `tests/artifacts/difficulty_prediction/comparisons/targeted_grid/` (5-fold CV, `shuffle=true`, `random_state=42`), covering regression (dummy, ridge alpha 1/10/100, elasticnet, RF) and classification (3-bin logistic/RF, CIPI 9-bin logistic/RF) across feature sets `runtime_all`, `runtime_core_no_expression`, `runtime_core_no_sparse`, `runtime_motor_texture`, `runtime_yan_overlap`, `yan2023_observed`. Machine-readable summary: `tests/artifacts/difficulty_prediction/feature_set_comparison_summary.csv` (70 rows, generated by `tests/scripts/generate_targeted_summary.py:1`).

Regression (continuous target, 5-fold CV):

| Dataset | Feature set | Preprocessing | Model | r2 | pearson | rmse | vs Yan ridge 100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Oktav | `runtime_all` (uncleaned, alpha=1) | standard | ridge | -0.366 | 0.495 | 15.85 | — |
| Oktav | `runtime_all` (uncleaned, alpha=100) | standard | ridge | 0.514 | 0.719 | 9.46 | -0.10 |
| Oktav | `runtime_all` **clean_winsor** (drop_sparse+winsor, alpha=100) | drop_sparse+winsor | ridge | **0.599** | 0.777 | 8.59 | -0.016 |
| Oktav | `runtime_core_no_expression` (alpha=100) | std | ridge | 0.575 | 0.762 | 8.84 | -0.04 |
| Oktav | `runtime_yan_overlap` (alpha=100) | std | ridge | 0.564 | 0.756 | 8.96 | -0.05 |
| Oktav | `runtime_yan_overlap` | std | RF (200, d8) | 0.599 | 0.775 | 8.58 | -0.016 |
| Oktav | `yan2023_observed` (baseline) | std | ridge 100 | **0.615** | 0.785 | 8.41 | — |
| CIPI | `runtime_all` (uncleaned, alpha=1) | std | ridge | -2.763 | 0.298 | 3.63 | — |
| CIPI | `runtime_all` (uncleaned, alpha=100) | std | ridge | -0.340 | 0.468 | 2.17 | -0.99 |
| CIPI | `runtime_all` **clean** (drop_sparse+nzv, alpha=10) | drop_sparse+nzv | ridge | **0.617** | 0.787 | 1.16 | -0.034 |
| CIPI | `runtime_all` **clean_winsor** (alpha=10) | drop_sparse+winsor | ridge | **0.628** | 0.793 | 1.14 | -0.023 |
| CIPI | `runtime_yan_overlap` (alpha=10) | std | ridge | 0.577 | 0.760 | 1.22 | -0.074 |
| CIPI | `runtime_yan_overlap` | std | RF | 0.637 | 0.799 | 1.13 | -0.014 |
| CIPI | `yan2023_observed` (baseline) | std | ridge 100 | **0.651** | 0.807 | 1.11 | — |

Classification (3-bin `quantile_bins:3`, balanced_accuracy):

| Dataset | Feature set | logreg | RF | vs Yan RF |
| --- | --- | --- | --- | --- |
| Oktav | `runtime_all` | 0.520 | 0.542 | -0.018 RF |
| Oktav | `runtime_core_no_sparse` | 0.552 | **0.577** | +0.017 |
| Oktav | `runtime_yan_overlap` | 0.513 | 0.548 | -0.011 |
| Oktav | `yan2023_observed` | 0.543 | 0.560 | — |
| CIPI | `runtime_all` | 0.609 | 0.632 | +0.015 |
| CIPI | `runtime_core_no_sparse` | 0.613 | **0.632** | +0.015 |
| CIPI | `runtime_yan_overlap` | 0.595 | 0.603 | -0.014 |
| CIPI | `yan2023_observed` | 0.577 | 0.617 | — |

CIPI 9-bin (`custom_bins` 1–9): `runtime_all` RF 0.312 vs Yan RF 0.345 (Δ -0.033); `runtime_yan_overlap` RF 0.294 vs Yan 0.345; `runtime_core_no_sparse` RF 0.304. Ordering is consistent with 3-bin and regression.

**Answers:**

1. **Does cleaning runtime features fix calibration?** Yes. Unregularized `runtime_all` ridge is miscalibrated (Oktav r2 -0.36→0.51 as alpha 1→100; CIPI r2 -2.76→-0.34). Adding hygiene (`drop_sparse_duration_ratio=True` + optional `winsorize`) plus ridge alpha 10–100 restores calibration: Oktav `runtime_all_clean_winsor` r2 0.599 (Δ +0.96 vs uncleaned alpha=1), CIPI 0.628 (Δ +3.39). The sparse `rhythm_duration_value_ratio_*` family alone contributes 20+ columns on Oktav and 100+ on CIPI with near-zero variance and high missingness; removing it via `runtime_core_no_sparse` or hygiene yields the same gain without expression removal alone. ElasticNet (alpha 0.1) on cleaned runtime gives similar (Oktav 0.504, CIPI 0.600) and RF on cleaned runtime is stable. No extraction bug was found; the gap is variance inflation from high-cardinality sparse columns plus under-regularization.

2. **Do Yan-overlap features recover old performance?** Substantially. The curated `runtime_yan_overlap` set (47 columns: `metadata_*`, `rhythm_note_density/attack/tuplet`, `pitch_geometry_*`, `leaps_*`, `texture_*`, `coordination_*`, `expression_staccato_*`) reaches ridge r2 0.564 (Oktav) and 0.577 (CIPI) and RF r2 0.599/0.637, within 0.02–0.08 of the Yan baseline `yan2023_observed` (ridge 0.615/0.651, RF 0.588/0.661). On 3-bin classification, Yan-overlap is within 0.01–0.02 of Yan. The remaining gap is attributable to the 11 missing high-priority statistical features (entropy, variability, black-key rate, duration aggregates, C4 deviation, chord typing) and blocked/MC features not yet in runtime.

3. **Which missing features should be promoted into runtime?** High priority per brief and gap analysis, because they are fast score-native, already implemented in the Yan harness (`tests/harness/yan2023/extractor.py:1`), and absent from runtime:
   - `pitch_mean` / `deviation_of_pitch` (std) — basic pitch aggregates
   - `mean_of_note_duration` / `deviation_of_note_duration`
   - `pitch_entropy` (Shannon entropy over MIDI pitches)
   - `deviation_of_pitch_from_C4` (mean abs distance from MIDI 60)
   - `pitch_variability` / `note_duration_variability` (shared variability bank)
   - `black_key_rate` (shared rate bank)
   - compact `polyphony_rate` (onset-based)
   - `triad` / `seventh_chord` / `ninth_chord` typed counts (currently `texture_chord_count_*` is untyped)
   - `length` / `tempo` / `key_signature` as explicit predictors (currently only `metadata_*` change counts and measure/note counts)
   Defer: `melodic_complexity/originality/melodiousness`, `pressing_velocity_*`, hand-size ergonomic stretch, anything requiring performance/MIDI.

**Acceptance:** At least one repo-native feature set now matches or approaches Yan-style results on both datasets without unstable continuous predictors presented as final: `runtime_all_clean_winsor` (r2 0.599/0.628) and `runtime_yan_overlap` RF (0.599/0.637) are within 0.02 of Yan ridge/RF baselines (0.615/0.651). The demo-facing claim remains ordinal (3-bin balanced_accuracy lift +0.18–0.20) unless calibrated regression is gated behind hygiene + regularization.

## 9. Caveats and Next Validation Needed

- Taxonomy weighting and learner-facing interpretation still need separate validation. Current results show families co-vary with labels, not that any specific weighting is pedagogically sound.
- Regression calibration: negative R2 on uncleaned `runtime_all` with alpha=1 is now explained as sparse-feature variance inflation; cleaned + regularized models (alpha 10–100, drop_sparse, winsorize) fix it, but should be validated on held-out data before promotion.
- Binning choices matter: 3-bin results use quantile bins (dataset-specific tertiles), not pedagogical cut points; 9-bin uses custom Henle edges covering 1–9 but still treats Henle as nominal bins for balanced_accuracy. Ordinal MAE and off-by-one accuracy are reported for nuance but not yet calibrated to learner utility.
- Corpus limits: Oktav has 370 labeled extracts (35 unlabeled missing), CIPI 744. Both are repo-native exports from their Python analysis pipelines (`cipi_labeled_feature_matrix.csv:194` / `oktav_labeled_feature_matrix.csv:120` columns). Results are CV estimates, not held-out external validation.
- Future work: promote the 11 high-priority Yan statistical features into runtime extraction, then re-run `runtime_yan_overlap` vs `runtime_all_clean` to quantify lift; keep `melodic_*` and `pressing_velocity_*` deferred; consider `og_plus_runtime` after promotion.

## 10. Deliverables Checklist

- Run dirs created: 19 original runs under `tests/artifacts/difficulty_prediction/oktav/` and `.../cipi/` plus 70 targeted-gap runs under `tests/artifacts/difficulty_prediction/comparisons/targeted_grid/` and 137 exploratory gap_grid runs (see `feature_set_comparison_summary.csv:1`).
- Preflight summary: Section 1 and `label_pairing_audit.json`.
- Metrics summary tables: `tests/artifacts/difficulty_prediction/label_validation_summary.csv` (19 rows) and `tests/artifacts/difficulty_prediction/feature_set_comparison_summary.csv` (70 rows, generated by `tests/scripts/generate_targeted_summary.py:1`).
- Gap diagnostic: `tests/artifacts/difficulty_prediction/yan_runtime_feature_gap.csv` (31 rows, generated by `tests/harness/difficulty_prediction/yan_runtime_gap.py:1`).
- Error-analysis table: `tests/artifacts/difficulty_prediction/label_validation_errors.csv` (60 rows).
- New harness: curated feature sets `runtime_core_no_expression`, `runtime_core_no_sparse`, `runtime_motor_texture`, `runtime_yan_overlap`, `yan2023_observed_no_blocked` in `tests/harness/shared/matrix_features.py:29`; hygiene flags in `tests/harness/difficulty_prediction/core.py:28` / `runner.py:1`; regularized models (ridge sweep, elasticnet, RF, GB) already in `models.py:1`.
- Docs updated: `docs/difficulty_label_validation.md` (this file, now with §8 gap experiment) and `docs/difficulty_prediction_matrix.md`.
- Interpretation and caveats: Sections 7–9 with explicit wording guardrails; demo-facing claim remains ordinal unless calibrated regression is hygiene-gated.

## 11. Verification

- Re-ran all newly added configs with `PYTHONPATH=. python tests/scripts/run_difficulty_prediction.py <config>` via `tests/harness/difficulty_prediction/runner.py:22`; all 10 new configs succeeded after handling all-NaN sparse rhythm columns.
- Generated summary and error tables via `tests/scripts/generate_label_validation_summary.py:1` and `tests/scripts/generate_label_validation_errors.py:1`.
- No unrelated full test suites were run; no runtime extraction formulas were changed (only harness preprocessing for empty columns and artifact regeneration of Oktav matrix from `/Users/campshelor/Desktop/oktav-thesis/datasets/oktav-starting-dataset` via `tests/harness/oktav_dataset/python_analysis.py:36`).

## 12. Promotion: Yan-overlap predictors now runtime-native (2026-09-16)

Compact Yan-style score-native predictors previously available only in `tests/harness/yan2023/extractor.py:1` are now emitted by the runtime extraction layer, so future `runtime_all` / `runtime_yan_overlap` matrices carry the signal directly:

- `src/piano_difficulty/features/statistics.py:1` — 13 descriptors: `statistics.pitch_mean`, `pitch_std`, `pitch_entropy`, `deviation_from_c4`, `duration_mean`, `duration_std`, `pitch_variability`, `duration_variability`, `black_key_rate`, `polyphony_rate`, `triad_count`, `seventh_chord_count`, `ninth_chord_count`
- `src/piano_difficulty/features/metadata.py:1` — 3 compact metadata predictors: `metadata.length_quarters`, `metadata.primary_tempo`, `metadata.key_signature`

These reuse the proven Yan-harness contracts (mean, population std, Shannon entropy, adjacent-normalized variability, written-note black-key ratio, polyphonic-onset ratio, typed chord counts, score duration / initial tempo / initial fifths) and are regression-checked against `tests/harness/yan2023/implementation_audit.py:90` fixture expectations on `tests/fixtures/feature_fixture.musicxml`. Blocked features (`pressing_velocity_*`, `melodic_*`, ergonomic `hand_stretch` beyond `pitch_geometry`, any MIDI/performance-dependent or ambiguous proxies) remain in the Yan lab and are not promoted.

Matrix selection: `tests/harness/shared/matrix_features.py:29` now exposes `runtime_statistical` (16 columns) and `runtime_yan_overlap` has been updated to include `statistics_*` + compact `metadata_*` columns, so `runtime_yan_overlap` is now runtime-native. `runtime_all` automatically includes `statistics_*` via `RUNTIME_FAMILY_PREFIXES`. `difficulty_overview.v1` remains a frozen 5-factor composite; promoted descriptors are available as raw descriptors and `difficulty_aspects.v1` traces.

Aspect grouping: `src/piano_difficulty/difficulty_analysis/aspects.py:1` maps the promoted features into their target aspects (see `docs/difficulty_aspect_taxonomy.md:1` and `docs/core_feature_registry.md:1`).

Next validation (harness): re-run `runtime_yan_overlap` vs `yan2023_observed` on regenerated matrices (CIPI/Oktav runtime exports) to quantify lift from the promoted statistical columns; no change to the 5-factor overview score behavior is expected.

