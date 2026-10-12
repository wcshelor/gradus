<!-- Semantic breakdown span 04: flagged 25,26 -> expanded 25-26 -->
<!-- Span provenance: extracted from research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json (leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans)); flagged_provenance: leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans); manual testing passages 25-26, 27-28; span source: manual_testing_round; flagged (25, 26) -> expanded (25, 26) (context 1, merge=True) -->
<!-- Generated via local inspection delegate; analysis_json: research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json -->
# Local Semantic Inspection: Measures 25-26

## Passage Scope
- Report span: 25-26
- Flagged measures: 25, 26
- Source score: /Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml

## Instruction Units
### 1. LH Chord Landing
The left hand sounds Ab3-Ab3-Eb4-Gb4-C5 (5 notes, span 16 semitones) on m.26, beat 4.

- Hand / voice: left
- Chord tones: Ab3-Ab3-Eb4-Gb4-C5 (5 notes), span 16 semitones
- Placement: m.26, beat 4 — quarter (3/2 quarters (1.5 q))
- Evidence: object: chord_landing [ges1112:bass_to_chord]; evidence_event_ids=['e558:n660', 'e563:n669', 'e559:n661']; confidence=0.78; components: launch_note:left, leap_interval:left, leap_interval_semitones:left
- Caveats: none — score-derived evidence
- Consistency: no warnings

### 2. Melody with accompaniment
Both hands form a melody-with-accompaniment texture at m.25-26: one layer carries the melodic line while another supplies aligned support. Melody Db5-Ab6 over accompaniment E4-Ab6.

