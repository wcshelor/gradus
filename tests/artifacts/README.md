# Analysis Artifacts

These directories hold generated evidence for the analysis-only lanes.

Current roots:

- `tests/artifacts/oktav_dataset/`: dataset staging and exported matrix work
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
