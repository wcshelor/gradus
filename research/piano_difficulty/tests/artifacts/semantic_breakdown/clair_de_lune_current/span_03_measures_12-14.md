<!-- Semantic breakdown span 03: flagged 13 -> expanded 12-14 -->
<!-- Span provenance: extracted from research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json (leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans)); flagged_provenance: leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans); manual testing passages 25-26, 27-28; span source: extracted_from_analysis_json; flagged (13,) -> expanded (12, 14) (context 1, merge=True) -->
<!-- Generated via local inspection delegate; analysis_json: research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json -->
# Local Semantic Inspection: Measures 12-14

## Passage Scope
- Report span: 12-14
- Flagged measures: 13
- Source score: /Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml

## Instruction Units
### 1. Octave-Doubled Melody
The right hand projects an octave-doubled melody on m.13, beat 1.5 as one structural unit: 5 doubled octaves ascending (span 21 semitones, mixed_octave_plus_other_tones).

- Hand / voice: right (right hand) — one structural octave-doubled line, not separate parallel notes
- Doubled octaves: 5 consecutive octave pairs (mixed_octave_plus_other_tones)
- Pitch range (sample): Db4-Db5 → F4-F5
- Direction/contour: ascending — intervals +2, +7, -2, -3
- Pitch span: 21 semitones
- Voicing: octave (12 semitones) doubling mixed with inner tones
- Evidence: object: octave_doubled_melody [evidence]; evidence_event_ids=['e136:n184', 'e137:n185', 'e138:n196']; confidence=0.66; components: doubling_type:right, octave_direction:right, octave_pair_sequence:right
- Placement: m.13, beat 1.5
- Caveats: mixed_octave_plus_other_tones
- Consistency: no warnings

### 2. Single-Hand Multi-Voice Texture
The right hand appears to carry multiple voices on m.12, beat 2.5 (gap 12 semitones): low C#4-D#4 (61-63) and high D#5-D#5 (75-75) show independent rhythmic behavior — octave_melody_plus_inner_chord_tones.

- Hand / voice: right (right hand) — single hand, multiple inferred roles
- Pitch bands separated by 12 semitones (roughly an octave or more): low C#4-D#4 (61-63), high D#5-D#5 (75-75)
- Evidence of independence: duration ratio 2.0, onset overlap 0.333; reasons: octave_melody_plus_inner_chord_tones
- Caveat: voice assignment is inferred from texture (not notated voice separation)
- Evidence: object: single_hand_multi_voice_texture [evidence]; evidence_event_ids=['e133:n165', 'e134:n166', 'e136:n184']; confidence=0.68; components: high_voice_role:left, rhythmic_independence_multi:left, voice_band_gap:left
- Placement: m.12, beat 2.5
- Caveats: voice_assignment_inferred
- Consistency: 4 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [high_voice_role]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence_multi]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [voice_band_gap]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [low_voice_role]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

### 3. Single-Hand Multi-Voice Texture
The left hand appears to carry multiple voices on m.11, beat 2.5 (gap 12 semitones): low F#2-C#3 (42-49) and high C#4-F4 (61-65) show independent rhythmic behavior — sustained_or_repeated_low_plus_moving_upper, pitch_bands_separated_octave_independent_rhythm, octave_melody_plus_inner_chord_tones.

- Hand / voice: left (left hand) — single hand, multiple inferred roles
- Pitch bands separated by 12 semitones (roughly an octave or more): low F#2-C#3 (42-49), high C#4-F4 (61-65)
- Evidence of independence: duration ratio 1.71, onset overlap 0.2; reasons: sustained_or_repeated_low_plus_moving_upper, pitch_bands_separated_octave_independent_rhythm, octave_melody_plus_inner_chord_tones
- Caveat: voice assignment is inferred from texture (not notated voice separation)
- Evidence: object: single_hand_multi_voice_texture [evidence]; evidence_event_ids=['e116:n156', 'e117:n157', 'e121:n158']; confidence=0.68; components: high_voice_role:left, rhythmic_independence_multi:left, voice_band_gap:left
- Placement: m.11, beat 2.5
- Caveats: voice_assignment_inferred
- Consistency: no warnings

## Supporting Local Objects
_Showing 6 of 6 object groups (compact). Full details in <details>._

