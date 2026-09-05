# Task list — 2026-09-05 — Flexible, piece-centered piano learning support

Status: revised research and implementation plan; new capabilities below are
planned, not implemented. This revision changes planning only.

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

The current request authorizes revising plans, not implementing all proposed
features, collecting real learner data, deploying into the company app, or
sending data to external models. When implementation is requested, claim a
bounded task below and record its verification rather than implementing the
entire capability wishlist at once.

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
- New learner-context and interaction experiments stay under
  `research/learning_support/`; choose a documented local boundary during LS-03,
  not a new top-level application by default.
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

### Minimum conceptual records to specify in LS-03

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

## 6. Bounded implementation plan

All LS tasks below are pending. Read applicable instructions and actual source
before implementation; plans do not prove an API exists. Each task should end
with changed-file notes, tests/evidence, limitations, and a next unblocked step.
Do not mark human evaluation complete based on automated tests.

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

**Done when:** contracts can express all LS-01 scenarios without a mandatory
profile, rating, hotspot, model call, or performance recording.

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

LS-01–LS-03 can proceed without completion of all DC tasks. LS-05–LS-07 need
working source/region contracts and their own tests, not universally accepted
difficulty ranking. If a task exposes a missing upstream capability, create a
small explicit component dependency rather than a global “finish difficulty first” gate.

## 8. Milestones and completion boundaries

- **M1 — Coherent plan/contracts:** LS-01–LS-03 complete; existing passage plans
  reconciled; no forced hotspot or learner-profile gate.
- **M2 — One usable research slice:** LS-04–LS-09 complete; user-selected passage,
  grounded aid, journal-only action, and returning-context scenarios work without
  performance capture. The semantic subset is clearly limited.
- **M3 — Evaluated next direction:** LS-10–LS-11 complete, or explicitly pending
  human review. Engineering success and learning benefit are reported separately.

The analyzer retains its own acceptance milestone. None of these milestones
alone claims a production assistant, support for all levels/material, or measured
improvement in learning outcomes.

## 9. Execution log

| Date | Change | Status | Evidence / remaining work |
| --- | --- | --- | --- |
| 2026-09-05 | Reframed program into three areas; added optional journaling/context, independent entry routes, and no-live-feedback scope | Planning revision only | Existing code preserved; LS-01–LS-11 pending; local passage-plan reconciliation explicitly assigned to LS-02 |
| 2026-09-05 | LS-01 complete (specification): first slice in `research/learning_support/first_slice.md` — one-hand broken-chord subset reused from passage-practice `prototype_v1`; needs N1–N3; scenarios S1–S5 positive plus S6–S7 abstention; outputs/abstention/exclusions/success rubric; no runtime, interface, model, or data-collection change | Specification, pending review | Changed: `research/learning_support/first_slice.md` (new), `research/learning_support/README.md` (link), `research/learning_support/tests/unit/test_first_slice.py` (new, 9 link/consistency/acceptance checks), `pytest.ini` (added `research/learning_support/tests` to testpaths). Tests: new file 9 passed; full suite 207 passed, 7 skipped (skips: optional local-corpus/ScoreAnalyzer fixtures, same as baseline). Limitation: rubric is document-reviewable only; automated scenario tests arrive with LS-04–LS-09; pedagogical effectiveness remains unproven | LS-02 next (reconcile passage plans with independent entry points) |
| 2026-09-05 | LS-02 complete (map + prose): entry reconciliation in `research/learning_support/passage_practice/docs/entry_points.md` — routes (A) analyzer-suggested and (B) user-selected converge at `Passage`; reused contracts verified in source (ScorePosition/Interval, SourceRef, Diagnostic, Passage, View; zero `hotspot` refs in `src/passage_practice/`); missing pieces named (manual selection API T02.5, adapter T05.3, hotspot-optional diagnosis gap for LS-03); smallest adapter documented (root `Passage` purpose=DETECTION, manual method + Diagnostic origin, optional evidence by reference, S7 mismatch behavior); D-013 proposed pending lead review; local prose corrected (README, architecture, contracts interim notes, prototype_v1, testing_strategy, traceability, review_checkpoints, WP-06 goal); no contract/status-board changes; hotspot regression kept | Map + prose, pending review (D-013) | Changed: `docs/entry_points.md` + `tests/unit/test_entry_points_ls02.py` (new, 9 checks); prose-only edits to README/architecture/contracts/prototype_v1/testing_strategy/traceability/review_checkpoints/WORK_PACKAGES/decisions. Tests: LS suites 18 passed; passage-practice 80 passed; overview/CLI/snapshot 23 passed; full suite 216 passed, 7 skipped (same optional-corpus skips). Limitation: adapter awaits T05.3 implementation; hotspot-ID optionality awaits LS-03 | LS-03 next (minimal request, journal, context contracts) |
