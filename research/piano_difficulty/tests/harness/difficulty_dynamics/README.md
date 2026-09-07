# Difficulty Dynamics Harness

The profile engine and typed contracts are now implemented in
`piano_difficulty.difficulty_analysis.dynamics`; exporters are in
`piano_difficulty.output.dynamics`. The local core/models/exports modules
preserve old import paths. This harness owns configurations, experiment runners,
plots and the manifest-driven piece lab.

For normal piece analysis, use `piano-difficulty analyze piece.mxl --out-dir analysis`.
The public overview has exact attack selection, reviewed factor defaults,
separate hand views and merged candidate sections. Existing experiments preserve
whole-overlapping-measure selection and their previous raw values; the output
metadata now states that policy. Do not treat legacy beat windows as exact
event selection.

This lane builds time-varying difficulty profiles over symbolic piano scores.

## Purpose

- segment a score into bounded measure windows
- reuse the existing repo feature extractors on each region
- normalize, smooth, and aggregate feature series without changing feature formulas
- detect high-difficulty passages for visualization or downstream use

## Current scope

- measure-window segmentation with configurable size, step, and final-window handling
- beat-window segmentation with configurable beat size, beat step, and final-window handling
- region-aligned extraction over the existing `piano_difficulty.features` package
- within-piece normalization: `none`, `min_max`, `z_score`, `robust`
- optional moving-average smoothing
- transparent weighted or unweighted composite series
- top-N, percentile, and local-maximum peak detection
- consensus hard-spot tagging that combines per-feature peaks and the composite peak
- per-hotspot feature attribution that ranks the strongest feature contributors in that region
- JSON and CSV exports plus a flat hotspot CSV and a compact markdown summary
- optional static plot generation using `matplotlib` when available, with a
  lightweight Pillow fallback in the workspace runtime
- a manifest-driven piece-lab wrapper for running the same setup over many known pieces

## Provenance rules

- `yan2023` provenance is used for currently reused Yan-derived runtime features
- `repo_native` provenance is used for the other runtime descriptors
- raw, normalized, and smoothed values are stored separately
- composite values are clearly labeled as descriptive aggregations, not ground truth
- feature contribution ranks use the region's normalized or smoothed feature value and the configured composite weight

## Known limitations

- within-piece normalization is only useful for relative variation inside one piece
- composite difficulty is not a validated universal weighting scheme
- local maxima are intentionally simple and interpretable
- hotspot tags are consensus summaries over the raw per-series peaks, not a replacement for them
- feature attribution is explanation scaffolding; it identifies the strongest local signals but does not yet produce prose pedagogy
- the public runtime owns the computation and export helpers; experiment orchestration remains here

## Working loop

- run one score with `tests/scripts/run_difficulty_dynamics.py`
- inspect `difficulty_hotspots.csv` and `difficulty_summary.md` in the run directory
- batch a known-piece manifest with `tests/scripts/run_difficulty_dynamics_piece_lab.py`
- start from `evaluation_scores/manifests/difficulty_dynamics_piece_lab.template.csv` for your personal piece list
- for the CEO demo surface over familiar CIPI repertoire (curated manifest,
  per-piece timelines, reviewer checklist), see
  `tests/harness/ceo_walkthrough/` — it consumes the promoted overview
  built on this engine and owns no new difficulty math
