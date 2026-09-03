# Testing Strategy

## Purpose

Tests in this area must show more than software stability. They must make the
musical meaning, provenance, supported subset, and failure behavior inspectable.

The suite should answer:

- Did we select the intended score events?
- Can we reproduce the feature value from its observations?
- Did the correct events drive the hotspot?
- Did a pattern detector recognize only its documented pattern?
- Is a diagnosis supported by its criteria?
- Did a transformation preserve what it promised?
- Can the generated notation be reopened without semantic drift?
- Does the whole pipeline remain deterministic?

## Test layers

### Unit tests

Cover pure operations:

- exact time and region comparisons;
- passage boundary inclusion;
- onset grouping and derived views;
- observation calculations;
- contribution ranking;
- individual pattern criteria;
- diagnostic rule evaluation;
- transformation duration arithmetic;
- provenance mapping; and
- individual validation checks.

Use constructed in-memory objects when XML syntax is irrelevant.

### Contract tests

Verify boundaries between research areas and pipeline layers:

- `ScoreIR` to `PassageSelection`;
- Difficulty Dynamics hotspot to `HotspotInvestigation`;
- summary feature to `FeatureEvidence`;
- attribution and pattern matches to diagnosis;
- diagnosis to exercise plan;
- transformation result to exporter; and
- diagnosis to explanation brief.

Contract tests must check schema versions, required IDs, resolvable references,
units, exact fractions, diagnostics, and deterministic serialization.

### Integration tests

Exercise a few layers together:

- MusicXML -> `ScoreIR` -> exact passage;
- passage -> views -> pattern match;
- hotspot -> attribution -> diagnosis;
- diagnosis -> plan -> transformation;
- generated representation -> MusicXML -> reopened `ScoreIR`.

Tests should use explicit temporary output directories and never write into the
committed fixture tree.

### End-to-end tests

One small fixture runs through the complete v1 acceptance scenario. Assert
semantic outputs rather than only checking that files exist.

### Regression tests

Freeze small, representative JSON payloads only for stable contracts. Avoid
large snapshots that obscure meaningful changes. A regression update must
explain why changed semantics are intended.

### Optional rendering tests

When MuseScore is available, render generated MusicXML and preserve a compact
manual-review artifact. Rendering tests should be clearly marked because CI may
not have the executable. Parser reopenability remains mandatory.

## Fixture matrix

Create purpose-built fixtures as work packages require them. The initial matrix
should eventually cover:

| Fixture | Purpose | Expected result |
|---|---|---|
| minimal regular broken chord | positive v1 path | high-confidence match |
| two transposed broken-chord groups | shape recurrence | positive match |
| scalar run | close negative | no broken-chord diagnosis |
| repeated notes | close negative | no broken-chord diagnosis |
| already blocked chords | close negative | no sequential broken-chord match |
| one candidate group only | insufficient evidence | no match or low confidence |
| left-hand pattern | hand scoping | left-hand result only |
| two voices on one staff | voice separation | explicit supported behavior |
| tie crossing passage start | boundary handling | context without false attack |
| note crossing passage end | boundary handling | documented clipping/preservation |
| simple triplet | unsupported boundary | explicit diagnostic in v1 |
| partial measure selection | export arithmetic | valid filled measure or rejection |
| inherited key/clef/meter | context propagation | standalone output reparses correctly |
| malformed duration total | validator negative | failure with stable check ID |
| mixed pattern and scalar context | boundary refinement | pattern region narrows correctly |

Each fixture README entry records:

- what musical construct it isolates;
- whether it is synthetic or derived from licensed material;
- expected supported/unsupported status; and
- which tests rely on it.

## Core invariants

### Passage invariants

- Source score is never mutated.
- Event ordering is stable.
- Included attacks obey half-open interval semantics.
- Sustaining boundary events are not counted as new attacks.
- Context state is the state active at the passage start.
- Refinement preserves a chain back to the detection region.

### Evidence invariants

- Aggregates are reproducible from observations under the named rule.
- Every observation references existing source objects.
- Units do not change between raw observation and compatible aggregate.
- Missing observations cannot silently become zero.
- Hand-specific evidence contains only the declared hand or an explicit
  ambiguity diagnostic.

