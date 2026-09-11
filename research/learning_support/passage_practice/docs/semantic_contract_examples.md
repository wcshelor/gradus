# Semantic Contract Examples (S1.7)

Status: illustrative documentation only. IDs (`passage.ex.*`, `hyp.ex.*`)
are synthetic and resolve to nothing; detector names reuse the illustrative
`method_versions` vocabulary from the S1.6 fixture and predate the S3
registry, which owns real detector IDs. These snippets are **not** test
fixtures — the only frozen example payload is
`tests/fixtures/semantic_no_supported_hypothesis.json` (S1.6). Band stances
follow `docs/semantic_confidence_policy.md` (§2 bands, §6 wording).

## High confidence — likely melody, with evidence

Band: high ($0.82$). Stance: "likely the top-voice melody", presented with
an evidence summary. No contradictions; the observation trail is complete.

```json
{
  "schema_version": "semantic_hypothesis.v1",
  "hypothesis_id": "hyp.ex.melody.1",
  "hypothesis_type": "role.melody",
  "source_passage_id": "passage.ex.1",
  "covered_region": {
    "schema_version": "score_interval.v1",
    "start": {
      "schema_version": "score_position.v1",
      "quarters": {"numerator": 0, "denominator": 1},
      "measure_index": 0,
      "offset_in_measure": {"numerator": 0, "denominator": 1}
    },
    "end": {
      "schema_version": "score_position.v1",
      "quarters": {"numerator": 4, "denominator": 1},
      "measure_index": 1,
      "offset_in_measure": {"numerator": 0, "denominator": 1}
    }
  },
  "covered_event_ids": [
    {"schema_version": "source_ref.v1", "id": "n1", "kind": "logical_note"},
    {"schema_version": "source_ref.v1", "id": "n2", "kind": "logical_note"}
  ],
  "confidence": 0.82,
  "confidence_method": "heuristic",
  "method_id": "melody_salience",
  "method_version": "v1",
  "supporting_observation_ids": ["passage.ex.1:pitch-transition:000"],
  "supporting_pattern_ids": [],
  "satisfied_criteria": ["top_voice", "longest_duration"],
  "contradictory_criteria": [],
  "missing_evidence": [],
  "diagnostics": []
}
```

## Low confidence — possible arpeggiation, with a named gap

