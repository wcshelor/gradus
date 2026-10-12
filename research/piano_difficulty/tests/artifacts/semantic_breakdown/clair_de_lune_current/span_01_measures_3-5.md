<!-- Semantic breakdown span 01: flagged 4 -> expanded 3-5 -->
<!-- Span provenance: extracted from research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json (leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans)); flagged_provenance: leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans); manual testing passages 25-26, 27-28; span source: extracted_from_analysis_json; flagged (4,) -> expanded (3, 5) (context 1, merge=True) -->
<!-- Generated via local inspection delegate; analysis_json: research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json -->
# Local Semantic Inspection: Measures 3-5

## Passage Scope
- Report span: 3-5
- Flagged measures: 4
- Source score: /Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml

## Instruction Units
### 1. Descending Scalar Run
The left hand moves stepwise down from C4 to Bb3 at m.5-7, covering 5 semitones across 4 notes. Steps: -2, -1, -2.

- Hand / voice: left
- Pitch line: C4 → Bb3 (down, span 5 semitones, 4 notes)
- Step intervals: -2, -1, -2
- Evidence: object: descending_scalar_run [ges52:scalar_run]; evidence_event_ids=['e47:n68', 'e46:n66', 'e52:n78']; confidence=0.85; components: beat_alignment:left, direction:left, note_count:left
- Caveats: none — score-derived evidence
- Consistency: no warnings

### 2. Melody with accompaniment
Both hands form a melody-with-accompaniment texture at m.5: one layer carries the melodic line while another supplies aligned support. Melody Gb4-C5 over accompaniment Db4-Eb4.

