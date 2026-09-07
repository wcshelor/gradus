# LS-07 review handoff — one grounded pedagogical aid

Date: 2026-09-05. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-03, LS-06 (done). Owner: pedagogical-assistance layer.

## Outcome

Implemented `transition_practice`: a text-only practice suggestion (name and
isolate consecutive pitch moves before practicing tempo) grounded in LS-06
pitch-transition observations. A deterministic, uncalibrated ≥7-semitone rule
selects applicability. Learner reports frame the aid and are referenced via
`report_refs` separately from `passage_refs`/`observation_refs`; score values
are never altered by reports. Region-scoped reports outside the observed
regions yield a mismatch caveat. Empty or below-threshold evidence yields an
aid-shaped abstention (`suggestion=None`) with rationale and limitations.
Every result states `prototype_unvalidated` provenance and unproven
effectiveness. Correction: LS-03b prose fields (`text`, `interpretation`,
`need`, `rationale`) were wrongly capped at the 128-char ID limit; a
`_check_text` validator now distinguishes prose from IDs (existing contract
tests still pass unchanged).

## Changed files

- `passage_practice/src/passage_practice/aids/__init__.py` (new integration
  layer; imports learner contracts but no low-level passage file imports
  learner code).
- `learner_context/src/learner_context/models.py` (prose-length correction).
- `passage_practice/tests/unit/test_transition_aid.py` (new, 6 tests).
- Plan log (LS-07 row). No other files touched.

## Commands and results (repo root, `piano-difficulty` env)

- Focused (aids + observations + learner contracts): green.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **317 passed, 7 skipped** (skips unchanged: optional local-corpus fixtures).
- `git diff --check` clean. Two test-side mistakes fixed (syntax-line merge,
  threshold-wording assertion); one genuine contract defect fixed (prose cap);
  no behavior weakened, no snapshots touched.

## Intentionally not implemented

- Diagnosis engine/rules, exercise generation or notation export, UI, live
  feedback, LLM output, trait inference, effectiveness evaluation (LS-10).

## Remaining risks/decisions

- The 7-semitone threshold is an uncalibrated heuristic; the aid must not be
  read as a validated difficulty claim.
- Report conflict detection is structural (region overlap) only; textual
  disagreement is not interpreted.
- Next: LS-08 (minimal flexible interaction surface). No WP gate released.
