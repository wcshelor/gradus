# Front-Facing Graph Taxonomy

Status: implemented mapping layer — executable taxonomy `gradus.front_graph_taxonomy.v1`. Authoritative IDs/weights live in `src/piano_difficulty/difficulty_analysis/front_graph_taxonomy.py`.
Related: `difficulty_aspect_taxonomy.md`, `core_feature_registry.md`,
`feature_registry.md`.

## Purpose

The front-facing graph taxonomy is the learner-visible layer for Gradus
difficulty graphs. It should answer a practical question:

> What kind of practice demand is visible in this passage?

This layer does not replace the 9-aspect backend taxonomy or the raw feature
registry. It is a compact presentation layer that groups score-derived evidence
into graph lines a learner can understand quickly. Raw features and the
9-aspect profile remain available for explanations, caveats, attribution, and
future learner-specific adjustment.

The graph dimensions are composite signals. A backend feature may contribute to
more than one graph dimension when that reflects the musical demand. Mappings
should stay sparse: most features should have one dominant graph dimension and
at most one or two secondary dimensions.

## Six Graph Dimensions

### Finger Dexterity

Finger-level execution demand: fast or intricate patterns, short written values,
articulation precision, repeated attacks, and chord or pitch patterns that make
finger control more demanding.

Includes:

- dense attacks or notes that create finger activity
- short durations and fast passagework proxies
- articulation density and articulation-specific note ratios
- black-key or chord-shape signals when they affect fingering

Does not include:

- large relocations across the keyboard, unless the feature also implies
  finger-level complexity
- notation that is primarily a reading burden

### Hand Movement / Position

Spatial demand at the keyboard: reaches, stretches, leaps, register shifts,
hand relocation, cross-staff movement, and awkward hand positions.

Includes:

- melodic leap and timed displacement features
- simultaneous span and register range
- pitch-range and pitch-distribution proxies
- octave-heavy or wide chord signals

Does not include:

- finger speed without spatial relocation
- visual reading burden except where notation implies physical relocation

### Layers & Coordination

Demand from managing multiple things at once: layered texture, polyphony,
inter-hand independence, chordal density, asynchronous onsets, and hand-role
separation.

Includes:

- texture and polyphony features
- inter-hand alignment, asynchrony, and subdivision mismatch
- cross-staff notes when they imply hand-role or staff-role conflict
- staff-specific dynamics where the score asks for hand-specific balance

Does not include:

- rhythm difficulty that is only about subdivision or duration variety
- expression markings that do not imply layered control

### Rhythm & Timing

Temporal demand: density in time, subdivision variety, tuplets, polyrhythm,
meter/tempo changes, duration variability, and timing independence.

Includes:

- note and attack density
- shortest values, tuplets, duration distributions, and duration variability
- polyrhythm and asymmetric tuplet signals
- tempo and meter changes
- coordination features when timing independence is the relevant burden

Does not include:

- physical movement that happens to occur quickly unless the feature explicitly
  captures timing pressure
- expressive timing nuance beyond what the score encodes

### Expression & Sound Control

Sound-shaping demand that is explicitly visible in the score: dynamics,
articulations, hairpins, staff-specific control, and written changes that ask
the learner to shape tone or balance.

Includes:

- dynamics count, rate, changes, and range
- crescendo and diminuendo wedge starts
- articulation ratios and articulation density
- staff-specific dynamics as a proxy for localized sound control

Does not include:

- unnotated interpretation, tone production, rubato, or performance nuance as a
  scored fact
- claims about actual performer velocity or musical maturity

### Notation / Reading

Visual and symbolic decoding burden: accidentals, key context, clef changes,
ledger lines, cross-staff notation, and other score-reading demands.

Includes:

- accidental density, counts, and ratios
- clef changes and ledger-line burden
- cross-staff note count
- key signature and key changes as reading context
- black-key rate when treated as notation/key familiarity rather than hand shape

Does not include:

- texture that only looks dense because many notes sound together
- motor difficulty after the score has already been decoded

This dimension is intentionally kept as-is for now. More refined notation and
reading semantics should be revisited later.

## Draft Feature Contribution Mapping

Weights below are design weights for the graph layer, not validated difficulty
weights. They indicate how much a normalized raw feature trace should contribute
to each learner-facing graph dimension. Zero-weight dimensions are omitted.

