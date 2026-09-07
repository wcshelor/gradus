# Proposed Contracts

This document specifies semantic contracts for implementation. Exact Python
names may change through a recorded decision, but agents must preserve the
distinctions and invariants described here.

All externally serialized contracts require a `schema_version`. Algorithmic
producers also require a `method_id` and `method_version`.

## Identity and time

### Stable event identity

Canonical written notes, logical notes, rests, directions, and generated events
must have stable IDs within one source document. A derived object never copies
an ID while silently changing its meaning.

### Score position

A position contains:

- exact global quarter-note offset;
- stable measure index;
- printed measure number when available;
- exact offset within the measure; and
- optional encoded voice, staff, and inferred hand qualifiers.

Fractions are serialized as numerator/denominator strings or objects, never as
lossy decimal values in canonical payloads.

### Interval convention

Regions are half-open: an event beginning at `end` is outside `[start, end)`.
Events beginning before `start` but sustaining into a region are represented as
boundary context, not new attacks.

## Passage selection

`PassageSelection` contains:

- `passage_id`;
- source score identity;
- exact start and end positions;
- selection purpose: `detection`, `evidence`, `pattern`, or `practice`;
- selected canonical event IDs;
- sustaining boundary-event IDs;
- inherited meter, key, clef, tempo, and direction context;
- boundary policy and diagnostics; and
- parent passage ID when refined from another selection.

Required invariants:

- start is strictly before end;
- selected attacks begin in the interval;
- event ordering is deterministic;
- source IDs remain resolvable;
- empty selections are explicit valid results or documented errors;
- selection never mutates the source `ScoreIR`.

## Derived view

Every view declares:

- `view_type` and schema version;
- source passage ID;
- construction method and parameters;
- included event IDs;
- ordering and grouping semantics;
- information intentionally omitted;
- confidence when the view includes inference; and
- diagnostics.

Initial views:

- `written_event_stream`: ordered written notes and rests;
- `logical_attack_stream`: tie-collapsed attacks;
- `hand_stream`: logical attacks filtered by inferred hand;
- `voice_stream`: written events filtered by encoded voice;
- `onset_slices`: simultaneous attacks and optionally sounding notes;
- `interval_transitions`: distances between consecutive attacks or onset groups;
- `hand_shapes`: pitch sets and transitions for a single hand;
- `rhythmic_cells`: bounded onset/duration patterns;
- `role_stream`: later inferred melody, bass, accompaniment, or inner voice.

V1 must implement only views required by the broken-chord prototype.

## Feature evidence

Window feature extraction must be capable of returning both an aggregate and
the observations from which it was calculated.

`FeatureEvidence` contains:

- stable `feature_id`;
- feature method/version;
- source passage or region;
- scope and optional hand/voice;
- aggregate value and units;
- summary statistics where relevant;
- ordered observations;
- aggregation rule;
- missingness state;
- reliability and diagnostics.

An `Observation` contains:

- stable observation ID and type;
- required source passage ID (resolvable in the request/result context);
- exact value and units;
- source event, group, or transition IDs;
- exact region;
- optional hand, staff, and voice;
- optional threshold relationship; and
- calculation metadata sufficient to reproduce the value.

Examples:

```text
feature: leaps.mean_inter_onset_distance
aggregate: 7.4 semitones
observations:
  - transition n41 -> n42: 12 semitones
  - transition n42 -> n43: 2 semitones
  - transition n43 -> n44: 9 semitones
```

Feature evidence must not contain a pedagogical diagnosis.

## Passage investigation request — D-013

Both entry adapters produce the same versioned `PassageInvestigation`. This is
a small envelope over the existing `Passage`, not a replacement region model:

- required `passage`: the existing object with score identity, exact interval,
  event references, and lineage;
- required `selection_origin`: `user_selected` or `analyzer_suggested`;
- optional requested hand, with declared unknown/unsupported handling;
- `difficulty_context`: zero or more validated evidence/context records or
  resolvable references; an empty collection is valid;
- producer method/version and diagnostics.

Difficulty context identifies its source score/version, covered region, method,
and actual feature/evidence references. A hotspot reference and its available
score/contributions occur only when supplied by a real analysis result. An
unscored region suggestion can have analyzer origin without a hotspot reference.
Unavailable values remain unavailable, not fabricated zeros. Validate source and
coverage compatibility; unrelated evidence must not silently become local support.

Selection origin records why this investigation began. Method metadata records
how it was produced. Neither `PassagePurpose.DETECTION` nor `parent_id=None`
implies analyzer selection. Keep origin structured through serialization and
refinement, in the investigation context linked to the root passage. Enrichment
with difficulty evidence does not change manual origin or passage identity.

Downstream observations, patterns, and diagnoses refer to passages. They must
not use a hotspot ID as their primary subject. Separate requests can have
different provenance; equivalence tests compare musical observations for matching
source, region, hand, and analysis settings, not whole-payload byte equality.

LS-03a implements this minimal contract and fixtures before entry adapters. It
must not require full evidence/diagnosis model trees: use validated references
where their owners have not implemented those contracts yet.

Implemented 2026-09-05 in `src/passage_practice/models/investigation.py`
(`passage_investigation.v1`, `difficulty_evidence.v1`, `contribution.v1`); no
adapter-equivalence claim follows from these contract fixtures (see T05.3).

### Analyzer-specific input

`HotspotInvestigation`, if retained as an analyzer-specific input, contains:

- source score ID;
- detection region;
- hotspot method and score;
- triggered feature or dimension IDs;
- raw and normalized values;
- dimension contribution ranks;
- references to available feature evidence;
- requested hand mode; and
- warnings inherited from hotspot analysis.

T05.2 translates this input to `PassageInvestigation`; T05.3 translates a manual
selection to the same contract. No downstream consumer must accept two different
request shapes. Preserve real analyzer metadata without duplicating detection.

## Event attribution

`AttributedSignal` contains:

- required source passage ID and feature ID;
- attribution target kind and resolvable target reference: an actual aggregate
  for aggregate attribution, or an actual hotspot/dimension for hotspot attribution;
- optional hotspot reference for aggregate attribution; required for hotspot attribution;
- ranked observation IDs;
- supporting source event IDs;
- contribution method;
- contribution value or rank;
- compact rationale assembled from calculations, not free text invention;
- minimal evidence region; and
- limitations.

Exact attribution is preferred for extrema and counts. Aggregate attribution
may use top observations, threshold exceedances, contiguous clusters, or a
documented leave-one-group-out delta. The method must be visible in the result.

An ordinary passage observation does not require an `AttributedSignal`. Without
a real attribution target, emit observations and leave attribution empty. Merely
making hotspot IDs nullable does not justify inventing contribution values or
target ranks. Manual requests may have real aggregate attribution when available.

## Pattern match

`PatternMatch` contains:

- stable pattern ID;
- required source passage ID;
- detector method/version;
- covered region and source event IDs;
- optional groups within the pattern;
- numeric confidence on a documented scale;
- satisfied criteria;
- failed or contradictory criteria;
- supporting observation IDs;
- inferred hand/voice with confidence; and
- diagnostics.

A pattern ID describes music, not difficulty. For example,
`pattern.broken_chord.equal_subdivision` is separate from a diagnosis about
rapid repositioning.

## Diagnosis

`PassageDiagnosis` contains:

- stable diagnosis ID and schema version;
- required source passage ID and optional validated difficulty-context references;
- affected event IDs, hand, and voices;
- evidence, pattern, and proposed practice regions;
- supporting dimensions when actually measured (may be empty);
- supporting observation references, optional attributed signals, and pattern matches;
- satisfied, missing, and contradictory criteria;
- confidence and confidence method;
- uncertainties and learner-dependent caveats;
- candidate objective IDs;
- candidate strategy IDs;
- provenance status for pedagogical recommendations; and
- diagnostics.

Diagnosis text is a label or template-derived summary. Rich natural-language
explanation is presentation output, not the canonical diagnosis.

The engine may return multiple ranked diagnoses or no supported diagnosis.

A diagnosis can be supported by passage observations and rule criteria without
any hotspot or attribution record. Individual rules must still satisfy their
musical evidence requirements; absence of a hotspot neither establishes a
diagnosis nor disqualifies a passage. Optional context preserves real hotspot
references for traceability, never substitutes for passage identity.

## Objective, strategy, and plan

`PracticeObjective` identifies a target such as recognizing recurring chord
shapes or preparing lateral hand-position changes.

`PracticeStrategy` contains:

- stable strategy ID;
- compatible diagnosis and objective IDs;
- preconditions;
- contraindications;
- transformation family;
- adjustable parameters;
- evidence status;
- literature source IDs or `prototype_unvalidated`; and
- review status.

`ExercisePlan` binds:

- one accepted diagnosis;
- one practice region;
- one objective;
- one strategy;
- one transformation and parameters;
- expected preserved and changed properties;
- validation requirements; and
- optional sequence position within a routine.

No plan may imply that repetition count, tempo, or physical technique is
personalized unless learner information actually supports it.

## Transformation result

`TransformationResult` contains:

- plan and transformation IDs plus versions;
- generated score or passage representation;
- mapping from generated event IDs to zero or more source event IDs;
- operation for each generated event: `copied`, `moved`, `retimed`,
  `lengthened`, `shortened`, `combined`, or `synthesized`;
- removed source event IDs and reasons;
- preserved and changed property reports;
- warnings and unsupported constructs; and
- validation result.

Generated IDs belong to the generated artifact and never replace canonical
source IDs.

## Validation result

`ExerciseValidation` separates categories:

- structural validity;
- rhythmic and measure validity;
- pitch and voice integrity;
- provenance completeness;
- transformation-specific invariants;
- MusicXML serialization validity;
- parser reopenability;
- optional rendering evidence; and
- warnings that require human review.

The result includes individual checks with stable IDs, pass/fail status, and
evidence. One Boolean alone is insufficient for research diagnostics.

## Explanation input

`ExplanationBrief` is the only canonical payload an explanatory LLM or template
renderer needs. It contains:

- bounded score and passage labels;
- structured selection origin and optional difficulty reasons, kept separate;
- diagnosis label, confidence, and caveats;
- a compact allowlist of supported observations and pattern claims;
- selected objective and strategy;
- factual description of each exercise transformation; and
- audience level and requested tone.

An explanation output must not introduce measurements, source claims,
biomechanical claims, or personalization absent from this brief.

## Versioning policy

- Additive optional fields may increment a minor internal version.
- Renamed fields, changed units, different interval semantics, or changed ID
  meaning require a new schema version.
- Registry entries have their own versions because criteria may evolve without
  changing container schemas.
- Frozen regression payloads state the producer and schema versions used.

## Contract-test policy

Each contract needs tests for:

- deterministic serialization;
- exact fraction round trips;
- stable ID references;
- missing and ambiguous values;
- diagnostics;
- forward rejection or handling of unsupported schema versions; and
- representative frozen JSON only after semantics stabilize.
