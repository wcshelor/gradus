# Task list — 2026-09-05 — Flexible, piece-centered piano learning support

Status: LS-01 through LS-11 are implemented and pending lead/human review.
The next selected increment is the CEO walkthrough prototype milestone
(DEMO-01–DEMO-10), planned but not yet built.

## 1. Purpose and authority

Investigate how AI and computational systems can help someone learn a chosen
piano piece, at the beginning, midway through, or when returning with a specific
problem. The company operates a piano-learning app; the research should support
useful features or an assistant-like experience without prematurely committing
to either interface or to an end-to-end autonomous tutor.

The learner can progress independently and return for relevant assistance.
No prescribed course, mandatory onboarding, continuous observation, or complete
practice history is assumed. No live-playing feedback, microphone performance
analysis, MIDI keyboard requirement, or automatic performance tracking is in
scope for this phase.

This is the cross-area plan linked from [project direction](project_direction.md).
It supersedes earlier **global** difficulty-first sequencing, but preserves
component contracts and useful implementation work. Detailed implementation
documents remain with their research areas. Read applicable `AGENTS.md` files
before changes; reconcile local contract conflicts explicitly rather than
treating this document as permission to bypass them.

This plan records implemented research-slice work and its evidence boundaries.
It does not authorize collecting real learner data, deploying into the company
app, sending data to external models, or claiming product readiness. New work
should claim a bounded DEMO or component task and record verification rather
than expanding the whole capability wishlist at once.

## 2. Three complementary areas

| Area | Responsibility | Example question | Evidence boundary |
| --- | --- | --- | --- |
| A. Semantic understanding of the piece | Score facts, patterns, relationships, structure, and descriptive demands | “What is happening in this passage, and where else does it occur?” | Distinguish encoded facts, measured observations, and musical hypotheses. |
| B. Development of pedagogical assistance | Relate supported observations and stated needs to explanations, practice approaches, and aids | “What could I try to make this transition easier to learn?” | A suggestion needs an objective, rationale, scope, and caveats; usefulness requires evaluation. |
| C. Support of flexible interaction | Questions, passage selection, optional journaling/context, and resuming when useful | “Last time I tried hands separately; today the join still feels uncertain.” | A self-report is not an observed performance result; saved context must be inspectable and controllable. |

These are complementary responsibilities, not three mandatory services, packages,
or sequential screens. Area A can answer a musical question without a practice
recommendation. Area C can save a note without triggering analysis. Area B can
work from a user-selected passage without a detected hotspot. A difficulty
overview can suggest where to investigate, but cannot overrule what the learner
says is difficult or make other passages ineligible for help.

### Existing work and ownership

- `research/piano_difficulty/` retains parsing, normalization, raw descriptors,
  generic temporal regions, and difficulty profiles. It is the most developed
  capability, not the architectural center of the learning system.
- `research/learning_support/passage_practice/` retains its source contracts,
  tests, and plans for passage-specific semantics, diagnoses, and transformations.
  Its hotspot-to-exercise route is one bounded experiment. Do not rebuild it.
- Learner-context and interaction experiments live under
  `research/learning_support/`, not as a new top-level application.
- Keep `research/shared/` for demonstrated multiple consumers only. Do not move
  score types or create an umbrella “assistant framework” speculatively.
- Keep literature provenance in `literature/`, implementation decisions beside
  their owner, and repository-wide decisions in `docs/`.

## 3. Supported starting points and intended behavior

| Starting point | Intended response | Must not require |
| --- | --- | --- |
| Whole piece, no history | An overview or a response to a piece-level question | A learner profile or difficulty grade |
| Learner-selected passage | Relevant observations and, if requested, a supported aid | Detection as a hotspot |
| “These measures are hard for me” | Preserve the report and optionally clarify the aspect that feels hard | Agreement from the computed ranking |
| Analyzer-suggested section | Offer it as a candidate and expose supporting measurements | Learner acceptance of the ranking |
| Journal-only entry | Save or retain only as requested; no unsolicited intervention required | Analysis or exercise generation |
| Return after a gap | Use permitted context with timestamps; ask what changed only when useful | A complete account of intervening practice |
| “Ignore my history for this” | Answer from the request and score alone | Deleting the history to disable its use |

Illustrative, synthetic example: “In measures 17–20, I can play the hands
separately, but lose my place when joining them. Slow repetition didn't help.”
The system should preserve the learner's words, locate the selected passage,
inspect relevant musical evidence, and offer a bounded next option if supported.
It must not translate that report into “measured poor coordination,” claim a
specific cause without evidence, or send the learner to a higher-ranked hotspot.

