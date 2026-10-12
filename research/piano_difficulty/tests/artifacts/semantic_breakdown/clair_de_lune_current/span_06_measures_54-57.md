<!-- Semantic breakdown span 06: flagged 55,56 -> expanded 54-57 -->
<!-- Span provenance: extracted from research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json (leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans)); flagged_provenance: leaps.timed_difficult_displacement_count (22 measures); diagnostics tie warnings (8 measures) — prioritized over timed displacements for Clair de Lune alignment; diagnostics overlap timed [9, 61]; timed extra measures [11, 20, 22, 24, 27, 28, 29, 31, 32, 33, 35, 36, 40, 41, 47, 48, 65, 66, 68, 72] (not used as flagged spans); manual testing passages 25-26, 27-28; span source: extracted_from_analysis_json; flagged (55, 56) -> expanded (54, 57) (context 1, merge=True) -->
<!-- Generated via local inspection delegate; analysis_json: research/piano_difficulty/tests/artifacts/cipi_dataset/python_analysis/full_run/piece_json/00449__pieces_debussy_debussy_clair-de-lune-d-flat-major-mvt1.json -->
# Local Semantic Inspection: Measures 54-57

## Passage Scope
- Report span: 54-57
- Flagged measures: 55, 56
- Source score: /Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_clair-de-lune-d-flat-major-mvt1.musicxml

## Instruction Units
### 1. Melody with accompaniment
Both hands form a melody-with-accompaniment texture at m.54: one layer carries the melodic line while another supplies aligned support. Melody Gb5-Db6 over accompaniment Ab4.

- Hand / voice: both
- Melody tones: Gb5-Db6 (8 notes)
- Accompaniment tones: Ab4 (1 notes)
- Register separation: 10 semitones
- Onset alignment: 0.25 of melody onsets coincide with accompaniment
- Evidence: object: melody_with_accompaniment [ges2432:melody_with_accompaniment]; evidence_event_ids=['e1292:n1423', 'e1293:n1424', 'e1294:n1431']; confidence=0.78; components: accompaniment_layer:left, accompaniment_pattern_reference:left, balance_relation:both
- Caveats: balance_inferred_from_texture
- Consistency: no warnings

### 2. LH Chord Landing
The left hand sounds C4-C4-Eb4-Eb4-F4-F4-Ab4-Ab4-C5-C5 (10 notes, span 12 semitones) on m.55, beat 4.

- Hand / voice: left
- Chord tones: C4-C4-Eb4-Eb4-F4-F4-Ab4-Ab4-C5-C5 (10 notes), span 12 semitones
- Placement: m.55, beat 4 — quarter (3/2 quarters (1.5 q))
- Evidence: object: chord_landing [ges2473:bass_to_chord]; evidence_event_ids=['e1313:n1459', 'e1324:n1467', 'e1325:n1468']; confidence=0.78; components: launch_note:left, leap_interval:left, leap_interval_semitones:left
- Caveats: none — score-derived evidence
- Consistency: 1 warning(s) — see JSON diagnostics and details below
<details>
<summary>Consistency warnings</summary>

  - **component_instance_mismatch** [other_hand_activity]: component hand 'right' conflicts with object hand 'left'

</details>

### 3. LH Broken-Chord Pattern
The left hand outlines a harmony as a broken-chord figure at m.54 on beats 1.5-2.25, spanning 10 semitones. Pitch collection Ab4-C5-Eb5-Gb5.

- Hand / voice: left
- Pitch collection: Ab4-C5-Eb5-Gb5, span 10 semitones
- Interval steps: +4, +3, +3
- Placement: m.54 beats 1.5-2.25
- Evidence: object: broken_chord_accompaniment [ges2427:arpeggio]; evidence_event_ids=['e1294:n1431', 'e1295:n1432', 'e1298:n1433']; confidence=0.70; components: accompaniment_role:left, bass_anchor:68, beat_placement:left
- Caveats: relocation_small
- Consistency: no warnings

## Supporting Local Objects
_Showing 7 of 7 object groups (compact). Full details in <details>._

