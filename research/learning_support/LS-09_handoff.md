# LS-09 review handoff — return visits, revisions, and uncertain context

Date: 2026-09-05. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-08 (done). Owner: integration tests in learning support.

## Outcome

Primarily an integration-test pass: 8 staged scenario tests walk one
synthetic multi-visit history through the unchanged LS-08 harness over the
LS-05 selection fixtures, asserting exact context entries, observations, and
aid refs at each step with score/observation/result/report layers separate:

- V1: first region report saved with `saved=True`, used by a REFERENCED
  request (grounded +14 aid, `reported_concern` carries the entry ID).
- Gap: nine days between recorded timestamps; asserted present in data and
  absent from every system output (no progress/inactivity language).
- V2: changed difficulty arrives as a dated correction (revision 2,
  supersedes); the old text stays readable but is never selected, referenced,
  or authoritative; aid suggestion identical to baseline.
- V3: a stale 2026-08-01 general habit report is selected as dated verbatim
  context; observation values and suggestion unchanged; no trait language.
- V4: a conflicting measure-2 report yields exactly one region-mismatch
  caveat; score facts and suggestion unchanged.
- V5: same request under `ContextScope.NONE` selects nothing, references
  nothing, reproduces score-only observations/suggestion, and is deterministic
  across runs.
- V6: excluding a source stales `sum.1` (re-including restores it); deleting a
  source cascades the summary (no hidden memory); later selections exclude
  both correctly.
- V7: a learner-reported hard passage on the sparse, never-ranked voices
  fixture gets manual `USER_SELECTED` help with `difficulty == ()`, zero
  hotspot codes or text, observed `[-4, 5, 2]`, and an honest below-threshold
  limitation with full observation refs.
- An aggregate scan asserts no system text (rationale, limitations,
  diagnostics) claims progress, improvement, inactivity, traits, ability
  beyond the explicit not-a-diagnosis denial, or time-gap language; reports
  survive verbatim as data.

## Changed files

- `research/learning_support/interaction/tests/unit/test_return_visits.py`
  (new, 8 tests; replays V1–V4 saves via one builder, issues per-stage
  requests; no harness changes needed).
- `research/learning_support/learner_context/src/learner_context/models.py`
  (one fix, see below) and `tests/unit/test_learner_contracts.py` (+1
  regression test).
- Plan log (LS-09 row). No observation, aid, selection, or difficulty files
  touched; LS-06 semantics and LS-07 threshold unchanged.

## Genuine defect found and fixed

The V3/V4/V6/language tests exposed a real behavior gap: `AssistanceResult`
validated `limitations` (prose sentences) with the 128-char ID-cap validator,
so any caveat naming a longer entry ID (e.g. `entry.conflict`) crashed result
construction. Same defect class as the LS-07 prose-cap correction, one field
missed. Fix: new `_check_text_tuple` prose validator for `limitations`; IDs
(`passage_refs`, `report_refs`, `observation_refs`) still ID-capped.
Regression-covered both at contract level and end to end (V4).

## Commands and results (repo root, `piano-difficulty` env)

- Focused (`interaction` + `learner_context` + LS-06 observations + LS-07
  aids): **74 passed**.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **340 passed, 7 skipped** (baseline 331 + 8 scenario + 1 contract;
  skips unchanged: optional local-corpus fixtures).
- `git diff --check` clean. No behavior weakened; no snapshots touched.
  Existing LS-04–LS-08 tests all still pass.

## Intentionally not implemented

- UI, chat flow, model calls, persistence service, diagnosis engine, new aids
  or observation families, summarizer (existing `ContextSummary` reused),
  elapsed-time or missing-entry semantics, effectiveness evaluation (LS-10).

## Remaining risks/decisions

- Coverage rests on one synthetic history and two fixture pieces; conflicting
  reports are detected structurally (region overlap) only — textual
  disagreement is still not interpreted (inherited LS-07 limit).
- The `limitations` validator change is behavior-relaxing (accepts longer
  prose); lead should confirm no downstream consumer relied on the cap.
- Next: LS-10 (separate + joint evaluation with human review). No WP gate
  released. Do not start LS-10 in this change.
