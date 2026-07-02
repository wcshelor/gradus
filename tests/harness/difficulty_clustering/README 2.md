# Difficulty Clustering Harness

This package is the reusable research lane for unsupervised difficulty
clustering over exported feature matrices.

Use it when you want to:

- load an OKTAV feature CSV
- choose an explicit feature list or a shared feature set
- standardize features, run PCA, and cluster pieces in PCA space
- sweep `k` across multiple candidate values and rank the results with a
  post-fit selection metric
- compare the resulting clusters to OKTAV difficulty labels only after the
  unsupervised steps are complete

This differs from `tests/harness/difficulty_prediction/` in one important way:
prediction is supervised and trains directly on difficulty labels, while this
harness treats labels as interpretation-only metadata.

## Relation To Sebastien et al. (2012)

The first pass is intentionally modest, but it follows the same broad research
shape:

- start from a hand-chosen difficulty descriptor matrix
- standardize features
- project into PCA space
- cluster in the reduced space
- inspect cluster structure against external difficulty labels afterward

The harness supports:

- `ward`
- `kmeans`
- `ward_then_kmeans`

For research sweeps, set `clustering.sweep.enabled: true` and provide either:

- an explicit `k_values` list, or
- a `k_min` / `k_max` / `k_step` range

The sweep keeps each candidate run label-free during fitting, then writes a
summary table and picks the best `k` using the configured selection metric.
The default ranking metric is `silhouette_score`, and the default goal is to
maximize it.

The `ward_then_kmeans` option uses Ward clusters to seed the initial k-means
centroids so the run can mimic a Ward-plus-k-means workflow without using
OKTAV labels during model fitting.

## Layout

- configs: `tests/harness/difficulty_clustering/configs/`
- run outputs: `tests/artifacts/difficulty_clustering/runs/`
- thin runner: `tests/scripts/run_difficulty_clustering.py`
- sweep summary helper:
  `tests/scripts/print_difficulty_clustering_sweep_summary.py`

## Run The First Experiment

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_clustering.py \
  tests/harness/difficulty_clustering/configs/oktav_sebastian_9features_k3.yaml
```

For the matching CIPI run:

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_clustering.py \
  tests/harness/difficulty_clustering/configs/cipi_sebastien_9features_k3.yaml \
  --runs-root tests/artifacts/difficulty_clustering/cipi
```

For a `k` sweep example:

```bash
PYTHONPATH=src python tests/scripts/run_difficulty_clustering.py \
  tests/harness/difficulty_clustering/configs/oktav_sebastian_7features_ksweep.yaml
```

The committed example configs point at:

- `tests/artifacts/oktav_dataset/og_export/full_run/og_full_dataset.csv`
- `tests/artifacts/retired/cipi_og_export/full_cipi_run/og_full_dataset.csv`

The CIPI config joins `henle` from
`evaluation_scores/manifests/cipi_dataset_catalog.csv` on
`dataset_relative_path` before building the label crosstab, then falls back to
a normalized filename match for the few retired-export rows whose path spelling
differs from the catalog. When the catalog contains multiple Henle values for
the same score path, the run keeps a deterministic primary `henle` value for
comparison and also writes `henle_catalog_values` into `piece_coordinates.csv`
so the alternate catalog labels stay available for post hoc analysis.

If the feature names in your target CSV differ, edit either:

- `feature_columns` in the YAML for exact-column selection, or
- `feature_set` if you want to rely on shared matrix feature-set definitions

The 9-feature Sebastien-style bundle is shared between Oktav and CIPI and
contains:

- `length`
- `rhythm`
- `speed`
- `harmonyRH`
- `harmonyLH`
- `chordsRH`
- `chordsLH`
- `displacementsRH`
- `displacementsLH`

## Outputs

Each run writes:

- `resolved_config.yaml`
- `pca_explained_variance.csv`
- `pca_loadings.csv`
- `piece_coordinates.csv`
- `cluster_assignments.csv`
- `cluster_label_crosstab.csv` when labels are available
- `cluster_profiles.csv`
- `metrics.json`
- `report.md`
- basic PCA / dendrogram / label-comparison plots when applicable

Sweep runs write the same per-candidate artifacts inside
`tests/artifacts/difficulty_clustering/runs/sweeps/<timestamp>__<slug>/k*/`
plus:

- `sweep_summary.csv`
- `sweep_summary.json`
- `sweep_report.md`
- `sweep_metric_curve.png`

To inspect a completed sweep:

```bash
PYTHONPATH=src python tests/scripts/print_difficulty_clustering_sweep_summary.py \
  tests/artifacts/difficulty_clustering/runs/sweeps/<timestamp>__<slug>
```