## 4. Optional journaling and learner context

### What may be useful to record

- Session notes: what was attempted, an optional time/duration or self-reported
  tempo, approach tried, what seemed to help, and a possible next intention.
- Piece/passage notes: what feels difficult, which hand/voice/transition the
  learner means when known, what feels secure, and questions to revisit.
- Goals and preferences: why they are learning the piece, preferred explanation
  style, available practice time, and types of assistance they want or dislike.
- Self-described tendencies and habits: for example, “I tend to restart from the
  beginning” or “I prefer working in short sections.” These are reports, not
  permanent traits or diagnoses.

Free text is sufficient to start. Structured fields are optional refinements,
not a compulsory form. No mandatory difficulty rating, personality inventory,
precise ability level, streak, or adherence score is required.

### Minimum conceptual records specified in LS-03

These are contract requirements to evaluate against existing models, not a
prescription for a database or final class names.

| Record | Minimum meaning |
| --- | --- |
| Assistance request | Current intent, optional question, piece/version reference, optional exact region, selection origin, and permitted context scope |
| Learner report / journal entry | Stable ID, original text, author/source, recorded time, optional practice time, scope (general/piece/region), and optional user-provided tags/fields |
| Context permission | Session-only versus explicitly saved intent, whether an entry may inform this request/later requests, and correction/deletion state |
| Derived context summary | Source-entry IDs, generation method/version, time, tentative interpretation, and confirmation state where used |
| Assistance result | Requested need, relevant score evidence and self-reports separately referenced, optional suggestion/objective, rationale, limitations, and optional learner response |

Store stable piece/version identity alongside score locations; printed measure
numbers alone are not enough. Unresolved references remain unresolved until
clarified. Do not attach an old note to a different score edition silently.

### Interpretation and data-control requirements

1. Separate score facts, learner reports, and system hypotheses in contracts and
   presentation. Reports can inform relevance without becoming verified facts
   about playing ability.
2. Preserve dates and scope. A difficulty reported last month need not still
   apply, and one passage does not establish a general weakness.
3. Absence of an entry is not evidence of inactivity. A claimed improvement is
   a reported outcome, not an independently measured improvement.
4. Repeated reports may motivate a tentative pattern for confirmation. Do not
   silently infer fixed abilities, psychological/medical traits, or habits from
   a small history. Do not build an automatic trait classifier in the first slice.
5. Let the learner inspect, correct, exclude, and delete saved entries; disable
   history use for an individual request. Start session-only unless saving is
   explicitly chosen. Do not equate saving with consent to external processing.
6. Derived summaries must reference their inputs and be invalidated or recomputed
   after corrections/deletions. Deleted context must not survive as hidden memory.
7. Retrieve only relevant, permitted context. Sending the entire journal to every
   request is not an acceptable default. Record which entries influenced an aid.
8. Score text and journal text are data, not instructions that can override the
   system's constraints or trigger tools. Test this if an LLM is introduced.
9. Use synthetic histories in committed tests. Before real data, decide storage,
   retention, deletion, access, external processing, and company boundaries with
   the owner. Do not claim production privacy controls from a local prototype.

## 5. Scope and research claims

The first integrated experiment should show that a learner-selected passage and
an optional report can yield an inspectable, relevant aid, without hotspot gating
or playing capture. A separate journal action should work without generating aid.
The learner should be able to return, revise the reported difficulty, or ignore
history without starting the piece over.

The semantic and pedagogical subset remains deliberately narrow. Existing
broken-chord work is a candidate for reuse, not a commitment to support every
pattern, every learner level, or every pedagogical aid in the thesis. The broad
interaction model permits varied stages; evaluation must still name the actual
supported material and participant context.

AI may help interpret a question, propose structured tags for confirmation,
retrieve appropriate evidence, or express a grounded explanation. It is not
required for every operation. Start with deterministic contracts/baselines and
compare any AI contribution against them. An LLM must not invent score evidence,
silently alter notation, or claim observed progress.

Out of scope for the initial implementation: live MIDI/audio assessment,
autonomous long-term curriculum, automatic fingering/biomechanical advice,
unconstrained exercise generation, general learner profiling, production account
infrastructure, and deployment into the company's app.

## 6. Bounded implementation record

All LS tasks below are implemented and pending lead/human review. Read
applicable instructions and actual source before continuing with DEMO or
component work. New implementation steps should update their execution log or
handoff with changed-file notes, tests/evidence, limitations, and a next
unblocked step. Do not mark human evaluation complete based on automated tests.

