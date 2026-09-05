# Task list — 2026-09-05 — Difficulty-analysis consolidation and acceptance

Status: implementation handoff; remaining tasks are not yet completed.

Planning revision, 2026-09-05: this is a **component checklist**, subordinate in
cross-area scope and sequencing to the
[three-area learning-support plan](../../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md).
Difficulty analysis is one part of understanding a piece, not the center of the
thesis. Its completion does not gate all semantic or learner-context work.

This document is the detailed execution checklist linked from the active
[roadmap](roadmap.md). It is sufficient to resume the consolidation without
the originating conversation. It does not replace repository working rules or
authorize the downstream semantic-analysis work described at the end.

## 1. Objective and completion boundary

Make the existing difficulty-analysis work a coherent, maintainable workflow:

1. Analyze a symbolic piano score.
2. Understand the selected factors contributing to its descriptive difficulty
   profile, with raw values and understandable limitations.
3. Locate each factor's peaks.
4. Inspect ranked candidate high-demand sections and their supporting evidence.
5. Export the same result for human inspection and later downstream processing.

Consolidate and validate the existing implementations before introducing new
models. The result must not imply calibrated difficulty grades, causal factor
importance, personalized learner difficulty, or musically validated phrase
boundaries. Those claims have not been established.

The consolidation is complete when tasks DC-01 through DC-16 below satisfy
their acceptance checks, including an explicit project-owner review. An agent
may report engineering completion while that review is pending, but must not
claim full acceptance. Teacher review is useful additional research evidence;
it is not a prerequisite for running the software and cannot be fabricated.

This acceptance concerns the analyzer only. Preserve raw score/region access
independently of difficulty ranks: a learner-selected region, whole-piece question,
or self-reported difficulty can initiate separate assistance. No journal data,
learner profiling, or pedagogical recommendations belong in raw feature extractors.

## 2. Instructions for the implementation agent

### Read first

Read the repository-root `AGENTS.md`, this subproject's `AGENTS.md`, and
`tests/AGENTS.md` before editing their respective areas. Then read:

- [Architecture](architecture.md): runtime ownership and dependency direction.
- [Consolidation record](consolidation.md): what was promoted and preserved.
- [Difficulty model](difficulty_model.md): current calculation semantics.
- [Factor registry](feature_registry.md): selected factors and retained work.
- [Decisions](decisions.md): compatibility and methodological choices.
- [Evaluation](evaluation.md): existing verification and evidence limits.
- [Analyzer README](../README.md): setup and supported public workflows.

All code paths below are relative to `research/piano_difficulty/`, unless
explicitly described as repository-root paths. Commands say where to run them.
New paths suggested by a task are proposals, not claims that those files exist.

### Preserve the current working tree

At handoff, the first consolidation implementation is present as uncommitted
changes and new files. Its starting revision was `4a1e948` on
`codex/passage-diagnosis-planning`. Inspect the actual checkout and diff before
work; the branch may have advanced. Do not reset, overwrite, or reimplement
existing work just because it is not committed. This document requests no
commit, push, corpus download, or external communication.

### Scope and compatibility rules

- Keep runtime in `src/piano_difficulty/`; keep experiment orchestration in
  `tests/harness/` and thin entry points in `tests/scripts/`.
- Keep evidence in `tests/artifacts/difficulty_dynamics/`. Commit only small,
  redistributable evidence; keep local score content and bulky previews ignored.
- Do not move speculative abstractions into `research/shared/`.
- Preserve raw extraction formulas and explicit legacy-profile behavior unless
  a separately documented, tested correction is necessary. Do not silently
  change legacy Dynamics defaults while refining the public overview.
- Keep compatibility wrappers until identified consumers have migrated. The
  repository-only legacy `dynamics` command need not become a standalone
  installed application as part of this task.
- Preserve prediction, clustering, Yan, OMR, dataset, parity, and passage-practice
  work. Do not introduce an analyzer dependency on passage practice.