| # | Object | Count | Best conf | Measures | Why not promoted |
|---|--------|-------|-----------|----------|------------------|
| G1 | leap_to_chord (Leap to chord) | 3 | 0.85 | 55-57 | relevant locally but not top-ranked; kept as supporting |
| G2 | melody_with_accompaniment (Melody with accompaniment) | 12 | 0.78 | 55-58 | relevant locally but not top-ranked; kept as supporting |
| G3 | chord_landing (Chord landing) | 6 | 0.78 | 55-57 | below promotion confidence threshold |
| G4 | repeated_position_pattern (Repeated position pattern) | 71 | 0.72 | 54-58 | relevant locally but not top-ranked; kept as supporting |
| G5 | broken_chord_accompaniment (Broken-chord accompaniment) | 3 | 0.70 | 55-57 | relevant locally but not top-ranked; kept as supporting |
| G6 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 13 | 0.66 | 54-58 | relevant locally but not top-ranked; kept as supporting |
| G7 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 4 | 0.66 | 54-57 | relevant locally but not top-ranked; kept as supporting |

<details>
<summary>All supporting objects (ungrouped)</summary>

| # | Object | Measures | Local reason | Why not promoted |
|---|--------|----------|--------------|------------------|
| S1 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S2 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S3 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.70, 3 events | relevant locally but not top-ranked; kept as supporting |
| S4 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 54 | local overlap m.54, confidence 0.66, 4 events | relevant locally but not top-ranked; kept as supporting |
| S5 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 54 | local overlap m.54, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S6 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S7 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S8 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S9 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S10 | repeated_position_pattern (Repeated position pattern) | 54 | local overlap m.54, confidence 0.62, 3 events | relevant locally but not top-ranked; kept as supporting |
| S11 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.63, 5 events | relevant locally but not top-ranked; kept as supporting |
| S12 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S13 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.62, 4 events | relevant locally but not top-ranked; kept as supporting |
| S14 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S15 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.72, 8 events | relevant locally but not top-ranked; kept as supporting |
| S16 | repeated_position_pattern (Repeated position pattern) | 54-55 | local overlap m.54-55, confidence 0.70, 4 events | relevant locally but not top-ranked; kept as supporting |
| S17 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S18 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S19 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 55 | local overlap m.55, confidence 0.66, 4 events | relevant locally but not top-ranked; kept as supporting |
| S20 | broken_chord_accompaniment (Broken-chord accompaniment) | 55 | local overlap m.55, confidence 0.70, 4 events | relevant locally but not top-ranked; kept as supporting |
| S21 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S22 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S23 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 55 | local overlap m.55, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S24 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 55 | local overlap m.55, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S25 | melody_with_accompaniment (Melody with accompaniment) | 55 | local overlap m.55, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S26 | melody_with_accompaniment (Melody with accompaniment) | 55 | local overlap m.55, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S27 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S28 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S29 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S30 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |
| S31 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S32 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.70, 5 events | relevant locally but not top-ranked; kept as supporting |
| S33 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S34 | leap_to_chord (Leap to chord) | 55 | local overlap m.55, confidence 0.85, 11 events | relevant locally but not top-ranked; kept as supporting |
| S35 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S36 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S37 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 55 | local overlap m.55, confidence 0.66, 15 events | relevant locally but not top-ranked; kept as supporting |
| S38 | melody_with_accompaniment (Melody with accompaniment) | 55 | local overlap m.55, confidence 0.78, 15 events | relevant locally but not top-ranked; kept as supporting |
| S39 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S40 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S41 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S42 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S43 | chord_landing (Chord landing) | 55 | local overlap m.55, confidence 0.58, 10 events | below promotion confidence threshold |
| S44 | repeated_position_pattern (Repeated position pattern) | 55 | local overlap m.55, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S45 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 55-56 | local overlap m.55-56, confidence 0.66, 7 events | relevant locally but not top-ranked; kept as supporting |
| S46 | melody_with_accompaniment (Melody with accompaniment) | 55-56 | local overlap m.55-56, confidence 0.78, 7 events | relevant locally but not top-ranked; kept as supporting |
| S47 | repeated_position_pattern (Repeated position pattern) | 55-56 | local overlap m.55-56, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S48 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 55-56 | local overlap m.55-56, confidence 0.66, 7 events | relevant locally but not top-ranked; kept as supporting |
| S49 | melody_with_accompaniment (Melody with accompaniment) | 55-56 | local overlap m.55-56, confidence 0.78, 7 events | relevant locally but not top-ranked; kept as supporting |
| S50 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 56 | local overlap m.56, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S51 | melody_with_accompaniment (Melody with accompaniment) | 56 | local overlap m.56, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S52 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 56 | local overlap m.56, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S53 | melody_with_accompaniment (Melody with accompaniment) | 56 | local overlap m.56, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S54 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S55 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S56 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 8 events | relevant locally but not top-ranked; kept as supporting |
| S57 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 56 | local overlap m.56, confidence 0.66, 4 events | relevant locally but not top-ranked; kept as supporting |
| S58 | broken_chord_accompaniment (Broken-chord accompaniment) | 56 | local overlap m.56, confidence 0.70, 4 events | relevant locally but not top-ranked; kept as supporting |
| S59 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S60 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S61 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S62 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.63, 6 events | relevant locally but not top-ranked; kept as supporting |
| S63 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S64 | repeated_position_pattern (Repeated position pattern) | 56 | local overlap m.56, confidence 0.62, 5 events | relevant locally but not top-ranked; kept as supporting |
| S65 | chord_landing (Chord landing) | 56 | local overlap m.56, confidence 0.78, 4 events | relevant locally but not top-ranked; kept as supporting |
| S66 | leap_to_chord (Leap to chord) | 56 | local overlap m.56, confidence 0.85, 4 events | relevant locally but not top-ranked; kept as supporting |
| S67 | chord_landing (Chord landing) | 56 | local overlap m.56, confidence 0.58, 3 events | below promotion confidence threshold |
| S68 | chord_landing (Chord landing) | 56 | local overlap m.56, confidence 0.58, 2 events | below promotion confidence threshold |
| S69 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 56-57 | local overlap m.56-57, confidence 0.66, 11 events | relevant locally but not top-ranked; kept as supporting |
| S70 | melody_with_accompaniment (Melody with accompaniment) | 56-57 | local overlap m.56-57, confidence 0.78, 11 events | relevant locally but not top-ranked; kept as supporting |
| S71 | repeated_position_pattern (Repeated position pattern) | 56-57 | local overlap m.56-57, confidence 0.70, 6 events | relevant locally but not top-ranked; kept as supporting |
| S72 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S73 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S74 | arpeggiated_accompaniment (Arpeggiated accompaniment) | 57 | local overlap m.57, confidence 0.66, 4 events | relevant locally but not top-ranked; kept as supporting |
| S75 | broken_chord_accompaniment (Broken-chord accompaniment) | 57 | local overlap m.57, confidence 0.70, 4 events | relevant locally but not top-ranked; kept as supporting |
| S76 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S77 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S78 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57 | local overlap m.57, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S79 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57 | local overlap m.57, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S80 | melody_with_accompaniment (Melody with accompaniment) | 57 | local overlap m.57, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S81 | melody_with_accompaniment (Melody with accompaniment) | 57 | local overlap m.57, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S82 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S83 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S84 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S85 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |
| S86 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S87 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.70, 5 events | relevant locally but not top-ranked; kept as supporting |
| S88 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S89 | chord_landing (Chord landing) | 57 | local overlap m.57, confidence 0.78, 5 events | relevant locally but not top-ranked; kept as supporting |
| S90 | leap_to_chord (Leap to chord) | 57 | local overlap m.57, confidence 0.85, 5 events | relevant locally but not top-ranked; kept as supporting |
| S91 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S92 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S93 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57 | local overlap m.57, confidence 0.66, 9 events | relevant locally but not top-ranked; kept as supporting |
| S94 | melody_with_accompaniment (Melody with accompaniment) | 57 | local overlap m.57, confidence 0.78, 9 events | relevant locally but not top-ranked; kept as supporting |
| S95 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S96 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S97 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S98 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S99 | chord_landing (Chord landing) | 57 | local overlap m.57, confidence 0.58, 4 events | below promotion confidence threshold |
| S100 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.62, 7 events | relevant locally but not top-ranked; kept as supporting |
| S101 | repeated_position_pattern (Repeated position pattern) | 57 | local overlap m.57, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S102 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S103 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S104 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 6 events | relevant locally but not top-ranked; kept as supporting |
| S105 | melody_voicing_over_accompaniment (Melody voicing over accompaniment) | 57-58 | local overlap m.57-58, confidence 0.66, 8 events | relevant locally but not top-ranked; kept as supporting |
| S106 | melody_with_accompaniment (Melody with accompaniment) | 57-58 | local overlap m.57-58, confidence 0.78, 8 events | relevant locally but not top-ranked; kept as supporting |
| S107 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S108 | repeated_position_pattern (Repeated position pattern) | 57-58 | local overlap m.57-58, confidence 0.72, 7 events | relevant locally but not top-ranked; kept as supporting |
| S109 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |
| S110 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 5 events | relevant locally but not top-ranked; kept as supporting |
| S111 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 3 events | relevant locally but not top-ranked; kept as supporting |
| S112 | repeated_position_pattern (Repeated position pattern) | 58 | local overlap m.58, confidence 0.72, 4 events | relevant locally but not top-ranked; kept as supporting |

