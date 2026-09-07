# Atomic Implementation Checklist

This checklist decomposes the work packages in `WORK_PACKAGES.md` into changes
small enough for one coding agent to implement and review at a time. It is an
execution aid, not a second status board: package readiness and completion stay
authoritative in `WORK_PACKAGES.md`.

## How to use this checklist

An agent takes exactly one unchecked task unless the task explicitly says it is
documentation-only follow-up for the preceding task. Before starting, the
agent must:

1. confirm that the parent `WP-*` package is `READY` or `CLAIMED` by that agent;
2. confirm every `Depends on` task is accepted on the package branch;
3. read the documents and code named by the parent work package;
4. state the files it expects to touch and the smallest test command it will
   run; and
5. stop if the task requires an unresolved decision listed below.

For every task, “done” means the focused positive, negative, and invariant
tests pass; relevant pre-existing tests still pass; diagnostics are stable and
asserted; source inputs remain unchanged; and no unrequested runtime, fixture,
dependency, or supported-format expansion was added. Check a box only after
review, not merely after implementation.

Each task should normally produce one narrow commit. Generic changes in
`research/piano_difficulty/` and their passage-practice consumers must remain
separate commits even when they belong to one work package.

## Global limits

- Preserve the dependency direction in `docs/architecture.md`.
- Use exact rational time and half-open regions; do not introduce canonical
  floating-point score positions.
- Keep staff, encoded voice, inferred hand, and musical role distinct.
- Do not add diagnoses to feature extraction or exercise choices to pattern
  detection.
- Do not let orchestration reimplement a stage.
- Do not add an LLM, network call, private corpus, or notation application to
  mandatory tests.
- Prefer small synthetic MusicXML fixtures with recorded provenance. Do not add
  copyrighted score material merely to exercise a case.
- Do not silently accept unsupported notation. Return an asserted diagnostic
  and no apparently valid exercise.
- Do not create empty future package trees or move speculative code to
  `research/shared/`.
- Do not tune musical thresholds on the v1 acceptance fixture alone.
- “No supported diagnosis” is a successful, testable outcome.

## Decision stops

The named task may investigate and propose the decision, but downstream work
must wait for a dated accepted entry in `docs/decisions.md`.

| Question | Resolve by | Blocks |
|---|---|---|
| Q-001 stable source identity | T01.2 | T01.3 onward |
| Q-002 generic passage ownership | T02.1 | T02.2 onward |
| Q-003 partial-measure policy | T02.5, finalized T13.1 | T13.2 onward |
| Q-004 blocked-group duration | T11.1 | T11.2 onward |
| Q-005 average attribution | T06.2 | T06.3 onward |
| Q-006 confidence meaning | T07.4, T08.2 | public confidence wording |
| Q-008 writer strategy | T13.1 | T13.2 onward |

## Test architecture growth

Build the suite in this order. A later tier may rely only on accepted contracts
from earlier tiers.

| Tier | Introduced | Purpose | Required by gate |
|---|---|---|---|
| A | T00.3–T01.4 | test roots, exact-time/ID/serialization contracts | G1 |
| B | T02.2–T03.6 | selection fixtures, views, source-reference invariants | G1–G2 |
| C | T04.1–T06.5 | observation reconstruction, adapter, attribution | G2–G3 |
| D | T07.1–T10.4 | musical close negatives, diagnosis branches, strategies | G3 |
| E | T09.1, T11.1–T13.6 | transformation invariants and parse-after-write | G2–G4 |
| F | T14.1–T16.5 | vertical regression, explanations, research metrics | G5 |

Goldens are deliberately sparse: one representative JSON payload per stable
contract family, one minimal MusicXML output per transformation family, and one
end-to-end report. All other tests should assert musical semantics directly.

## Milestone 0 — Reviewed repository baseline (WP-00, gate G0)

- [x] **T00.1 Inventory the migration without changing it.** Depends on: none.
  Scope: classify staged paths as repository move, submodule, source, licensed
  fixture, compact evidence, or ad hoc output; identify accidental caches and
  metadata. Test/evidence: a short baseline note with counts and unresolved
  provenance items. Limit: do not delete, unstage, or rewrite user work.

- [x] **T00.2 Verify submodule and clone boundaries.** Depends on: T00.1. Scope:
  inspect `.gitmodules`, pinned revisions, and clone/setup instructions.
  Test/evidence: submodule status plus a dry-run setup checklist. Limit: do not
  advance submodule commits or edit vendored contents.