### LS-01 — Define the first learning-support slice

**Depends on:** none. **Owner:** learning-support experiment documentation.

Specify one supported musical subset and a small set of user needs. Include
user-selected passage help, no-history use, a journal-only action, and a returning
learner who changes or withdraws an earlier report. Include a case where perceived
difficulty disagrees with computed ranking. Define useful outputs and abstention
before choosing an interface or AI model.

**Done when:** the slice has positive/negative scenarios, explicit exclusions,
and a reviewable success rubric. Candidate aids need not all be implemented.

### LS-02 — Reconcile existing passage plans with independent entry points

**Depends on:** LS-01. **Owner:** `research/learning_support/passage_practice/`.

Read its scoped rules and required design files; inspect code, tests, work-package
status, and handoffs. Map what can already represent source/region evidence and
what assumes a hotspot. Document the smallest adapter for user-selected regions,
preserving selection origin and optional difficulty evidence. Update local plans,
checklists, dependencies, status text, and accepted decisions through their review
process before changing contracts. Do not erase the existing hotspot regression.

**Done when:** an implementation map identifies reused contracts, genuinely missing
pieces, affected work packages, and required tests for both user-selected and
analyzer-suggested entry. Local plans no longer imply all assistance needs a hotspot.

### LS-03 — Specify minimal request, journal, and context contracts

**Depends on:** LS-01, LS-02. **Owner:** a documented experiment boundary under
`research/learning_support/`; no speculative move to `research/shared/`.

Define the records in section 4, reusing source/time contracts. Separate request
intent from persisted history. Specify optionality, source identity, revision,
time, scope, permissions, and unknown values. Decide session-only behavior and
the smallest explicit local save mechanism for synthetic data. Write representative
payloads and contract tests, including a free-text-only note and unresolved region.

Execute this task in two bounded substeps (D-013 accepted design):

1. **LS-03a — Passage-first investigation boundary.** Follow passage-practice
   `docs/contracts.md` and `docs/entry_points.md`: reuse `Passage` in one minimal
   `PassageInvestigation` envelope for both entries, explicit selection origin,
   optional hand, and zero-or-more validated difficulty-context references.
   Require passage identity downstream; never fake hotspot IDs or attribution.
   Implement only minimal types, validation, versioned examples, and contract
   tests. Defer adapters/selection to their existing tasks; do not implement the
   full attribution or diagnosis tree to satisfy this contract task.
2. **LS-03b — Learner request/journal/context contracts.** Complete the records
   above using the investigation boundary where a resolved passage exists.
   Keep unresolved/free-text requests valid without making `Passage` accept
   invalid intervals. Keep learner data out of score/feature models.

LS-03a depends on LS-01/LS-02, not T05.1/T05.3. The latter consume its contract.
Verify existing implementations first; no new parser, detector, duplicate region
type, or shared framework. Tests must cover manual and suggested entry, optional
context, enrichment without changing origin/identity, source-version mismatch,
exact serialization, and resolvable evidence. Update stale documentation tests
that freeze a proposed decision or pending board status, not behavioral assertions.

**Done when:** contracts can express all LS-01 scenarios without a mandatory
profile, rating, hotspot, model call, or performance recording.

This task completes only when both substeps pass their acceptance tests and the
full suite. D-013's design review is resolved; runtime review is still required.

### LS-04 — Implement optional context operations and provenance

**Depends on:** LS-03. **Owner:** learner-context experiment.

Implement create/read/correct/delete/exclude and explicit save behavior on
synthetic records, with stable IDs and the declared persistence boundary. Add
relevant-context selection by request scope and permission. If summaries are
used, link them to source entries and invalidate them after source changes.
Do not add automatic habit inference or external model processing here.

**Done when:** tests prove session-only notes are not unintentionally persisted,
excluded/deleted entries cannot influence future responses or summaries, score
version mismatches are surfaced, and empty history remains valid input.

### LS-05 — Accept user-selected regions independently of difficulty

**Depends on:** LS-02, LS-03. **Owner:** passage-specific adapter; generic parsing
repairs, if any, remain in the difficulty subproject.

Resolve a selected region to exact source events using existing score contracts.
Keep user selection, reported concern, and measured difficulty distinct. Accept
a whole-piece request or unresolved selection with an explicit outcome. Preserve
the analyzer-suggested route as another entry point, without a nonzero-score gate.

**Done when:** contract tests handle a valid low-ranked/user-selected passage
without computing a difficulty profile, a suggested hotspot, and invalid/ambiguous
locations without fabricating evidence.