</details>

## Broad Context / Low Local Specificity
| Object | Span | Reason for exclusion |
|--------|------|----------------------|
| dynamic_swell_across_phrase | 1-72 (72 measures) | span 72 measures exceeds local span 4; piece-level or long gesture |
| phrase_shaping_over_repeated_pattern | 1-72 (72 measures) | span 72 measures exceeds local span 4; piece-level or long gesture |
| balance_between_voices | 1-72 (72 measures) | span 72 measures exceeds local span 4; piece-level or long gesture |
| pedal_point_accompaniment | 1,3,9,26,29,34-38,51,53-54,57-59,67,69-71 | span 71 measures exceeds local span 4; piece-level or long gesture |
| two_voice_counterpoint | 1-72 (72 measures) | span 72 measures exceeds local span 4; piece-level or long gesture |
| pedal_point_accompaniment | 1,9,13,21,23-24,34-38,41,55-56,59 | span 59 measures exceeds local span 4; piece-level or long gesture |
| repeated_chord_accompaniment | 1,9,35-36,55-56,59 | span 59 measures exceeds local span 4; piece-level or long gesture |
| repeated_chord_accompaniment | 1-2,9,29-30,57,59 | span 59 measures exceeds local span 4; piece-level or long gesture |
| repeated_chord_accompaniment | 2-3,58 | span 57 measures exceeds local span 4; piece-level or long gesture |
| chordal_homophonic_texture | 5-6,8,11,15-26,56,61,63-65,67,72 | span 68 measures exceeds local span 4; piece-level or long gesture |
| left_hand_stride_like_motion | 8-72 (65 measures) | span 65 measures exceeds local span 4; piece-level or long gesture |

