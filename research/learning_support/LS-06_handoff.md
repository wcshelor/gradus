# LS-06 review handoff — one bounded semantic observation

Date: 2026-09-05. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-05 (done). Owner: passage-practice semantic layer.

## Outcome

Implemented consecutive-attack pitch-interval observations (signed semitones)
over investigation passages. Every observation links ordered logical-note
source refs, an exact region (omitted with a diagnostic for simultaneous
pairs, never padded), and producing method/version. Unscoped runs are marked
FACT; hand-scoped runs are marked INFERENCE with a diagnostic recording
reliance on staff-inferred labels. Fewer than two usable attacks, empty
passages, and unresolvable refs abstain with explicit diagnostics and no
learner-directed claims.

## Changed files

- `passage_practice/src/passage_practice/models/observations.py` (new:
  `Observation`, `ObservationBasis`, `ObservationResult` contract versions
  `observation.v1` / `observation_result.v1`), `models/__init__.py` (exports).
- `passage_practice/src/passage_practice/observations/__init__.py` (new:
  `observe_pitch_transitions`, reusing `resolve_ref`; no new lookup logic).
- `passage_practice/tests/unit/test_observations.py` (new, 9 tests).
- Plan log (LS-06 row). No other files touched.

## Commands and results (repo root, `piano-difficulty` env)

- Focused passage-practice (incl. LS-05 entry tests): 138 passed.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **311 passed, 7 skipped** (skips unchanged: optional local-corpus fixtures).
- `git diff --check` clean. No behavior weakened; no snapshots touched.

## Intentionally not implemented

- Diagnosis rules (WP-08/LS-07), pedagogical aids, exercise generation,
  attribution records (ordinary observations need none per D-013),
  learner-context concepts in this layer, LLM output, UI.
- Only one observation family (pitch transitions); onset grouping, hand
  shapes, and rhythmic cells remain WP-03/T04.x work.

## Remaining risks/decisions

- Hand-scoped observations inherit staff-inference uncertainty; consumers
  must read the `hand_scoped_inference` diagnostic, not the label alone.
- Simultaneous pairs carry no region; downstream grouping must handle
  region-less observations explicitly.
- Next: LS-07 (one grounded pedagogical aid; needs LS-03 + LS-06). No WP
  gate released.
