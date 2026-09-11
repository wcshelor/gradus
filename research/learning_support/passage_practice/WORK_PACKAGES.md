# Work Packages

This is the implementation control board. Coding agents select only work marked
`READY`, satisfy its dependencies and acceptance criteria, and leave a handoff
record. The lead changes downstream items from `BLOCKED` to `READY` after the
required review gate passes.

## Status vocabulary

- `BLOCKED`: a dependency or lead decision is incomplete.
- `READY`: safe for one agent to claim.
- `CLAIMED`: an agent is actively implementing it.
- `REVIEW`: implementation is complete and awaiting independent review.
- `CHANGES`: review found required changes.
- `DONE`: merged and accepted; downstream work may depend on it.
- `DEFERRED`: intentionally outside the current milestone.

Only the lead edits live status on the integration branch and marks a package
`DONE`. An implementer announces that work is ready for review and adds
`handoffs/WP-XX.md`; this avoids forcing every parallel branch to edit the same
status table.

> Status reconciliation note (2026-09-09): this board was updated to reflect
> work that had already landed on the active branch. WP-00 through WP-02 are
> treated as completed because their handoffs and tests exist. WP-03 is treated
> as active because the semantic S2 view work (`attack_stream`, `written_stream`,
> `rhythm_grid`, `texture_grid`, `salience_view`) is already implemented and
> tested. The semantic
> track is tracked separately in `docs/semantic_music_extraction_tasks.md`.

## Dependency map

D-013 review (2026-09-05): LS-03a from the repository-wide plan owns the minimal
passage-first investigation contract. It may proceed after LS-02 without waiting
for WP-05. WP-05 and WP-08 consume it; the detailed T05.3 task additionally requires
the selection API T02.5. These are design dependencies, not claims that any package
has passed its review gate. This revision does not change live board statuses.

```text
WP-00 Repository baseline
  -> WP-01 Contract models
      -> WP-02 Exact passage selection
          -> WP-03 Derived views
              -> WP-04 Feature evidence
                  -> WP-05 Hotspot adapter
                      -> WP-06 Event attribution
              -> WP-07 Broken-chord detector
          -> WP-09 Transformation foundation
              -> WP-12 Rhythmic variants
              -> WP-13 MusicXML writer
  WP-06 + WP-07
      -> WP-08 Diagnosis engine
          -> WP-10 Strategy registry
              -> WP-11 Blocked-chord transformation
  WP-05 + WP-06 + WP-07 + WP-08 + WP-10 + WP-11 + WP-12 + WP-13
      -> WP-14 Vertical pipeline
          -> WP-15 Grounded explanation
          -> WP-16 Evaluation harness
```

After WP-02, derived-view work and transformation-foundation work may proceed
in parallel. After WP-03, feature-evidence and broken-chord-detector work may
proceed in parallel. The writer can proceed after passage and transformation
contracts stabilize, but it cannot define those contracts itself.

## Board

| ID | Package | Status | Depends on | Suggested owner | Review gate |
|---|---|---|---|---|---|
| WP-00 | Baseline and repository hygiene | DONE | — | repository steward | G0 |
| WP-01 | Cross-layer contract models | DONE | WP-00 | representation agent | G1 |
| WP-02 | Exact passage selection and context | DONE | WP-01 | score-time agent | G1 |
| WP-03 | Derived view engine | CLAIMED | WP-02 | representation agent | G2 |
| WP-04 | Feature evidence traces | BLOCKED | WP-03 | difficulty agent | G2 |
| WP-05 | Passage investigation adapters | BLOCKED | WP-04, LS-03a | integration agent | G2 |
| WP-06 | Event attribution and region refinement | BLOCKED | WP-05 | attribution agent | G3 |
| WP-07 | Restricted broken-chord detector | BLOCKED | WP-03 | music-analysis agent | G3 |
| WP-08 | Diagnostic registry and rule engine | BLOCKED | WP-06, WP-07, LS-03a | diagnosis agent | G3 |
| WP-09 | Transformation foundation and validators | BLOCKED | WP-02 | transformation agent | G2 |
| WP-10 | V1 objective and strategy registry | BLOCKED | WP-08 | pedagogy-contract agent | G3 |
| WP-11 | Blocked-chord transformation | BLOCKED | WP-07, WP-09, WP-10 | transformation agent | G4 |
| WP-12 | Long-short and short-long transformations | BLOCKED | WP-09, WP-10 | transformation agent | G4 |
| WP-13 | Supported-subset MusicXML writer | BLOCKED | WP-02, WP-09 | notation agent | G4 |
| WP-14 | End-to-end v1 orchestration | BLOCKED | WP-05–WP-13 | integration agent | G5 |
| WP-15 | Grounded explanation adapter | BLOCKED | WP-14 | explanation agent | G5 |
| WP-16 | Research evaluation harness | BLOCKED | WP-14 | evaluation agent | G5 |
| WP-17 | Literature knowledge-base population | DEFERRED | WP-10 | literature team | later |
| WP-18 | LLM-backed explanation experiment | DEFERRED | WP-15 | model experiment agent | later |

