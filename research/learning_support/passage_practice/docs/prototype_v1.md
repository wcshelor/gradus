# Prototype V1: Broken-Chord Passage Practice

## Research purpose

The first prototype demonstrates the complete architectural chain using one
narrow, inspectable musical situation:

> A window is flagged partly because one hand plays a fast sequence of notes
> organized into recurring broken-chord groups with meaningful movement between
> groups. The system locates the responsible events, recognizes the pattern,
> proposes a qualified diagnosis, and produces blocked-chord and rhythmic
> practice variants.

This is a vertical slice, not a claim that broken chords are the most important
or general difficulty category.

## Supported input profile

V1 deliberately supports passages with:

- `score-partwise` MusicXML or MXL accepted by the existing raw loader;
- one selected piano-like part;
- one or two piano staves;
- an explicit or conservatively inferable hand;
- regular measure context with known divisions and meter;
- pitched, non-grace attacks in a single encoded voice for the target hand;
- equal or simply related subdivisions within each candidate group;
- no tuplet crossing the selected transformation boundary;
- no repeat expansion requirement; and
- enough local context to form at least two candidate groups.

Unsupported inputs must return diagnostics. They must not be transformed using
silent approximations.

## Entry modes

The pipeline supports two equivalent entry paths after score normalization:

1. **Automatic**: accept a `HotspotInvestigation` produced from Difficulty
   Dynamics.
2. **Controlled baseline**: accept an explicit exact region and optional target
   hand.

The controlled path isolates pattern, diagnosis, and transformation quality
from hotspot-detection quality and is required for testing. It requires no
hotspot ID, difficulty score, or profile: an exact region plus optional target
hand is a complete investigation input (see `docs/entry_points.md`).

Both adapters return `PassageInvestigation` over the existing `Passage` (D-013).
The automatic input remains supported, but is not the downstream subject type.
Selection origin and optional difficulty context are separate. Equivalent source,
region, hand, and observation settings must give equivalent musical observations;
route-specific IDs, reasons, and attribution context need not be identical.

## Candidate hotspot triggers

The broken-chord investigation is prioritized when one or more of these signals
are elevated for a hand:

- attack or note density;
- mean, upper-quantile, or maximum inter-onset pitch distance;
- register range;
- hand-shape transition distance;
- short written duration;
- repeated harmonic-group evidence.

These triggers select a detector; they do not themselves establish the pattern
or diagnosis.

## Event attribution

For the selected region, V1 must expose:

- ordered target-hand attacks;
- exact distance between consecutive attacks or onset groups;
- duration and inter-onset interval of each attack;
- metrical position;
- pitch sets sounding or attacking at each onset;
- top observations responsible for triggered aggregates; and
- a minimal evidence region covering those observations.

For an average, the attribution method must state whether it uses threshold
exceedances, top observations, contiguous clusters, or leave-one-out change.

## Restricted broken-chord definition

A v1 match consists of at least two adjacent groups in one hand. Each group:

- contains at least three pitched attacks;
- occupies a documented metrical unit, initially one beat or a configured
  simple multiple;
- contains mostly non-simultaneous attacks;
- has regular or near-regular inter-onset spacing under a configured tolerance;
- can be represented as a pitch set with at least three distinct pitches; and
- shares sufficient pitch-class or interval-shape similarity with a neighboring
  group, or participates in a recurring group structure.

The detector reports its exact grouping policy and thresholds. It must reject
or lower confidence for:

- scalar runs with no stable harmonic grouping;
- repeated single notes;
- already blocked chords;
- ornamental figures too short to form two groups;
- overlapping voices that cannot be separated confidently; and
- irregular tuplets outside the supported subset.

Initial tests should use obvious synthetic fixtures. Threshold optimization on
a repertoire corpus is a later research task.

## V1 diagnosis

Initial stable ID:

```text
technical.broken_chord.rapid_reconfiguration
```

The diagnosis may be proposed when:

- the restricted broken-chord pattern matches;
- attack timing is sufficiently compressed relative to the local beat;
- one or more relocation or hand-shape observations support reconfiguration;
- the relevant events materially support a hotspot dimension or occur inside a
  controlled baseline region; and