### Pattern invariants

- Covered events exist and lie in the pattern region.
- Criteria and contradictions are recorded deterministically.
- Confidence is bounded and calculated by the documented method.
- Transposition does not change a transposition-invariant match unexpectedly.
- Rhythmic scaling preserves a rhythm-shape match when the detector claims
  tempo invariance.

### Diagnosis invariants

- Every diagnosis cites at least one attributed signal or explicit controlled
  baseline observation plus one satisfied rule criterion.
- Candidate strategies come from registered compatibility, not string
  invention.
- Missing learner data appears as a caveat where relevant.
- Contradictory evidence cannot increase confidence.
- No-match is stable and explainable.

### Transformation invariants

Shared invariants:

- Generated event IDs are unique.
- Every non-synthesized event maps to source events.
- Pitches remain within the intended source pitch set unless the plan explicitly
  allows synthesis.
- Measure and voice duration totals satisfy the selected export policy.
- Staff, voice, and hand are not silently conflated.
- Running a transformation never mutates its input.

Blocked-chord invariants:

- Generated pitch set equals the documented source group pitch set.
- Chord notes share an onset.
- Group timing remains within the source group's span.
- Source-group membership is recoverable from provenance.

Rhythmic-variant invariants:

- Pitch and attack order remain unchanged.
- Each transformed pair retains its total duration.
- The long-short and short-long versions are complementary.
- Measure and group endpoints do not drift.

### Serialization invariants

- Output is valid XML.
- The repository loader accepts the output.
- Reopened pitches, attacks, durations, voices, and staves match the generated
  representation within the supported subset.
- Required inherited context is present.
- Serialization is deterministic apart from explicitly ignored metadata.

## Metamorphic tests

Use metamorphic tests where exact expected labels are less useful:

- Transpose a fixture: interval-shape patterns and diagnoses should remain,
  while absolute pitches change predictably.
- Double all durations and meter-compatible regions: pattern grouping should
  remain while density-related observations change as documented.
- Swap staves and update hand annotations: hand-scoped outputs should swap, not
  disappear.
- Add an unrelated neighboring measure: the exact controlled passage result
  should remain stable.
- Serialize and reopen: semantic events should remain equivalent.
- Run twice: canonical JSON and MusicXML should be semantically identical.

Property-based tests may be added for exact duration partitions, fraction
round-trips, stable ordering, and provenance completeness. They supplement,
not replace, readable musical fixtures.

## Negative testing

Every work package must identify unsupported or ambiguous cases. Negative tests
assert:

- a stable diagnostic code;
- no misleading successful result;
- no partial file presented as a valid exercise;
- source objects remain unchanged; and
- fallback behavior, when allowed, is visible.

## Golden-output policy

Golden files are appropriate for:

- one compact contract payload per stable schema;
- one minimal generated MusicXML artifact per stable transformation; and
- one end-to-end v1 report.

They are not appropriate for every threshold variation or a large repertoire
run. Prefer targeted assertions for calculations and invariants.

## Test commands and isolation

Agents must document exact commands in each handoff. Until the package exists,
the intended command groups are:

```text
passage-practice unit and contract tests
passage-practice integration tests
relevant piano-difficulty unit tests
full piano-difficulty suite at review gates
```

Tests must not require network access, an LLM API, private corpora, or locally
installed notation software unless explicitly marked optional.

## Coverage expectations

Line coverage is a secondary signal. Required behavioral coverage is:

- positive, negative, and ambiguous path for each detector;
- each diagnostic rule branch;
- every transformation invariant;
- every documented boundary policy;
- every structured diagnostic; and
- one cross-area compatibility path for each promoted contract.

## Research evaluation versus software testing

Software tests establish deterministic correctness relative to documented
rules. They do not validate pedagogical usefulness or diagnosis truth.

Later evaluation must separately assess:

- agreement with teacher annotations;
- precision and recall of pattern detections;
- relevance of diagnoses;
- playability and purposefulness of exercises;
- clarity and restraint of explanations; and
- learner outcomes under an appropriate study design.