- Hand / voice: both
- Melody tones: Gb4-C5 (4 notes)
- Accompaniment tones: Db4-Eb4 (2 notes)
- Register separation: 2 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_with_accompaniment [ges40:melody_with_accompaniment]; evidence_event_ids=['e36:n63', 'e37:n65', 'e38:n67']; confidence=0.78; components: accompaniment_pattern_reference:left, balance_relation:both, onset_alignment:both
- Caveats: balance_inferred_from_texture
- Consistency: 5 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [accompaniment_pattern_reference]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [balance_relation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [onset_alignment]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [register_separation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

### 3. Melody Voicing over Accompaniment
The texture presents a melody voicing over accompaniment at m.5: the upper line projects while lower tones provide harmonic support. Melody Gb4-C5 over accompaniment Db4-Eb4.

- Hand / voice: both
- Melody tones: Gb4-C5 (4 notes)
- Accompaniment tones: Db4-Eb4 (2 notes)
- Register separation: 2 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_voicing_over_accompaniment [ges40:melody_with_accompaniment]; evidence_event_ids=['e36:n63', 'e37:n65', 'e38:n67']; confidence=0.66; components: accompaniment_pattern_reference:left, balance_relation:both, onset_alignment:both
- Caveats: balance_inferred_from_texture
- Consistency: 5 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [accompaniment_pattern_reference]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [balance_relation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [onset_alignment]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [register_separation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

## Supporting Local Objects
_Showing 8 of 15 object groups (compact). Full details in <details>._

| # | Object | Count | Best conf | Measures | Why not promoted |
|---|--------|-------|-----------|----------|------------------|
| G1 | melody_with_accompaniment (Melody with accompaniment) | 3 | 0.78 | 3-6 | relevant locally but not top-ranked; kept as supporting |
| G2 | repeated_position_pattern (Repeated position pattern) | 8 | 0.72 | 2-3,5-7 | relevant locally but not top-ranked; kept as supporting |
| G3 | broken_chord_accompaniment (Broken-chord accompaniment) | 1 | 0.70 | 3-4 | relevant locally but not top-ranked; kept as supporting |
| G4 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 3 | 0.66 | 3-6 | relevant locally but not top-ranked; kept as supporting |
| G5 | dotted_rhythm (Dotted rhythm) | 4 | 0.66 | 3,5 | relevant locally but not top-ranked; kept as supporting |
| G6 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 1 | 0.66 | 3-4 | relevant locally but not top-ranked; kept as supporting |
| G7 | sequence (Sequence) | 3 | 0.62 | 2-3 | relevant locally but not top-ranked; kept as supporting |
| G8 | repeated_rhythm_cell (Repeated rhythm cell) | 3 | 0.62 | 5-6 | relevant locally but not top-ranked; kept as supporting |

<details>
<summary>All supporting objects (ungrouped)</summary>

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | ornamented_melody (Ornamented melody) | 2 | local overlap m.2, confidence 0.55, 6 events | below promotion confidence threshold |
| S2 | stepwise_melody (Stepwise melody) | 2-3 | local overlap m.2-3, confidence 0.58, 8 events | below promotion confidence threshold |
| S3 | syncopation (Syncopation) | 2 | local overlap m.2, confidence 0.51, 4 events | below promotion confidence threshold |
| S4 | turn_mordent_trill_like_figure (Turn/mordent/trill-like figure) | 2 | local overlap m.2, confidence 0.52, 6 events | below promotion confidence threshold |
| S5 | chromatic_line (Chromatic line) | 2-3 | local overlap m.2-3, confidence 0.60, 6 events | relevant locally but not top-ranked; kept as supporting |
| S6 | repeated_position_pattern (Repeated position pattern) | 2-3 | local overlap m.2-3, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S7 | repeated_position_pattern (Repeated position pattern) | 2-3 | local overlap m.2-3, confidence 0.72, 8 events | relevant locally but not top-ranked; kept as supporting |
| S8 | sequence (Sequence) | 2-3 | local overlap m.2-3, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S9 | sequence (Sequence) | 2-3 | local overlap m.2-3, confidence 0.62, 8 events | relevant locally but not top-ranked; kept as supporting |
| S10 | ornamented_melody (Ornamented melody) | 3 | local overlap m.3, confidence 0.55, 6 events | below promotion confidence threshold |
| S11 | repeated_position_pattern (Repeated position pattern) | 3 | local overlap m.3, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S12 | sequence (Sequence) | 3 | local overlap m.3, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S13 | syncopation (Syncopation) | 3 | local overlap m.3, confidence 0.47, 6 events | below promotion confidence threshold |
| S14 | turn_mordent_trill_like_figure (Turn/mordent/trill-like figure) | 3 | local overlap m.3, confidence 0.52, 6 events | below promotion confidence threshold |
| S15 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 3-4 | local overlap m.3-4, confidence 0.66, 5 events | relevant locally but not top-ranked; kept as supporting |
| S16 | broken_chord_accompaniment (Broken-chord accompaniment) | 3-4 | local overlap m.3-4, confidence 0.70, 5 events | relevant locally but not top-ranked; kept as supporting |
| S17 | dotted_rhythm (Dotted rhythm) | 3 | local overlap m.3, confidence 0.66, 1 events | relevant locally but not top-ranked; kept as supporting |
| S18 | intervallic_melody (Intervallic melody) | 3-4 | local overlap m.3-4, confidence 0.58, 5 events | below promotion confidence threshold |
| S19 | dotted_rhythm (Dotted rhythm) | 3 | local overlap m.3, confidence 0.66, 1 events | relevant locally but not top-ranked; kept as supporting |
| S20 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 3-4 | local overlap m.3-4, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S21 | melody_with_accompaniment (Melody with accompaniment) | 3-4 | local overlap m.3-4, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S22 | stepwise_melody (Stepwise melody) | 4 | local overlap m.4, confidence 0.58, 7 events | below promotion confidence threshold |
| S23 | syncopation (Syncopation) | 4 | local overlap m.4, confidence 0.51, 4 events | below promotion confidence threshold |
| S24 | turn_mordent_trill_like_figure (Turn/mordent/trill-like figure) | 4 | local overlap m.4, confidence 0.52, 6 events | below promotion confidence threshold |
| S25 | repeated_rhythm_cell (Repeated rhythm cell) | 5-6 | local overlap m.5-6, confidence 0.62, 8 events | relevant locally but not top-ranked; kept as supporting |
| S26 | repeated_position_pattern (Repeated position pattern) | 5 | local overlap m.5, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S27 | repeated_rhythm_cell (Repeated rhythm cell) | 5 | local overlap m.5, confidence 0.62, 4 events | relevant locally but not top-ranked; kept as supporting |
| S28 | repeated_rhythm_cell (Repeated rhythm cell) | 5 | local overlap m.5, confidence 0.62, 4 events | relevant locally but not top-ranked; kept as supporting |
| S29 | syncopation (Syncopation) | 5 | local overlap m.5, confidence 0.51, 4 events | below promotion confidence threshold |
| S30 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 5 | local overlap m.5, confidence 0.66, 7 events | relevant locally but not top-ranked; kept as supporting |
| S31 | melody_with_accompaniment (Melody with accompaniment) | 5 | local overlap m.5, confidence 0.78, 7 events | relevant locally but not top-ranked; kept as supporting |
| S32 | repeated_position_pattern (Repeated position pattern) | 5 | local overlap m.5, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S33 | repeated_position_pattern (Repeated position pattern) | 5 | local overlap m.5, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S34 | stepwise_melody (Stepwise melody) | 5 | local overlap m.5, confidence 0.58, 5 events | below promotion confidence threshold |
| S35 | dotted_rhythm (Dotted rhythm) | 5 | local overlap m.5, confidence 0.66, 1 events | relevant locally but not top-ranked; kept as supporting |
| S36 | dotted_rhythm (Dotted rhythm) | 5 | local overlap m.5, confidence 0.66, 1 events | relevant locally but not top-ranked; kept as supporting |
| S37 | repeated_position_pattern (Repeated position pattern) | 5 | local overlap m.5, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S38 | thumb_under_scale_passage (Thumb-under scale passage) | 5-7 | local overlap m.5-7, confidence 0.52, 8 events | below promotion confidence threshold |
| S39 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 5-6 | local overlap m.5-6, confidence 0.66, 6 events | relevant locally but not top-ranked; kept as supporting |
| S40 | melody_with_accompaniment (Melody with accompaniment) | 5-6 | local overlap m.5-6, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S41 | repeated_position_pattern (Repeated position pattern) | 6-7 | local overlap m.6-7, confidence 0.70, 6 events | relevant locally but not top-ranked; kept as supporting |

</details>

_+7 additional groups hidden in full table above; top 8 shown for readability._

## Broad Context / Low Local Specificity
| Object | Span | Reason for exclusion |
|--------|------|----------------------|
| dynamic_swell_across_phrase | 1-72 (72 measures) | span 72 measures exceeds local span 3; piece-level or long gesture |
| phrase_shaping_over_repeated_pattern | 1-72 (72 measures) | span 72 measures exceeds local span 3; piece-level or long gesture |
| balance_between_voices | 1-72 (72 measures) | span 72 measures exceeds local span 3; piece-level or long gesture |
| pedal_point_accompaniment | 1,3,9,26,29,34-38,51,53-54,57-59,67,69-71 | span 71 measures exceeds local span 3; piece-level or long gesture |
| two_voice_counterpoint | 1-72 (72 measures) | span 72 measures exceeds local span 3; piece-level or long gesture |
| pedal_point_accompaniment | 1,9,13,21,23-24,34-38,41,55-56,59 | span 59 measures exceeds local span 3; piece-level or long gesture |
| repeated_chord_accompaniment | 1,9,35-36,55-56,59 | span 59 measures exceeds local span 3; piece-level or long gesture |
| repeated_chord_accompaniment | 1-2,9,29-30,57,59 | span 59 measures exceeds local span 3; piece-level or long gesture |
| repeated_chord_accompaniment | 2-3,58 | span 57 measures exceeds local span 3; piece-level or long gesture |
| chordal_homophonic_texture | 5-6,8,11,15-26,56,61,63-65,67,72 | span 68 measures exceeds local span 3; piece-level or long gesture |

## Evidence Summary
- Token kind counts: chord_shape: 13, density_spike: 22, hand_movement: 26, harmonic_simultaneity: 17, melodic_interval: 47, onset_alignment: 4, pattern_repetition: 8
- Gesture kind counts: accompaniment_pattern: 8, arpeggio: 1, block_chord_landing: 4, cadence_like_arrival: 30, melody_with_accompaniment: 4, scalar_run: 1
- Component type counts: accompaniment_layer: 8, accompaniment_pattern_reference: 2, accompaniment_role: 2, balance_relation: 8, bass_anchor: 2, beat_alignment: 1, beat_placement: 2, beat_positions: 3, direction: 1, duration_pattern: 3, hand_relocation: 2, harmonic_collection: 2, interval_path: 2, melody_layer: 8, note_count: 1, onset_alignment: 8, register_separation: 8, repetition_count: 3, rhythm_cell: 5, rhythmic_independence: 8, span_semitones: 1, start_anchor: 1, step_pattern: 1, upper_chord_landing: 2
- Musical objects in span: 54
- Components in span: 84
- Top components: balance_relation ×8 (register_gap_semitones=2); melody_layer ×8 (melody_pitch_range=[68, 73]); onset_alignment ×8 (overlapping_onsets=1)
- Consistency warnings: 10 (see Instruction Units and JSON diagnostics)

<details>
<summary>Raw object/component evidence</summary>

_Raw JSON truncated for readability (349076 chars total, showing first 12000). Full payload written to sibling .json when generated via script._

```json
{
  "span": "3-5",
  "flagged_measures": [
    "4"
  ],
  "source_score": "/Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml",
  "musical_objects": [
    {
      "object_id": "dynamic_swell_across_phrase",
      "kind": "dynamic_swell_across_phrase",
      "label": "Dynamic swell across phrase",
      "hand": null,
      "start_onset": "0",
      "end_onset": "154321/480",
      "measure_start": 1,
      "measure_end": 72,
      "measure_numbers": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "70",
        "71",
        "72"
      ],
      "evidence_event_ids": [
        "e1:n2",
        "e2:n3",
        "e3:n11",
        "e4:n12",
        "e5:n4",
        "e6:n5",
        "e7:n8",
        "e8:n9"
      ],
      "token_ids": [],
      "gesture_ids": [],
      "confidence": 0.62,
      "payload": {
        "related_dimensions": [
          "expression_sound_control",
          "rhythm_timing"
        ],
        "detection_heuristic": "dynamics_swell_wedge",
        "wedge_count": 33,
        "dynamics": [
          "crescendo",
          "f",
          "diminuendo"
        ]
      },
      "caveats": []
    },
    {
      "object_id": "phrase_shaping_over_repeated_pattern",
      "kind": "phrase_shaping_over_repeated_pattern",
      "label": "Phrase shaping over repeated pattern",
      "hand": "right",
      "start_onset": "0",
      "end_onset": "154321/480",
      "measure_start": 2,
      "measure_end": 3,
      "measure_numbers": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "70",
        "71",
        "72"
      ],
      "evidence_event_ids": [
        "e15:n21",
        "e16:n22",
        "e19:n29",
        "e20:n30",
        "e21:n31",
        "e22:n32",
        "e1:n2",
        "e2:n3"
      ],
      "token_ids": [
        "tok45:pattern_repetition"
      ],
      "gesture_ids": [],
      "confidence": 0.5,
      "payload": {
        "related_dimensions": [
          "expression_sound_control",
          "finger_dexterity"
        ],
        "detection_heuristic": "phrase_shape",
        "repeated": "repeated_position_pattern",
        "shape": "dynamic_swell_across_phrase"
      },
      "caveats": [
        "heuristic_phrase_shape"
      ]
    },
    {
      "object_id": "balance_between_voices",
      "kind": "balance_between_voices",
      "label": "Balance between voices",
      "hand": null,
      "start_onset": "1/2",
      "end_onset": "154801/480",
      "measure_start": 1,
      "measure_end": 72,
      "measure_numbers": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "70",
        "71",
        "72"
      ],
      "evidence_event_ids": [
        "e1:n2",
        "e2:n3",
        "e3:n11",
        "e4:n12",
        "e5:n4",
        "e6:n5",
        "e7:n8",
        "e8:n9"
      ],
      "token_ids": [],
      "gesture_ids": [],
      "confidence": 0.52,
      "payload": {
        "related_dimensions": [
          "expression_sound_control",
          "layers_coordination"
        ],
        "detection_heuristic": "balance_poly",
        "polyphonic": true
      },
      "caveats": [
        "heuristic_balance"
      ]
    },
    {
      "object_id": "pedal_point_accompaniment",
      "kind": "pedal_point_accompaniment",
      "label": "Pedal-point accompaniment",
      "hand": "left",
      "start_onset": "1/2",
      "end_onset": "152401/480",
      "measure_start": 1,
      "measure_end": 71,
      "measure_numbers": [
        "1",
        "3",
        "9",
        "26",
        "29",
        "34",
        "35",
        "36",
        "37",
        "38",
        "51",
        "53",
        "54",
        "57",
        "58",
        "59",
        "67",
        "69",
        "70",
        "71"
      ],
      "evidence_event_ids": [
        "e1:n2",
        "e2:n3",
        "e3:n11",
        "e4:n12",
        "e17:n38",
        "e18:n39",
        "e87:n116",
        "e88:n117",
        "e582:n681",
        "e650:n753",
        "e792:n891",
        "e817:n917",
        "e843:n943",
        "e853:n970",
        "e863:n973",
        "e872:n976",
        "e873:n982",
        "e882:n985",
        "e883:n1003",
        "e1248:n1365",
        "e1273:n1410",
        "e1294:n1431",
        "e1361:n1511",
        "e1385:n1534",
        "e1400:n1552",
        "e1401:n1553",
        "e1526:n1701",
        "e1561:n1740",
        "e1571:n1753",
        "e1587:n1770"
      ],
      "token_ids": [],
      "gesture_ids": [],
      "confidence": 0.58,
      "payload": {
        "related_dimensions": [
          "hand_movement_position",
          "layers_coordination",
          "expression_sound_control"
        ],
        "detection_heuristic": "pedal_point",
        "pedal_pitch": 68,
        "occurrences": 22
      },
      "caveats": []
    },
    {
      "object_id": "two_voice_counterpoint",
      "kind": "two_voice_counterpoint",
      "label": "Two-voice counterpoint",
      "hand": null,
      "start_onset": "1/2",
      "end_onset": "154801/480",
      "measure_start": 1,
      "measure_end": 72,
      "measure_numbers": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "67",
        "68",
        "69",
        "70",
        "71",
        "72"
      ],
      "evidence_event_ids": [
        "e1:n2",
        "e2:n3",
        "e5:n4",
        "e6:n5",
        "e7:n8",
        "e8:n9",
        "e11:n17",
        "e12:n18",
        "e13:n19",
        "e14:n20",
        "e15:n21",
        "e16:n22",
        "e19:n29",
        "e20:n30",
        "e21:n31",
        "e22:n32",
        "e23:n33",
        "e25:n34",
        "e26:n36",
        "e27:n42",
        "e30:n44",
        "e31:n45",
        "e32:n46",
        "e33:n47",
        "e34:n48",
        "e35:n49",
        "e39:n55",
        "e40:n56",
        "e41:n57",
        "e42:n58",
        "e43:n59",
        "e44:n60",
        "e48:n61",
        "e49:n62",
        "e53:n70",
        "e54:n71",
        "e55:n72",
        "e56:n73",
        "e63:n81",
        "e64:n82",
        "e65:n83",
        "e66:n84",
        "e67:n85",
        "e68:n86",
        "e70:n87",
        "e71:n88",
        "e75:n96",
        "e76:n97",
        "e77:n98",
        "e78:n99",
        "e89:n108",
        "e90:n109",
        "e91:n110",
        "e92:n111",
        "e95:n122",
        "e102:n123",
        "e103:n124",
        "e106:n142",
        "e107:n143",
        "e111:n144",
        "e112:n145",
        "e113:n146",
        "e114:n147",
        "e115:n148",
        "e118:n149",
        "e119:n150",
        "e120:n151",
        "e125:n163",
        "e132:n164",
        "e133:n165",
        "e134:n166",
        "e136:n184",
        "e137:n185",
        "e141:n186",
        "e142:n187",
        "e143:n188",
        "e144:n189",
        "e149:n190",
        "e150:n191",
        "e151:n194",
        "e152:n195",
        "e154:n212",
        "e160:n213",
        "e161:n214",
        "e162:n215",
        "e164:n217",
        "e167:n234",
        "e168:n235",
        "e169:n236",
        "e173:n240",
        "e174:n241",
        "e175:n242",
        "e179:n243",
        "e180:n244",
        "e181:n245",
        "e185:n246",
        "e186:n247",
        "e187:n248",
        "e191:n249",
        "e192:n250",
        "e193:n251",
        "e197:n252",
        "e198:n253",
        "e199:n254",
        "e203:n279",
        "e204:n280",
        "e205:n281",
        "e209:n282",
        "e210:n283",
        "e211:n284",
        "e212:n285",
        "e216:n286",
        "e217:n287",
        "e218:n288",
        "e219:n289",
        "e223:n290",
        "e224:n291",
        "e225:n292",
        "e226:n293",
        "e230:n294",
        "e231:n295",
        "e232:n296",
        "e236:n297",
        "e237:n298",
        "e238:n299",
        "e245:n319",
        "e246:n320",
        "e247:n321",
        "e251:n325",
        "e252:n326",
        "e253:n327",
        "e257:n328",
        "e258:n329",
        "e259:n330",
        "e263:n331",
        "e264:n332",
        "e265:n333",
        "e269:n334",
        "e270:n335",
        "e271:n336",
        "e275:n337",
        "e276:n338",
        "e277:n339",
        "e281:n365",
        "e282:n366",
        "e283:n367",
        "e287:n368",
        "e288:n369",
        "e289:n370",
        "e293:n371",
        "e294:n372",
        "e295:n373",
        "e299:n374",
... (truncated)
```

</details>