- Do not add factors or change weights merely to make a demonstration look
  convincing. Record measurement and interpretation decisions explicitly.
- Do not update snapshots blindly. Explain every changed field and distinguish
  intentional overview changes from regressions in preserved behavior.

### Execution and reporting

Use the dependency list below. For each task, record status, changed files,
verification command/results, evidence location, and any unresolved decision
in this document's execution log. A task is complete only when its acceptance
checks pass, not when its code has been written. Keep implementation changes
small and independently verifiable. No agent delegation is required by this
document.

If existing code already satisfies a task, verify it and record the evidence
instead of rewriting it. Resolve ordinary implementation details locally;
pause for project-owner input when a decision changes the product's intended
meaning, expands scope, or requires human acceptance. Record a pending review
honestly and continue independent in-scope checks where possible.

## 3. Implemented baseline — do not redo

| Area | Current implementation |
| --- | --- |
| Runtime consolidation | Dynamics core/models live in `src/piano_difficulty/difficulty_analysis/dynamics/`; exports live in `src/piano_difficulty/output/dynamics.py`. Old harness paths are compatibility imports. |
| Computation reuse | Existing normalization, smoothing, peaks, and contributions are reused; descriptors are extracted once per region for all selected series. |
| Public entry point | `analyze_score` defaults to `difficulty_overview`; explicit `scoreanalyzer_reference` selection retains legacy analysis. |
| Overview result | `difficulty_overview.v1` contains factors, regions, tracks, composite, separate factor/composite peaks, candidate sections, region evidence, hand views, warnings, and methods. |
| Selected factors | Attack density, largest pitch transition, largest simultaneous hand span, hand timing mismatch, and accidental density. Other raw descriptors remain available. |
| Temporal selection | Exact half-open attack intervals, clipped measure contexts, preserved source durations/IDs, and non-mutating hand filtering. |
| Missing/constant data | Missing hand-dependent measurements remain unavailable; constant normalized tracks do not produce distinct positive peaks. |
| Sections | Overlapping/touching peak windows merge transitively; sections retain support and representative-window contributions. |
| Reporting | Single-piece and batch CLI; JSON, Markdown, temporal CSV, standalone HTML with score-time-aligned tracks and shaded sections. |
| Repository migration | Development dependencies, root test discovery, fixture paths, and audited legacy snapshots were repaired. |
| Documentation | Architecture, factor definitions, model semantics, decisions, evaluation, preservation map, and legacy workflows are documented. |

### Verified evidence at handoff

- Full repository-root suite: **198 passed, 7 skipped** on 2026-09-05. Skips
  include optional PHP/local-corpus checks; they are not proof those paths pass.
- Original versus promoted legacy Dynamics matched in 16 configurations:
  two inputs, four normalization modes, and two smoothing modes.
- Installed normal analysis was invoked outside the repository without loading
  test/harness modules. A fresh isolated installation has not yet been tested.
- A self-authored fixture, Beethoven Bagatelle Op.119 No.10, and Bach Prelude
  BWV 881 were analyzed twice with deterministic results and resolvable region
  written-note IDs. Local scores must not become mandatory CI dependencies.
- The Bagatelle HTML was visually inspected. Automated and visual checks do
  not establish expert agreement or learning benefit.

See [validation evidence](../tests/artifacts/difficulty_dynamics/consolidation_validation.md).
That record currently describes 197 tests plus a separately checked snapshot;
DC-01 reconciles it with the subsequent combined 198-test run.

### Known gaps and interpretation constraints

1. The executable overview registry covers five factors, not a complete
   descriptor-by-descriptor inventory of the repository.
2. `DifficultyAnalysisResult` currently wraps an unrestricted dictionary.
3. `top_sections` currently also sets the detector's per-series `top_n`, so a
   display-limit change can change candidate construction.
