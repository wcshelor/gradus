# OMR Hotspot Robustness Experiment

- Timestamp: 2026-10-04T19:13:51.220475+00:00
- Source count: 1
- Success: 1 / Failures: 0
- Out dir: /Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/experiment/debussy_direct_manifest_real_omr_fixed_ext

## Did the OMR version identify roughly the same hard passages?

Average peak distance is large (45.8 measures) — hotspot locations diverge. Mean recall within ±2 measures is high (100%) — OMR version identifies roughly the same hard passages. Difficulty traces show modest correlation (mean r=0.35). Failure categories observed: measure_count_mismatch: 1.

## Mean Metrics (across successful comparisons)

- measure_count_mismatch: 1.000
- peak_distance_measures: 45.833
- pearson_r: 0.348
- spearman_r: 0.386
- top_1_exact_jaccard: 0.000
- top_1_exact_overlap: 0.000
- top_1_exact_overlap_ratio: 0.000
- top_1_overlap_within_0: 0.000
- top_1_overlap_within_0_ratio: 0.000
- top_1_overlap_within_1: 0.000
- top_1_overlap_within_1_ratio: 0.000
- top_1_overlap_within_2: 0.000
- top_1_overlap_within_2_ratio: 0.000
- top_1_recall_within_0: 1.000
- top_1_recall_within_1: 1.000
- top_1_recall_within_2: 1.000
- top_3_exact_jaccard: 0.667
- top_3_exact_overlap: 2.000
- top_3_exact_overlap_ratio: 0.667
- top_3_overlap_within_0: 2.000
- top_3_overlap_within_0_ratio: 0.667
- top_3_overlap_within_1: 2.000
- top_3_overlap_within_1_ratio: 0.667
- top_3_overlap_within_2: 2.000
- top_3_overlap_within_2_ratio: 0.667
- top_3_recall_within_0: 1.000
- top_3_recall_within_1: 1.000
- top_3_recall_within_2: 1.000
- top_5_exact_jaccard: 1.000
- top_5_exact_overlap: 5.000
- top_5_exact_overlap_ratio: 1.000
- top_5_overlap_within_0: 5.000
- top_5_overlap_within_0_ratio: 1.000
- top_5_overlap_within_1: 5.000
- top_5_overlap_within_1_ratio: 1.000
- top_5_overlap_within_2: 5.000
- top_5_overlap_within_2_ratio: 1.000
- top_5_recall_within_0: 1.000
- top_5_recall_within_1: 1.000
- top_5_recall_within_2: 1.000

## Failure Categories

- measure_count_mismatch: 1

## Per-Score Details

| # | Score | PDF | OMR | Peak distance | Pearson r | Recall ±2 (top-3) | Answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | debussy_arabesque-no-1.musicxml | success | success | 45.8 | 0.35 | 100% | Peak hotspots diverge (distance 45.8 measures). Most original hard regions ar... |

## Notes

- Region-based comparison: hard passages are compared by measure windows, not exact notes.
- Tolerances ±1 and ±2 measures account for OMR measure-count drift.
- Failure categories: unreadable_page, measure_count_mismatch, rhythm_corruption, staff_hand_confusion, pitch_register_drift, plus audiveris/pipeline errors.
- OMR errors especially damage text/voices/hands/articulations/tuplets/cross-staff, but physical difficulty signals (dense rhythms, spans, leaps, chords) may survive.
- Keep OMR behavior test-scoped; do not promote noisy-OCR assumptions into runtime code.