| Feature or family | Draft contributions |
| --- | --- |
| `rhythm.note_density` | Rhythm & Timing 0.55; Finger Dexterity 0.35; Layers & Coordination 0.10 |
| `rhythm.attack_density` | Rhythm & Timing 0.55; Finger Dexterity 0.35; Layers & Coordination 0.10 |
| `rhythm.shortest_written_duration` | Rhythm & Timing 0.65; Finger Dexterity 0.35 |
| `rhythm.tuplet_count` | Rhythm & Timing 0.75; Finger Dexterity 0.15; Layers & Coordination 0.10 |
| `rhythm.duration_value_ratio` | Rhythm & Timing 0.90; Finger Dexterity 0.10 |
| `rhythm.significant_shortest_value` | Rhythm & Timing 0.75; Finger Dexterity 0.25 |
| `rhythm.asymmetric_tuplet_measure_ratio` | Rhythm & Timing 0.75; Layers & Coordination 0.15; Finger Dexterity 0.10 |
| `rhythm.polyrhythm_measure_ratio`, `rhythm.polyrhythm_flag` | Rhythm & Timing 0.65; Layers & Coordination 0.35 |
| `leaps.mean_melodic_leap`, `leaps.max_melodic_leap`, `leaps.count_ge_*` | Hand Movement / Position 0.90; Finger Dexterity 0.10 |
| `leaps.timed_difficult_displacement_*` | Hand Movement / Position 0.75; Rhythm & Timing 0.10; Finger Dexterity 0.10; Layers & Coordination 0.05 |
| `pitch_geometry.max_simultaneity_span`, `pitch_geometry.mean_simultaneity_span` | Hand Movement / Position 0.80; Finger Dexterity 0.15; Layers & Coordination 0.05 |
| `pitch_geometry.register_range` | Hand Movement / Position 0.85; Rhythm & Timing 0.15 |
| `texture.notes_per_onset` | Layers & Coordination 0.60; Hand Movement / Position 0.20; Finger Dexterity 0.10; Expression & Sound Control 0.10 |
| `texture.simultaneity_density` | Layers & Coordination 0.70; Hand Movement / Position 0.15; Expression & Sound Control 0.10; Finger Dexterity 0.05 |
| `texture.vertical_density_proxy` | Layers & Coordination 0.65; Hand Movement / Position 0.10; Finger Dexterity 0.10; Expression & Sound Control 0.10; Rhythm & Timing 0.05 |
| `texture.chord_count`, `texture.chord_ratio` | Layers & Coordination 0.55; Hand Movement / Position 0.25; Finger Dexterity 0.15; Expression & Sound Control 0.05 |
| `texture.octave_chord_ratio` | Hand Movement / Position 0.55; Layers & Coordination 0.30; Finger Dexterity 0.10; Expression & Sound Control 0.05 |
| `coordination.aligned_hand_onset_count` | Layers & Coordination 0.70; Rhythm & Timing 0.30 |
| `coordination.asynchronous_hand_onset_count` | Layers & Coordination 0.70; Rhythm & Timing 0.25; Hand Movement / Position 0.05 |
| `coordination.aligned_hand_onset_ratio` | Layers & Coordination 0.75; Rhythm & Timing 0.25 |
| `coordination.subdivision_mismatch_proxy` | Layers & Coordination 0.55; Rhythm & Timing 0.45 |
| `notation.accidental_density`, `notation.accidental_count`, `notation.accidental_ratio` | Notation / Reading 0.90; Finger Dexterity 0.10 |
| `notation.clef_change_count` | Notation / Reading 0.85; Hand Movement / Position 0.15 |
| `notation.cross_staff_note_count` | Notation / Reading 0.60; Layers & Coordination 0.25; Hand Movement / Position 0.15 |
| `notation.ledger_line_burden` | Notation / Reading 0.90; Hand Movement / Position 0.10 |
| `expression.articulated_note_ratio` | Expression & Sound Control 0.50; Finger Dexterity 0.35; Rhythm & Timing 0.10; Layers & Coordination 0.05 |
| `expression.articulation_density` | Finger Dexterity 0.40; Expression & Sound Control 0.40; Rhythm & Timing 0.15; Layers & Coordination 0.05 |
| `expression.staccato_note_ratio`, `expression.accent_note_ratio`, `expression.strong_accent_note_ratio`, `expression.tenuto_note_ratio` | Expression & Sound Control 0.55; Finger Dexterity 0.30; Rhythm & Timing 0.10; Layers & Coordination 0.05 |
| `expression.dynamic_marking_*`, `expression.dynamic_range_span` | Expression & Sound Control 0.90; Rhythm & Timing 0.05; Layers & Coordination 0.05 |
| `expression.wedge_start_count`, `expression.crescendo_start_count`, `expression.diminuendo_start_count` | Expression & Sound Control 0.80; Rhythm & Timing 0.15; Layers & Coordination 0.05 |
| `expression.staff_specific_dynamic_ratio` | Expression & Sound Control 0.70; Layers & Coordination 0.30 |
| `statistics.pitch_mean` | Hand Movement / Position 0.30 |
| `statistics.pitch_std` | Hand Movement / Position 0.55 |
| `statistics.pitch_entropy` | Hand Movement / Position 0.35; Finger Dexterity 0.10; Layers & Coordination 0.10 |
| `statistics.deviation_from_c4` | Hand Movement / Position 0.55 |
| `statistics.duration_mean`, `statistics.duration_std`, `statistics.duration_variability` | Rhythm & Timing 0.70; Finger Dexterity 0.15 |
| `statistics.black_key_rate` | Notation / Reading 0.45; Finger Dexterity 0.25; Hand Movement / Position 0.20 |
| `statistics.polyphony_rate` | Layers & Coordination 0.75; Hand Movement / Position 0.10; Expression & Sound Control 0.10; Finger Dexterity 0.05 |
| `statistics.triad_count`, `statistics.seventh_chord_count`, `statistics.ninth_chord_count` | Layers & Coordination 0.45; Hand Movement / Position 0.35; Finger Dexterity 0.15; Expression & Sound Control 0.05 |
| `metadata.primary_tempo` | Rhythm & Timing 0.50; Finger Dexterity 0.20 |
| `metadata.tempo_change_count` | Rhythm & Timing 0.45; Expression & Sound Control 0.40 |
| `metadata.meter_change_count` | Rhythm & Timing 0.70; Layers & Coordination 0.10 |
| `metadata.key_signature` | Notation / Reading 0.75; Finger Dexterity 0.10 |
| `metadata.key_change_count` | Notation / Reading 0.75; Rhythm & Timing 0.10; Expression & Sound Control 0.10 |
| `metadata.pitch_range` | Hand Movement / Position 0.75 |
| `metadata.length_quarters`, `metadata.measure_count`, `metadata.note_count`, `metadata.page_count` | Context only; do not score directly into the graph layer. |