4. Positive top-N windows and transitive overlap can produce broad sections.
5. Global factor ordering is mean within-piece normalized value times weight;
   it is not empirically measured importance. Separate hand normalization does
   not establish which hand is absolutely harder.
6. Section contribution shares describe one representative window, not the
   entire merged interval.
7. Region IDs identify computation inputs, not exact notes responsible for an
   extremum or a semantic explanation.
8. Incoming sustains and transitions crossing a window start are omitted by
   current attack-based selection. These are declared limitations, not hidden
   support for sounding-note or physical-motion analysis.

## 4. Task order and progress checklist

IDs in this document are a new **remaining-work checklist**. They are not the
earlier DC-00–DC-11 package labels in `consolidation.md`; cite this filename
when referring to these IDs to avoid ambiguity.

| Status | Task | Depends on |
| --- | --- | --- |
| [ ] | DC-01 Reconcile baseline and status documentation | None |
| [ ] | DC-02 Complete the descriptor inventory | DC-01 |
| [ ] | DC-03 Audit selected-factor semantics | DC-02 |
| [ ] | DC-04 Complete isolated factor fixtures | DC-03 |
| [ ] | DC-05 Complete temporal and hand boundary fixtures | DC-03 |
| [ ] | DC-06 Strengthen the public result contract | DC-03 |
| [ ] | DC-07 Decouple detection from display limits | DC-06 |
| [ ] | DC-08 Define and implement overview peak policy | DC-04, DC-05, DC-07 |
| [ ] | DC-09 Refine candidate-section merging | DC-08 |
| [ ] | DC-10 Lock peak/section behavior with regressions | DC-09 |
| [ ] | DC-11 Verify cross-output consistency | DC-06, DC-10 |
| [ ] | DC-12 Make compatibility and smoke evidence repeatable | DC-01, DC-10 |
| [ ] | DC-13 Measure window-setting sensitivity | DC-10, DC-12 |
| [ ] | DC-14 Verify fresh isolated installation | DC-11, DC-12 |
| [ ] | DC-15 Obtain project-owner report acceptance | DC-11, DC-13, DC-14 |
| [ ] | DC-16 Close review findings and run final acceptance | DC-15 |

## 5. Detailed consolidation tasks

### DC-01 — Reconcile the baseline and status documentation

**Purpose:** give the next agent a trustworthy starting point.

**Inspect/edit:** `docs/consolidation.md`, `docs/roadmap.md`,
`docs/evaluation.md`, and the validation evidence linked above.

**Work:**

1. Inspect the working tree and record the actual starting revision and local
   changes without modifying unrelated files.
2. Run the baseline suite; record current counts, skip reasons, and environment
   constraints. Preserve historical results as dated observations.
3. Reconcile the 197-plus-snapshot versus 198-combined result. Describe current
   package outcomes as implemented functionality, not completed research validation.
4. Ensure the roadmap points to this checklist and does not resurrect the
   historical `docs/tasks.md` as the active plan.

**Done when:** status/evidence documents agree, baseline failures are either
resolved within scope or explicitly recorded, and no validation claim exceeds
the checks actually performed.

### DC-02 — Complete the descriptor-by-descriptor preservation inventory

**Purpose:** account for useful existing work before extending the overview.

**Inspect/edit:** `src/piano_difficulty/features/`, `docs/feature_registry.md`,
`docs/analysis_lanes.md`, and relevant harness definitions.

**Work:**

1. Enumerate emitted raw descriptor IDs from extractor definitions, including
   conditional outputs; a single example score is not a complete inventory.
2. For each ID record owner/extractor, definition, units, valid scope,
   availability conditions, provenance capability, direction if established,
   overlap with other descriptors, and disposition.
3. Use explicit dispositions: selected overview factor, retained raw evidence,
   experimental-only, or legacy compatibility. Record exclusion rationale;
   use unknown/not established rather than inventing metadata.
