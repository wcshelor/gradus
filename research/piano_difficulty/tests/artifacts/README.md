# Analysis Artifacts

These directories hold generated evidence for the analysis-only lanes.

Current roots:

- `tests/artifacts/difficulty_dynamics/`: temporal analysis evidence, including
  the compact consolidation verification record

- `tests/artifacts/oktav_dataset/`: dataset staging and exported matrix work
  - `og_export/full_run/`: legacy ScoreAnalyzer matrix export
- `tests/artifacts/omr_pipeline/`: OMR prototyping and PDF render evidence
- `tests/artifacts/retired/`: older evidence layouts kept for compatibility
- `tests/artifacts/difficulty_prediction/`: supervised experiments over
  exported matrices
- `tests/artifacts/difficulty_clustering/`: PCA and clustering experiments over
  exported matrices
- `tests/artifacts/inspection-candidates/`: lightweight manifests for manual
  score inspection
- `tests/artifacts/scoreanalyzer_parity/`: OG parity evidence

Keep these roots separate. The prediction and clustering harnesses consume
matrices and write evidence; they do not own raw corpus staging.

The OMR prototyping root is intended for rendered score pages and any future
small OMR readback experiments that sit between source scores and downstream
feature extraction.