## Implementation Notes (Implemented)

Implemented as `src/piano_difficulty/difficulty_analysis/front_graph_taxonomy.py` (presentation layer, separate from raw feature extraction), containing:

- version `gradus.front_graph_taxonomy.v1`
- stable graph-dimension IDs, labels, descriptions, and caveats (six dimensions)
- executable feature-to-graph-dimension weight table (sparse, weights >0 ≤1)
- tests that validate known dimensions, known features, and weight ranges

The graph calculation operates on normalized feature traces: each graph dimension is the weighted mean of its contributing normalized feature traces (multiplied by dimension weights, aggregated per region/window). Context-only features (`metadata.length_quarters`, `metadata.measure_count`, `metadata.note_count`, `metadata.page_count`) are excluded from scoring. The graph exposes the six broad dimensions, while hover/click explanations retain the raw contributing feature IDs and plain-language causes. Refined candidate-section metadata (`local_causes[]`, `distinct_local_causes[]`, `distinct_local_cause_count`, `supporting_window_indices`, `setup_window_indices`, `continuation_window_indices`, `hand_tempering`/`is_single_hand_window`, `has_mosso_tempo`/`tempo_texts[]`/`tempo_influence`) can support graph explanations/tooltips where available; they are explanation/detail metadata and not required for graph computation. See the executable module for authoritative IDs and exact weights.

## Open Questions

- Whether `Hand Movement / Position` should later be shortened to `Hand
  Movement`, `Hand Positioning`, or another label after seeing real graph copy.
- Whether `Finger Dexterity` reads as a passage demand rather than a personal
  trait; if not, alternatives include `Fingerwork` or `Technical Fluency`.
- How much of notation difficulty should remain in the graph versus local
  explanation tags once reading-specific features are refined.
- Whether expression features should receive confidence modifiers because
  written markings do not always imply greater difficulty.