4. Add a lightweight completeness check against the maintained descriptor
   definitions where feasible. Keep historical/experimental IDs distinct from
   active runtime outputs.

**Done when:** every identified descriptor has an owner and disposition, the
five selected IDs resolve to real extractors, and no code is removed or moved
solely because it is excluded from the composite.

### DC-03 — Audit the five selected factors and their public interpretation

**Inspect/edit:** `features/registry.py`, underlying factor extractors,
`difficulty_analysis/overview.py`, and `docs/difficulty_model.md`.

**Work:**

1. Trace each factor from source events through raw value, hand aggregation,
   normalization, contribution, and displayed label.
2. Verify rate denominators, written versus logical event use, closest-pitch
   leap semantics, simultaneous-attack span semantics, and coordination scope.
3. Check stronger-hand aggregation in the combined overview against separate
   hand views, and preserve the legacy mean-of-hands policy.
4. Document how unavailable factors change the composite denominator and how
   constant factors remain visible despite having no local peak.
5. Make wording corrections where needed. Keep equal weights and the current
   descriptive interpretation unless a justified decision is documented.

**Done when:** every factor has a precise executable meaning and honest label;
the report does not suggest absolute comparisons across independently normalized
factors/hands or claim validated importance.

### DC-04 — Add isolated positive and negative factor fixtures

**Inspect/edit:** `tests/unit/test_difficulty_overview.py`, factor unit tests,
and self-authored fixture helpers under `tests/` as needed.

**Work:**

1. Add paired examples for wider versus narrower simultaneous spans, aligned
   versus mismatched two-hand onsets, and explicit accidentals versus an
   otherwise comparable notation control.
2. Assert expected raw measurements first, then their overview availability,
   normalized behavior, and peak location where local contrast exists.
3. Keep other inputs controlled where possible. Where a musical change affects
   multiple descriptors, document those effects instead of asserting artificial
   independence.
4. Retain density/leap spike and constant-track checks; add missing negative
   cases identified by DC-03.

**Done when:** all five defaults have direct measurement tests and appropriate
overview positive/negative coverage. Fixtures are self-authored or demonstrably
redistributable and require no private corpus.

### DC-05 — Complete temporal-selection and hand-boundary coverage

**Inspect/edit:** `temporal/selection.py`, `temporal/windows.py`, the promoted
Dynamics core, and unit tests.

**Work:**

1. Test attacks exactly at start/end, fractional beat offsets, incoming tied
   sustains, notes extending beyond the interval, and transitions crossing start.
2. Test pickup/printed measure numbering and final partial windows, including
   a final beat window spanning multiple measures.
3. Test absent requested hands, partially unknown hands, one-hand-only material,
   and coordination unavailability. Distinguish zero measurements from missing data.
4. Assert original score immutability, ID preservation, exact interval strings,
   and clipped rate denominators.

**Done when:** the declared half-open attack-selection policy is covered at its
boundaries; tests do not accidentally treat an analysis view as a notation excerpt.
Any discovered bug fix has a regression and a legacy compatibility check.

### DC-06 — Strengthen the public overview result contract

**Inspect/edit:** `difficulty_analysis/overview.py`, existing Dynamics models,
`pipeline.py`, serializers, and `tests/regression/difficulty_overview_contract.json`.

**Work:**

1. Replace or surround the unrestricted result dictionary with explicit typed
   records and/or validation. Reuse existing region/series contracts; do not
   create a duplicate score representation or add a heavy dependency unnecessarily.
2. Validate required keys, finite numeric values, allowed missing values, exact
   intervals, hand scope, factor IDs, and resolvable peak/window references.
3. Specify invariants for array lengths, contribution scope, candidate ranking,
   evidence scope, diagnostics, and method/registry/schema versions.
4. Add malformed-payload and serialization tests as well as valid examples.
   Keep renderer and batch consumers using the same validated result.
