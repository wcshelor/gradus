<!-- Semantic breakdown span 07: flagged 59,61 -> expanded 58-62 -->
<!-- Span provenance: extracted from research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json (leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans)); flagged_provenance: leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans); manual testing passages 25-26, 27-28; span source: extracted_from_analysis_json; flagged (59, 61) -> expanded (58, 62) (context 1, merge=True) -->
<!-- Generated via local inspection delegate; analysis_json: research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json -->
# Local Semantic Inspection: Measures 58-62

## Passage Scope
- Report span: 58-62
- Flagged measures: 59, 61
- Source score: /Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml

## Instruction Units
### 1. Octave-Doubled Melody
The right hand projects an octave-doubled melody on m.61, beat 1.5 as one structural unit: 4 doubled octaves ascending (span 19 semitones, mixed_octave_plus_other_tones).

- Hand / voice: right (right hand) — one structural octave-doubled line, not separate parallel notes
- Doubled octaves: 4 consecutive octave pairs (mixed_octave_plus_other_tones)
- Pitch range (sample): Db4-Db5 → F4-F5
- Direction/contour: ascending — intervals +2, +5, -3
- Pitch span: 19 semitones
- Voicing: octave (12 semitones) doubling mixed with inner tones
- Evidence: object: octave_doubled_melody [evidence]; evidence_event_ids=['e1420:n1580', 'e1421:n1581', 'e1422:n1590']; confidence=0.66; components: doubling_type:right, octave_direction:right, octave_pair_sequence:right
- Placement: m.61, beat 1.5
- Caveats: mixed_octave_plus_other_tones
- Consistency: no warnings

### 2. LH Leap To Chord
The left hand moves from Gb2 on m.60, beat 1 to an Db3-Gb3-Bb3-Db4 chord on m.60, beat 1.5.

- Hand / voice: left (left hand)
- Launch: Gb2 on m.60, beat 1 — half (2 quarters)
- Landing: Db3-Gb3-Bb3-Db4 (4 notes, span 12 semitones) on m.60, beat 1.5
- Interval: 16 semitones up — octave + major third
- Timing: 1/2 quarters (0.5 q) from m.60, beat 1 to m.60, beat 1.5
- Evidence: object: leap_to_chord [ges2657:bass_to_chord]; evidence_event_ids=['e1408:n1577', 'e1409:n1578', 'e1413:n1569']; confidence=0.85; components: leap_interval:left, leap_interval_semitones:left, other_hand_activity:left
- Caveats: none — score-derived evidence
- Consistency: 4 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **duration_representation_mismatch**: landing event e1413:n1569 duration_type 'quarter' expects 1 quarters but logical duration is 4 quarters (tie_merged=True) — written and logical durations disagree
  - **duration_representation_mismatch**: landing event e1414:n1570 duration_type 'quarter' expects 1 quarters but logical duration is 4 quarters (tie_merged=True) — written and logical durations disagree
  - **duration_representation_mismatch**: landing event e1415:n1571 duration_type 'quarter' expects 1 quarters but logical duration is 4 quarters (tie_merged=True) — written and logical durations disagree
  - **duration_representation_mismatch**: landing event e1416:n1572 duration_type 'quarter' expects 1 quarters but logical duration is 4 quarters (tie_merged=True) — written and logical durations disagree

</details>

### 3. Melody with accompaniment
Both hands form a melody-with-accompaniment texture at m.58: one layer carries the melodic line while another supplies aligned support. Melody Bb4-Eb5 over accompaniment Bb3.

