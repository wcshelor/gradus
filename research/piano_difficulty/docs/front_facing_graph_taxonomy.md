# Front-Facing Graph Taxonomy

Status: implemented mapping layer — executable taxonomy `gradus.front_graph_taxonomy.v2`. Authoritative IDs/weights live in `src/piano_difficulty/difficulty_analysis/front_graph_taxonomy.py`. This document's table is the human-readable tracker; `front_graph_taxonomy.py` is the executable source of truth.
Related: `difficulty_aspect_taxonomy.md`, `core_feature_registry.md`,
`feature_registry.md`.

**David demo binding (2026-09):** The David demo's visible difficulty chart (`chart.series` / `chart.graph_dimension_ids`, 6 lines) and hotspot ranking / primary explanation copy (`manifest.hotspots[].top_contributors` with nested `feature_contributors`) are driven exclusively by this 6-dimension taxonomy (`gradus.front_graph_taxonomy.v2`). The 9-way aspect taxonomy (`difficulty_aspects.v1`: 9 aspects) remains available as backend coverage/provenance evidence only — under `difficulty_aspects` / `aspects` and `backend_aspect_hotspots` — and is not used for visible hotspot selection, ranking, or primary explanation. The demo does not imply calibrated grades, learner diagnosis, or final validated weights; weights here are design weights for presentation, not validated difficulty weights.

## Purpose

The front-facing graph taxonomy is the learner-visible layer for Gradus
difficulty graphs. It should answer a practical question:

> What kind of practice demand is visible in this passage?

This layer does not replace the 9-aspect backend taxonomy or the raw feature
registry. It is a compact presentation layer that groups score-derived evidence
into graph lines a learner can understand quickly. Raw features and the
9-aspect profile remain available for explanations, caveats, attribution, and
future learner-specific adjustment. Every extracted micro-component (raw feature ID in `FEATURE_TO_DIMENSION_WEIGHTS`) has a visible destination, a weight, and a caveat trail; that micro-component → 6-dimension mapping table below is the key source of truth for the David demo story and must stay maintainable.

The graph dimensions are composite signals. A backend feature may contribute to
more than one graph dimension when that reflects the musical demand. Mappings
should stay sparse: most features should have one dominant graph dimension and
at most one or two secondary dimensions.

## Six Graph Dimensions

### Finger Dexterity

Finger-level execution demand: fast or intricate patterns, short written values,
articulation precision, repeated attacks, and finger-pattern complexity.

Includes:

- dense attacks or notes that create finger activity
- short durations and fast passagework proxies
- articulation density and articulation-specific note ratios
- black-key signals when they affect fingering

Does not include:

- large relocations, wide simultaneous spans, octave shapes, or dense block-chord
  shapes unless the feature explicitly captures finger-pattern instability;
  those are hand position/span demand, not finger dexterity
- notation that is primarily a reading burden

### Hand Position / Movement

Spatial demand at the keyboard: reaches, stretches, leaps, register shifts,
hand relocation, cross-staff movement, wide simultaneous spans, octaves,
dense block-chord shapes, and awkward hand positions.

Includes:

- melodic leap and timed displacement features
- simultaneous span and register range (max/mean simultaneity span)
- pitch-range and pitch-distribution proxies
- octave-heavy, wide-span, and dense block-chord signals — vertical density and
  chord shape belong here as physical hand shape/position demand

Does not include:

- finger speed without spatial relocation
- visual reading burden except where notation implies physical relocation

Note: until a separate texture dimension exists, vertical density / dense chord
shapes are routed primarily here (and modestly to Control/Expression), not to
Coordination / Layers or Finger Dexterity.

### Coordination / Layers

Demand from managing independently timed or layered material: asynchronous hand
onsets, subdivision mismatch, contrasting rhythms between hands, polyrhythm /
asymmetric tuplets, independently moving layers, and hand-role separation.

Includes:

- asynchronous hand onsets and subdivision mismatch
- polyrhythm and asymmetric tuplet signals
- cross-staff notes when they imply hand-role or staff-role conflict
- staff-specific dynamics where the score asks for hand-specific balance
- future explicit voice/layer independence features

Does not include:

- rhythm difficulty that is only about subdivision or duration variety
- expression markings that do not imply layered control
- both-hands-aligned chordal density, wide simultaneous spans, octaves, or dense
  block chords on their own — those are hand position/span demand, not
  coordination, unless there is independent timing, subdivision mismatch,
  asynchrony, or explicit layer evidence
