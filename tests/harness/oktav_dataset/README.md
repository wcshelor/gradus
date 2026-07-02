# Oktav Dataset Harness

This lane owns the local Oktav corpus export pipeline.

The restored ScoreAnalyzer export runner:

- scans `evaluation_scores/ad_hoc/oktav_starting_dataset/`
- stages each score into the external ScoreAnalyzer repo
- enforces a 15-second timeout per piece by default
- writes the exported matrix to `tests/artifacts/oktav_dataset/og_export/full_run/`

Keep corpus staging, export metadata, and failure diagnostics here.