## Package specifications

### WP-00 — Baseline and repository hygiene

**Goal:** establish a reviewable commit and clean implementation branch before
runtime development.

**Scope:**

- Audit the currently staged repository reorganization.
- Keep the two external repositories as explicit submodules.
- Remove system metadata and caches from tracking.
- Decide which generated artifacts are intentional evidence and ignore or
  unstage ad hoc timestamped runs.
- Verify provenance and redistribution permission for newly added score files.
- Run the existing piano-difficulty tests from their new location.
- Commit the repository migration separately from passage-practice runtime work.
- Create the implementation branch or worktree from that reviewed commit.

**Acceptance evidence:**

- `git status` is clean after the baseline commit.
- Fresh-clone instructions include submodule initialization.
- No unreviewed bulk artifact directory or restricted score material is added.
- Existing tests pass or failures are documented as pre-existing with logs.
- The commit contains no passage-practice runtime code.

**Do not:** delete local research data merely to make Git clean.

### WP-01 — Cross-layer contract models

**Goal:** implement the minimal immutable types and serialization helpers needed
by subsequent packages.

**Scope:**

- Score positions and exact fraction serialization.
- Passage identity and region-purpose enums.
- Diagnostics and provenance references.
- Versioned containers needed by WP-02 and WP-03.
- A contract-version policy in package documentation.

Do not implement detectors, rules, transformations, or a complete speculative
model tree.

**Tests:**

- fraction round trips;
- deterministic serialization;
- invalid interval rejection;
- unique/stable IDs;
- missing optional context; and
- unsupported schema version behavior.

**Acceptance evidence:** a compact frozen JSON payload and API documentation.

### WP-02 — Exact passage selection and context

**Goal:** replace whole-overlapping-measure slicing with exact time-bounded,
non-mutating selection.

**Scope:**

- Select attacks under `[start, end)` semantics.
- Track notes sustaining across both boundaries.
- Preserve written and logical note relationships.
- Inherit active measure, key, meter, clef, tempo, and relevant direction
  context.
- Represent detection, evidence, pattern, and practice selections.
- Make manual exact-region selection a public research API.

Generic reusable primitives may require a small, separately committed change in
`piano_difficulty`; passage semantics stay here.

**Tests:**

- events exactly on each boundary;
- ties and sustaining notes crossing boundaries;
- partial measures;
- two voices and two staves;
- inherited context;
- empty selection; and
- unchanged input object.

**Acceptance evidence:** a selection report for a tiny fixture listing included,
boundary-context, and excluded event IDs.

### WP-03 — Derived view engine

**Goal:** generate purpose-specific projections from one canonical passage.

**V1 views:**

- target-hand logical attack stream;
- onset slices;
- interval transitions;
- hand shapes with group timing; and
- minimal voice-aware written stream needed for export.

Each view declares ordering, grouping, omissions, method/version, source IDs,
and diagnostics.

**Tests:**

- deterministic ordering;
- chord/onset grouping;
- hand and voice separation;
- source-reference completeness;
- transposition metamorphism; and
- ambiguous/missing hand behavior.

**Acceptance evidence:** view payloads for positive and ambiguous fixtures.

### WP-04 — Feature evidence traces

**Goal:** make hotspot-relevant aggregate features explainable through ordered
event-level observations.

**Initial features:**

- attack density;
- shortest written duration;
- consecutive onset-group or attack pitch distance by hand;
- maximum and mean hand-shape span;
- hand-shape transition distance; and
- any existing v1 hotspot features needed by the agreed fixture.

Preserve existing feature values unless an explicit defect is found. If a
formula changes, add a regression test and decision entry.

**Tests:**

- aggregate reconstructs from observations;
- correct units and scopes;
- exact event references;
- missing hand data;
- chords versus sequential notes; and
- compatibility with current extraction payloads.

**Acceptance evidence:** before/after payload showing additive evidence without
breaking the established summary consumer.

### WP-05 — Hotspot investigation adapter