- merely "many notes at the same time" — vertical density belongs primarily to
  Hand Position / Movement (and modestly to Control/Expression) until a texture
  dimension exists; Coordination / Layers is driven by mismatch, asynchrony,
  polyrhythm, and layer independence, not vertical density

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

### Control / Expression

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
| `rhythm.note_density` | Rhythm & Timing 0.55; Hand Position / Movement 0.20; Finger Dexterity 0.05; Coordination / Layers 0.05 |
| `rhythm.attack_density` | Rhythm & Timing 0.65; Finger Dexterity 0.15; Coordination / Layers 0.05 |
| `rhythm.shortest_written_duration` | Rhythm & Timing 0.75; Finger Dexterity 0.15 |
| `rhythm.tuplet_count` | Rhythm & Timing 0.75; Finger Dexterity 0.15; Coordination / Layers 0.10 |
| `rhythm.duration_value_ratio` | Rhythm & Timing 0.90; Finger Dexterity 0.10 |
| `rhythm.significant_shortest_value` | Rhythm & Timing 0.80; Finger Dexterity 0.10 |
| `rhythm.asymmetric_tuplet_measure_ratio` | Rhythm & Timing 0.75; Coordination / Layers 0.15; Finger Dexterity 0.10 |
| `rhythm.polyrhythm_measure_ratio`, `rhythm.polyrhythm_flag` | Rhythm & Timing 0.65; Coordination / Layers 0.35 |
| `leaps.mean_melodic_leap`, `leaps.max_melodic_leap`, `leaps.count_ge_*` | Hand Position / Movement 0.90; Finger Dexterity 0.10 |
| `leaps.timed_difficult_displacement_*` | Hand Position / Movement 0.75; Rhythm & Timing 0.10; Finger Dexterity 0.10; Coordination / Layers 0.05 |
| `pitch_geometry.max_simultaneity_span` | Hand Position / Movement 0.90; Finger Dexterity 0.05 |
| `pitch_geometry.mean_simultaneity_span` | Hand Position / Movement 0.85; Finger Dexterity 0.05 |
| `pitch_geometry.register_range` | Hand Position / Movement 0.85; Rhythm & Timing 0.15 |
| `texture.notes_per_onset` | Hand Position / Movement 0.50; Control / Expression 0.15; Coordination / Layers 0.15 (texture proxy); Finger Dexterity 0.05 |
| `texture.simultaneity_density` | Hand Position / Movement 0.45; Control / Expression 0.15; Coordination / Layers 0.15 (texture proxy); Finger Dexterity 0.05 |
| `texture.vertical_density_proxy` | Hand Position / Movement 0.40; Control / Expression 0.20; Coordination / Layers 0.10 (texture proxy); Finger Dexterity 0.05; Rhythm & Timing 0.05 |
| `texture.chord_count`, `texture.chord_ratio` | Hand Position / Movement 0.55; Control / Expression 0.10; Coordination / Layers 0.10 (texture proxy); Finger Dexterity 0.05 |
| `texture.octave_chord_ratio` | Hand Position / Movement 0.85; Control / Expression 0.10; Finger Dexterity 0.05 |
| `coordination.aligned_hand_onset_count` | Rhythm & Timing 0.20 (context only; not coordination) |
| `coordination.asynchronous_hand_onset_count` | Coordination / Layers 0.70; Rhythm & Timing 0.25; Hand Position / Movement 0.05 |
| `coordination.aligned_hand_onset_ratio` | Rhythm & Timing 0.20 (context only; not coordination) |
| `coordination.subdivision_mismatch_proxy` | Coordination / Layers 0.55; Rhythm & Timing 0.45 |
| `notation.accidental_density`, `notation.accidental_count`, `notation.accidental_ratio` | Notation / Reading 0.90; Finger Dexterity 0.10 |
| `notation.clef_change_count` | Notation / Reading 0.85; Hand Position / Movement 0.15 |
| `notation.cross_staff_note_count` | Notation / Reading 0.60; Coordination / Layers 0.25; Hand Position / Movement 0.15 |
| `notation.ledger_line_burden` | Notation / Reading 0.90; Hand Position / Movement 0.10 |
| `expression.articulated_note_ratio` | Control / Expression 0.65; Finger Dexterity 0.10; Rhythm & Timing 0.10 |
| `expression.articulation_density` | Control / Expression 0.60; Finger Dexterity 0.15; Rhythm & Timing 0.15 |
| `expression.staccato_note_ratio`, `expression.accent_note_ratio`, `expression.strong_accent_note_ratio` | Control / Expression 0.65; Finger Dexterity 0.15; Rhythm & Timing 0.10 |
| `expression.tenuto_note_ratio` | Control / Expression 0.70; Finger Dexterity 0.05; Rhythm & Timing 0.05 |
| `expression.dynamic_marking_*`, `expression.dynamic_range_span` | Control / Expression 0.90; Rhythm & Timing 0.05; Coordination / Layers 0.05 |
| `expression.wedge_start_count`, `expression.crescendo_start_count`, `expression.diminuendo_start_count` | Control / Expression 0.80; Rhythm & Timing 0.15; Coordination / Layers 0.05 |
| `expression.staff_specific_dynamic_ratio` | Control / Expression 0.70; Coordination / Layers 0.30 |
| `statistics.pitch_mean` | Hand Position / Movement 0.30 |
| `statistics.pitch_std` | Hand Position / Movement 0.55 |
| `statistics.pitch_entropy` | Hand Position / Movement 0.35; Finger Dexterity 0.10; Coordination / Layers 0.10 |
| `statistics.deviation_from_c4` | Hand Position / Movement 0.55 |
| `statistics.duration_mean`, `statistics.duration_std`, `statistics.duration_variability` | Rhythm & Timing 0.70; Finger Dexterity 0.15 |
| `statistics.black_key_rate` | Notation / Reading 0.45; Finger Dexterity 0.25; Hand Position / Movement 0.20 |
| `statistics.polyphony_rate` | Hand Position / Movement 0.40; Control / Expression 0.15; Coordination / Layers 0.15 (texture proxy); Finger Dexterity 0.05 |
| `statistics.triad_count`, `statistics.seventh_chord_count`, `statistics.ninth_chord_count` | Hand Position / Movement 0.55; Control / Expression 0.10; Coordination / Layers 0.10 (texture proxy); Finger Dexterity 0.05 |
| `metadata.primary_tempo` | Rhythm & Timing 0.50; Finger Dexterity 0.20 |
| `metadata.tempo_change_count` | Rhythm & Timing 0.45; Control / Expression 0.40 |
| `metadata.meter_change_count` | Rhythm & Timing 0.70; Coordination / Layers 0.10 |
| `metadata.key_signature` | Notation / Reading 0.75; Finger Dexterity 0.10 |
| `metadata.key_change_count` | Notation / Reading 0.75; Rhythm & Timing 0.10; Control / Expression 0.10 |
| `metadata.pitch_range` | Hand Position / Movement 0.75 |
| `hand_shape.octave_onset_rate` | Hand Position / Movement 0.85; Finger Dexterity 0.05 |
| `hand_shape.large_span_onset_rate` | Hand Position / Movement 0.90 |
| `hand_shape.mean_large_span_burden` | Hand Position / Movement 0.90 |
| `hand_shape.wide_chord_density` | Hand Position / Movement 0.80; Rhythm & Timing 0.10 |
| `hand_shape.repeated_octave_texture_rate` | Hand Position / Movement 0.85 |
| `hand_shape.chord_shape_change_rate` | Hand Position / Movement 0.75; Finger Dexterity 0.10 |
| `hand_shape.chord_shape_entropy` | Hand Position / Movement 0.75; Finger Dexterity 0.10 |
| `hand_shape.chord_shape_edit_distance_mean` | Hand Position / Movement 0.75; Finger Dexterity 0.10 |
| `hand_shape.chord_size_change_rate` | Hand Position / Movement 0.65; Finger Dexterity 0.10 |
| `hand_shape.repeated_shape_ratio` | Hand Position / Movement 0.60 |
| `hand_shape.chord_tone_motion_variability` | Hand Position / Movement 0.70; Finger Dexterity 0.15 |
| `hand_shape.nonparallel_chord_tone_motion_rate` | Hand Position / Movement 0.70; Finger Dexterity 0.15 |
| `hand_shape.inner_chord_tone_change_rate` | Hand Position / Movement 0.70; Finger Dexterity 0.15 |
| `hand_position.max_center_shift` | Hand Position / Movement 0.90 |
| `hand_position.mean_center_shift` | Hand Position / Movement 0.85 |
| `hand_position.large_center_shift_rate` | Hand Position / Movement 0.90 |
| `hand_position.timed_center_shift` | Hand Position / Movement 0.85; Rhythm & Timing 0.10 |
| *Hand shape / Hand position family — Gradus experimental / Yan-adjacent* | *Hand shape/position features are Gradus experimental and not Yan-derived; they relate to Yan `hand_stretch`/`chord_number` families but use Gradus-defined formulas. They do not infer fingering, actual repositioning, independent voices, or voice-leading. Center shifts are “likely hand-position shifts.”* |
| `metadata.length_quarters`, `metadata.measure_count`, `metadata.note_count`, `metadata.page_count` | Context only; do not score directly into the graph layer. |

