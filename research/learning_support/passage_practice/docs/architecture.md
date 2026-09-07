# Architecture

## Architectural objective

Build an explainable passage-first pipeline that accepts a learner-selected
region or a suggestion from the established difficulty system. A separate passage
engine measures events, attributes real signals when available, recognizes musical
patterns, proposes qualified diagnoses, and generates controlled practice material.

The architecture favors independently testable stages over a single model that
maps a score directly to advice.

## System context

```text
                    PIANO DIFFICULTY AREA

 MusicXML/MXL -> loader -> ScoreIR -> window features -> hotspots
                    |          |             |
                    |          |             +-- dimension contribution
                    |          +---------------- event evidence
                    +--------------------------- source identity

                  PASSAGE PRACTICE AREA

  hotspot + ScoreIR                    (analyzer-suggested entry)
        OR
  exact user-selected region + ScoreIR (controlled entry; see docs/entry_points.md)
        -> passage selection and context expansion
       -> derived views and event attribution
       -> targeted pattern detectors
       -> diagnostic rule engine
       -> practice-objective and strategy selection
       -> deterministic transformations
       -> exercise validation and MusicXML export
       -> structured explanation input
```

Both entry adapters produce `PassageInvestigation` over the existing `Passage`,
with structured selection origin and optional difficulty context (D-013). Musical
observations require passage identity, not a hotspot ID. Adding difficulty context
to a user selection does not change its origin. Ordinary observations are distinct
from attribution to an actual aggregate or hotspot target.

The difficulty area remains useful without the passage-practice area. Passage
practice consumes its outputs but does not redefine difficulty extraction.

## Layer model

### Layer 0: source document

The original MusicXML payload and source metadata. It provides the authoritative
notation and archive boundary. It is not itself the analysis API.

### Layer 1: canonical score facts

The normalized, parser-independent representation of written and logical score
events. Existing `ScoreIR` is the starting point. This layer contains facts and
normalization diagnostics, not melody labels or difficulty diagnoses.

### Layer 2: passages and derived views

A passage is an exact selection with inherited score context. Views project
that passage into representations needed by algorithms, such as hand streams,
onset slices, interval transitions, hand shapes, rhythmic cells, or encoded
voices.

Views are disposable and reproducible. They must link their elements back to
canonical event IDs and document what information they omit.

### Layer 3: observations and hotspot attribution

An observation measures a concrete event, transition, or group. Examples are
the span of one onset group, the pitch distance between two attacks, or an
unmatched left-hand onset.

Window features summarize observations. Hotspot attribution connects a high
window value to:

- the difficulty dimensions that contributed to the hotspot; and
- the observations and score events that materially contributed to each
  dimension.

### Layer 4: musical pattern hypotheses

Pattern detectors interpret observations and relationships. A detector returns
a match with confidence, evidence, covered events, method/version, and
contradictions. It does not prescribe an exercise.

The v1 pattern is a deliberately restricted broken-chord grouping. Later
patterns may include scale fragments, repeated notes, octaves, chord streams,
melody-in-chords, hand-position changes, or rhythmic independence.

### Layer 5: passage diagnoses

A diagnostic rule combines hotspot triggers or controlled-baseline
observations, event evidence, and pattern
matches into a qualified hypothesis about a potential challenge. It identifies
the affected material, narrows the relevant region, states uncertainty, and
names possible practice objectives.

A diagnosis concerns score-derived potential difficulty unless learner evidence
is separately supplied. It must never claim certainty about an individual.

### Layer 6: objectives, strategies, and exercise plans

An objective states what the exercise is intended to develop. A strategy states
the pedagogical approach. An exercise plan binds a supported strategy to a
passage, parameters, and safety constraints.

This layer will eventually consult a literature-grounded knowledge base. V1 may
use a small reviewed registry with explicit provenance status.

### Layer 7: transformations and validation

Transformations deterministically modify or select score material. They return
generated events with provenance plus a report describing preserved, changed,
removed, and synthesized material.

Validation checks musical and serialization invariants before export. A failed
validation must not be silently converted into an apparently successful
exercise.

### Layer 8: presentation adapters

MusicXML export, JSON reports, CLI output, and optional LLM prompts consume
structured results. Presentation adapters do not create new diagnoses or alter
notation semantics.

## Dependency direction

Allowed dependencies point downward in this list:

```text
presentation
    -> validation and transformations
    -> exercise plans and strategies
    -> diagnoses
    -> patterns
    -> observations and attribution
    -> passages and views
    -> score facts
    -> source document
```

Registries depend on contracts and concrete plugins depend on registry
interfaces. Core contracts must not import individual detectors or strategies.

## Coarse-to-fine execution

Whole-score analysis should remain comparatively cheap:

1. Build fixed or sliding windows.
2. Extract summary features.
3. Detect and rank hotspots.
4. Carry forward the dimensions responsible for each candidate.

Selected candidates or learner-selected regions receive more expensive analysis:

1. Build an exact passage and neighboring context.
2. retrieve or calculate event-level feature evidence;
3. prioritize pattern detectors using triggered dimensions;
4. evaluate diagnostic rules;
5. refine detection boundaries into evidence, pattern, and practice regions;
6. propose strategies and transform only accepted plans.

Candidate triggers prioritize work but are not absolute gates. A detector may
run as a fallback when evidence is ambiguous.

## Region semantics

The system distinguishes four regions:

- **Detection region**: the initial region under investigation, either a difficulty
  window or user-selected interval; the existing enum does not encode origin.
- **Evidence region**: the minimal event range materially contributing to its
  signals.
- **Pattern region**: the complete recognized musical figure, which may cross
  the window boundary.
- **Practice region**: the pattern plus enough approach and release context for
  a useful exercise.

All regions use exact half-open time intervals `[start, end)` and stable measure
references. Boundary policies for sustaining notes, grace notes, and ties must
be explicit.

## Representation strategy

Use a hybrid source/normalized design:

```text
retained source document
        <-> stable source references
normalized score and passage objects
        -> derived views
        -> generated exercise document
```

V1 does not require a lossless custom model of all MusicXML. It requires a
documented supported subset and the ability to report unsupported or lossy
constructs.

There is no universal token vocabulary. Algorithms request typed projections
from the canonical passage. A future sequence model may tokenize a chosen view,
but model tokens must not become the repository's only musical representation.

## LLM boundary

An LLM may:

- turn structured evidence into learner-appropriate language;
- organize approved strategies into a routine;
- retrieve candidate literature records for human review; or
- propose hypotheses that are labeled unverified.

An LLM must not be required to:

- parse or validate MusicXML;
- fabricate source-event evidence;
- decide that a score-derived challenge applies to a particular learner;
- directly mutate the canonical score; or
- make deterministic tests depend on network access or nondeterministic text.

The explanation interface receives a bounded, versioned diagnosis payload.
Tests assert that explanations do not introduce unsupported claims.

## Error and uncertainty model

Each layer returns results plus structured diagnostics. Errors are reserved for
conditions that prevent a contract from being fulfilled. Warnings identify
loss, ambiguity, fallback logic, or weak confidence.

Important examples:

- region boundary intersects an unsupported tuplet;
- a hand is inferred from staff with low confidence;
- a pattern matches rhythmically but not harmonically;
- transformation would create an overfull voice;
- source directions cannot be represented in the supported writer;
- no diagnosis meets its minimum evidence threshold.

"No supported diagnosis" is a valid outcome, not a pipeline failure.

## Extensibility rules

- New views implement a stable projection interface and declare information
  loss.
- New observations use stable IDs and identify source events.
- New pattern detectors register metadata, supported contexts, and versions.
- New diagnoses are data/rules over structured evidence when possible.
- New strategies state objective, evidence status, contraindications, and
  compatible transformations.
- New transformations are deterministic plugins with invariant tests.
- Learned models may replace or rank a stage only behind the same typed
  contract and against a documented baseline.

## Proposed package boundary

Agents may refine names through a recorded decision, but should start from:

```text
passage_practice/
  src/passage_practice/
    models/              cross-layer contracts
    passages/            exact selection and context
    views/               derived projections
    attribution/         event contribution logic
    patterns/            semantic pattern detectors
    diagnosis/           registry and rule engine
    strategies/          objectives and exercise planning
    transformations/     score transformations
    export/              MusicXML and JSON adapters
    validation/          musical and format checks
    pipeline.py          thin orchestration only
  tests/
    fixtures/
    unit/
    contract/
    integration/
    regression/
```

Do not create this entire tree as empty scaffolding. Each work package creates
only the directories it actually uses.
