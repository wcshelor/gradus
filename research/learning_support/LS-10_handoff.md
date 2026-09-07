# LS-10 review handoff — evaluate the three areas separately and together

Date: 2026-09-06. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-09 (done). Owner: experiment evaluation documentation/evidence.

## Outcome

Evaluation/documentation task; no feature code. Produced a reproducible
technical report plus machine-checked evidence links:

- `research/learning_support/evaluation_ls10.md` (dated 2026-09-06):
  reproduction commands, fixture/scenario inventory (3 synthetic fixtures,
  S1–S7, V1–V7), per-area verdicts (A: correct within one transition family;
  B: traceable text aid, effectiveness unproven; C: control operations met),
  joint comparisons (score-only ≡ score-plus-report on facts; NONE ≡
  score-only; non-hotspot manual path without fabrication; conflict/stale/
  revision handling), language audit, 6 limitation/risk items including
  misleading-personalization risks, and an explicit review status with a
  walkthrough proposal. Appendix E maps checks E01–E12 to scenarios and tests.
- `research/learning_support/tests/unit/test_evaluation_ls10.py` (7 tests):
  every E-ID and mapped test name present in the report, fixtures on disk,
  required guards present (`synthetic`, `unproven`, `not yet reviewed`,
  `pending lead review`, denied-form benefit/data claims), overclaims absent
  (negation-aware, word-boundary, `prototype_unvalidated` allowed as a code
  literal), and live re-verification of the starred joint facts.
- No AI exists in this slice, so the plan's AI-vs-deterministic-baseline
  comparison is recorded as not applicable. No measured learning benefit, no
  real data, no new observations/aids/UI, no model calls.

## Changed files

- `research/learning_support/evaluation_ls10.md` (new).
- `research/learning_support/tests/unit/test_evaluation_ls10.py` (new).
- Plan log (LS-10 row). No runtime, contract, fixture, or existing-test files
  touched.

## Commands and results (repo root, `piano-difficulty` env)

- Focused (evaluation + interaction + learner-context + LS-06 observations +
  LS-07 aids): **81 passed**.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **347 passed, 7 skipped** (baseline 340 + 7 new; skips unchanged:
  optional local-corpus fixtures).
- `git diff --check` clean. Two test-side mistakes fixed (evidence-link
  substring form for multi-test rows; overclaim matcher false positives on
  "Reproduction" and the `prototype_unvalidated` literal). No behavior
  weakened; no snapshots touched. Existing LS-04–LS-09 tests all still pass.

## Intentionally not evaluated / not built

- Human usefulness evaluation (requires teacher/owner walkthrough — proposed
  in the report, not performed); any real learner data; statistical or
  longitudinal claims; AI/model comparisons; new semantic patterns, aids,
  interactions, or product integration (LS-11 scope).

## Remaining risks/decisions

- The report's numbers are only as current as the suite: re-run the focused
  set if behavior changes, since the eval tests pin live values.
- Review status is explicitly negative (no teacher/owner review yet;
  LS-01–LS-10 pending lead review); nothing here authorizes real-data
  collection or app integration.
- Next: LS-11 (next increment decision with the owner). No WP gate released.
  Do not start LS-11 in this change.