5. Document additive versus breaking schema changes. Record method changes
   separately; do not silently reinterpret a versioned field or golden file.

**Done when:** invalid internal results fail clearly before export, valid results
serialize deterministically without NaN/Infinity, and the public contract is
documented and regression-tested.

### DC-07 — Separate detection configuration from display limits

**Inspect/edit:** `OverviewOptions`, `_build_view`, `PeakDetectionConfig`,
`consolidate_sections`, CLI option plumbing, and integration tests.

**Work:**

1. Remove the coupling between `top_sections` and detector `top_n`.
2. Give detection its own documented policy/settings, independent of how many
   sections a caller wants displayed. Record effective settings in method metadata.
3. Construct and rank candidates before applying the final presentation limit.
4. Test the same score with several positive section limits and all other
   settings identical, through both API and CLI.

**Done when:** shared leading candidates retain identical IDs, boundaries,
scores, support, and ordering when the display limit changes; only truncation
changes. Legacy experimental detector settings retain their meaning.

### DC-08 — Define and implement a deliberate overview peak policy

**Inspect/edit:** `difficulty_analysis/dynamics/core.py` peak helpers,
configuration models, overview assembly, and `docs/decisions.md`.

**Work:**

1. Write a short policy decision covering positive eligibility, plateaus,
   equal-value ties, endpoints, missing-value gaps, and minimum separation.
2. Compare the existing top-N behavior with existing local-maximum capabilities
   on isolated spikes, broad plateaus, and repeated nearby peaks. Reuse suitable
   helpers; keep new overview defaults isolated from legacy behavior.
3. Require deterministic plateau representation, no invented constant-track
   peaks, and no neighborhood comparison across unavailable gaps. Measure any
   separation in declared score-time units rather than an unexplained index count.
4. Retain factor-specific peaks even when the composite is modest. If introducing
   a prominence/threshold rule, document its units and rationale; do not present
   an arbitrary cutoff as validated pedagogy.
5. Record the chosen policy/version and effective parameters in exported methods.

**Done when:** peak selection is understandable and deterministic across the
listed cases, has no display-limit dependency, and retains legacy compatibility.
The implementation includes executable examples of every policy decision.

### DC-09 — Refine section merging without pretending to find phrases

**Inspect/edit:** `difficulty_analysis/sections.py`, overview options/contracts,
`docs/difficulty_model.md`, and new focused section tests.

**Work:**

1. Construct fixtures for duplicate evidence at one peak, two nearby distinct
   peaks, touching windows, a long transitive chain, and a genuinely sustained
   high-demand interval.
2. Evaluate a simple peak-anchored or valley-aware grouping rule against the
   current unrestricted union. Choose and document one explicit rule before
   implementing it; use the smallest rule that addresses the fixtures.
3. Prevent low-demand bridges from automatically collapsing distinct peaks into
   one broad section. Do not impose arbitrary phrase labels or split genuine
   sustained demand merely to produce short sections.
4. Preserve exact source intervals, supporting peak/window IDs, distinct factor
   support, representative windows, and deterministic IDs/tie-breaking.
5. Keep representative-window contribution labels explicit. If changing that
   meaning, introduce a distinct contract rather than relabeling existing values.

**Done when:** duplicate evidence consolidates, independently supported passages
can remain distinct, broad retained sections have an inspectable rationale, and
all support references resolve. Section boundaries remain heuristic analysis
regions, not claims of semantic segmentation.

### DC-10 — Lock peak and section policies with focused regressions

**Inspect/edit:** overview unit tests, a focused section test module if useful,
and compact regression fixtures under `tests/regression/`.

**Work:**

1. Cover plateaus, ties, missing gaps, isolated/adjacent peaks, transitive chains,
   sustained regions, and all supported hand modes.
2. Assert ranks, exact boundaries, representative selection, IDs, support sets,
   and contribution/share invariants; do not rely on screenshots alone.
