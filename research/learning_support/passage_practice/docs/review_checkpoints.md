# Review Checkpoints

These gates are mandatory integration reviews. Package-level tests alone are
not sufficient because errors in representation or provenance amplify across
the later pipeline.

## G0 — Clean baseline

**After:** WP-00.

Review:

- repository migration and directory boundaries;
- submodule configuration;
- artifact and dataset staging policy;
- score licensing/provenance;
- test command paths after the move; and
- clean Git state.

Exit criteria:

- reviewed baseline commit exists;
- implementation worktree/branch starts from it;
- existing failures, if any, have a dated baseline record.

## G1 — Score and passage foundations

**After:** WP-01 and WP-02.

Lead reads all new contract and passage-selection code.

Review:

- exact time and interval convention;
- stable identity and source references;
- written/logical-note relationships;
- sustaining boundary events;
- inherited context;
- source immutability;
- separation of staff, voice, and hand; and
- whether any `ScoreIR` change is truly generic.

Required demonstrations:

- boundary fixture selection report;
- fraction serialization round trip;
- partial-measure and crossing-tie tests;
- relevant piano-difficulty normalization suite.

Exit criteria: derived-view and transformation-foundation APIs can depend on
the passage contract without importing one another.

## G2 — Evidence and transformation foundations

**After:** WP-03, WP-04, WP-05, and WP-09.

Review:

- every view declares omissions and source links;
- aggregates reproduce from observations;
- existing feature consumers remain compatible;
- hotspot adapter does not duplicate detection;
- generated-event provenance operations are adequate;
- validator check IDs and failure semantics are stable; and
- no semantic diagnosis has leaked into these layers.

Required demonstrations:

- view payload for one passage;
- evidence trace rebuilding one aggregate;
- the same `PassageInvestigation` contract for automatic and manual entry,
  with required passage identity, structured origin, and optional difficulty
  context; no invented hotspot or attribution in the manual example;
- valid and invalid identity transformation reports;
- relevant old and new test suites.

Exit criteria: attribution, pattern recognition, and concrete transformations
can proceed against stable upstream contracts.

## G3 — Semantic diagnosis

**After:** WP-06, WP-07, WP-08, and WP-10.

Lead and a musically informed reviewer inspect fixtures and results.

Review:

- event contribution is traceable and reproducible;
- evidence-region refinement behaves sensibly across overlapping windows;
- broken-chord criteria distinguish close negatives;
- confidence follows documented criteria;
- diagnosis language is qualified;
- learner-dependent claims become caveats;
- strategy registry exposes prototype evidence status; and
- no-match remains a first-class result.

Required demonstrations:

- positive and negative pattern suite;
- exact attributed source events;
- diagnosis/no-diagnosis payloads;
- strategy precondition and contraindication tests.

Exit criteria: transformations can consume plans without embedding new
diagnostic reasoning.

## G4 — Exercise correctness and notation

**After:** WP-11, WP-12, and WP-13.

Review:

- transformation-specific invariants;
- source-to-generated provenance completeness;
- non-mutation and deterministic output;
- exact duration and voice totals;
- boundary and unsupported-construct behavior;
- MusicXML output subset;
- parse-after-write semantic equality; and
- optional visual render quality where available.

Required demonstrations:

- blocked-chord artifact and invariant report;
- both rhythmic variants and conservation report;
- generated MusicXML reopened by the repository parser;
- negative validation examples.

Exit criteria: each transformation works independently before orchestration.

## G5 — Vertical slice and research readiness

**After:** WP-14, WP-15, and WP-16.

Review the complete pipeline without allowing orchestration to hide stage
failures.

Review:

- automatic and controlled entry modes;
- full provenance chain;
- deterministic artifacts;
- grounded explanation allowlist;
- error isolation and no-diagnosis behavior;
- evaluation schema separation from software tests;
- committed artifact size and reproducibility; and
- remaining thesis claims versus demonstrated evidence.

Required demonstrations:

- ten-point v1 acceptance scenario;
- one close negative end-to-end case;
- clean regeneration from a fresh environment;
- full relevant test suite;
- synthetic evaluation report.

Exit criteria: the system is ready for small teacher review and literature-base
population, not yet for claims about learner effectiveness.

## Review report template

```text
# Gate GX review — YYYY-MM-DD

Reviewed commits:
Reviewers:
Test environments:

## Passed contracts

## Findings requiring changes

## Musical/notation inspection

## Test evidence

## Known limitations accepted for this gate

## Decisions made or superseded

## Packages released
```