### LS-06 — Produce one bounded semantic observation

**Depends on:** LS-05. **Owner:** passage-practice semantic layer.

Select a pattern/relationship justified by LS-01 and existing work. Link every
observation to the source events and method; distinguish direct facts from
inference. Add exact attribution only where the chosen observation requires it,
not for every factor before starting. Test nearby negative/ambiguous material and
explicit unsupported cases. Keep learner-context concepts out of score extractors.

**Done when:** the chosen observation works on either entry route, has resolvable
evidence, and abstains outside its supported subset without diagnosing the learner.

### LS-07 — Develop one grounded pedagogical aid

**Depends on:** LS-03, LS-06. **Owner:** pedagogical-assistance layer.

Choose one explanation or practice approach for the selected need. Record its
objective, evidence, pedagogical rationale/provenance, applicability, and caveats.
Use optional self-report to select or frame the aid, not to alter score facts.
Test a no-history baseline, an applicable reported difficulty, and a conflicting
or unsupported report. If a notation transformation is selected, use the existing
provenance and parse-after-write requirements; do not make exercise export mandatory
for a text-only aid.

**Done when:** an aid is traceable and actionable within the declared scope;
unsupported needs receive an honest limitation or focused clarification, not a
plausible but ungrounded diagnosis. Pedagogical effectiveness remains unproven.

### LS-08 — Expose a minimal flexible interaction surface

**Depends on:** LS-04, LS-05, LS-07. **Owner:** learning-support experiment.

Select the smallest interface needed to exercise the scenarios: a simple local
form, CLI, or API harness is sufficient. Allow request help, save a note without
help, inspect/correct history, and request help without history. Do not require
a chat interface or a fixed sequence of practice steps. If free text is mapped
to structured intent by AI, validate its output and retain the original text;
deterministic tests must not require network/model access.

**Done when:** a learner can enter at different stages, decline a suggestion,
and return without completing onboarding or a prescribed practice plan.

### LS-09 — Test return visits, revisions, and uncertain context

**Depends on:** LS-08. **Owner:** integration tests in learning support.

Exercise a multi-visit synthetic history: first report, independent practice,
return after a gap, changed difficulty, corrected note, ignored history, and
deletion. Assert what evidence/context each response uses. Include a stale
habit report, conflicting reports, and a learner difficulty absent from the
analyzer's top sections. No elapsed-time or missing-entry inference may become
a claim of progress or inactivity.

**Done when:** assistance respects the latest permitted context, old reports
remain dated rather than authoritative, and the same request can run without
history. Deletion and correction propagate to derived summaries.

### LS-10 — Evaluate the three areas separately and together

**Depends on:** LS-09. **Owner:** experiment evaluation documentation/evidence.

Evaluate semantic correctness/evidence, pedagogical relevance/actionability, and
interaction burden/control separately. Compare score-only versus score-plus-
self-report responses on declared scenarios. If AI is added, compare with the
deterministic baseline and record model/settings and failure cases. Prepare
owner/reviewer walkthroughs; obtain approval before collecting real learner data.
Do not treat synthetic scenario success as measured learning benefit.

**Done when:** there is a reproducible technical report and an explicit human
review status, including unsupported cases and misleading personalization risks.

### LS-11 — Select the next research increment with the owner

**Depends on:** LS-10. **Owner:** repository-wide direction and local roadmap.

Use evidence to choose one next increment: another semantic pattern, another aid,
a better context interaction, or a narrowly specified company integration.
Record what is deferred, what the thesis can claim, and any new data or product
boundary. Do not automatically expand to live feedback or universal assistance.

**Done when:** the next work package has explicit scope and evidence-based
acceptance criteria; the broad vision has not become an unbounded feature list.

## 7. Relationship to the existing difficulty checklist

The [difficulty-consolidation task list](../research/piano_difficulty/docs/Task_list_2026-09-05_difficulty_analysis_consolidation.md)
remains valid for that component. Its DC IDs are local to that file. Do not
repeat completed runtime promotion or discard pending quality work.

| Existing work | Revised role |
| --- | --- |
| DC-01–DC-06: baseline, inventory, semantics, fixtures, result contract | Harden reusable piece-understanding evidence; coordinate only on contracts the selected LS slice actually consumes. |
| DC-07–DC-10: detector/display separation, peaks, sections | Improve one optional source of candidate regions; not a prerequisite for user-selected passage assistance. |
| DC-11–DC-14: outputs, reproducible checks, sensitivity, installation | Establish quality and limits of the analysis component, not the whole assistant. |
| DC-15–DC-16: review and acceptance | Accept the analyzer's behavior independently of acceptance of pedagogical or interaction experiments. |
| SB-01–SB-04: semantic follow-up sketch | Refine through LS-02/LS-05–LS-07 and existing passage work packages. Do not implement a duplicate semantic pipeline. |