- [x] **T00.3 Record the pre-implementation test baseline.** Depends on: T00.1.
  Scope: run the documented piano-difficulty test groups from their new paths
  and classify failures as environmental, pre-existing, or migration-induced.
  Test/evidence: dated commands, versions, pass/fail counts, and concise failure
  references. Limit: do not weaken tests to create a green baseline.

- [x] **T00.4 Audit fixture and artifact provenance.** Depends on: T00.1. Scope:
  verify licenses/origins for newly tracked score material and distinguish
  named evidence from timestamped runs. Test/evidence: provenance disposition
  for every questionable file. Limit: do not commit uncertain material.

- [x] **T00.5 Establish the clean implementation base.** Depends on: T00.2–T00.4.
  Scope: finish and review the repository migration, document fresh-clone
  setup, then create the passage-practice branch/worktree. Evidence: clean
  status and reviewed base commit. Limit: no passage-practice runtime code.

**G0 exit:** the lead records the baseline and releases WP-01. Any unresolved
license, submodule, or migration failure blocks implementation.

## Milestone 1 — Stable score and passage contracts (WP-01–WP-02, gate G1)

- [x] **T01.1 Add exact-time value objects.** Depends on: T00.5. Scope: implement
  score position and strict non-empty half-open interval validation with exact
  fraction serialization. Tests: fraction round-trip, negative/zero interval,
  boundary equality, unsupported schema version. Limit: no passage selection.

- [x] **T01.2 Decide and implement source identity primitives.** Depends on:
  T01.1. Scope: inspect existing `ScoreIR` IDs, propose Q-001, then implement
  the smallest stable source-reference type and resolver. Tests: uniqueness,
  deterministic regeneration, resolvable/missing references. Limit: no XML
  mutation and no identity scheme justified only by one fixture.

- [x] **T01.3 Add shared diagnostics and provenance references.** Depends on:
  T01.2. Scope: immutable severity/code/context and source-reference containers.
  Tests: deterministic order, JSON round-trip, missing optional context, invalid
  reference. Limit: no layer-specific diagnostic catalogs yet.

- [x] **T01.4 Add minimal versioned passage/view containers.** Depends on:
  T01.3. Scope: only fields required by WP-02 and WP-03, including passage ID,
  purpose, parent, event references, method metadata, and omissions. Tests:
  frozen compact JSON, deterministic serialization, invalid enum/version/ID.
  Limit: no speculative diagnosis, strategy, or transformation model tree.

- [x] **T02.1 Decide ownership of the generic region primitive.** Depends on:
  T01.4. Scope: inspect actual consumers and resolve Q-002. Evidence: dated
  decision naming package/import direction and migration consequence. Limit:
  do not move anything to `research/shared/`.

- [ ] **T02.2 Add the minimal selection fixture family.** Depends on: T02.1.
  Scope: synthetic fixtures for exact boundaries, crossing tie/sustain, inherited
  context, two staves, and two voices, each with a manifest entry. Tests: loader
  smoke assertions and provenance metadata. Limit: each fixture isolates one or
  two constructs; do not import repertoire excerpts.

- [ ] **T02.3 Implement attack and boundary-context selection.** Depends on:
  T02.2. Scope: select attacks in `[start,end)` and separately retain events
  sustaining across either boundary. Tests: start included, end excluded,
  crossing events, empty interval result, stable ordering, source immutability.
  Limit: do not expand to whole measures.

- [ ] **T02.4 Preserve relationships and active context.** Depends on: T02.3.
  Scope: written/logical-note links and meter, key, clef, tempo, and relevant
  directions active at the start. Tests: ties, voice/staff separation, missing
  optional context, deterministic context ordering. Limit: hand inference must
  remain labeled and separate from staff.

- [ ] **T02.5 Add purpose, refinement, and partial-measure behavior.** Depends
  on: T02.4. Scope: detection/evidence/pattern/practice purposes, parent chain,
  exact manual selection API, and a proposed Q-003 selection-side policy.
  Tests: refinement lineage, partial measure, invalid parent, unchanged source.
  Limit: no export padding or rebarring implementation.