| # | Object | Count | Best conf | Measures | Why not promoted |
|---|--------|-------|-----------|----------|------------------|
| G1 | leap_to_chord (Leap to chord) | 9 | 0.85 | 11-15 | relevant locally but not top-ranked; kept as supporting |
| G2 | melody_with_accompaniment (Melody with accompaniment) | 7 | 0.78 | 11-14 | relevant locally but not top-ranked; kept as supporting |
| G3 | chord_landing (Chord landing) | 17 | 0.78 | 11-15 | below promotion confidence threshold |
| G4 | repeated_position_pattern (Repeated position pattern) | 10 | 0.72 | 12-14 | relevant locally but not top-ranked; kept as supporting |
| G5 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 7 | 0.66 | 11-14 | relevant locally but not top-ranked; kept as supporting |
| G6 | octave_doubled_melody (Octave-doubled melody) | 1 | 0.66 | 11 | relevant locally but not top-ranked; kept as supporting |

<details>
<summary>All supporting objects (ungrouped)</summary>

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 11 | local overlap m.11, confidence 0.66, 13 events | relevant locally but not top-ranked; kept as supporting |
| S2 | melody_with_accompaniment (Melody with accompaniment) | 11 | local overlap m.11, confidence 0.78, 13 events | relevant locally but not top-ranked; kept as supporting |
| S3 | octave_doubled_melody (Octave-doubled melody) | 11 | local overlap m.11, confidence 0.66, 11 events | relevant locally but not top-ranked; kept as supporting |
| S4 | chord_landing (Chord landing) | 11-12 | local overlap m.11-12, confidence 0.75, 4 events | relevant locally but not top-ranked; kept as supporting |
| S5 | chord_landing (Chord landing) | 11-12 | local overlap m.11-12, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S6 | leap_to_chord (Leap to chord) | 11-12 | local overlap m.11-12, confidence 0.82, 4 events | relevant locally but not top-ranked; kept as supporting |
| S7 | leap_to_chord (Leap to chord) | 11-12 | local overlap m.11-12, confidence 0.85, 8 events | relevant locally but not top-ranked; kept as supporting |
| S8 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 11-12 | local overlap m.11-12, confidence 0.66, 10 events | relevant locally but not top-ranked; kept as supporting |
| S9 | melody_with_accompaniment (Melody with accompaniment) | 11-12 | local overlap m.11-12, confidence 0.78, 10 events | relevant locally but not top-ranked; kept as supporting |
| S10 | chord_landing (Chord landing) | 12 | local overlap m.12, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S11 | leap_to_chord (Leap to chord) | 12 | local overlap m.12, confidence 0.85, 6 events | relevant locally but not top-ranked; kept as supporting |
| S12 | chord_landing (Chord landing) | 12 | local overlap m.12, confidence 0.58, 4 events | below promotion confidence threshold |
| S13 | chord_landing (Chord landing) | 12 | local overlap m.12, confidence 0.58, 3 events | below promotion confidence threshold |
| S14 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 12 | local overlap m.12, confidence 0.66, 10 events | relevant locally but not top-ranked; kept as supporting |
| S15 | melody_with_accompaniment (Melody with accompaniment) | 12 | local overlap m.12, confidence 0.78, 10 events | relevant locally but not top-ranked; kept as supporting |
| S16 | repeated_position_pattern (Repeated position pattern) | 12 | local overlap m.12, confidence 0.63, 5 events | relevant locally but not top-ranked; kept as supporting |
| S17 | repeated_position_pattern (Repeated position pattern) | 12 | local overlap m.12, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S18 | repeated_position_pattern (Repeated position pattern) | 12-13 | local overlap m.12-13, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S19 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S20 | leap_to_chord (Leap to chord) | 13 | local overlap m.13, confidence 0.85, 6 events | relevant locally but not top-ranked; kept as supporting |
| S21 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.58, 3 events | below promotion confidence threshold |
| S22 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 13 | local overlap m.13, confidence 0.66, 12 events | relevant locally but not top-ranked; kept as supporting |
| S23 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 13 | local overlap m.13, confidence 0.66, 13 events | relevant locally but not top-ranked; kept as supporting |
| S24 | melody_with_accompaniment (Melody with accompaniment) | 13 | local overlap m.13, confidence 0.78, 12 events | relevant locally but not top-ranked; kept as supporting |
| S25 | melody_with_accompaniment (Melody with accompaniment) | 13 | local overlap m.13, confidence 0.78, 13 events | relevant locally but not top-ranked; kept as supporting |
| S26 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.58, 2 events | below promotion confidence threshold |
| S27 | chord_landing (Chord landing) | 13-14 | local overlap m.13-14, confidence 0.78, 7 events | relevant locally but not top-ranked; kept as supporting |
| S28 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.58, 3 events | below promotion confidence threshold |
| S29 | leap_to_chord (Leap to chord) | 13-14 | local overlap m.13-14, confidence 0.85, 7 events | relevant locally but not top-ranked; kept as supporting |
| S30 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.58, 2 events | below promotion confidence threshold |
| S31 | repeated_position_pattern (Repeated position pattern) | 13-14 | local overlap m.13-14, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S32 | repeated_position_pattern (Repeated position pattern) | 13-14 | local overlap m.13-14, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S33 | chord_landing (Chord landing) | 13 | local overlap m.13, confidence 0.58, 2 events | below promotion confidence threshold |
| S34 | repeated_position_pattern (Repeated position pattern) | 13-14 | local overlap m.13-14, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S35 | repeated_position_pattern (Repeated position pattern) | 13-14 | local overlap m.13-14, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S36 | chord_landing (Chord landing) | 14 | local overlap m.14, confidence 0.78, 4 events | relevant locally but not top-ranked; kept as supporting |
| S37 | leap_to_chord (Leap to chord) | 14 | local overlap m.14, confidence 0.85, 4 events | relevant locally but not top-ranked; kept as supporting |
| S38 | chord_landing (Chord landing) | 14 | local overlap m.14, confidence 0.58, 3 events | below promotion confidence threshold |
| S39 | chord_landing (Chord landing) | 14 | local overlap m.14, confidence 0.58, 3 events | below promotion confidence threshold |
| S40 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 14 | local overlap m.14, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S41 | melody_with_accompaniment (Melody with accompaniment) | 14 | local overlap m.14, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S42 | repeated_position_pattern (Repeated position pattern) | 14 | local overlap m.14, confidence 0.63, 5 events | relevant locally but not top-ranked; kept as supporting |
| S43 | repeated_position_pattern (Repeated position pattern) | 14 | local overlap m.14, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S44 | repeated_position_pattern (Repeated position pattern) | 14 | local overlap m.14, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S45 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 14 | local overlap m.14, confidence 0.66, 7 events | relevant locally but not top-ranked; kept as supporting |
| S46 | melody_with_accompaniment (Melody with accompaniment) | 14 | local overlap m.14, confidence 0.78, 7 events | relevant locally but not top-ranked; kept as supporting |
| S47 | chord_landing (Chord landing) | 14-15 | local overlap m.14-15, confidence 0.75, 3 events | relevant locally but not top-ranked; kept as supporting |
| S48 | chord_landing (Chord landing) | 14-15 | local overlap m.14-15, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S49 | leap_to_chord (Leap to chord) | 14-15 | local overlap m.14-15, confidence 0.82, 3 events | relevant locally but not top-ranked; kept as supporting |
| S50 | leap_to_chord (Leap to chord) | 14-15 | local overlap m.14-15, confidence 0.85, 6 events | relevant locally but not top-ranked; kept as supporting |
| S51 | leap_to_chord (Leap to chord) | 14-15 | local overlap m.14-15, confidence 0.62, 4 events | relevant locally but not top-ranked; kept as supporting |