Band: low ($0.31$). Stance: "possible arpeggiated texture" — presented
only with a learner question (e.g. "Do these notes sound like one broken
shape to you?"), otherwise abstained with a diagnostic. The gap is named
in `missing_evidence`, never zeroed or treated as contradiction.

```json
{
  "schema_version": "semantic_hypothesis.v1",
  "hypothesis_id": "hyp.ex.arp.1",
  "hypothesis_type": "texture.arpeggiated",
  "source_passage_id": "passage.ex.2",
  "covered_region": {
    "schema_version": "score_interval.v1",
    "start": {
      "schema_version": "score_position.v1",
      "quarters": {"numerator": 0, "denominator": 1},
      "measure_index": 0,
      "offset_in_measure": {"numerator": 0, "denominator": 1}
    },
    "end": {
      "schema_version": "score_position.v1",
      "quarters": {"numerator": 2, "denominator": 1},
      "measure_index": 0,
      "offset_in_measure": {"numerator": 2, "denominator": 1}
    }
  },
  "covered_event_ids": [
    {"schema_version": "source_ref.v1", "id": "n7", "kind": "logical_note"},
    {"schema_version": "source_ref.v1", "id": "n8", "kind": "logical_note"}
  ],
  "confidence": 0.31,
  "confidence_method": "heuristic",
  "method_id": "accompaniment_pattern",
  "method_version": "v1",
  "supporting_observation_ids": [],
  "supporting_pattern_ids": [],
  "satisfied_criteria": ["sequential_attacks"],
  "contradictory_criteria": [],
  "missing_evidence": ["bass_line_unresolved"],
  "diagnostics": [
    {
      "schema_version": "diagnostic.v1",
      "code": "single_cue_only",
      "severity": "info",
      "message": "one satisfied criterion; bass evidence unavailable"
    }
  ]
}
```

## Contradictory — rival hypotheses preserved and ranked, not merged

One detector emits two ranked rivals over the same passage: a medium
melody claim ($0.68$, "may be the melody", caveat attached) and a low
inner-voice claim ($0.42$, "possible inner line", learner question). The
criterion `top_voice` is satisfied by the first and contradicted by the
second — the bundle keeps both, in authored order, with the authored
ranking intact (S1.3 preservation rule).

```json
{
  "schema_version": "semantic_bundle.v1",
  "bundle_id": "bundle.ex.rivals.1",
  "source_passage_id": "passage.ex.3",
  "hypotheses": [
    {
      "schema_version": "semantic_hypothesis.v1",
      "hypothesis_id": "hyp.ex.rival.melody",
      "hypothesis_type": "role.melody",
      "source_passage_id": "passage.ex.3",
      "covered_region": {
        "schema_version": "score_interval.v1",
        "start": {
          "schema_version": "score_position.v1",
          "quarters": {"numerator": 0, "denominator": 1},
          "measure_index": 0,
          "offset_in_measure": {"numerator": 0, "denominator": 1}
        },
        "end": {
          "schema_version": "score_position.v1",
          "quarters": {"numerator": 4, "denominator": 1},
          "measure_index": 1,
          "offset_in_measure": {"numerator": 0, "denominator": 1}
        }
      },
      "covered_event_ids": [
        {"schema_version": "source_ref.v1", "id": "n1", "kind": "logical_note"},
        {"schema_version": "source_ref.v1", "id": "n2", "kind": "logical_note"}
      ],
      "confidence": 0.68,
      "confidence_method": "heuristic",
      "method_id": "melody_salience",
      "method_version": "v1",
      "supporting_observation_ids": ["passage.ex.3:pitch-transition:000"],
      "supporting_pattern_ids": [],
      "satisfied_criteria": ["top_voice"],
      "contradictory_criteria": ["accompaniment_ostinato_overlap"],
      "missing_evidence": [],
      "diagnostics": []
    },
    {
      "schema_version": "semantic_hypothesis.v1",
      "hypothesis_id": "hyp.ex.rival.inner",
      "hypothesis_type": "role.inner_voice",
      "source_passage_id": "passage.ex.3",
      "covered_region": {
        "schema_version": "score_interval.v1",
        "start": {
          "schema_version": "score_position.v1",
          "quarters": {"numerator": 0, "denominator": 1},
          "measure_index": 0,
          "offset_in_measure": {"numerator": 0, "denominator": 1}
        },
        "end": {
          "schema_version": "score_position.v1",
          "quarters": {"numerator": 4, "denominator": 1},
          "measure_index": 1,
          "offset_in_measure": {"numerator": 0, "denominator": 1}
        }
      },
      "covered_event_ids": [
        {"schema_version": "source_ref.v1", "id": "n3", "kind": "logical_note"},
        {"schema_version": "source_ref.v1", "id": "n4", "kind": "logical_note"}
      ],
      "confidence": 0.42,
      "confidence_method": "heuristic",
      "method_id": "melody_salience",
      "method_version": "v1",
      "supporting_observation_ids": [],
      "supporting_pattern_ids": [],
      "satisfied_criteria": ["sustained_inner_tone"],
      "contradictory_criteria": ["top_voice"],
      "missing_evidence": ["voice_leading_continuity"],
      "diagnostics": []
    }
  ],
  "ranked_hypothesis_ids": ["hyp.ex.rival.melody", "hyp.ex.rival.inner"],
  "view_refs": ["attack_stream:passage.ex.3"],
  "observation_refs": ["passage.ex.3:pitch-transition:000"],
  "method_versions": ["melody_salience@v1"],
  "diagnostics": []
}
```

## No-supported — nothing to present, honestly recorded

When no hypothesis reaches the $0.25$ presentation floor, the producer
returns an empty bundle with a `no_supported_hypothesis` diagnostic —
never a low-confidence filler. The frozen payload lives in
`tests/fixtures/semantic_no_supported_hypothesis.json` (S1.6); its shape:

```json
{
  "schema_version": "semantic_bundle.v1",
  "bundle_id": "bundle.empty.1",
  "source_passage_id": "passage.empty.1",
  "hypotheses": [],
  "ranked_hypothesis_ids": [],
  "method_versions": ["melody_salience@v1", "bass_anchor@v1"],
  "diagnostics": [
    {
      "code": "no_supported_hypothesis",
      "message": "no detector met its minimum evidence threshold"
    }
  ]
}
```

(abridged: `view_refs`/`observation_refs` are `[]`; see the fixture file
for the complete frozen payload.)

## What these examples must not be used for

- Not fixtures: no test may load them (the S1.6 file is the only frozen
  example payload).
- Not thresholds: numeric cutoffs stay detector-local; the $0.25$ floor is
  a presentation rule.
- Not evidence: IDs, criteria, and detector names are illustrative. Real
  hypotheses cite resolvable passage events, real observation IDs, and
  S3-registered detector versions.