- [ ] **T02.6 Produce the G1 selection report.** Depends on: T02.5. Scope:
  serialize one tiny case listing included, boundary-context, excluded IDs and
  inherited state. Evidence: compact deterministic artifact and all WP-01/02
  tests plus relevant normalization tests. Limit: report only implemented
  semantics.

**G1 exit:** identity, exact time, context, and passage ownership are accepted;
WP-03 and WP-09 may be released independently.

## Milestone 2A — Derived views and evidence (WP-03–WP-05)

- [ ] **T03.1 Define the view builder interface.** Depends on: T02.6. Scope:
  typed request/result with method version, parameters, ordering, grouping,
  omissions, source IDs, confidence where inferred, and diagnostics. Tests:
  registry resolution and unsupported view diagnostic. Limit: no concrete
  pattern logic.

- [ ] **T03.2 Implement the target-hand logical attack stream.** Depends on:
  T03.1. Scope: tie-collapsed, deterministically ordered attacks filtered by
  explicit or conservatively inferred hand. Tests: tie behavior, ambiguous and
  missing hand, two staves, two voices, source completeness. Limit: do not call
  staff or voice a hand.

- [ ] **T03.3 Implement onset slices.** Depends on: T03.2. Scope: group attacks
  sharing exact onset and optionally identify already-sounding notes. Tests:
  chord grouping, sequential notes, cross-voice onset, stable member ordering.
  Limit: no harmonic or difficulty label.

- [ ] **T03.4 Implement interval transitions.** Depends on: T03.3. Scope:
  consecutive attack/onset-group distances with declared units and source
  pairs. Tests: sequential notes, chord-to-note policy, rests, transposition
  metamorphism. Limit: choose one documented v1 distance policy only.

- [ ] **T03.5 Implement hand shapes with group timing.** Depends on: T03.3.
  Scope: pitch sets, spans, group regions, and transitions for one hand. Tests:
  duplicate pitch policy, stable pitch order, ambiguous hand, transposition.
  Limit: do not claim fingering or biomechanical span.

- [ ] **T03.6 Implement the minimal written export view.** Depends on: T03.2.
  Scope: voice-aware written events and rests needed to retain supported v1
  notation relationships. Tests: voice/staff separation, ties, omissions, all
  references resolve. Limit: no writer and no full-MusicXML projection.

- [ ] **T04.1 Define observation and feature-evidence contracts.** Depends on:
  T03.4. Scope: value, units, region, source group/transition IDs, aggregation
  rule, missingness, reliability, and method metadata. Tests: compact frozen
  payload, missing-not-zero, bad units/reference/version. Limit: no pedagogy.
  Require a source passage reference; ordinary observations require neither
  hotspot IDs nor fabricated attribution records (D-013).

- [ ] **T04.2 Trace density and shortest-duration evidence.** Depends on:
  T04.1. Scope: expose ordered observations behind the existing aggregates.
  Tests: reconstruct count/rate/minimum, ties not double-counted, empty/missing
  behavior, established aggregate compatibility. Limit: do not change formulas
  without a defect test and decision entry.

- [ ] **T04.3 Trace pitch-distance evidence.** Depends on: T04.1, T03.4. Scope:
  expose consecutive hand-scoped transition observations for required mean,
  quantile, or maximum summaries. Tests: reconstruct aggregates, chord policy,
  hand ambiguity, stable ties. Limit: preserve current units and semantics.

- [ ] **T04.4 Trace hand-shape evidence.** Depends on: T04.1, T03.5. Scope:
  maximum/mean spans and shape-transition distance required by v1. Tests:
  reconstruction, duplicate pitches, missing shape, exact group references.
  Limit: descriptors remain score facts, not ergonomic diagnoses.

- [ ] **T04.5 Add the additive compatibility payload.** Depends on: T04.2–T04.4.
  Scope: demonstrate summary consumers receive unchanged values while evidence
  is available by value or reference. Tests: old consumer regression and
  deterministic before/after fixture. Limit: no forced migration of unrelated
  feature families.

- [ ] **T05.1 Define the hotspot investigation adapter contract.** Depends on:
  T04.5, LS-03a (D-013 shared contract). Scope: reuse `PassageInvestigation`,
  validate analyzer input/context mappings; do not redefine the envelope.
  Map score, exact region, score/method, dimensions, values,
  contribution ranks, evidence refs, hand mode, and warnings. Tests: schema,
  exact fractions, unknown dimension and missing evidence diagnostics. Limit:
  do not select or rerank hotspots.