The completed LS slice proceeded without requiring all DC tasks. Future DEMO
work should follow the same rule: create a small explicit component dependency
when needed rather than a global “finish difficulty first” gate.

## 8. Milestones and completion boundaries

- **M1 — Coherent plan/contracts:** LS-01–LS-03 complete; existing passage plans
  reconciled; no forced hotspot or learner-profile gate.
- **M2 — One usable research slice:** LS-04–LS-09 complete; user-selected passage,
  grounded aid, journal-only action, and returning-context scenarios work without
  performance capture. The semantic subset is clearly limited.
- **M3 — Evaluated next direction:** LS-10–LS-11 complete, or explicitly pending
  human review. Engineering success and learning benefit are reported separately.
- **M4 — CEO walkthrough prototype (planned, not built):** DEMO-01–DEMO-10 in
  [ceo_demo_milestone_2026-09-06](../research/learning_support/ceo_demo_milestone_2026-09-06.md)
  scope a thin, local, unpolished presentation harness over the M2 slice and
  the difficulty overview. It comes after the LS research slice, reuses
  LS-10's limitations/review status, keeps difficulty as one modular source,
  and claims no product readiness, effectiveness, or integration.

The analyzer retains its own acceptance milestone. None of these milestones
alone claims a production assistant, support for all levels/material, or measured
improvement in learning outcomes.

## 9. Execution log

Current state (2026-09-06): LS-01 through LS-11 are implemented and pending
lead/human review. The selected next increment is DEMO-01 of the CEO
walkthrough prototype milestone. Final verified LS baseline: full suite
`353 passed, 7 skipped`; learning-support doc/link suite `32 passed`;
`git diff --check` clean. Nothing committed or pushed by these changes.

Earlier rows preserve historical per-step evidence and superseded next-step
language for auditability.

