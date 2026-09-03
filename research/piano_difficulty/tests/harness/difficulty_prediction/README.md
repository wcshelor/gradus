# Difficulty Prediction Harness

This harness is the supervised side of the matrix-evaluation lane. It runs
config-driven experiments over exported feature matrices and shares its
loader/selection backbone with the clustering harness.

Current intended uses:

- Oktav regression baselines on `difficulty_numeric`
- Oktav ordinal/binning experiments, including the Henle-matched 9-bin setup
- CIPI regression baselines on `overallDifficulty`
- feature-set comparisons across OG aggregate features, the Sebastien
  clustering bundle, and repo-native runtime families, including expression
  ablations

Key properties:

- consumes matrices only; it does not stage corpora or export OG features
- keeps configs in `tests/harness/difficulty_prediction/configs/`
- writes run directories under `tests/artifacts/difficulty_prediction/`
- can compare multiple completed runs with
  `tests/scripts/compare_difficulty_prediction_runs.py`

Named feature sets:

- `og_php`: legacy aggregate PHP / Sebastien-style features
- `sebastien_clustering`: nine-feature bundle used for the Sebastien-style
  clustering comparison
- `runtime_all`, `runtime_no_expression`, `rhythm_only`, `leaps_only`,
  `texture_only`, `coordination_only`, `notation_only`, `expression_only`,
  `og_plus_runtime`

Notes:

- the default Oktav configs expect an exported matrix at
  `tests/artifacts/oktav_dataset/og_export/full_run/og_full_dataset.csv` for
  OG / Sebastien baselines
- the default Oktav runtime-family configs expect an exported matrix at
  `tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv`
- the default CIPI configs expect the retired export path at
  `tests/artifacts/retired/cipi_og_export/full_cipi_run/og_full_dataset.csv`
- `og_plus_runtime` expects a joined matrix and is not produced by the default
  Oktav runtime export wrapper
- if those exports are absent, point the config at a regenerated matrix before
  running the harness