- [ ] **T05.2 Adapt automatic Difficulty Dynamics hotspots.** Depends on:
  T05.1. Scope: translate composite and per-feature outputs without duplicating
  detection. Tests: both hotspot forms, hand-specific/both-hand mode, warnings,
  reference resolution. Limit: additive changes only in the difficulty area.

- [ ] **T05.3 Add controlled manual-region entry.** Depends on: T05.1, T02.5,
  LS-03a. Scope: construct the same `PassageInvestigation` as T05.2, with the
  existing selected `Passage`, structured manual origin, optional hand, and empty
  difficulty context by default. Tests: equivalent observations for equal source,
  region, hand, and settings; no profile call; absent hotspot/score; origin and
  identity preserved after adding valid evidence; mismatched evidence rejected.
  Limit: no placeholder IDs, fabricated contributions, or parallel pipeline.

- [ ] **T05.4 Produce G2 evidence demonstrations.** Depends on: T05.2–T05.3 and
  T09.5. Scope: compact view, reconstructed aggregate, hotspot, and manual-entry
  payloads. Test/evidence: WP-03–05 tests and affected difficulty regressions.
  Limit: no semantic diagnosis in artifacts.

## Milestone 2B — Transformation foundation (WP-09, parallel after G1)

- [ ] **T09.1 Define generated-event and result contracts.** Depends on: T02.6.
  Scope: immutable generated identity, source mapping, operation enum, removed
  events, preservation/change reports, warnings, and validation placeholder.
  Tests: unique IDs, missing provenance, deterministic JSON, input immutability.
  Limit: no blocked or rhythmic algorithm.

- [ ] **T09.2 Define exercise-plan and plugin interfaces.** Depends on: T09.1.
  Scope: plan binding, declared invariants, parameters, transformation metadata,
  and deterministic registry lookup. Tests: duplicate/unknown plugin, stable
  ordering, invalid parameter surface. Limit: no strategy-selection logic.

- [ ] **T09.3 Implement structural, identity, and provenance validators.**
  Depends on: T09.1. Scope: stable check IDs for uniqueness, resolvability,
  operation/source consistency, and source coverage. Tests: one fault per check
  plus valid identity transformation. Limit: validators report; they do not
  repair.

- [ ] **T09.4 Implement timing, pitch, voice, and immutability validators.**
  Depends on: T09.3. Scope: exact duration totals, endpoints, allowed pitch-set
  changes, staff/voice preservation, and unchanged input. Tests: overfull,
  underfull, drift, pitch injection, voice conflation. Limit: export-format
  validity remains WP-13.

- [ ] **T09.5 Freeze valid and invalid foundation reports.** Depends on:
  T09.2–T09.4. Scope: compact representative payloads with stable check IDs.
  Tests: serialization determinism and full WP-09 suite. Limit: freeze only the
  public report semantics, not incidental messages.

**G2 exit:** after T05.4, the lead reviews WP-03–05 and WP-09 together and
releases attribution, pattern, diagnosis, and concrete transformation work.

## Milestone 3 — Attribution, pattern, diagnosis, and plans (WP-06–WP-10, G3)

- [ ] **T06.1 Implement exact attribution for extrema and counts.** Depends on:
  T05.4. Scope: ranked observations, source events, ranks/values, rationale from
  calculations, minimal evidence region, limitations. Tests: tied maximum,
  one outlier, count contributors, stable tie break. Limit: use “contributed to
  the signal,” not causal learner claims.

- [ ] **T06.2 Compare average-attribution candidates and resolve Q-005.** Depends
  on: T06.1. Scope: implement a small experiment comparing top observations,
  threshold, cluster, and where feasible leave-one-group-out on the fixture.
  Evidence: dated decision with selected deterministic default. Limit: do not
  tune for an attractive prose explanation.

- [ ] **T06.3 Implement the accepted average attribution.** Depends on: T06.2.
  Scope: method metadata, stable ranking, contribution values, and explicit
  limitations. Tests: outlier versus dense cluster, tied values, empty evidence,
  aggregate that cannot be localized. Limit: no pattern inference.