- contradictory evidence does not dominate.

The diagnosis should use cautious language: the passage exhibits a potential
challenge involving rapid broken-chord organization or repositioning. Without
learner evidence it must not claim that the passage is difficult for a specific
person.

Candidate objectives:

- `objective.recognize_chord_shapes`;
- `objective.prepare_position_changes`;
- `objective.stabilize_even_subdivision`.

## Required exercise variants

### Blocked-chord reduction

For each recognized group:

- collect the intended pitch set;
- create one simultaneous onset at the group's start;
- preserve target hand, staff, and supported articulation context;
- give the chord a duration that fills the group under the selected v1 policy;
- remove or replace the original sequential target-hand attacks;
- preserve non-target material only when the plan explicitly requests it; and
- map every generated chord note to the source group notes that justify it.

V1 default output is target hand alone. Keeping the other hand is a separate
plan parameter because it changes the pedagogical task.

### Rhythmic variants

For regular pairs of equal subdivisions, generate:

- long-short; and
- short-long.

The transformation must preserve:

- attack order;
- pitch order;
- total duration of every transformed pair;
- group and measure duration;
- target hand and voice; and
- source provenance.

Odd residual notes, tuplets, grace notes, and ties crossing a transformed pair
must be handled by an explicit supported policy or rejected.

### Optional integration variant

Once the two required transformations work, a later v1 package may create a
short routine:

1. blocked groups;
2. long-short;
3. short-long;
4. original passage;
5. original passage with approach and release context.

This composition step must reuse validated transformations rather than
reimplement them.

## Practice-region policy

The pattern region covers complete detected groups. The default practice region
adds one configurable metrical unit before and after when available. Context
expansion must not split an unsupported tuplet or create invalid partial voice
durations.

Detection, evidence, pattern, and practice regions are all retained in the
result so boundary refinement can be evaluated.

## MusicXML output contract

V1 output must:

- be valid XML and supported `score-partwise` MusicXML;
- contain sufficient part, measure, divisions, meter, key, clef, voice, staff,
  pitch, duration, chord, rest, and tie information for its supported material;
- reopen through the repository's raw MusicXML loader and normalization path;
- preserve exact intended attack positions and durations after reopening;
- avoid claiming original engraving fidelity;
- use deterministic IDs/order where the format permits; and
- accompany the score with a JSON provenance and validation report.

Compressed `.mxl` output is optional for v1 if plain `.musicxml` is reliable.

## Explanation contract

The initial explanation can be template-driven. It must identify:

- why the region was investigated;
- which hand and events carried the main signals;
- which broken-chord criteria matched;
- the qualified diagnosis and its uncertainty;
- the objective of each exercise; and
- how to return from the exercise to the original passage.

It must not invent fingering, repetitions, target tempo, pain guidance, or
learner-specific conclusions.

## V1 acceptance scenario

Given a small fixture containing an ordinary opening window and a later
right-hand broken-chord window:

1. Difficulty Dynamics ranks the latter as a hotspot using configured features
   (automatic entry). The controlled twin starts instead from the same exact
   region with no profile computed.
2. Observations name the target-hand transitions and attacks on both routes.
   Attribution identifies contributions only to real available aggregate/hotspot
   targets; the controlled twin does not invent a hotspot or contributions.
3. The broken-chord detector covers the intended groups and excludes surrounding
   scalar or sustained material.
4. The diagnosis engine returns the stable v1 diagnosis with evidence and
   caveats.
5. Blocked, long-short, and short-long exercises are generated.
6. Every generated note has valid provenance.
7. Each exercise passes structural and transformation-specific validation.
8. Each MusicXML output reparses to the intended pitches, onsets, and durations.
9. A negative scalar-run fixture produces no broken-chord diagnosis.
10. Repeated runs produce semantically identical serialized results.

## Deferred questions

- Optimal group-boundary inference across irregular meter.
- Harmonic analysis requiring key-aware chord spelling.
- Fingering and learner hand size.
- Pedal-aware blocking choices.
- Melody preservation inside arpeggiated textures.
- New, composed etude material rather than source transformations.
- Empirically calibrated diagnosis confidence.
- Personalized strategy sequencing and dosage.