**Goal:** adapt manual regions and Difficulty Dynamics results to the same
passage-first investigation boundary specified by LS-03a/D-013.

**Scope:**

- Map hotspot region, score, contributing dimensions, values, and warnings.
- Resolve available feature-evidence references.
- Preserve detection method/version and hand mode.
- Support controlled manual regions using the same downstream interface.
- Require passage identity and structured selection origin; keep difficulty
  context optional and retain genuine hotspot IDs only within that context.
- Do not duplicate hotspot selection logic.

**Tests:**

- composite and per-feature hotspots;
- missing evidence;
- unknown feature IDs;
- hand-specific and both-hands modes;
- exact serialized region; and
- manual-region equivalence downstream.

**Acceptance evidence:** one contract payload from the existing Difficulty
Dynamics fixture or a minimal new fixture.

### WP-06 — Event attribution and region refinement

**Goal:** attribute real aggregate/hotspot targets to supporting observations and
derive evidence regions. Ordinary passage observations remain valid without an
attribution target; do not manufacture attribution for manual entry.

**Scope:**

- Exact attribution for maxima and counts.
- Ranked top-observation or threshold attribution for averages.
- One documented leave-one-group-out method where useful.
- Contiguous-cluster grouping.
- Minimal evidence-region calculation.
- Explicit limitations when a feature cannot be localized.
- Passage-linked observations and optional attribution are separate inputs;
  hotspot-specific attribution requires a real hotspot reference, while aggregate
  attribution names its actual aggregate target without requiring a hotspot.

**Tests:**

- a high aggregate caused by one outlier;
- a high aggregate caused by a dense cluster;
- overlapping windows;
- ties and chord groups;
- stable tie-breaking; and
- unlocalizable feature behavior.

**Acceptance evidence:** a report that names exact source event IDs for every v1
triggered feature.

### WP-07 — Restricted broken-chord detector

**Goal:** implement the musical-pattern contract in `prototype_v1.md` without
embedding diagnosis or exercise selection.

**Scope:**

- Candidate group boundaries under a configurable simple metrical policy.
- Regularity, sequentiality, distinct-pitch, and recurrence criteria.
- Pitch-class and interval-shape comparison.
- Confidence from visible criterion scores.
- Covered event groups, contradictions, and diagnostics.

**Tests:** use every relevant fixture row from the initial fixture matrix,
including scalar, repeated-note, blocked-chord, single-group, transposed, and
mixed-context cases.

**Acceptance evidence:** precision-oriented results over the synthetic fixture
suite with no false positive on close negatives.

### WP-08 — Diagnostic registry and rule engine

**Goal:** combine structured triggers, attribution, and patterns into ranked,
qualified diagnoses.

**Scope:**

- Registry metadata and versioning.
- Required, supporting, and contradictory criteria.
- Transparent confidence calculation.
- Multiple-candidate and no-match results.
- V1 `technical.broken_chord.rapid_reconfiguration` rule.
- Evidence, pattern, and proposed-practice regions.
- Learner-data caveats.
- Required passage identity; observations and patterns can support a rule without
  hotspot IDs, triggered dimensions, or invented contribution records (D-013).

**Tests:**

- required criterion missing;
- supporting criteria raise confidence;
- contradictions lower or prevent diagnosis;
- no learner-specific claim;
- multiple ranked candidates; and
- registry version serialization.

**Acceptance evidence:** canonical v1 diagnosis and no-diagnosis payloads.

### WP-09 — Transformation foundation and validators

**Goal:** establish immutable generated-score structures, provenance operations,
transformation plugins, and reusable validation checks.

**Scope:**

- Exercise-plan and transformation-result contracts.
- Generated event identity and source mapping.
- Preservation/change/removal reports.
- Structural, timing, pitch, voice, and provenance validators.
- Plugin registry with deterministic invocation.

Do not implement the specific blocked or rhythmic transformations here.

**Tests:**

- duplicate IDs;
- missing provenance;
- invalid duration totals;
- input immutability;
- deterministic plugin resolution; and
- valid minimal identity transformation.

**Acceptance evidence:** validator output with stable check IDs for a valid and
an intentionally invalid generated passage.

### WP-10 — V1 objective and strategy registry

**Goal:** create the reviewed bridge from the v1 diagnosis to allowed practice
plans.

**Scope:**

- Three v1 objectives from `prototype_v1.md`.
- Blocked-chord, long-short, and short-long strategy records.
- Preconditions, contraindications, compatible transformation IDs, and
  parameters.
