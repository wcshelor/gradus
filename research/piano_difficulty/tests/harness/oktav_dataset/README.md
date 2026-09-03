# Oktav Dataset Harness

This is one dataset adapter in the broader dataset-staging lane.

It currently handles the local Oktav corpus staging and export pipeline.
The PDF-rendering / OMR-prototyping lane now lives in
`tests/harness/omr_pipeline/`.

Active runners:

- `tests/scripts/run_oktav_og_export.py`
  - scans `evaluation_scores/ad_hoc/oktav_starting_dataset/`
  - stages each score into the external ScoreAnalyzer repo for archived runs
  - enforces a 15-second timeout per piece by default
  - writes the exported matrix to `tests/artifacts/oktav_dataset/og_export/full_run/`
- `tests/scripts/run_oktav_python_analysis.py`
  - scans `evaluation_scores/ad_hoc/oktav_starting_dataset/`
  - runs repo-native `extract_score(...)` feature extraction over each score
  - writes the exported matrix to `tests/artifacts/oktav_dataset/python_analysis/full_run/`
  - reuses a prior labeled matrix as an optional label source when Oktav labels are not staged in a committed manifest
- `tests/scripts/run_oktav_pdf_export.py`
  - compatibility alias for the OMR prototyping lane
- `tests/scripts/run_omr_pdf_export.py`
  - scans Oktav `.mxl` files under the same local dataset root
  - converts each file to a PDF with MuseScore's command-line exporter
  - writes the PDFs to `tests/artifacts/omr_pipeline/pdf_export/full_run/pdfs/`
  - writes `pdf_manifest.csv`, `corpus_summary.json`, and per-file logs alongside the PDFs

Keep corpus staging, export metadata, and failure diagnostics here. New work
should prefer the shared dataset helpers and matrix-evaluation lanes where
possible. OMR-specific rendering and readback experiments belong in the
separate OMR lane.
