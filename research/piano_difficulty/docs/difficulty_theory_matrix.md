# Difficulty Theory Matrix

This matrix connects the survey dimensions to the repo feature families and the
current literature support. It is meant to be a living theory document, not a
final claim that every feature is settled.

## How to read this

- **Survey dimension** is the human-facing construct we ask pianists about.
- **Candidate score features** are the symbolic descriptors we can already
  extract or are close to extracting.
- **Evidence strength** is my practical judgment about how strongly the feature
  is supported by the current repo and literature.
- **Recommended stance** is the working policy for analysis.

## Matrix

| Survey dimension | Candidate score features | Why it fits | Best current evidence | Evidence strength | Recommended stance |
| --- | --- | --- | --- | --- | --- |
| Hand movement / jumps | `leaps.mean_melodic_leap`, `leaps.max_melodic_leap`, `leaps.count_ge_5`, `leaps.count_ge_8`, `leaps.count_ge_12`, `leaps.timed_difficult_displacement_ratio`, `hand_displacement_rate` | Captures the physical distance the hands must cover between attacks. | Yan 2023-style difficulty features; 2024 CIPI/RubricNet descriptors; 2018 statistical piano reduction difficulty work. | Strong | Core feature family |
| Finger ergonomics / stretching / big chords | `pitch_geometry.max_simultaneity_span`, `pitch_geometry.mean_simultaneity_span`, `pitch_geometry.register_range`, `texture.chord_count`, `texture.chord_ratio`, `texture.octave_chord_ratio`, `hand_stretch`, `ninth_chord` | Captures hand span, chord size, and awkward vertical spread. | Same sources as above, especially hand displacement / hand stretch literature and explainable descriptor papers. | Strong | Core feature family, with some proxies |
| Articulation / style / exposure / precision | `expression.articulated_note_ratio`, `expression.articulation_density`, `expression.staccato_note_ratio`, `expression.accent_note_ratio`, `expression.strong_accent_note_ratio`, `expression.tenuto_note_ratio`, `staccato_rate` | Measures how specifically the score demands attack shape and precision. | Early hand-crafted difficulty feature literature; recent explainable score descriptors. | Moderate to strong | Core feature family |
| Hand independence | `coordination.aligned_hand_onset_ratio`, `coordination.asynchronous_hand_onset_count`, `coordination.subdivision_mismatch_proxy`, `rhythm.polyrhythm_measure_ratio` | Captures bimanual timing separation and offset mismatch. | Yan 2026 structure-aware work; score-coordination reasoning in difficulty literature. | Strong | Core feature family |
| Polyphony / managing multiple voices | `texture.notes_per_onset`, `texture.simultaneity_density`, `texture.vertical_density_proxy`, `polyphony_rate`, `pitch_geometry.mean_simultaneity_span` | Captures how many simultaneous notes and voices must be controlled. | Yan 2026 simultaneous-note encoding; CIPI and RubricNet-style descriptors. | Strong | Core feature family |
| Harmonic complexity | `metadata.key_change_count`, `notation.accidental_density`, `notation.accidental_count`, `black_key_rate`, `pitch_entropy`, `key_signature` | Captures tonal instability, accidentals, and pitch-class spread. | CIPI/RubricNet descriptors; Yan 2023 feature set; sight-reading / difficulty-aware score generation paper. | Strong | Core feature family, but split tonal vs accidental burden if needed |
| Rhythmic complexity | `rhythm.note_density`, `rhythm.attack_density`, `rhythm.shortest_written_duration`, `rhythm.tuplet_count`, `rhythm.duration_value_ratio`, `rhythm.significant_shortest_value`, `rhythm.asymmetric_tuplet_measure_ratio`, `rhythm.polyrhythm_measure_ratio`, `note_duration_variability`, `playing_speed_variation` | Captures density, subdivision, irregularity, and temporal variation. | Yan 2023, CIPI, and older handcrafted feature work. | Strong | Core feature family |
| Tempo | `tempo`, `metadata.tempo_change_count`, `playing_speed`, `playing_speed_variation` | Tempo amplifies nearly every other technical demand. | Statistical piano reduction difficulty work; CIPI / Yan framing. | Strong | Global multiplier, not a standalone human dimension |
| Unpredictability / instability | `pitch_entropy`, `rhythm.duration_value_ratio`, `pitch_variability`, `note_duration_variability`, `playing_speed_variation`, `rhythm.asymmetric_tuplet_measure_ratio`, `rhythm.polyrhythm_measure_ratio` | Captures irregularity and surprise in pitch or rhythm patterns. | Yan 2023-style entropy/variability features and difficulty-aware score descriptors. | Moderate | Secondary construct and hypothesis layer |

## Practical interpretation policy

1. A feature is worth keeping if it is predictive, reproducible, and musically
   intelligible.
2. Strong correlation with difficulty ratings is valid evidence of
   predictive validity.
3. Predictive validity alone does not settle construct validity, so features
   that are empirically strong but theoretically ambiguous should stay marked as
   proxies until the math is sharpened.
4. Survey data should be used to decide whether a construct deserves to be
   split, renamed, or merged.

## Suggested use in analysis

- Use the survey dimensions as the top-level feature-theory map.
- Use the repo feature families as the measurable implementation layer.
- Track which survey dimensions are best predicted by which feature families.
- Track which dimensions are most strongly endorsed by pianists even when the
  current symbolic proxy is weak.
- Keep a separate column for “literature support” when the matrix is extended
  into a working log of papers and claims.

## Next refinements to add

- a paper citation column with one or more sources per row
- a `direct / proxy / hypothesis` status column for each candidate feature
- a `survey item wording` column
- a `prediction evidence` column once the existing run summaries are fully
  consolidated
