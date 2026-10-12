# OMR Hotspot Robustness Experiment

- Timestamp: 2026-10-04T16:54:44.138604+00:00
- Source count: 1
- Success: 0 / Failures: 1
- Out dir: /Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/experiment/debussy_direct_manifest

## Did the OMR version identify roughly the same hard passages?

No successful comparisons; OMR outputs may be unreadable or recognizer not available.

## Failure Categories

- unreadable_page: 1

## Per-Score Details

| # | Score | PDF | OMR | Peak distance | Pearson r | Recall ±2 (top-3) | Answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | debussy_arabesque-no-1.musicxml | success | failure | — | — | — | Comparison failed: OMR score not found: /Users/campshelor/repos/gradus/resear... |

## Notes

- Region-based comparison: hard passages are compared by measure windows, not exact notes.
- Tolerances ±1 and ±2 measures account for OMR measure-count drift.
- Failure categories: unreadable_page, measure_count_mismatch, rhythm_corruption, staff_hand_confusion, pitch_register_drift, plus audiveris/pipeline errors.
- OMR errors especially damage text/voices/hands/articulations/tuplets/cross-staff, but physical difficulty signals (dense rhythms, spans, leaps, chords) may survive.
- Keep OMR behavior test-scoped; do not promote noisy-OCR assumptions into runtime code.