- [ ] **T06.4 Implement contiguous clusters and evidence-region refinement.**
  Depends on: T06.3. Scope: group selected observations and calculate the
  smallest exact covering region with lineage to detection. Tests: overlapping
  windows, gaps, chords, boundary events, deterministic grouping. Limit:
  evidence region is not automatically the pattern or practice region.

- [ ] **T06.5 Produce the v1 attribution report.** Depends on: T06.4. Scope:
  name exact source IDs for every triggered feature and document unlocalizable
  signals. Tests: reference resolution and repeat-run equality. Limit: no
  hand-authored event explanation outside calculated rationale.

- [ ] **T07.1 Add the musical positive and close-negative fixtures.** Depends on:
  T03.6. Scope: minimal broken chord, transposed groups, scalar run, repeated
  notes, blocked chord, one group, left-hand, and mixed context. Tests: manifest
  expectations and loader/view smoke tests. Limit: no detector thresholds chosen
  from outputs yet.

- [ ] **T07.2 Implement candidate group boundaries.** Depends on: T07.1. Scope:
  configurable one-beat/simple-multiple policy and complete-group regions.
  Tests: meter positions, insufficient groups, mixed context, simple triplet
  diagnostic. Limit: no diagnosis or transformation.

- [ ] **T07.3 Implement individual broken-chord criteria.** Depends on: T07.2.
  Scope: attack count, mostly sequential onsets, spacing regularity, distinct
  pitch count, pitch-class/interval-shape recurrence. Tests: isolate pass/fail
  for each criterion and transposition metamorphism. Limit: criteria return
  observations, not a final practice recommendation.

- [ ] **T07.4 Compose the detector and document confidence.** Depends on: T07.3.
  Scope: visible uncalibrated criterion score, covered groups/events,
  contradictions, method/version, hand confidence, and diagnostics. Tests:
  complete fixture matrix, bounded score, deterministic result, rhythmic-scale
  metamorphism if tempo invariance is claimed. Limit: precision first; abstain
  rather than weaken close negatives.

- [ ] **T08.1 Define the diagnosis registry and rule schema.** Depends on:
  T06.5, T07.4, LS-03a. Scope: required passage references, optional difficulty
  context, ordinary observations distinct from genuine attribution, and
  versioned required/supporting/contradictory criteria,
  evidence inputs, candidate objectives/strategies, caveats, and no-match.
  Tests: registry duplicates/version, missing criterion, unknown references.
  Limit: canonical text is a label/template summary only.

- [ ] **T08.2 Implement transparent rule scoring and ranking.** Depends on:
  T08.1. Scope: deterministic uncalibrated confidence components, threshold,
  contradictions, multiple candidates, and stable tie break. Tests: support can
  raise, contradiction cannot raise, below-threshold no-match. Limit: never
  imply probability or learner-specific certainty.

- [ ] **T08.3 Register the v1 diagnosis.** Depends on: T08.2. Scope: implement
  `technical.broken_chord.rapid_reconfiguration` exactly from `prototype_v1.md`
  with evidence/pattern/practice regions and learner caveats. Tests: canonical
  positive, scalar negative, missing relocation evidence, controlled baseline.
  The controlled baseline has no hotspot ID and need not have attribution;
  musical criteria still require actual observations and pattern evidence.
  Limit: one diagnosis only unless a test needs a synthetic ranking stub.

- [ ] **T08.4 Freeze diagnosis and no-diagnosis payloads.** Depends on: T08.3.
  Scope: compact goldens exposing criteria, evidence, confidence method,
  uncertainty, versions, and diagnostics. Tests: all references resolve and
  serialization repeats. Limit: do not freeze presentation prose.

- [ ] **T10.1 Define objective and strategy registry records.** Depends on:
  T08.4. Scope: compatibility, preconditions, contraindications, transformation
  IDs/parameters, literature IDs or `prototype_unvalidated`, and review status.
  Tests: schema/version, invalid references, visible evidence status. Limit:
  source claims, heuristics, and executable strategy remain distinct.

- [ ] **T10.2 Register the three v1 objectives.** Depends on: T10.1. Scope:
  recognize chord shapes, prepare position changes, and stabilize even
  subdivision with restrained descriptions. Tests: stable IDs/order and no
  personalized dosage, tempo, anatomy, or effectiveness claim.

