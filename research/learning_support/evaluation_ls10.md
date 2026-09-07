# LS-10 — Technical evaluation of the first learning-support slice

Date: 2026-09-06. Author: muse-spark. Status: implemented, pending lead review.
Scope: LS-01–LS-09 as built (no AI added, so the plan's conditional AI-vs-baseline
comparison is vacuous — recorded as not applicable, not as skipped evidence).
No real learner data was used or collected. No measured learning benefit is claimed.

Authority: [three-area plan](../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md)
(LS-10), [first slice](first_slice.md) (scenarios S1–S7, success rubric),
[LS-09 scenario suite](interaction/tests/unit/test_return_visits.py) (stages V1–V7).

## 1. Reproduction

Environment: `piano-difficulty` conda env, repo root, working tree (nothing
committed). Commands:

```text
conda run -n piano-difficulty python -m pytest -q
conda run -n piano-difficulty python -m pytest research/learning_support/interaction/tests \
  research/learning_support/learner_context/tests \
  research/learning_support/passage_practice/tests/unit/test_observations.py \
  research/learning_support/passage_practice/tests/unit/test_transition_aid.py \
  research/learning_support/tests/unit/test_evaluation_ls10.py -q
git diff --check
```

Results at evaluation time: full suite **340 passed, 7 skipped** (skips are
pre-existing optional local-corpus/ScoreAnalyzer fixtures, unchanged since
baseline); focused evaluation set **81 passed**. `git diff --check` clean.

## 2. Fixture and scenario inventory (all synthetic, redistributable)

Score fixtures (`passage_practice/tests/fixtures/`, listed in `manifest.md`):

| Fixture | Content | Role in evaluation |
| --- | --- | --- |
| `selection_two_staff.musicxml` | 2 measures, quarters 0–8, two staves | Main passage [0,4): transitions [-12, 14, 2, 1] |
| `selection_ties.musicxml` | Tie chains | Tie-collapse (no self-transition), below-threshold [2] case |
| `selection_two_voices.musicxml` | Sparse two-voice material, never ranked | Reported-hard non-hotspot: transitions [-4, 5, 2] |

