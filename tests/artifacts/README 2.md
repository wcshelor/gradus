# Test Artifacts

This directory holds generated evidence only.

Current active evidence:

- `scoreanalyzer_parity/`: the current Alla Turca parity loop
  - `fresh_alla_turca/`: whole-piece compare and the current open mismatch set
  - `displacement_probe/`, `displacement_trace/`, `verbose_diff/`,
    `verbose_diff_left/`, `octave_ratio_probe/`, `chord_event_map/`,
    `window_extraction/`, `forensics/`: zoom-in evidence used to explain each
    mismatch family
- `normalization_battery/`: the current Alla Turca normalization sensitivity
  battery
- `oktav_dataset/`: the active thesis dataset evidence
  - `og_export/full_run/`: the current resumable batch export
  - `slowdown_diagnostics/20260615T155655Z/`: the current instrumented
    hotspot run
- `difficulty_prediction/`: reusable prediction runs and comparison tables
  over exported matrices
  - `runs/`: per-experiment metrics, fold predictions, and feature importance
    outputs
  - `oktav/`: Oktav-scoped prediction runs kept separate from CIPI evidence
  - `cipi/`: CIPI-scoped prediction runs kept separate from Oktav evidence
  - `oktav_henle_9bin/`: Oktav 9-bin label experiments matched to Henle
  - `comparisons/`: run-to-run comparison tables
- `difficulty_clustering/`: reusable clustering runs over exported matrices
  - `oktav/`: Oktav clustering runs, including the 9-feature Sebastien-style
    bundle
  - `cipi/`: CIPI clustering runs using the same shared bundle
- `inspection-candidates/`: curated PCA-quadrant shortlist for manual piece
  inspection across Oktav and CIPI

Historical evidence that is no longer part of the active loop lives in:

- `retired/`: archived CIPI outputs, superseded Oktav smoke runs, the old
  Oktav testset export, and other one-off diagnostic runs that are useful to
  keep but no longer need to sit in the main tree

If a run is part of the current Alla Turca investigation, keep it in the active
tree. If it only documents an old probe or smoke test, archive it under
`retired/`.