3. Add display-limit invariance and repeated-run determinism tests.
4. Review and update compact overview goldens only for explained method changes.
   Run existing legacy snapshots and harness tests unchanged in meaning.

**Done when:** the policies from DC-08/DC-09 are guarded by targeted tests and
compact readable snapshots, with no unexplained legacy numeric changes.

### DC-11 — Verify every supported output tells the same story

**Inspect/edit:** `output/overview.py`, `difficulty_analysis/markdown.py`,
`difficulty_analysis/batch.py`, CLI integration tests, and output tests.

**Work:**

1. Export one canonical result in JSON, Markdown, HTML, and temporal CSV. Check
   agreement of fields each format claims to expose: locations, hand scope,
   factors, units, values, ranking, and warnings.
2. Test default overview, explicit legacy selection, and repeated multi-profile
   selection. Ensure rendered output does not silently hide a requested profile;
   document supported report packaging if profiles require separate sections/files.
3. Verify unavailable values stay unavailable, diagnostics remain discoverable,
   and representative contributions are not described as section-wide totals.
4. Check escaped source text, missing-value line breaks, score-time alignment,
   highlighted sections, and a readable narrow-window layout in the HTML report.
5. Preserve batch continuation, nonzero failure signaling, and collision-safe
   filenames. Test these behaviors with a mix of valid and invalid inputs.

**Done when:** outputs consistently present the canonical result. CSV may remain
temporal-only if clearly documented; do not invent missing section tables merely
to make every format structurally identical. Record automated and visual checks.

### DC-12 — Make compatibility and real-score checks reproducible

**Inspect/edit:** `tests/harness/difficulty_dynamics/`, a thin runner under
`tests/scripts/`, and lane validation evidence/docs.

**Work:**

1. Turn the previous ad hoc compatibility matrix into a documented repeatable
   check: none/min-max/z-score/robust normalization crossed with no/moving-average
   smoothing on two declared inputs.
2. Use a provenance-recorded frozen expected result or test-scoped reference
   from the verified original revision. Comparing a compatibility wrapper with
   the same runtime implementation is not an independent parity check.
3. Prefer committed safe fixtures for mandatory checks. Make local Beethoven/Bach
   checks optional with explicit missing-input reporting and no network download.
4. Run each smoke input twice, compare deterministic analysis fields, validate
   every exported evidence reference, and record section counts/locations and warnings.
5. Write compact evidence with input identifiers/checksums, revision, settings,
   environment, and result status; exclude copyrighted score content.

**Done when:** another agent can reproduce the checks from documented commands,
without temporary files from the originating session or a private corpus.

### DC-13 — Measure sensitivity to window size and stride

**Inspect/edit:** test-scoped Dynamics evaluation code/config, a small declared
input manifest, and `docs/evaluation.md`.

**Work:**

1. Select a small set covering isolated spikes, sustained demand, sparse material,
   and contrasting hands. Include mandatory safe fixtures and clearly optional
   real-score examples; record selection rationale and availability.
2. Declare the sweep before inspecting its results. Start with measure sizes
   1/2/4 and strides 1/2, plus beat sizes 2/4/8 quarter notes and strides 1/2;
   record unsupported/degenerate combinations rather than silently omitting them.
3. Compare factor peak locations, section interval overlap, rank changes, section
   count/width, and availability. Use exact score coordinates for comparisons,
   not window indices. Document matching/tie rules and unmatched peaks/sections.
4. Produce a compact stability report and concrete unstable examples. Do not
   tune and report success on the same examples without disclosing that process.
5. Recommend whether existing defaults remain reasonable and list unresolved
   limitations for project-owner review; do not claim corpus-wide stability.

**Done when:** the sweep is rerunnable and its report explains where settings
materially change the answer. Stability measurements need not be uniformly good
to complete the task; unfavorable findings must remain visible.

### DC-14 — Verify installation independently of the working checkout

