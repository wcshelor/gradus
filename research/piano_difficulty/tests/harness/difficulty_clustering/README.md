# Difficulty Clustering Harness

This harness is the unsupervised side of the matrix-evaluation lane. It runs
config-driven experiments over exported feature matrices and shares its
loader/selection backbone with the supervised harness.

Current intended uses:

- PCA + clustering over Oktav exported feature matrices
- PCA + clustering over CIPI exported feature matrices
- post-hoc comparison of clusters against difficulty labels
- comparison of the Sebastien nine-feature bundle against older aggregate
  feature bundles

Key properties:

- fitting stays label-free; labels are used only after clustering
- configs live in `tests/harness/difficulty_clustering/configs/`
- run directories live under `tests/artifacts/difficulty_clustering/`
- output includes PCA coordinates, explained variance, loadings, cluster
  profiles, metrics, plots, and a markdown report

Special CIPI behavior:

- when a config asks for `label_column: henle` and the matrix does not already
  include `henle`, the runner joins it post hoc from
  `evaluation_scores/manifests/cipi_dataset_catalog.csv`
- the join uses normalized `dataset_relative_path` first and a controlled
  filename fallback second
- `piece_coordinates.csv` preserves provenance columns such as
  `henle_catalog_values`, `henle_catalog_value_count`, and
  `label_join_source`
