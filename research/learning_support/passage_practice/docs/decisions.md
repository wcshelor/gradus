# Architecture Decisions and Open Questions

This log prevents agents from silently making incompatible assumptions. Add a
dated entry when a decision materially affects more than one work package.

Statuses: `accepted`, `proposed`, `superseded`, `rejected`, `open`.

## Accepted decisions

### D-001 — Separate hotspot detection from passage diagnosis

- **Status:** accepted
- **Date:** 2026-09-02

The difficulty analyzer identifies regions worth investigating and reports
contributing dimensions. A separate passage engine attributes events,
recognizes patterns, and proposes diagnoses.

### D-002 — Use a rich canonical representation with multiple derived views

- **Status:** accepted
- **Date:** 2026-09-02

There is no single universal musical token stream. Algorithms consume typed,
documented projections derived from canonical score/passage facts.

### D-003 — Keep score fact, pattern, diagnosis, and intervention separate

- **Status:** accepted
- **Date:** 2026-09-02

This separation enables independent testing, evaluation, and uncertainty
reporting.

### D-004 — Use a hybrid source and normalized representation

- **Status:** accepted for v1
- **Date:** 2026-09-02

Retain the source document and stable source references while using normalized
objects for analysis and generation. Do not attempt a lossless model of the
entire MusicXML standard in v1.

### D-005 — Use exact half-open score regions

- **Status:** accepted
- **Date:** 2026-09-02

Canonical regions use exact rational time and `[start, end)` attack inclusion.
Sustaining boundary notes are represented separately.

### D-006 — Distinguish four region purposes

- **Status:** accepted
- **Date:** 2026-09-02

Detection, evidence, pattern, and practice regions are related but not assumed
identical.

### D-007 — Begin exercise generation deterministically

- **Status:** accepted for v1
- **Date:** 2026-09-02

Rule-driven, provenance-preserving transformations form the testable baseline.
An LLM may explain or organize approved results but is not required for score
mutation.

### D-008 — First vertical slice is a restricted broken-chord diagnosis

- **Status:** accepted
- **Date:** 2026-09-02

V1 produces blocked-chord and complementary rhythmic variants under the
supported subset in `prototype_v1.md`.

### D-009 — Preserve event-level evidence behind window summaries

- **Status:** accepted
- **Date:** 2026-09-02

Hotspot features expose or reference reproducible observations so the passage
engine can identify which events drove a window value.

### D-010 — Keep literature claims separate from formalized rules

- **Status:** accepted
- **Date:** 2026-09-02

Source claims, formalized heuristics, and executable strategies are independently
versioned and reviewed.

## Open questions requiring decisions during implementation

### Q-001 — Stable source identity mechanism

Should source references use normalized generated IDs, XML paths, retained node
identities, explicit MusicXML IDs when available, or a composite locator? WP-01
must propose a strategy that survives selection and serialization tests.

### Q-002 — Ownership of generic passage types

Should the most generic exact-region type live in `piano_difficulty`, with
passage-practice semantics layered above it, or should v1 keep all new contracts
inside passage practice? Resolve only after inspecting actual consumers.

### Q-003 — Boundary handling for partial measures

Should exercise export preserve partial measures with implicit measure
semantics, pad with rests, or rebar the passage? WP-02 and WP-13 must propose one
v1 default plus explicit alternatives/rejections.

### Q-004 — Broken-chord group duration

Should a blocked group sustain for the whole source group, until the next group,
or for a configured articulation-aware duration? WP-11 must connect the choice
to the stated practice objective.

### Q-005 — Attribution for averages

Which method should be the v1 default: top observations, threshold exceedances,
contiguous cluster, or leave-one-group-out delta? WP-06 should compare behavior
on the minimal fixture before proposing a default.

### Q-006 — Confidence scale and calibration

V1 needs a deterministic uncalibrated score with visible components. Later work
must decide whether expert-labeled data supports calibration and what the score
then means.

### Q-007 — Explanation implementation

Deterministic templates are the v1 baseline. Whether an LLM variant adds value
is deferred until grounded briefs and unsupported-claim evaluation exist.

### Q-008 — MusicXML writer implementation strategy

WP-13 must compare a small repository-native writer with a maintained library
adapter. The decision should consider exact timing, source provenance, minimal
dependencies, reopenability, and supported-subset diagnostics.

## Decision-entry template

```text
### D-NNN — Title

- Status:
- Date:
- Deciders:
- Affected work packages:

Context:

Decision:

Alternatives considered:

Consequences:

Required tests or migration:
```