- Evidence status explicitly set to `prototype_unvalidated` until literature
  review supports stronger provenance.
- Deterministic plan selection with manual override.

**Tests:** incompatible diagnosis, missing prerequisite, contraindication,
manual selection, stable ordering, and provenance-status visibility.

**Acceptance evidence:** strategy records produce plans but no claim of
pedagogical validation.

### WP-11 — Blocked-chord transformation

**Goal:** turn each accepted broken-chord group into one simultaneous hand shape.

**Scope:** follow the exact preservation, duration, and provenance rules in
`prototype_v1.md`. Default to target-hand-only material. Reject ambiguous groups
or unsupported boundary constructs.

**Tests:**

- pitch-set equality;
- common onset;
- intended group duration;
- duplicate pitch handling;
- target-hand filtering;
- source mapping from combined groups;
- no input mutation; and
- explicit rejection of unsupported tuplets/ties.

**Acceptance evidence:** generated representation and validation report for the
positive fixture.

### WP-12 — Rhythmic variants

**Goal:** produce complementary long-short and short-long variants for supported
equal subdivisions.

**Scope:** rational duration ratios, pair grouping, residual policy, exact
endpoint preservation, and provenance. Do not silently regularize unsupported
rhythms.

**Tests:** pair duration conservation, pitch/order preservation, multiple
groups, barline boundaries, odd residual, tie and tuplet rejection, and inverse
variant relationship.

**Acceptance evidence:** invariant report for both variants.

### WP-13 — Supported-subset MusicXML writer

**Goal:** serialize validated generated passages as minimal standalone
`score-partwise` MusicXML.

**Scope:** implement only the v1 output contract. Emit explicit warnings for
omitted nonessential engraving. Include inherited context and sufficient rests
or measure handling to produce valid voice durations.

**Tests:**

- XML parsing;
- repository loader reopening;
- normalized semantic equality;
- partial-measure policy;
- chords, rests, ties, voices, and staves;
- deterministic output; and
- unsupported construct diagnostics.

**Acceptance evidence:** compact golden MusicXML plus parse-after-write report.

### WP-14 — End-to-end v1 orchestration

**Goal:** connect established components without moving their logic into a
monolithic pipeline.

**Scope:**

- automatic and controlled-baseline entry modes;
- stage-by-stage result bundle;
- selectable diagnosis/strategy when multiple candidates exist;
- output directory with stable JSON, MusicXML, and validation artifacts;
- failure isolation and stage diagnostics; and
- a thin research CLI or script only after the library API works.

**Tests:** the ten-point v1 acceptance scenario, stage failure propagation,
determinism, and no-network execution.

**Acceptance evidence:** one small checked-in regression report; keep ad hoc run
directories ignored.

### WP-15 — Grounded explanation adapter

**Goal:** produce a clear explanation using only the structured allowlist in an
`ExplanationBrief`.

**Scope:** begin with deterministic templates. State why the region was
investigated, what evidence and pattern were found, the qualified diagnosis,
the exercise objective, and reconnection to the original passage.

**Tests:** no unsupported measurements, no fingering or personalized claim,
missing-confidence handling, no-diagnosis language, and deterministic output.

**Acceptance evidence:** positive and cautious/no-match explanation snapshots.

### WP-16 — Research evaluation harness

**Goal:** make pattern, diagnosis, transformation, and expert-review results
measurable without confusing them with software tests.

**Scope:**

- annotation schema for intended regions, patterns, diagnoses, and strategies;
- evaluator agreement and disagreement capture;
- pattern precision/recall and boundary overlap metrics;
- diagnosis relevance ratings;
- exercise correctness, playability, clarity, and purpose ratings;
- versioned run manifests; and
- compact reports preserving score and method provenance.

**Tests:** metric calculations, missing ratings, disagreement, manifest
round-trip, and deterministic summaries.

**Acceptance evidence:** a synthetic evaluation run, not a claim of pedagogical
effectiveness.

### WP-17 — Literature knowledge-base population

Deferred until the v1 registry schema has survived implementation. Follow
`docs/pedagogy_knowledge_base.md`. This is primarily research work and must not
be auto-populated from unverified model summaries.

### WP-18 — LLM-backed explanation experiment

Deferred until deterministic explanations and their tests exist. The model must
consume `ExplanationBrief`, emit separately labeled prose, and be evaluated
against unsupported-claim and reproducibility criteria.

## Handoffs

Completed package records live in `handoffs/WP-XX.md`. Start from the template
in `handoffs/README.md`. Do not place long command output in a handoff.