- Hand / voice: both
- Melody tones: Bb4-Eb5 (7 notes)
- Accompaniment tones: Bb3 (1 notes)
- Register separation: 10 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_with_accompaniment [ges2603:melody_with_accompaniment]; evidence_event_ids=['e1382:n1523', 'e1383:n1524', 'e1384:n1533']; confidence=0.78; components: accompaniment_pattern_reference:left, balance_relation:both, onset_alignment:both
- Caveats: balance_inferred_from_texture
- Consistency: 6 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [accompaniment_pattern_reference]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [balance_relation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [onset_alignment]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [register_separation]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [rhythmic_independence]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only
  - **component_instance_mismatch** [accompaniment_layer]: component has no shared evidence/token/gesture with promoted object; attached by onset overlap only

</details>

## Supporting Local Objects
_Showing 7 of 7 object groups (compact). Full details in <details>._

| # | Object | Count | Best conf | Measures | Why not promoted |
|---|--------|-------|-----------|----------|------------------|
| G1 | leap_to_chord (Leap to chord) | 9 | 0.85 | 58-63 | relevant locally but not top-ranked; kept as supporting |
| G2 | melody_with_accompaniment (Melody with accompaniment) | 10 | 0.78 | 57-63 | relevant locally but not top-ranked; kept as supporting |
| G3 | chord_landing (Chord landing) | 18 | 0.78 | 58-62 | below promotion confidence threshold |
| G4 | repeated_position_pattern (Repeated position pattern) | 45 | 0.72 | 57-62 | relevant locally but not top-ranked; kept as supporting |
| G5 | broken_chord_accompaniment (Broken-chord accompaniment) | 1 | 0.70 | 58 | relevant locally but not top-ranked; kept as supporting |
| G6 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 11 | 0.66 | 57-63 | relevant locally but not top-ranked; kept as supporting |
| G7 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 1 | 0.66 | 58 | relevant locally but not top-ranked; kept as supporting |

<details>
<summary>All supporting objects (ungrouped)</summary>

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57 | local overlap m.57, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S2 | melody_with_accompaniment (Melody with accompaniment) | 57 | local overlap m.57, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S3 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.62, 7 events | relevant locally but not top-ranked; kept as supporting |
| S4 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S5 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S6 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S7 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57-58 | local overlap m.57-58, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S8 | melody_with_accompaniment (Melody with accompaniment) | 57-58 | local overlap m.57-58, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S9 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S10 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |
| S11 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S12 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S13 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S14 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S15 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 58 | local overlap m.58, confidence 0.66, 4 events | relevant locally but not top-ranked; kept as supporting |
| S16 | broken_chord_accompaniment (Broken-chord accompaniment) | 58 | local overlap m.58, confidence 0.70, 4 events | relevant locally but not top-ranked; kept as supporting |
| S17 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 58 | local overlap m.58, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S18 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S19 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S20 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S21 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 8 events | relevant locally but not top-ranked; kept as supporting |
| S22 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S23 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S24 | chord_landing (Chord landing) | 58 | local overlap m.58, confidence 0.78, 4 events | relevant locally but not top-ranked; kept as supporting |
| S25 | leap_to_chord (Leap to chord) | 58 | local overlap m.58, confidence 0.85, 4 events | relevant locally but not top-ranked; kept as supporting |
| S26 | chord_landing (Chord landing) | 58-59 | local overlap m.58-59, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S27 | leap_to_chord (Leap to chord) | 58-59 | local overlap m.58-59, confidence 0.85, 8 events | relevant locally but not top-ranked; kept as supporting |
| S28 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 58-59 | local overlap m.58-59, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S29 | melody_with_accompaniment (Melody with accompaniment) | 58-59 | local overlap m.58-59, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S30 | repeated_position_pattern (Repeated position pattern) | 58-59 | local overlap m.58-59, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S31 | repeated_position_pattern (Repeated position pattern) | 58-59 | local overlap m.58-59, confidence 0.63, 10 events | relevant locally but not top-ranked; kept as supporting |
| S32 | repeated_position_pattern (Repeated position pattern) | 58-59 | local overlap m.58-59, confidence 0.62, 7 events | relevant locally but not top-ranked; kept as supporting |
| S33 | chord_landing (Chord landing) | 59 | local overlap m.59, confidence 0.58, 4 events | below promotion confidence threshold |
| S34 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 59 | local overlap m.59, confidence 0.66, 11 events | relevant locally but not top-ranked; kept as supporting |
| S35 | melody_with_accompaniment (Melody with accompaniment) | 59 | local overlap m.59, confidence 0.78, 11 events | relevant locally but not top-ranked; kept as supporting |
| S36 | repeated_position_pattern (Repeated position pattern) | 59 | local overlap m.59, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S37 | repeated_position_pattern (Repeated position pattern) | 59-60 | local overlap m.59-60, confidence 0.63, 9 events | relevant locally but not top-ranked; kept as supporting |
| S38 | chord_landing (Chord landing) | 59-60 | local overlap m.59-60, confidence 0.75, 4 events | relevant locally but not top-ranked; kept as supporting |
| S39 | chord_landing (Chord landing) | 59-60 | local overlap m.59-60, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S40 | leap_to_chord (Leap to chord) | 59-60 | local overlap m.59-60, confidence 0.82, 4 events | relevant locally but not top-ranked; kept as supporting |
| S41 | leap_to_chord (Leap to chord) | 59-60 | local overlap m.59-60, confidence 0.85, 8 events | relevant locally but not top-ranked; kept as supporting |
| S42 | repeated_position_pattern (Repeated position pattern) | 59-60 | local overlap m.59-60, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S43 | repeated_position_pattern (Repeated position pattern) | 59-60 | local overlap m.59-60, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S44 | leap_to_chord (Leap to chord) | 59-60 | local overlap m.59-60, confidence 0.62, 5 events | relevant locally but not top-ranked; kept as supporting |
| S45 | repeated_position_pattern (Repeated position pattern) | 59-60 | local overlap m.59-60, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S46 | repeated_position_pattern (Repeated position pattern) | 59-60 | local overlap m.59-60, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S47 | chord_landing (Chord landing) | 60 | local overlap m.60, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S48 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.62, 7 events | relevant locally but not top-ranked; kept as supporting |
| S49 | chord_landing (Chord landing) | 60 | local overlap m.60, confidence 0.58, 4 events | below promotion confidence threshold |
| S50 | chord_landing (Chord landing) | 60 | local overlap m.60, confidence 0.58, 3 events | below promotion confidence threshold |
| S51 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 60 | local overlap m.60, confidence 0.66, 12 events | relevant locally but not top-ranked; kept as supporting |
| S52 | melody_with_accompaniment (Melody with accompaniment) | 60 | local overlap m.60, confidence 0.78, 12 events | relevant locally but not top-ranked; kept as supporting |
| S53 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.62, 7 events | relevant locally but not top-ranked; kept as supporting |
| S54 | repeated_position_pattern (Repeated position pattern) | 60 | local overlap m.60, confidence 0.63, 5 events | relevant locally but not top-ranked; kept as supporting |
| S55 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S56 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.62, 5 events | relevant locally but not top-ranked; kept as supporting |
| S57 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S58 | repeated_position_pattern (Repeated position pattern) | 60-61 | local overlap m.60-61, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S59 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S60 | leap_to_chord (Leap to chord) | 61 | local overlap m.61, confidence 0.85, 6 events | relevant locally but not top-ranked; kept as supporting |
| S61 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.58, 3 events | below promotion confidence threshold |
| S62 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 61 | local overlap m.61, confidence 0.66, 13 events | relevant locally but not top-ranked; kept as supporting |
| S63 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 61 | local overlap m.61, confidence 0.66, 14 events | relevant locally but not top-ranked; kept as supporting |
| S64 | melody_with_accompaniment (Melody with accompaniment) | 61 | local overlap m.61, confidence 0.78, 13 events | relevant locally but not top-ranked; kept as supporting |
| S65 | melody_with_accompaniment (Melody with accompaniment) | 61 | local overlap m.61, confidence 0.78, 14 events | relevant locally but not top-ranked; kept as supporting |
| S66 | repeated_position_pattern (Repeated position pattern) | 61 | local overlap m.61, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |
| S67 | repeated_position_pattern (Repeated position pattern) | 61 | local overlap m.61, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S68 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.58, 2 events | below promotion confidence threshold |
| S69 | repeated_position_pattern (Repeated position pattern) | 61 | local overlap m.61, confidence 0.72, 8 events | relevant locally but not top-ranked; kept as supporting |
| S70 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.58, 3 events | below promotion confidence threshold |
| S71 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.58, 3 events | below promotion confidence threshold |
| S72 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.72, 9 events | relevant locally but not top-ranked; kept as supporting |
| S73 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.63, 10 events | relevant locally but not top-ranked; kept as supporting |
| S74 | chord_landing (Chord landing) | 61-62 | local overlap m.61-62, confidence 0.78, 6 events | relevant locally but not top-ranked; kept as supporting |
| S75 | chord_landing (Chord landing) | 61 | local overlap m.61, confidence 0.58, 3 events | below promotion confidence threshold |
| S76 | leap_to_chord (Leap to chord) | 61-62 | local overlap m.61-62, confidence 0.85, 6 events | relevant locally but not top-ranked; kept as supporting |
| S77 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 61-62 | local overlap m.61-62, confidence 0.66, 10 events | relevant locally but not top-ranked; kept as supporting |
| S78 | melody_with_accompaniment (Melody with accompaniment) | 61-62 | local overlap m.61-62, confidence 0.78, 10 events | relevant locally but not top-ranked; kept as supporting |
| S79 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S80 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S81 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.63, 7 events | relevant locally but not top-ranked; kept as supporting |
| S82 | repeated_position_pattern (Repeated position pattern) | 61-62 | local overlap m.61-62, confidence 0.63, 8 events | relevant locally but not top-ranked; kept as supporting |
| S83 | chord_landing (Chord landing) | 62 | local overlap m.62, confidence 0.78, 4 events | relevant locally but not top-ranked; kept as supporting |
| S84 | leap_to_chord (Leap to chord) | 62 | local overlap m.62, confidence 0.85, 4 events | relevant locally but not top-ranked; kept as supporting |
| S85 | repeated_position_pattern (Repeated position pattern) | 62 | local overlap m.62, confidence 0.62, 5 events | relevant locally but not top-ranked; kept as supporting |
| S86 | chord_landing (Chord landing) | 62 | local overlap m.62, confidence 0.58, 3 events | below promotion confidence threshold |
| S87 | chord_landing (Chord landing) | 62 | local overlap m.62, confidence 0.58, 3 events | below promotion confidence threshold |
| S88 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 62 | local overlap m.62, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S89 | melody_with_accompaniment (Melody with accompaniment) | 62 | local overlap m.62, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S90 | repeated_position_pattern (Repeated position pattern) | 62 | local overlap m.62, confidence 0.63, 5 events | relevant locally but not top-ranked; kept as supporting |
| S91 | repeated_position_pattern (Repeated position pattern) | 62 | local overlap m.62, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S92 | repeated_position_pattern (Repeated position pattern) | 62 | local overlap m.62, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S93 | leap_to_chord (Leap to chord) | 62-63 | local overlap m.62-63, confidence 0.62, 6 events | relevant locally but not top-ranked; kept as supporting |
| S94 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 62-63 | local overlap m.62-63, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S95 | melody_with_accompaniment (Melody with accompaniment) | 62-63 | local overlap m.62-63, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |

</details>

## Broad Context / Low Local Specificity
| Object | Span | Reason for exclusion |
|--------|------|----------------------|
| dynamic_swell_across_phrase | 1-72 (72 measures) | span 72 measures exceeds local span 5; piece-level or long gesture |
| phrase_shaping_over_repeated_pattern | 1-72 (72 measures) | span 72 measures exceeds local span 5; piece-level or long gesture |
| balance_between_voices | 1-72 (72 measures) | span 72 measures exceeds local span 5; piece-level or long gesture |
| pedal_point_accompaniment | 1,3,9,26,29,34-38,51,53-54,57-59,67,69-71 | span 71 measures exceeds local span 5; piece-level or long gesture |
| two_voice_counterpoint | 1-72 (72 measures) | span 72 measures exceeds local span 5; piece-level or long gesture |
| pedal_point_accompaniment | 1,9,13,21,23-24,34-38,41,55-56,59 | span 59 measures exceeds local span 5; piece-level or long gesture |
| repeated_chord_accompaniment | 1,9,35-36,55-56,59 | span 59 measures exceeds local span 5; piece-level or long gesture |
| repeated_chord_accompaniment | 1-2,9,29-30,57,59 | span 59 measures exceeds local span 5; piece-level or long gesture |
| repeated_chord_accompaniment | 2-3,58 | span 57 measures exceeds local span 5; piece-level or long gesture |
| chordal_homophonic_texture | 5-6,8,11,15-26,56,61,63-65,67,72 | span 68 measures exceeds local span 5; piece-level or long gesture |
| left_hand_stride_like_motion | 8-72 (65 measures) | span 65 measures exceeds local span 5; piece-level or long gesture |

## Evidence Summary
- Token kind counts: chord_shape: 24, density_spike: 49, hand_movement: 40, harmonic_simultaneity: 34, leap: 19, melodic_interval: 69, onset_alignment: 10, pattern_break: 25, pattern_repetition: 45, register_shift: 9
- Gesture kind counts: accompaniment_pattern: 45, arpeggio: 1, bass_to_chord: 16, block_chord_landing: 34, cadence_like_arrival: 58, melody_with_accompaniment: 11
- Component type counts: accompaniment_layer: 20, accompaniment_pattern_reference: 6, accompaniment_role: 2, balance_relation: 22, bass_anchor: 2, beat_placement: 2, chord_note_count: 27, doubling_type: 1, hand_relocation: 2, harmonic_collection: 2, interval_path: 2, landing_beat: 27, landing_onset: 27, launch_note: 28, leap_interval: 28, leap_interval_semitones: 28, melody_layer: 20, octave_direction: 1, octave_pair_sequence: 1, octave_span: 1, onset_alignment: 22, other_hand_activity: 26, register_separation: 22, rhythm_cell: 2, rhythmic_independence: 22, target_chord: 27, target_span: 27, upper_chord_landing: 2
- Musical objects in span: 109
- Components in span: 399
- Top components: launch_note ×28 (pitch_midi=68); leap_interval ×28 (leap_interval_semitones=-14); leap_interval_semitones ×28 (leap_interval_semitones=-14)
- Consistency warnings: 10 (see Instruction Units and JSON diagnostics)

<details>
<summary>Raw object/component evidence</summary>

_Raw JSON truncated for readability (1031938 chars total, showing first 12000). Full payload written to sibling .json when generated via script._

```json
{
  "span": "58-62",
  "flagged_measures": [
    "59",
    "61"
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
