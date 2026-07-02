# Oktav Dataset Harness

This package is the thesis-scoped lane for the local Oktav dataset.

Use it for:

- normalizing the provided arrangement mapping workbook into committed CSV
- building a clean file-to-difficulty catalog for the copied local corpus
- running OG PHP `ScoreAnalyzer` batch exports over a local corpus and writing
  resumable per-piece CSV artifacts
- generating labeled feature matrices for downstream modeling
- sampling a handful of pieces and instrumenting the OG PHP runtime to diagnose
  slowdown hotspots in individual scores
- keeping dataset mechanics out of `src/` and out of the `scoreanalyzer`
  parity harness
- keeping reusable prediction experiments in
  `tests/harness/difficulty_prediction/`

Repository layout for this lane:

- ignored raw score files:
  `evaluation_scores/ad_hoc/oktav_starting_dataset/`
- committed mapping CSV:
  `evaluation_scores/manifests/oktav_arrangement_mapping.csv`
- committed catalog CSV:
  `evaluation_scores/manifests/oktav_starting_dataset_catalog.csv`
- committed OG export artifacts:
  `tests/artifacts/oktav_dataset/og_export/<run_id>/`
- committed Python-analysis artifacts:
  `tests/artifacts/oktav_dataset/python_analysis/<run_id>/`
- combined labeled feature matrix for downstream modeling:
  `tests/artifacts/oktav_dataset/python_analysis/<run_id>/oktav_labeled_feature_matrix.csv`
- legacy Oktav-only label-prediction wrapper:
  `tests/scripts/run_oktav_label_prediction.py`
- committed slowdown-diagnostic artifacts:
  `tests/artifacts/oktav_dataset/slowdown_diagnostics/<run_id>/`
- thin runner:
  `tests/scripts/build_oktav_dataset_catalog.py`
- thin OG export runner:
  `tests/scripts/run_oktav_og_export.py`
- thin Python-analysis runner:
  `tests/scripts/run_oktav_python_analysis.py`
- thin slowdown-diagnostics runner:
  `tests/scripts/run_oktav_slowdown_diagnostics.py`

Active evidence in the current cleanup is concentrated in
`tests/artifacts/oktav_dataset/og_export/full_run/` and
`tests/artifacts/oktav_dataset/slowdown_diagnostics/20260615T155655Z/`.
Older smoke and manual runs were moved to `tests/artifacts/retired/oktav_dataset/`
so the active tree stays readable.

Typical refresh command:

```bash
PYTHONPATH=src python tests/scripts/build_oktav_dataset_catalog.py \
  --mapping-xlsx /path/to/arrangement-mapping.xlsx
```

Full OG export:

```bash
PYTHONPATH=src python tests/scripts/run_oktav_og_export.py \
  --out-dir tests/artifacts/oktav_dataset/og_export/full_run \
  --php-bin /path/to/php \
  --timeout-seconds 180 \
  --heartbeat-seconds 10
```

Current Python replication over the same catalog:

```bash
PYTHONPATH=src python tests/scripts/run_oktav_python_analysis.py \
  --out-dir tests/artifacts/oktav_dataset/python_analysis/full_run
```

Resume an interrupted run:

```bash
PYTHONPATH=src python tests/scripts/run_oktav_og_export.py \
  --out-dir tests/artifacts/oktav_dataset/og_export/full_run \
  --php-bin /path/to/php \
  --timeout-seconds 180 \
  --heartbeat-seconds 10 \
  --resume
```

Use the same `--out-dir` for the initial run and the resumed run. The exporter
uses `og_full_dataset.csv` in that directory as the authoritative incremental
state and skips rows that are already present there.

Timeout handling:

- per-piece PHP timeouts are treated as `skipped`, not fatal failures
- skipped pieces keep the run moving and still leave a row in the main CSV
- real non-timeout exceptions still become failures and are written to
  `errors.csv`

Runtime logging behavior:

- prints a timestamped start line for each piece
- prints phase changes such as resolving, loading, staging, and invoking PHP
- prints periodic heartbeat lines while the OG PHP process is still running
- prints a final success or failure line with elapsed seconds for each piece
- prints a final skipped line when a piece hits the PHP timeout
- appends each completed piece directly to `og_full_dataset.csv`
- records lightweight per-file MusicXML metadata in the same CSV, including
  source size, part count, measure count, note count, rest count, and duration
  totals derived from the raw XML
- rebuilds `errors.csv` and `run_summary.json` as the run progresses so resume
  can continue from the saved main CSV

Current export behavior:

- input catalog rows must provide `filename` and `repo_relative_path`
- the runner stages one full score at a time into the OG PHP runtime
- the runner emits a heartbeat while the PHP process is still active
- output rows include metadata plus the canonical OG metric fields
- `run_summary.json` reports `success_count`, `skipped_count`, and
  `failure_count`

Current Python-analysis behavior:

- loads the same Oktav catalog used by the OG export path
- evaluates the current runtime feature set against the internal Oktav labels
- writes run-scoped CSV, metric, and summary artifacts for later comparison
- writes a combined one-row-per-piece feature matrix with label columns for modeling
- stays in the Oktav lane because it prepares the labeled matrix consumed by
  `tests/harness/difficulty_prediction/`

Downstream prediction:

- reusable modeling over the labeled matrix lives in
  `tests/harness/difficulty_prediction/`
- `tests/scripts/run_difficulty_prediction.py` runs config-driven experiments
  over exported matrices
- `tests/scripts/compare_difficulty_prediction_runs.py` compares run outputs
- `tests/scripts/run_oktav_label_prediction.py` remains available as an
  Oktav-specific legacy wrapper if the old feature-subset helper is needed

Slowdown diagnostics:

- samples `--sample-size` random pieces from the Oktav dataset root
- copies the sampled scores into
  `tests/artifacts/oktav_dataset/slowdown_diagnostics/<run_id>/selected_dataset/`
- stages each sampled piece individually into an instrumented OG PHP runtime
- logs phase markers and helper-function hotspot summaries to stderr and to per
  piece artifact files
- runs PHP with warnings and fatal errors enabled, then gives timed-out pieces a
  short graceful shutdown window so shutdown profiling can flush when possible
- writes `sample_manifest.csv`, `diagnostic_timeline.csv`, `report.md`, and
  per-piece summaries for later inspection

Example diagnostic command:

```bash
PYTHONPATH=src python tests/scripts/run_oktav_slowdown_diagnostics.py \
  --dataset-root /Users/campshelor/Desktop/oktav-thesis/datasets/oktav-starting-dataset \
  --php-bin /Users/campshelor/miniconda3/bin/php \
  --scoreanalyzer-root /Users/campshelor/Desktop/github-repos/piano-difficulty/external/ScoreAnalyzer \
  --sample-size 5 \
  --timeout-seconds 900 \
  --heartbeat-seconds 10
```