- Hand / voice: both
- Melody tones: Db5-Ab6 (12 notes)
- Accompaniment tones: E4-Ab6 (13 notes)
- Register separation: -19 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_with_accompaniment [ges1109:melody_with_accompaniment]; evidence_event_ids=['e539:n627', 'e540:n628', 'e541:n629']; confidence=0.78; components: balance_relation:both, melody_layer:right, onset_alignment:both
- Caveats: balance_inferred_from_texture
- Consistency: 4 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [balance_relation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [onset_alignment]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [register_separation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

### 3. Melody Voicing over Accompaniment
The texture presents a melody voicing over accompaniment at m.25-26: the upper line projects while lower tones provide harmonic support. Melody Db5-Ab6 over accompaniment E4-Ab6.

- Hand / voice: both
- Melody tones: Db5-Ab6 (12 notes)
- Accompaniment tones: E4-Ab6 (13 notes)
- Register separation: -19 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_voicing_over_accompaniment [ges1109:melody_with_accompaniment]; evidence_event_ids=['e539:n627', 'e540:n628', 'e541:n629']; confidence=0.66; components: balance_relation:both, melody_layer:right, onset_alignment:both
- Caveats: balance_inferred_from_texture
- Consistency: 4 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [balance_relation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [onset_alignment]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [register_separation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

## Supporting Local Objects
_Showing 5 of 5 object groups (compact). Full details in <details>._

| # | Object | Count | Best conf | Measures | Why not promoted |
|---|--------|-------|-----------|----------|------------------|
| G1 | leap_to_chord (Leap to chord) | 3 | 0.85 | 24-26 | relevant locally but not top-ranked; kept as supporting |
| G2 | melody_with_accompaniment (Melody with accompaniment) | 6 | 0.78 | 24-27 | relevant locally but not top-ranked; kept as supporting |
| G3 | chord_landing (Chord landing) | 8 | 0.78 | 24-26 | below promotion confidence threshold |
| G4 | repeated_position_pattern (Repeated position pattern) | 4 | 0.72 | 25-26 | relevant locally but not top-ranked; kept as supporting |
| G5 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 6 | 0.66 | 24-27 | relevant locally but not top-ranked; kept as supporting |

<details>
<summary>All supporting objects (ungrouped)</summary>

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 24 | local overlap m.24, confidence 0.66, 15 events | relevant locally but not top-ranked; kept as supporting |
| S2 | melody_with_accompaniment (Melody with accompaniment) | 24 | local overlap m.24, confidence 0.78, 15 events | relevant locally but not top-ranked; kept as supporting |
| S3 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 24 | local overlap m.24, confidence 0.66, 15 events | relevant locally but not top-ranked; kept as supporting |
| S4 | melody_with_accompaniment (Melody with accompaniment) | 24 | local overlap m.24, confidence 0.78, 15 events | relevant locally but not top-ranked; kept as supporting |
| S5 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 24 | local overlap m.24, confidence 0.66, 15 events | relevant locally but not top-ranked; kept as supporting |
| S6 | melody_with_accompaniment (Melody with accompaniment) | 24 | local overlap m.24, confidence 0.78, 15 events | relevant locally but not top-ranked; kept as supporting |
| S7 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 24-25 | local overlap m.24-25, confidence 0.66, 23 events | relevant locally but not top-ranked; kept as supporting |
| S8 | melody_with_accompaniment (Melody with accompaniment) | 24-25 | local overlap m.24-25, confidence 0.78, 23 events | relevant locally but not top-ranked; kept as supporting |
| S9 | chord_landing (Chord landing) | 24-25 | local overlap m.24-25, confidence 0.78, 14 events | relevant locally but not top-ranked; kept as supporting |
| S10 | leap_to_chord (Leap to chord) | 24-25 | local overlap m.24-25, confidence 0.85, 14 events | relevant locally but not top-ranked; kept as supporting |
| S11 | chord_landing (Chord landing) | 25 | local overlap m.25, confidence 0.58, 11 events | below promotion confidence threshold |
| S12 | chord_landing (Chord landing) | 25 | local overlap m.25, confidence 0.58, 3 events | below promotion confidence threshold |
| S13 | repeated_position_pattern (Repeated position pattern) | 25-26 | local overlap m.25-26, confidence 0.72, 37 events | relevant locally but not top-ranked; kept as supporting |
| S14 | repeated_position_pattern (Repeated position pattern) | 25-26 | local overlap m.25-26, confidence 0.72, 9 events | relevant locally but not top-ranked; kept as supporting |
| S15 | chord_landing (Chord landing) | 25 | local overlap m.25, confidence 0.58, 13 events | below promotion confidence threshold |
| S16 | chord_landing (Chord landing) | 25 | local overlap m.25, confidence 0.58, 3 events | below promotion confidence threshold |
| S17 | chord_landing (Chord landing) | 26 | local overlap m.26, confidence 0.58, 3 events | below promotion confidence threshold |
| S18 | leap_to_chord (Leap to chord) | 26 | local overlap m.26, confidence 0.85, 18 events | relevant locally but not top-ranked; kept as supporting |
| S19 | leap_to_chord (Leap to chord) | 26 | local overlap m.26, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S20 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 26-27 | local overlap m.26-27, confidence 0.66, 21 events | relevant locally but not top-ranked; kept as supporting |
| S21 | melody_with_accompaniment (Melody with accompaniment) | 26-27 | local overlap m.26-27, confidence 0.78, 21 events | relevant locally but not top-ranked; kept as supporting |
| S22 | repeated_position_pattern (Repeated position pattern) | 26 | local overlap m.26, confidence 0.63, 19 events | relevant locally but not top-ranked; kept as supporting |
| S23 | chord_landing (Chord landing) | 26 | local overlap m.26, confidence 0.58, 5 events | below promotion confidence threshold |
| S24 | chord_landing (Chord landing) | 26 | local overlap m.26, confidence 0.58, 3 events | below promotion confidence threshold |
| S25 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 26-27 | local overlap m.26-27, confidence 0.66, 11 events | relevant locally but not top-ranked; kept as supporting |
| S26 | melody_with_accompaniment (Melody with accompaniment) | 26-27 | local overlap m.26-27, confidence 0.78, 11 events | relevant locally but not top-ranked; kept as supporting |
| S27 | repeated_position_pattern (Repeated position pattern) | 26 | local overlap m.26, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |

</details>

## Broad Context / Low Local Specificity
| Object | Span | Reason for exclusion |
|--------|------|----------------------|
| dynamic_swell_across_phrase | 1-72 (72 measures) | span 72 measures exceeds local span 2; piece-level or long gesture |
| phrase_shaping_over_repeated_pattern | 1-72 (72 measures) | span 72 measures exceeds local span 2; piece-level or long gesture |
| balance_between_voices | 1-72 (72 measures) | span 72 measures exceeds local span 2; piece-level or long gesture |
| pedal_point_accompaniment | 1,3,9,26,29,34-38,51,53-54,57-59,67,69-71 | span 71 measures exceeds local span 2; piece-level or long gesture |
| two_voice_counterpoint | 1-72 (72 measures) | span 72 measures exceeds local span 2; piece-level or long gesture |
| pedal_point_accompaniment | 1,9,13,21,23-24,34-38,41,55-56,59 | span 59 measures exceeds local span 2; piece-level or long gesture |
| repeated_chord_accompaniment | 1,9,35-36,55-56,59 | span 59 measures exceeds local span 2; piece-level or long gesture |
| repeated_chord_accompaniment | 1-2,9,29-30,57,59 | span 59 measures exceeds local span 2; piece-level or long gesture |
| repeated_chord_accompaniment | 2-3,58 | span 57 measures exceeds local span 2; piece-level or long gesture |
| chordal_homophonic_texture | 5-6,8,11,15-26,56,61,63-65,67,72 | span 68 measures exceeds local span 2; piece-level or long gesture |
| left_hand_stride_like_motion | 8-72 (65 measures) | span 65 measures exceeds local span 2; piece-level or long gesture |

## Evidence Summary
- Token kind counts: chord_shape: 8, density_spike: 30, hand_movement: 16, harmonic_simultaneity: 12, leap: 6, melodic_interval: 27, onset_alignment: 4, pattern_break: 2, pattern_repetition: 4, register_shift: 1
- Gesture kind counts: accompaniment_pattern: 4, bass_to_chord: 4, block_chord_landing: 20, cadence_like_arrival: 20, melody_with_accompaniment: 7
- Component type counts: accompaniment_layer: 8, balance_relation: 14, chord_note_count: 12, landing_beat: 12, landing_onset: 12, launch_note: 10, leap_interval: 12, leap_interval_semitones: 12, melody_layer: 10, onset_alignment: 14, other_hand_activity: 12, register_separation: 14, rhythmic_independence: 14, target_chord: 12, target_span: 12
- Musical objects in span: 41
- Components in span: 180
- Top components: balance_relation ×14 (register_gap_semitones=4); onset_alignment ×14 (overlapping_onsets=1); register_separation ×14 (register_gap_semitones=4)
- Consistency warnings: 8 (see Instruction Units and JSON diagnostics)

<details>
<summary>Raw object/component evidence</summary>

_Raw JSON truncated for readability (511329 chars total, showing first 12000). Full payload written to sibling .json when generated via script._

```json
{
  "span": "25-26",
  "flagged_measures": [
    "25",
    "26"
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
... (truncated)
```

</details>