</details>

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
| left_hand_stride_like_motion | 8-72 (65 measures) | span 65 measures exceeds local span 3; piece-level or long gesture |

## Evidence Summary
- Token kind counts: chord_shape: 12, density_spike: 24, hand_movement: 24, harmonic_simultaneity: 18, leap: 12, melodic_interval: 42, onset_alignment: 6, pattern_break: 1, pattern_repetition: 10, register_shift: 6
- Gesture kind counts: accompaniment_pattern: 10, bass_to_chord: 16, block_chord_landing: 28, cadence_like_arrival: 30, melody_with_accompaniment: 7
- Component type counts: accompaniment_layer: 10, balance_relation: 14, chord_note_count: 22, doubling_type: 2, high_voice_role: 2, landing_beat: 21, landing_onset: 21, launch_note: 22, leap_interval: 26, leap_interval_semitones: 26, low_voice_role: 2, melody_layer: 16, octave_direction: 2, octave_pair_sequence: 2, octave_span: 2, onset_alignment: 14, other_hand_activity: 23, register_separation: 14, rhythmic_independence: 14, rhythmic_independence_multi: 2, target_chord: 22, target_span: 22, voice_band_gap: 2
- Musical objects in span: 65
- Components in span: 303
- Top components: leap_interval ×26 (leap_interval_semitones=-7); leap_interval_semitones ×26 (leap_interval_semitones=-7); other_hand_activity ×23 (note_count=8)
- Consistency warnings: 4 (see Instruction Units and JSON diagnostics)

<details>
<summary>Raw object/component evidence</summary>

_Raw JSON truncated for readability (683003 chars total, showing first 12000). Full payload written to sibling .json when generated via script._

```json
{
  "span": "12-14",
  "flagged_measures": [
    "13"
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