- [ ] **T10.3 Register the three v1 strategies.** Depends on: T10.2. Scope:
  blocked chord, long-short, and short-long records with explicit prerequisites,
  contraindications, compatible plugin IDs, parameters, and unvalidated status.
  Tests: incompatible diagnosis, missing prerequisite, contraindication.

- [ ] **T10.4 Implement deterministic plan selection and override.** Depends on:
  T10.3. Scope: stable default ordering, manual accepted selection, practice
  region, preservation/change promises, and validation requirements. Tests:
  automatic/manual choice, invalid override, no compatible plan. Limit: do not
  personalize sequence or repetition count.

**G3 exit:** a musically informed reviewer inspects attribution, every fixture,
the diagnosis/no-match outputs, and strategy restraint before G4 work proceeds.

## Milestone 4 — Correct transformations and notation (WP-11–WP-13, gate G4)

- [ ] **T11.1 Resolve blocked-group duration and boundary policy.** Depends on:
  T07.4, T09.5, T10.4. Scope: propose Q-004 using the stated objective and
  determine explicit rejection for tuplets, crossing ties, and ambiguous groups.
  Evidence: accepted decision and focused policy tests. Limit: no silent clipping
  or articulation-aware expansion beyond v1.

- [ ] **T11.2 Implement one-group blocked conversion.** Depends on: T11.1. Scope:
  simultaneous generated notes, accepted duration, target hand/staff/voice, and
  combined source mappings. Tests: pitch-set equality, common onset, duplicate
  pitch policy, intended duration, immutable input. Limit: target hand alone by
  default.

- [ ] **T11.3 Extend blocking across a supported practice region.** Depends on:
  T11.2. Scope: convert all accepted groups, preserve ordering and optionally
  supported non-target material only when the plan requests it. Tests: multiple
  groups, filtering, approach/release behavior, deterministic IDs. Limit: reject
  ambiguous overlap rather than guessing.

- [ ] **T11.4 Attach transformation-specific validation.** Depends on: T11.3.
  Scope: stable checks for group pitch set, onset, span, source membership, and
  declared preservation. Tests: one intentional failure per check plus positive
  artifact. Limit: a failed result is not exportable success.

- [ ] **T12.1 Define exact pair and residual policies.** Depends on: T09.5,
  T10.4. Scope: rational long/short ratios, equal-subdivision eligibility,
  grouping across boundaries, odd residual behavior, and explicit rejection of
  ties/tuplets. Tests: policy table as parameterized unit cases. Limit: do not
  regularize unsupported source rhythms.

- [ ] **T12.2 Implement long-short transformation.** Depends on: T12.1. Scope:
  retime supported pairs while preserving pitch/attack order, source mapping,
  pair total, group endpoint, hand, voice, and staff. Tests: one/multiple groups,
  barline, residual, immutable input, exact fractions.

- [ ] **T12.3 Implement short-long as the complementary operation.** Depends on:
  T12.2. Scope: reuse pair eligibility and provenance while reversing duration
  allocation. Tests: complement relationship, same endpoints/order, independent
  deterministic IDs. Limit: do not duplicate policy logic.

- [ ] **T12.4 Attach rhythmic invariant validation.** Depends on: T12.3. Scope:
  stable checks for pair conservation, order, complements, endpoints, and voice
  totals. Tests: one intentional fault per check and both valid artifacts.
  Limit: no pedagogical-effectiveness assertion.

- [ ] **T13.1 Compare writer strategies and finalize Q-003/Q-008.** Depends on:
  T02.6, T09.5. Scope: small spike comparing repository-native serialization
  and a maintained adapter for exact timing, dependencies, diagnostics,
  provenance companion output, and reopenability; choose partial-measure policy.
  Evidence: accepted decision. Limit: do not adopt a library solely for broader
  MusicXML coverage.

- [ ] **T13.2 Write the minimal document/context skeleton.** Depends on: T13.1.
  Scope: deterministic `score-partwise`, part/measure structure, divisions,
  meter, key, clef, tempo where supported, and partial-measure representation.
  Tests: XML parse, inherited context, deterministic bytes/semantic form.
  Limit: omit nonessential engraving with explicit warnings.

- [ ] **T13.3 Serialize pitches, rests, chords, voices, and staves.** Depends on:
  T13.2. Scope: only constructs required by generated v1 passages. Tests: each
  construct in isolation, exact duration totals, chord onset semantics, stable
  event order. Limit: no general-purpose MusicXML writer claim.

