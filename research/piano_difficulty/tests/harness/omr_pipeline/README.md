# OMR Pipeline Harness

This lane prototypes a small OMR-friendly workflow for symbolic piano scores.
It does not change runtime extraction logic. Instead, it tests the page-render
and readback boundary that a lightweight OMR setup would sit on top of.

## Purpose

- render source scores into page-oriented PDFs that can feed a small OMR system
- keep a stable manifest for source-to-rendered-file traceability
- make it easy to inspect how downstream feature extraction behaves when the
  score source comes from imperfect recognition or page rendering
- keep the OMR staging boundary separate from dataset cataloging and from
  matrix-evaluation work

## Current scope

- MuseScore-based PDF rendering of Oktav `.mxl` scores
- configurable suffix filtering for future score subsets
- configurable MuseScore binary selection on macOS
- manifest, summary, and per-file log export
- output under `tests/artifacts/omr_pipeline/pdf_export/full_run/`

## Provenance rules

- raw source scores stay in `evaluation_scores/ad_hoc/oktav_starting_dataset/`
- rendered evidence stays under `tests/artifacts/omr_pipeline/`
- this lane is about OMR prototyping and readback experiments, not canonical
  corpus staging
- any future OMR recognizer outputs should be kept in this lane, not folded back
  into the Oktav dataset harness

## Working loop

1. Run `tests/scripts/run_omr_pdf_export.py`.
2. Inspect `pdf_manifest.csv`, `corpus_summary.json`, and any `errors.csv`.
3. Feed the PDFs into the small OMR setup you want to test.
4. Compare the recognized output against the downstream difficulty extraction
   boundary.