### Conceptual note on vertical density and aligned hands

- **Both-hands-aligned chordal density is not coordination difficulty.** Vertically dense,
  wide-span, rhythmically aligned chord/octave passages where both hands share the same
  rhythm and onsets are aligned create hand position/span demand, not inter-hand
  independence demand. True coordination difficulty requires asynchronous onsets,
  subdivision mismatch, contrasting rhythms, polyrhythm, or explicit layer/voice
  independence.
- **Vertical density / chord shape belongs mainly to Hand Position / Movement** (and
  modestly to Control / Expression for voicing/balance) unless there is independent
  timing or layer evidence. Texture features (`notes_per_onset`, `simultaneity_density`,
  `vertical_density_proxy`, `chord_count/ratio`, `octave_chord_ratio`, `polyphony_rate`,
  `triad/seventh/ninth` counts) and span features (`max/mean simultaneity span`) are
  therefore weighted primarily to `hand_movement_position`, not to `layers_coordination`
  or `finger_dexterity`.
- **These graph weights are presentation/explanation weights, not the Yan predictive
  model.** They control what the learner sees in the 6-dimension chart and hotspot
  explanations. Raw feature extraction formulas are unchanged; the Yan-inspired
  prediction lane and the 9-aspect backend taxonomy remain separate.