- [ ] **T13.4 Serialize supported ties and reject unsupported constructs.**
  Depends on: T13.3. Scope: required tie encoding and stable diagnostics for
  tuplets, grace notes, unrepresentable directions, or boundary cases. Tests:
  positive tie round-trip and one negative per diagnostic. Limit: no lossy
  fallback presented as valid.

- [ ] **T13.5 Add parse-after-write semantic comparison.** Depends on: T13.4.
  Scope: reopen through the repository loader/normalizer and compare pitches,
  exact attacks/durations, voice, staff, and context. Tests: identity, blocked,
  and both rhythmic outputs. Limit: engraving equality is not semantic equality.

- [ ] **T13.6 Freeze minimal outputs and G4 evidence.** Depends on: T11.4,
  T12.4, T13.5. Scope: one compact MusicXML/provenance/validation example per
  family and negative reports. Tests: clean regeneration and affected full
  suites. Limit: optional visual renders stay clearly optional and compact.

**G4 exit:** each transformation independently validates and reparses before
any end-to-end orchestrator is allowed to call it.

## Milestone 5 — Vertical slice and research readiness (WP-14–WP-16, gate G5)

- [ ] **T14.1 Define the stage-result bundle and failure semantics.** Depends on:
  T05.4, T06.5, T07.4, T08.4, T10.4, T13.6. Scope: versioned per-stage outputs,
  diagnostics, success/no-match/failure distinction, and stable artifact names.
  Tests: schema, stopped-stage visibility, no-diagnosis success. Limit: no stage
  logic in the bundle.

- [ ] **T14.2 Orchestrate the controlled manual path.** Depends on: T14.1.
  Scope: call accepted APIs from exact region through validated transformations
  and exports. Tests: canonical positive, scalar no-match, one injected stage
  failure, repeat-run semantic equality. Limit: library API before CLI.
  Input is the shared passage-first contract, with no required difficulty context.

- [ ] **T14.3 Orchestrate the automatic hotspot path.** Depends on: T14.2. Scope:
  add Difficulty Dynamics entry while preserving its hotspot and warnings.
  Tests: expected later-window rank and downstream stage equivalence after the
  investigation boundary. Limit: do not change hotspot selection here.
  Compare ordinary observations with equal source/region/hand/settings, not
  origin-specific metadata or contribution fields. Preserve analyzer provenance.

- [ ] **T14.4 Add explicit multi-candidate selection.** Depends on: T14.3. Scope:
  stable defaults and manual diagnosis/strategy selection when multiple results
  exist. Tests: invalid choice, no compatible plan, deterministic ordering.
  Limit: no opaque best-advice ranking.

- [ ] **T14.5 Add deterministic artifact writing and thin CLI.** Depends on:
  T14.4. Scope: caller-selected output directory containing stable JSON,
  MusicXML, provenance, and validation reports; CLI only delegates to library.
  Tests: temporary-directory isolation, existing-file policy, no network, no
  writes into fixtures. Limit: timestamped ad hoc runs remain ignored.

- [ ] **T14.6 Freeze the ten-point vertical regression.** Depends on: T14.5.
  Scope: assert every acceptance point in `prototype_v1.md` plus close negative.
  Evidence: one compact checked-in report regenerated from a fresh environment.
  Limit: assert semantics, not merely file existence.

- [ ] **T15.1 Build `ExplanationBrief` from allowed fields.** Depends on: T14.6.
  Scope: bounded labels, observations, pattern claims, confidence/caveats,
  objective, strategy, factual transformation descriptions, audience, and tone.
  Include structured selection origin separately from optional difficulty reasons;
  manual selection must not be described as an automatically detected hotspot.
  Tests: source allowlist, missing confidence, no-match, deterministic JSON.
  Limit: no raw MusicXML or unrestricted evidence dump.

- [ ] **T15.2 Implement restrained deterministic templates.** Depends on:
  T15.1. Scope: why investigated, contributing score signals, matched criteria,
  qualified diagnosis, objective, and reconnection. Tests: positive and cautious
  snapshots. Limit: no invented fingering, dosage, target tempo, pain advice,
  measurement, citation, or learner-specific claim.

- [ ] **T15.3 Add unsupported-claim guards.** Depends on: T15.2. Scope: tests or
  structured checks proving every variable claim comes from the brief and
  prohibited categories remain absent. Tests: adversarial labels/missing data
  and stable no-diagnosis language. Limit: this is not general natural-language
  safety validation.