**Inspect/edit:** `pyproject.toml`, `environment.yml`, setup documentation, and
packaging checks if repairs are needed.

**Work:**

1. Create an isolated disposable Python 3.12-or-newer environment without
   repurposing or deleting the user's existing environment. Obtain any required
   permission for dependency downloads; report unavailable checks honestly.
2. Build and install the package non-editably, with runtime dependencies only.
3. From a directory outside the repository, exercise public imports, extraction,
   default analysis, explicit legacy analysis, and batch analysis on safe fixture
   paths; inspect normal-analysis imports for test/harness dependencies.
4. Verify documented editable development setup and tests separately. Distinguish
   runtime dependencies from dev/test dependencies and optional external tools.
5. Fix packaging/setup defects without moving experiment runners into runtime.

**Done when:** the normal supported package workflows succeed without checkout
import paths or dev extras. The legacy repository-only `dynamics` exception is
explicit. Record exact installation commands/environment and verification results.

### DC-15 — Obtain project-owner acceptance of representative reports

**Outputs:** a small report review pack under ignored previews plus a compact
review record in `docs/evaluation.md` or linked lane evidence.

**Work:**

1. Prepare a walkthrough using an isolated-spike fixture, a constant-demand
   example, and available representative real scores with legal local use.
2. Ask the project owner to assess whether each report makes the main factors,
   peak locations, candidate sections, hand scope, and uncertainty understandable.
3. Show broad/unstable sections and omitted demands from DC-13, not only favorable
   examples. Explain relative normalization and representative-window contributions.
4. Record accepted behavior, concrete defects, and deferred research questions.
   Seek teacher feedback only if the user arranges or authorizes it; do not send
   scores or reports externally on this document's authority.

**Done when:** the project owner explicitly accepts the baseline or supplies an
actionable correction list. If unavailable, mark this task pending human review
and report engineering status without claiming full acceptance.

### DC-16 — Close review findings and perform final acceptance

**Work:**

1. Turn accepted review defects into bounded fixes with regression tests. Keep
   requests for calibrated models, semantic diagnosis, or a new UI out of this
   consolidation unless separately authorized.
2. Re-run the full repository suite, reproducible compatibility checks, smoke
   runs, output verification, and isolated-install checks affected by changes.
3. Re-run sensitivity measurements if the peak/section/default policies changed;
   seek renewed review for material interpretation changes.
4. Update method/schema versions where required, goldens with explanations,
   documentation, task statuses, and evidence counts.
5. Inspect the final diff for unintended code removal, private data, generated
   bulk files, broken documentation links, and misleading completion claims.
6. Deliver a concise implementation summary, validation results, remaining
   limitations, and working-tree status. Do not commit or push unless requested.

**Done when:** all mandatory acceptance criteria below hold, no accepted defect
is left unresolved without explicit deferral, and human acceptance is recorded.

## 6. Commands and final acceptance checklist

Run these baseline commands from the repository root with the documented
environment available. They are starting commands, not substitutes for the
additional validation runners introduced by DC-12–DC-14.

```bash
conda run -n piano-difficulty python -m pytest -q
conda run -n piano-difficulty python -m pytest -q research/piano_difficulty/tests/unit/test_difficulty_overview.py research/piano_difficulty/tests/integration/test_analysis_cli.py research/piano_difficulty/tests/regression/test_difficulty_overview_snapshot.py
conda run -n piano-difficulty piano-difficulty analyze research/piano_difficulty/tests/fixtures/feature_fixture.musicxml --out-dir research/piano_difficulty/tests/artifacts/difficulty_dynamics/previews/consolidation_acceptance
conda run -n piano-difficulty piano-difficulty analyze research/piano_difficulty/tests/fixtures/feature_fixture.musicxml --profile scoreanalyzer_reference --format json
git diff --check
```

If that named environment does not exist, follow the setup in `README.md` and
record the chosen environment; do not silently install into a system Python.
Add exact commands for new validation runners to `docs/evaluation.md` as they
are implemented.