## Evidence Summary
- Token kind counts: chord_shape: 24, density_spike: 66, hand_movement: 57, harmonic_simultaneity: 37, leap: 6, melodic_interval: 100, onset_alignment: 13, pattern_break: 23, pattern_repetition: 71, register_shift: 2
- Gesture kind counts: accompaniment_pattern: 71, arpeggio: 4, bass_to_chord: 6, block_chord_landing: 21, cadence_like_arrival: 61, melody_with_accompaniment: 14
- Component type counts: accompaniment_layer: 24, accompaniment_pattern_reference: 26, accompaniment_role: 8, balance_relation: 26, bass_anchor: 8, beat_placement: 8, chord_note_count: 10, hand_relocation: 8, harmonic_collection: 8, interval_path: 8, landing_beat: 10, landing_onset: 10, launch_note: 10, leap_interval: 10, leap_interval_semitones: 10, melody_layer: 26, onset_alignment: 26, other_hand_activity: 10, register_separation: 26, rhythm_cell: 8, rhythmic_independence: 26, target_chord: 10, target_span: 10, upper_chord_landing: 8
- Musical objects in span: 126
- Components in span: 334
- Top components: accompaniment_pattern_reference ×26 (accompaniment_attack_density=0); balance_relation ×26 (register_gap_semitones=10); melody_layer ×26 (melody_pitch_range=[78, 85])
- Consistency warnings: 1 (see Instruction Units and JSON diagnostics)

<details>
<summary>Raw object/component evidence</summary>

_Raw JSON truncated for readability (1037977 chars total, showing first 12000). Full payload written to sibling .json when generated via script._

```json
{
  "span": "54-57",
  "flagged_measures": [
    "55",
    "56"
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