## Implementation Notes (Implemented)

Implemented as `src/piano_difficulty/difficulty_analysis/front_graph_taxonomy.py` (presentation layer, separate from raw feature extraction), containing:

- version `gradus.front_graph_taxonomy.v2`
- stable graph-dimension IDs, labels, descriptions, and caveats (six dimensions)
- executable feature-to-graph-dimension weight table (sparse, weights >0 ≤1) — **executable source of truth**; the table above is the human-readable tracker that must stay in sync
- tests that validate known dimensions, known features, and weight ranges

The graph calculation operates on normalized feature traces: each graph dimension is the weighted mean of its contributing normalized feature traces (multiplied by dimension weights, aggregated per region/window). Context-only features (`metadata.length_quarters`, `metadata.measure_count`, `metadata.note_count`, `metadata.page_count`) are excluded from scoring. The graph exposes the six broad dimensions, while hover/click explanations retain the raw contributing feature IDs (micro-components) and plain-language causes. **Micro-components** are the raw feature IDs in `FEATURE_TO_DIMENSION_WEIGHTS`; every extracted signal has a visible destination, a weight, and a caveat trail, giving a clean maintenance surface. Refined candidate-section metadata (`local_causes[]`, `distinct_local_causes[]`, `distinct_local_cause_count`, `supporting_window_indices`, `setup_window_indices`, `continuation_window_indices`, `hand_tempering`/`is_single_hand_window`, `has_mosso_tempo`/`tempo_texts[]`/`tempo_influence`) can support graph explanations/tooltips where available; they are explanation/detail metadata and not required for graph computation. See the executable module for authoritative IDs and exact weights. Hotspot ranking for the David demo uses the graph composite (mean of the 6 dimension signals), not the 9-aspect composite; aspect composites remain as backend provenance.

## Open Questions

- Whether `Hand Position / Movement` should later be shortened to `Hand
  Movement`, `Hand Positioning`, or another label after seeing real graph copy.
- Whether `Finger Dexterity` reads as a passage demand rather than a personal
  trait; if not, alternatives include `Fingerwork` or `Technical Fluency`.
- How much of notation difficulty should remain in the graph versus local
  explanation tags once reading-specific features are refined.
- Whether expression features should receive confidence modifiers because
  written markings do not always imply greater difficulty.