- [ ] Raw descriptor ownership and preservation are fully accounted for.
- [ ] All five selected factors and temporal/hand boundary policies are tested.
- [ ] One validated, versioned result drives all supported outputs.
- [ ] Display count cannot change candidate construction or leading rankings.
- [ ] Peak/section policies are explicit, deterministic, and regression-tested.
- [ ] Legacy compatibility is checked against independent recorded evidence.
- [ ] Normal installed workflows do not depend on repository test imports.
- [ ] The full suite passes, with every skip/failure explained rather than hidden.
- [ ] Real-score smoke checks and sensitivity evidence are reproducible.
- [ ] Reports are visually checked and accepted by the project owner.
- [ ] Limitations and deferred research are visible in reports and documentation.
- [ ] No unauthorized corpus content, participant data, or unrelated edits are added.

## 7. Separately gated follow-up: semantic breakdown

The following steps explain the intended next boundary. They are **not** part
of DC-01–DC-16 and are not authorization to start implementing semantic diagnosis.
Their scheduling follows the repository-wide plan rather than a blanket wait
for consolidation acceptance. Before any
learning-support edits, read its applicable `AGENTS.md` and existing passage
contracts; useful passage-practice work already exists and must be reused.

### SB-01 — Add observation-level evidence for selected factors

Choose the factors needed for one agreed semantic experiment. Extend evidence
to identify the actual onset pair/pitch set behind an extremum, or the event
set and numerator/denominator behind an aggregate. Preserve source IDs and
tie handling. Keep this distinct from current region-input provenance.

**Acceptance:** selected observations can be recomputed from their evidence;
unsupported factors explicitly lack exact attribution rather than fabricating it.

### SB-02 — Define the score-region-to-passage handoff

Inspect existing passage contracts and map exact user-selected or suggested
intervals, hand scope, optional factor observations, and source IDs into the
smallest compatible adapter. Preserve selection origin separately from evidence.
Do not require a nonzero difficulty score or a hotspot ID for a user selection. Define
boundary, missing-evidence, and version-mismatch behavior. Keep dependency
direction explicit; do not move types into `research/shared/` speculatively.

**Acceptance:** contract tests pass both a learner-selected region without a
difficulty profile and an analyzer-suggested region into a passage consumer,
without reparsing ambiguity or duplicating the score representation.

### SB-03 — Implement one bounded semantic breakdown

Agree one pattern family supported by the evidence. Implement a deterministic,
inspectable breakdown first unless a different method is explicitly chosen.
Include abstention for unsupported/ambiguous material. Do not expand directly
into exercise generation, fingering, or learner modeling.

**Acceptance:** positive, negative, and ambiguous examples demonstrate what the
breakdown recognizes, what source evidence supports it, and when it abstains.

### SB-04 — Evaluate before expanding

Compare the breakdown with source notation and reviewer judgments. Record false
positives, omissions, boundary errors, and usefulness independently from passing
code tests. Use the findings to decide whether to add another pattern family.

**Acceptance:** the experiment has an evidence-backed continue/revise/defer
decision, without claiming general pedagogical validity from a small trial.

## 8. Execution log

Append one row per completed task or meaningful blocked attempt. Keep historical
entries; do not overwrite unfavorable findings with later success.

| Date | Task | Status | Changed files / decision | Verification and evidence | Remaining issue |
| --- | --- | --- | --- | --- | --- |
| 2026-09-05 | Handoff | Documented | Initial implementation summarized; DC-01–DC-16 pending | Prior full suite: 198 passed, 7 skipped; see baseline above | Engineering hardening and project-owner acceptance remain |
| 2026-09-05 | Scope revision | Planning only | Linked three-area program; removed global difficulty-first gate; expanded SB-02 entry points | Documentation revision, no runtime changes | Component tasks remain pending; cross-area work follows the new plan |