| Date | Change | Status | Evidence / remaining work |
| --- | --- | --- | --- |
| 2026-09-05 | Reframed program into three areas; added optional journaling/context, independent entry routes, and no-live-feedback scope | Planning revision only | Existing code preserved; LS-01–LS-11 pending; local passage-plan reconciliation explicitly assigned to LS-02 |
| 2026-09-05 | LS-01 complete (specification): first slice in `research/learning_support/first_slice.md` — one-hand broken-chord subset reused from passage-practice `prototype_v1`; needs N1–N3; scenarios S1–S5 positive plus S6–S7 abstention; outputs/abstention/exclusions/success rubric; no runtime, interface, model, or data-collection change | Specification, pending review | Changed: `research/learning_support/first_slice.md` (new), `research/learning_support/README.md` (link), `research/learning_support/tests/unit/test_first_slice.py` (new, 9 link/consistency/acceptance checks), `pytest.ini` (added `research/learning_support/tests` to testpaths). Tests: new file 9 passed; full suite 207 passed, 7 skipped (skips: optional local-corpus/ScoreAnalyzer fixtures, same as baseline). Limitation: rubric is document-reviewable only; automated scenario tests arrive with LS-04–LS-09; pedagogical effectiveness remains unproven | LS-02 next (reconcile passage plans with independent entry points) |
| 2026-09-05 | LS-02 complete (map + prose): entry reconciliation in `research/learning_support/passage_practice/docs/entry_points.md` — routes (A) analyzer-suggested and (B) user-selected converge at `Passage`; reused contracts verified in source (ScorePosition/Interval, SourceRef, Diagnostic, Passage, View; zero `hotspot` refs in `src/passage_practice/`); missing pieces named (manual selection API T02.5, adapter T05.3, hotspot-optional diagnosis gap for LS-03); smallest adapter documented (root `Passage` purpose=DETECTION, manual method + Diagnostic origin, optional evidence by reference, S7 mismatch behavior); D-013 proposed pending lead review; local prose corrected (README, architecture, contracts interim notes, prototype_v1, testing_strategy, traceability, review_checkpoints, WP-06 goal); no contract/status-board changes; hotspot regression kept | Map + prose, pending review (D-013) | Changed: `docs/entry_points.md` + `tests/unit/test_entry_points_ls02.py` (new, 9 checks); prose-only edits to README/architecture/contracts/prototype_v1/testing_strategy/traceability/review_checkpoints/WORK_PACKAGES/decisions. Tests: LS suites 18 passed; passage-practice 80 passed; overview/CLI/snapshot 23 passed; full suite 216 passed, 7 skipped (same optional-corpus skips). Limitation: adapter awaits T05.3 implementation; hotspot-ID optionality awaits LS-03 | LS-03 next (minimal request, journal, context contracts) |
| 2026-09-05 | LS-03a complete: shared `PassageInvestigation` contract implemented and tested (`passage_investigation.v1`, `difficulty_evidence.v1`, `contribution.v1`) | Implemented, pending review | Changed: `research/learning_support/passage_practice/src/passage_practice/models/investigation.py` (new: `SelectionOrigin`, `Contribution`, `DifficultyEvidence`, `PassageInvestigation` + `with_evidence` enrichment), `models/__init__.py` (exports), `tests/unit/test_investigation.py` (new, 24 tests: both origins, empty difficulty, enrichment preserves origin/identity, no manufactured hotspots, orphan-score rejection, source/coverage mismatch, exact-time serialization, versions, frozen payloads). Reused `Passage`/`ScoreInterval`/`Diagnostic` unchanged. Tests: focused learning-support suites 123 passed; full suite 241 passed, 7 skipped (same optional-corpus skips). Limitation: contract only; adapters (T05.2/T05.3) and full diagnosis/attribution trees not implemented; no adapter-equivalence claim | LS-03b next (learner request, journal, context contracts) |
| 2026-09-05 | LS-03b complete: learner contracts implemented and tested in new boundary `research/learning_support/learner_context/` (`assistance_request.v1`, `journal_entry.v1`, `context_permission.v1`, `context_summary.v1`, `assistance_result.v1`) | Implemented, pending review | Changed: `learner_context/README.md` (boundary choice), `src/learner_context/models.py` + `__init__.py` (new), `tests/unit/test_learner_contracts.py` (new, 20 tests: free-text-only notes, scope/region invariants, revision chain, ISO time, permission matrix, summary sources, unresolved requests, evidence/report separation, required rationale+limitations, versions, frozen payloads), `pytest.ini` (learner_context testpaths/pythonpath). Reuses `ScoreInterval`/`Diagnostic`; passages by ID ref only. Tests: new file 20 passed; full suite 261 passed, 7 skipped (same optional-corpus skips). Limitation: contracts only; storage/selection/invalidation arrive in LS-04; no real data | LS-03 done; LS-04 next (optional context operations and provenance) |
| 2026-09-05 | LS-04 complete: `ContextStore` operations implemented and tested in `research/learning_support/learner_context/src/learner_context/store.py` (`context_store.v1`, `selected_context.v1`) | Implemented, pending review | Changed: `store.py` + `__init__.py` exports (new `ContextStore`/`SelectedContext`: create session-only-by-default, read, correct via `supersedes` revisions, delete with summary cascade, exclude, scope/permission selection, summary currency, JSON save/load of saved records only), `tests/unit/test_context_store.py` (new, 16 tests), `README.md` (operations section). No inference, no external calls. Tests: learner-context files 36 passed; full suite 277 passed, 7 skipped (same optional-corpus skips). Proven: session-only never persisted; excluded/deleted entries never selected and stale/cascade summaries; version warnings on edition-bound entries; empty history valid. Limitation: deletion has no tombstone; cross-session "later request" handling deferred to LS-08; no real data | LS-05 next (user-selected regions independent of difficulty) |
| 2026-09-05 | LS-05 complete (with WP-02 T02.2–T02.6 dependency built first): exact selection + user-selected entry implemented and tested | Implemented, pending review | Changed: `passage_practice/src/passage_practice/passages/{__init__,selection,investigate}.py` (new: `select_passage`/`refine_selection`/`whole_piece_range`/`locate_measure_by_number`, `SelectedPassage`/`PassageContext`, `UnresolvableRegion`, `manual_investigation`/`whole_piece_investigation`), `tests/fixtures/selection_{two_staff,ties,two_voices}.musicxml` + `manifest.md` (new synthetic), `tests/unit/test_selection.py` (18 tests) + `test_user_selected_entry.py` (7 tests), `docs/decisions.md` (D-014 proposed for Q-003), `docs/entry_points.md` (map status). Reused ScoreIR/loader unchanged; no difficulty imports on the manual path (import-delta test). Proven: low-demand passage investigated with no profile; concern/difficulty/score-evidence distinct; whole-piece explicit; unresolved explicit (reason codes); analyzer origin valid empty/zero with no gate. Tests: full suite 302 passed, 7 skipped (same optional-corpus skips). Limitation: T05.2 analyzer translation still pending; no WP gate released; D-014 needs lead review | LS-06 next (one bounded semantic observation) |
| 2026-09-05 | LS-06 complete: consecutive-attack pitch-interval observations implemented and tested (`observation.v1`, `observation_result.v1`) | Implemented, pending review | Changed: `passage_practice/src/passage_practice/models/observations.py` (new `Observation`/`ObservationBasis`/`ObservationResult`) + `models/__init__.py` exports, `src/passage_practice/observations/__init__.py` (new `observe_pitch_transitions` via existing source resolver; hand-scoping marked INFERENCE, unscoped FACT; simultaneous pairs omit region with diagnostic; <2 attacks abstain), `tests/unit/test_observations.py` (new, 9 tests). No diagnosis, aid, attribution records, learner concepts, or LLM/UI. Proven: identical values on both entry routes; refs resolve; tie collapse yields no self-transition; empty/single/unknown abstain without learner claims. Tests: passage-practice 138 passed; full suite 311 passed, 7 skipped (same optional-corpus skips). Limitation: single transition family only; hand filter relies on staff-inferred labels; region None for simultaneities | LS-07 next (one grounded pedagogical aid) |
| 2026-09-05 | LS-07 complete: text-only `transition_practice` aid implemented and tested over LS-06 observations (no new public contract; reuses `AssistanceResult`) | Implemented, pending review | Changed: `passage_practice/src/passage_practice/aids/__init__.py` (new integration layer above observations; deterministic ≥7-semitone rule, `prototype_unvalidated` provenance; reports frame by reference only; region-mismatched reports get a caveat; empty/below-threshold yield aid-shaped abstentions), `tests/unit/test_transition_aid.py` (new, 6 tests: no-history baseline, framed report, conflicting report, empty, below-threshold, bad inputs). Correction: LS-03b prose fields (`text`/`interpretation`/`need`/`rationale`) no longer capped at ID length (new `_check_text`); existing contract tests still pass. Proven: suggestion names grounded moves (+14) with obs/source refs; report never alters score values; rationale+limitations always present; effectiveness unproven stated. Tests: full suite 317 passed, 7 skipped (same optional-corpus skips). Limitation: single heuristic aid; threshold uncalibrated; no diagnosis engine, notation, or UI | LS-08 next (minimal flexible interaction surface) |
| 2026-09-05 | LS-08 complete: minimal deterministic `InteractionSession` harness implemented and tested over LS-04/LS-05/LS-07 contracts (no UI, no model, no parsing) | Implemented, pending review | Changed: `research/learning_support/interaction/README.md` + `src/interaction/{__init__,session}.py` (new: `InteractionSession` composes `ContextStore.select_context`, `manual/whole_piece_investigation`, `observe_pitch_transitions`, `suggest_transition_practice`; `save_note` journal-only with `JournalConfirmation(aid_generated=False)`; `inspect_context` shows entries/permissions/current summaries only; `correct/delete/set_excluded` delegate to store; `request_help` accepts loaded scores, falls back to `request.region` bounds, sets `investigation_ref`, returns layered `HelpResponse`; missing score/identity/region and `UnresolvableRegion` yield harness-method aid-shaped abstentions), `tests/unit/test_interaction_surface.py` (new, 14 tests: no-history grounded aid, framed report unchanged facts, NONE ignores saved context, region-from-request, journal-only, inspect saved+session, correction revision, delete/exclude, with/without history, missing-score/unresolved/out-of-range/empty abstentions, stray-region caveat), `pytest.ini` (interaction testpaths/pythonpath). Proven: report_refs separate, observation values identical with/without reports, NONE selects empty with saved entries present, superseded never selected, deleted/excluded never selected, abstentions carry explicit diagnostics with no learner-trait claims. Tests: focused interaction+learner-context+observations+aids 65 passed; full suite 331 passed, 7 skipped (same optional-corpus skips); `git diff --check` clean. Limitation: accepts loaded scores only (no file parsing in harness); no new wire contract/serialization; single observation family and single aid inherited from LS-06/LS-07; no chat/CLI polish, onboarding, or live feedback | LS-09 next (return visits, revisions, uncertain context) |
| 2026-09-05 | LS-09 complete: multi-visit return/revision scenario suite over the LS-08 harness (integration tests only, plus one genuine contract fix) | Implemented, pending review | Changed: `research/learning_support/interaction/tests/unit/test_return_visits.py` (new, 8 staged tests on one synthetic history: V1 first region report saved+used; 9-day gap as timestamps only; V2 correction supersedes with old dated/unselected; V3 stale 2026-08-01 habit report stays verbatim GENERAL context; V4 conflicting region report yields single mismatch caveat with identical suggestion/observations; V5 NONE run matches score-only evidence and is deterministic; V6 exclusion stales then deletion cascades `sum.1`; V7 sparse never-ranked voices passage gets manual USER_SELECTED help with `difficulty == ()`, no hotspot codes, honest below-threshold limitation; aggregate scan forbids progress/improv/inactive/trait/streak/adherence/elapsed/poor/unmotivated/day/week/month/gap/since in all system text), `learner_context/tests/unit/test_learner_contracts.py` (+1 regression test), `learner_context/src/learner_context/models.py` (fix: `AssistanceResult.limitations` now uses new `_check_text_tuple` prose validator instead of the 128-char ID cap — longer caveat sentences crashed construction; same defect class as the LS-07 prose-cap correction). Proven: exact entry/observation/aid refs asserted per stage; superseded/deleted/excluded never selected; NONE yields identical observations with empty report_refs; conflicting/stale reports appear only as refs/caveats; no LS-06/LS-07 semantic changes. Tests: focused interaction+learner-context+observations+aids 74 passed; full suite 340 passed, 7 skipped (same optional-corpus skips); `git diff --check` clean. Limitation: single synthetic history, one fixture family + voices; summary coverage via existing ContextSummary only; no elapsed-time semantics by design | LS-10 next (evaluate areas separately and together) |
| 2026-09-06 | LS-10 complete: reproducible technical evaluation `research/learning_support/evaluation_ls10.md` (2026-09-06) covering Areas A/B/C separately plus joint comparisons, with evidence table E01–E12 and explicit review status | Implemented, pending review | Changed: `research/learning_support/evaluation_ls10.md` (new: scope/reproduction/commands, fixture+scenario inventory, per-area verdicts with live-verified values [-12,14,2,1] and [-4,5,2], joint table score-only≡score+report/NONE/non-hotspot/conflict/stale/revision, language audit, 6 limitation/risk items incl. personalization risks, review status not-yet-reviewed with walkthrough proposal, Appendix E mapping checks to tests), `research/learning_support/tests/unit/test_evaluation_ls10.py` (new, 7 tests: E01–E12 link presence incl. fixture files, required-guard/forbidden-overclaim phrases with negation-aware and word-boundary matching, live re-verification of score-only≡score+report, NONE, non-hotspot path, correct/delete/abstention spot, forbidden-claim scan). No AI exists so the plan's AI-vs-baseline comparison is recorded N/A; no new observations/aids/UI; no real data; effectiveness unproven stated throughout. Tests: focused evaluation set 81 passed; full suite 347 passed, 7 skipped (same optional-corpus skips); `git diff --check` clean. Two test-side mistakes fixed (evidence-link substring form; overclaim matcher now word-boundary with `prototype_unvalidated` allowed-literal). Limitation: single synthetic history, 3 fixtures, 1 observation family, 1 heuristic aid; human evaluation (usefulness) still requires teacher/owner walkthrough | LS-11 next (select next research increment with owner) |
| 2026-09-06 | LS-11 complete: next increment selected as CEO walkthrough prototype (planning only; demo not built) | Implemented, pending review | Changed: `research/learning_support/ceo_demo_milestone_2026-09-06.md` (new: why-after-LS-10 rationale, reuse-vs-new table for the owner flow, 5 architecture guardrails incl. thin-harness and difficulty-as-one-source, graph-data boundary over overview payload series/regions/sections/composite, DEMO-01–DEMO-10 atomic tasks with owner/depends/done-when, deferred list, thesis-claim boundary), `research/learning_support/tests/unit/test_ceo_demo_milestone.py` (new, 6 doc tests: planning-only status, link resolution, all DEMO tasks with done criteria, plan reference + LS-11 closure, scope guards without product claims, modularity/not-difficulty-centered), milestones section (new M4 referencing the milestone doc). Proven: all owner flow beats map to existing components (`InteractionSession`, overview payload/SVG/CSV, exact selectors); no GUI/graph code added; no live feedback, real data, or product claims. Tests: new file 6 passed; full suite 353 passed, 7 skipped (same optional-corpus skips); `git diff --check` clean. Limitation: plan only — toolkit choice (stdlib default), demo scores/licenses, and walkthrough approval all deferred to DEMO tasks with owner/lead | DEMO-01 next (demo scores, fixture policy, walkthrough script skeleton; do not start implementation under LS-11) |