Scenario inventory: first-slice scenarios S1–S5 (positive) plus S6–S7
(abstention) from `first_slice.md`; multi-visit stages V1–V7 from LS-09
(first report, 9-day gap, correction, stale habit, conflict, ignored history,
delete/exclude cascade, non-hotspot Voices visit). Evaluation checks E01–E12
are defined in the [evidence table](#appendix-e-evidence-table).

## 3. Area A — semantic understanding (LS-05/LS-06)

Method: `manual_investigation` (user-selected, no difficulty computed) then
`observe_pitch_transitions` (method `pitch_transition_observation/v1`).

- **Correctness.** On [0,4) the observer emits exactly `[-12, 14, 2, 1]`
  semitones, unscoped basis FACT; hand-scoped runs (`hand="right"`) emit
  `[2, 2, 1]` marked INFERENCE with a `hand_scoped_inference` diagnostic.
  Tie chains collapse (no self-transition). Entry routes (manual vs. analyzer
  envelope) observe identically.
- **Source evidence.** Every observation carries two logical-note source refs
  that resolve in the score; consecutive pairs carry exact regions except
  simultaneous pairs, which omit the region with a `simultaneous_pair`
  diagnostic rather than padding time.
- **Abstention.** Fewer than two usable attacks (empty selection, single-hand
  remainder, unresolvable refs skipped with `unresolvable_attack_ref`) yields
  `insufficient_attacks` and zero observations, with no learner-directed
  language. Out-of-range/empty/unknown/ambiguous locations raise
  `UnresolvableRegion` with stable reason codes; nothing is guessed.
- **Verdict.** Correct and evidenced *within one transition family*.
  Onset grouping, hand shapes, and rhythmic cells remain unimplemented; hand
  labels inherit staff-inference uncertainty; simultaneous pairs are
  region-less by design (consumers must handle that explicitly).

## 4. Area B — pedagogical assistance (LS-07)

Method: `suggest_transition_practice` over LS-06 observations; deterministic
≥7-semitone notability rule; provenance `prototype_unvalidated`.

- **Actionability.** The grounded suggestion names each notable move with its
  observation ID and prescribes isolating moves before practicing tempo, e.g.
  `-12 semitones down (…:pitch-transition:000); +14 semitones up (…:001)`.
  Objective recorded as `objective.isolate_consecutive_pitch_moves`.
- **Grounding.** Aid results always carry rationale, ≥2 limitations,
  `passage_refs`/`observation_refs`; learner reports travel only in
  `report_refs` and never alter observation values (byte-identical suggestion
  with and without reports). Region-mismatched reports add a caveat, not a
  diagnosis. Empty or below-threshold evidence yields `suggestion=None` with
  an explicit limitation (e.g. the Voices `[-4, 5, 2]` case cites the
  7-semitone rule).
- **Effectiveness: unproven.** Stated in every rationale and limitation. No
  outcome was measured; synthetic success must not be reported as learning
  benefit.
- **Verdict.** Traceable and actionable as text, honestly bounded — but a
  single uncalibrated heuristic. The numeric threshold could be misread as an
  established difficulty claim; it is not one.

## 5. Area C — flexible interaction (LS-04/LS-08/LS-09)

- **Learner control.** Journal-only saves confirm scope/permission/ID with
  `aid_generated=False`; inspection shows entries, permissions, and current
  summaries only; corrections supersede (old dated, never selected);
  deletion removes entries, permissions, and dependent summaries; exclusion
  wins and is reversible; per-request `ContextScope.NONE` selects empty
  context even with saved entries present. No onboarding, profile, rating,
  hotspot gate, or practice plan is required anywhere.
- **Optional history.** V1–V7 demonstrate entering with no history, saving
  without help, returning after a gap, revising, withdrawing, and ignoring
  history — all deterministically reproducible (identical repeated requests
  give identical result payloads).
- **Verdict.** Control requirements met for the declared operations. Deletion
  leaves no tombstone; entries carry no edition identity (version risk is
  surfaced only as a `score_version_unverified` warning); summaries are
  hand-built `ContextSummary` records, not system inference.

## 6. Joint evaluation (score × report × history)

| Comparison | Evidence | Finding |
| --- | --- | --- |
| Score-only vs. score-plus-report | Same [0,4) request, empty vs. permitted store | Identical observation values and suggestion; framed response adds only `report_refs` + "Framed by learner report(s)…" in rationale |
| History used vs. declined | REFERENCED/PERMITTED vs. NONE on identical history | NONE selects nothing and references nothing; observations and suggestion identical |
| Reported-hard non-hotspot | Voices passage, `difficulty == ()`, no hotspot codes/text | Manual help flows without fabrication; honest below-threshold limitation |
| Conflicting context | Measure-2 report alongside opening-jump report | Single region-mismatch caveat; facts unchanged |
| Stale context | 2026-08-01 general habit note | Dated verbatim framing; no trait inference |
| Revision | 9-day-later correction | Latest revision selected; old retained but unreferenced |

## 7. Language and overclaim audit

Automated scans (`test_return_visits.py`, `test_evaluation_ls10.py`) assert no
system text (rationales, limitations, diagnostics) contains: progress,
improvement, inactivity, trait, streak, adherence, elapsed-time, poor,
unmotivated, or day/week/month/gap/since language. Denials are explicit
("not a diagnosis of why the passage feels hard", "not a diagnosis of playing
ability"). This report itself claims no measured learning benefit, no model
comparison (no AI exists here), no product readiness, and no real-data
findings.

## 8. Limitations and misleading-personalization risks

1. One synthetic history, three synthetic fixtures, one observation family,
   one heuristic aid — coverage is narrow by design (M2 scope).
2. The 7-semitone threshold is uncalibrated; its numeric presentation risks
   misreading as an established claim.
3. Conflict handling is structural (region overlap) only; textual disagreement
   is not interpreted, and "framed by" records influence without endorsing
   the report.
4. Hand labels are staff-inferred; region-less simultaneous observations need
   explicit downstream handling.
5. No edition identity on entries; cross-version reuse relies on a warning.
6. Pedagogical effectiveness is entirely unproven (LS-10 human evaluation
   still required; owner/reviewer walkthroughs pending).

## 9. Review status

**Not yet reviewed by teacher/company owner. LS-01–LS-10 are implemented and
pending lead review.** No walkthrough has occurred; no approval for real
learner data has been sought or granted. Proposed walkthrough: replay V1–V7
via `test_return_visits.py`, inspect the E01–E12 rows against the cited
tests, and confirm the section-8 risks before any LS-11 increment decision.

## Appendix E — evidence table

Each row: evaluation check → scenario(s) → test file :: test → key asserted fact.
All rows are machine-checked by `research/learning_support/tests/unit/test_evaluation_ls10.py`
(presence of IDs/links plus live re-verification of the starred facts).

| ID | Area | Scenario | Test | Key fact |
| --- | --- | --- | --- | --- |
| E01 | A | S1 | passage_practice/tests/unit/test_observations.py :: test_user_selected_transitions_are_signed_facts | ★ Values [-12, 14, 2, 1], FACT, simultaneous pair region-less with diagnostic |
| E02 | A | S1/S2 | passage_practice/tests/unit/test_observations.py :: test_evidence_refs_resolve_to_source_events | Every observation's source refs resolve |
| E03 | A | S6 | passage_practice/tests/unit/test_observations.py :: test_empty_and_single_attack_abstain_without_diagnosing_learner | `insufficient_attacks`, no learner language |
| E04 | A | S7 | passage_practice/tests/unit/test_selection.py :: test_rejects_malformed_and_unlocatable_bounds; passage_practice/tests/unit/test_user_selected_entry.py :: test_unresolved_selections_are_explicit_without_fabrication | Reason-coded `UnresolvableRegion`, no guessing |
| E05 | A | S1 | passage_practice/tests/unit/test_observations.py :: test_hand_scoping_is_marked_inference; test_analyzer_route_observes_identically | Hand scope = INFERENCE; routes agree |
| E06 | B | S1/N2 | passage_practice/tests/unit/test_transition_aid.py :: test_no_history_baseline_aid_is_traceable | ★ Grounded +14/-12 suggestion, objective, rationale, limitations, `prototype_unvalidated` |
| E07 | B | S3 | passage_practice/tests/unit/test_transition_aid.py :: test_applicable_report_frames_without_altering_facts; test_conflicting_region_report_yields_caveat_not_diagnosis; interaction/tests/unit/test_return_visits.py :: test_visit4_conflicting_reports_caveat_without_changing_facts | ★ Reports frame only; mismatch caveat; facts identical |
| E08 | B | S6 | passage_practice/tests/unit/test_transition_aid.py :: test_empty_observations_abstain_honestly; test_below_threshold_returns_limitation; interaction/tests/unit/test_return_visits.py :: test_visit7_reported_hard_non_hotspot_gets_manual_help | ★ Aid-shaped abstentions; Voices [-4, 5, 2] below threshold |
| E09 | C | S4/S5 | learner_context/tests/unit/test_context_store.py (16 tests); interaction/tests/unit/test_interaction_surface.py (14 tests) | ★ Save/inspect/correct/delete/exclude/NONE semantics |
| E10 | C | V1–V7 | interaction/tests/unit/test_return_visits.py (8 tests) | ★ Full multi-visit history with exact refs per stage |
| E11 | joint | S3/S5 | interaction/tests/unit/test_return_visits.py :: test_visit2_changed_report_supersedes_without_rewriting_history; test_visit5_ignored_history_matches_score_only_evidence; test_visit7_reported_hard_non_hotspot_gets_manual_help | ★ Score-only ≡ score+report on facts; NONE ≡ score-only; non-hotspot manual path |
| E12 | joint | global | interaction/tests/unit/test_return_visits.py :: test_outputs_claim_no_progress_inactivity_traits_or_diagnosis; tests/unit/test_evaluation_ls10.py :: test_report_makes_no_overclaims | ★ Forbidden-language scan; report guards |