- [ ] **T16.1 Define versioned annotation and run-manifest schemas.** Depends on:
  T14.6. Scope: intended regions, patterns, diagnoses, strategies, evaluator
  identity codes, disagreement, score/method provenance, and missing ratings.
  Tests: round-trip, versions, missing optional ratings. Limit: no participant-
  identifiable data.

- [ ] **T16.2 Implement region and pattern metrics.** Depends on: T16.1. Scope:
  precision/recall and exact-time boundary-overlap calculations with abstentions.
  Tests: perfect, partial, disjoint, empty prediction/truth, exact fractions.
  Limit: metrics do not establish pedagogical value.

- [ ] **T16.3 Implement diagnosis and exercise rating summaries.** Depends on:
  T16.1. Scope: relevance, correctness, playability, clarity, purpose, missing
  ratings, and evaluator disagreement. Tests: small hand-calculated tables and
  deterministic aggregation. Limit: preserve raw disagreement; do not collapse
  it into consensus.

- [ ] **T16.4 Generate a synthetic evaluation report.** Depends on: T16.2–T16.3.
  Scope: versioned manifest and compact deterministic report exercising every
  metric and missing-data path. Tests: repeated summary equality. Limit: label
  it synthetic; make no teacher or learner-effectiveness claim.

- [ ] **T16.5 Complete the G5 evidence ledger.** Depends on: T15.3, T16.4. Scope:
  record implemented contracts, supported cases, synthetic versus expert
  evidence, known failures, versions, decisions, and safe claim boundary.
  Tests/evidence: fresh regeneration, full relevant suite, automatic/manual
  demonstrations, negative end-to-end result. Limit: release for small expert
  review, not deployment or learning-benefit claims.

**G5 exit:** the v1 vertical slice is technically and representationally ready
for controlled teacher review. WP-17 and WP-18 remain deferred until separately
released by the lead.

## Deferred research expansion

- [ ] **T17.1 Pilot one source-claim record.** Depends on: accepted WP-10 and a
  lead release of WP-17. Scope: one verified bibliographic source with exact
  locator, conservative paraphrase, context, cautions, author/date, and review
  state. Tests: bibliography reference resolves and required metadata validates.
  Limit: do not auto-populate from model summaries.

- [ ] **T17.2 Pilot one formalized heuristic.** Depends on: reviewed T17.1.
  Scope: separately version observable criteria, unavailable learner inputs,
  contradictions, objective link, uncertainty, formalizer, and reviewer. Tests:
  positive and negative passage examples. Limit: do not present interpretation
  as a source quotation.

- [ ] **T17.3 Link one reviewed strategy.** Depends on: T17.2. Scope: connect the
  heuristic to an executable strategy, distinguishing source-fixed parameters
  from implementation choices and retaining reconnection/contraindications.
  Tests: complete reference chain and version mismatch. Limit: keep status below
  validated until appropriate expert/learner evidence exists.

- [ ] **T18.1 Define the grounded LLM experiment protocol.** Depends on: accepted
  WP-15 and lead release of WP-18. Scope: compare template, brief-grounded LLM,
  and raw-score/unstructured baseline for unsupported claims and reproducibility.
  Tests: deterministic fixture inputs and a network-free mocked adapter suite.
  Limit: the LLM never parses, diagnoses, validates, or mutates notation.

- [ ] **T18.2 Implement an optional explanation adapter.** Depends on: T18.1.
  Scope: accept only `ExplanationBrief`, label model/version/output separately,
  and fail cleanly without credentials/network. Tests: request boundary, mocked
  response, prohibited-claim evaluator, deterministic core unaffected. Limit:
  no mandatory runtime or test dependency.

## Per-task handoff stub

Use this inside the parent package handoff while tasks are in progress:

```text
Task:
Outcome:
Changed files by layer:
Contract or decision affected:
Positive, negative, and invariant tests added:
Commands and results:
Representative evidence:
Diagnostics and unsupported cases:
Compatibility tests run:
Known limitations:
Next unblocked task:
```

When the final task in a package is complete, consolidate these entries into
`handoffs/WP-XX.md` using the repository template. The package is still not
`DONE` until independent review and its assigned gate accept it.
