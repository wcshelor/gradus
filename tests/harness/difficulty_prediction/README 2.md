# Difficulty Prediction Harness

This package is the reusable research lane for controlled symbolic piano
difficulty-prediction experiments.

Use it for:

- config-driven experiments over OKTAV and later CIPI-style matrices
- feature-set selection by explicit OG column names or runtime feature prefixes
- target transforms for continuous, rounded-class, quantile-bin, and custom-bin
  setups
- cross-validated model comparison with saved fold predictions
- run-to-run comparison tables for research notes and reports

This lane is intentionally separate from the Oktav dataset operations lane.
The Oktav lane stages corpora, labels, and exports. This lane consumes feature
matrices and runs controlled modeling experiments.

## Layout

- configs: `tests/harness/difficulty_prediction/configs/`
- run outputs: `tests/artifacts/difficulty_prediction/runs/`
- dataset-scoped run roots for cleaner lanes: `tests/artifacts/difficulty_prediction/oktav/`
  and `tests/artifacts/difficulty_prediction/cipi/`
- run comparison tables: `tests/artifacts/difficulty_prediction/comparisons/`
- runnable experiment wrapper: `tests/scripts/run_difficulty_prediction.py`
- runnable comparison wrapper:
  `tests/scripts/compare_difficulty_prediction_runs.py`

## Run one experiment

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_prediction.py \
  tests/harness/difficulty_prediction/configs/oktav_og_php_logreg_3bin.yaml
```

For the 9-variable Sebastien-style bundle, use:

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_prediction.py \
  tests/harness/difficulty_prediction/configs/oktav_sebastien_clustering_ridge_regression.yaml
```

The matching CIPI 9-variable runs use:

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_prediction.py \
  tests/harness/difficulty_prediction/configs/cipi_sebastien_clustering_ridge_regression.yaml
```

The first OKTAV configs point at the committed OG export matrix:

- `tests/artifacts/oktav_dataset/og_export/full_run/og_full_dataset.csv`

The CIPI Sebastien-style configs point at:

- `tests/artifacts/retired/cipi_og_export/full_cipi_run/og_full_dataset.csv`

For CIPI, the prediction target is the matrix's `overallDifficulty` column.

For the Oktav Henle-matched 9-bin experiment, use the dedicated configs:

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_prediction.py \
  tests/harness/difficulty_prediction/configs/oktav_sebastien_clustering_henle_9bin_logreg.yaml \
  --runs-root tests/artifacts/difficulty_prediction/oktav_henle_9bin
```

That lane freezes the bin edges derived from the committed Oktav export so the
experiment stays reproducible and easy to compare later.

The runtime-feature configs expect the labeled matrix produced by the Oktav
Python-analysis lane:

- `tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv`

If that runtime matrix is not present yet, the harness will fail with a precise
missing-file error instead of guessing a path.

## Compare runs

```bash
PYTHONPATH=src python tests/scripts/compare_difficulty_prediction_runs.py \
  tests/artifacts/difficulty_prediction/runs/<run_a> \
  tests/artifacts/difficulty_prediction/runs/<run_b>
```

The default comparison table is written to
`tests/artifacts/difficulty_prediction/comparisons/run_comparison.csv`.

## Add a new dataset

1. Add a loader branch in `tests/harness/difficulty_prediction/data.py`.
2. Point a config at the new matrix CSV.
3. Keep the raw corpus plumbing in the dataset-specific lane, not here.

## Add a new feature set

1. Add a new `FeatureSetSpec` in `tests/harness/difficulty_prediction/features.py`.
2. Prefer exact column names for stable OG features.
3. Prefer prefixes for family-based runtime features.
4. Update or add a YAML config that uses the new feature set name.

## Interpret the outputs

- `resolved_config.yaml`: the fully resolved config used for the run
- `metrics.json`: overall metrics plus run metadata and resolved paths
- `fold_metrics.csv`: one row per cross-validation fold
- `predictions.csv`: fold-level predictions with ids and errors
- `confusion_matrix.csv`: ordered confusion matrix for classification runs
- `feature_importance.csv`: mean feature importance or coefficient summaries
- `missingness_report.csv`: missing-value counts for the target and selected features
- `feature_selection_report.json`: which feature columns were selected or missing

## Notes

- `og_php` selects the OG PHP difficulty columns already used by the older
  Oktav label-prediction helper.
- `sebastien_clustering` selects the 9-variable bundle from the Sebastien
  clustering experiments: `length`, `rhythm`, `speed`, `harmonyRH`,
  `harmonyLH`, `chordsRH`, `chordsLH`, `displacementsRH`, and
  `displacementsLH`.
- `runtime_all` and the family-specific feature sets select `feature__...`
  columns from the runtime matrix.
- `og_plus_runtime` will keep whichever OG and runtime columns are actually
  available in the matrix and report any missing expected columns.
