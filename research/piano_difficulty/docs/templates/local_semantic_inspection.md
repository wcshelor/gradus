# Local Semantic Inspection: Measures A-B

<!-- Copy this template for each inspected passage. Fill spans, evidence, and instruction units deterministically from SemanticBundle. No LLM prose. -->
<!-- Builder: research/piano_difficulty/src/piano_difficulty/semantic_tokens/local_inspection.py → build_local_inspection() + render_markdown() -->
<!-- Runner: research/piano_difficulty/tests/scripts/generate_local_inspection.py -->

## Passage Scope
- Report span: A-B
- Flagged measures: ...
- Source score: ...

## Instruction Units

### 1. LH Leap To Chord
Instruction sentence.
- Hand / voice: LH — left hand
- Interval / distance: ... semitones
- Context: single note → chord, landing beat ...
- Evidence: component: leap_interval=..., token: leap@ m.X [...]
- Caveats: ...

### 2. RH Chord Shape / Voicing
Instruction sentence.
- Hand / voice: RH
- Shape: ...-note chord, span ... semitones
- Repetition / shift: ...
- Evidence: component: target_span=..., token: chord_shape@ m.Y [...]
- Caveats: ...

## Supporting Local Objects

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | ... | A | ... | below threshold / not top-ranked |
| S2 | ... | ... | ... | ... |

## Broad Context / Low Local Specificity

| Object | Span | Reason for exclusion |
|--------|------|----------------------|
| ... | 1-N | piece-level statistic, no measure-specific action |
| ... | 1-N | broad context, not a local driver here |

## Evidence Summary
- Token kind counts: ...
- Gesture kind counts: ...
- Component type counts: ...
- Musical objects in span: ...
- Components in span: ...
- Top components: ...

<details>
<summary>Raw object/component evidence</summary>

```json
{
  "span": "A-B",
  "musical_objects": [],
  "object_components": [],
  "derived_tokens": [],
  "gestures": []
}
```

</details>
