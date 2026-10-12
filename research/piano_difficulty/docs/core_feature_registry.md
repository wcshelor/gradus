# Core Feature Registry

This file tracks the first stable feature families that the repository should
support before aspect grouping, practice recommendations, or weighted scoring
enter the picture.

Canonical framing: the 9-aspect difficulty taxonomy in
[difficulty_aspect_taxonomy.md](difficulty_aspect_taxonomy.md) is the conceptual
target. The families below are the raw, directly observable descriptors that
operationalize that taxonomy. See the taxonomy for the mapping from each family
to its aspect(s) and for which descriptors are candidates, missing, or caveated.
This registry should stay focused on measurable facts; taxonomy, ranking, and
validation remain separate layers (see taxonomy doc).

## Mapping to the 9-aspect target taxonomy

| Raw family (this registry) | Primary aspect(s) | Notes |
| --- | --- | --- |
| Metadata and score context | 1 Rhythmic (tempo/meter), 6 Notation (key), 8 Structural (context only) | Piece-level context, not a ranked difficulty aspect on its own. Now includes compact predictors `metadata.length_quarters`, `metadata.primary_tempo`, `metadata.key_signature` promoted from Yan harness (direct, score-native). |
| Rhythm | 1 Rhythmic demand | Includes density, duration, tuplet, and polyrhythm descriptors. Duration aggregates now also available via `statistics.duration_*` / `duration_variability`. |
| Pitch geometry | 3 Hand-shape/span demand | Instantaneous hand span and register. |
| Leaps | 2 Pitch/movement demand | Inter-onset relocation distance per hand. |
| Texture | 4 Texture/polyphony demand | Also overlaps Aspect 3 for chord-type variants. Now includes typed counts via `statistics.triad/seventh/ninth` and compact `statistics.polyphony_rate`. |
| Coordination | 5 Coordination demand | Inter-hand timing independence (combined view). |
| Notation and reading | 6 Notation/reading demand | Accidental, clef, cross-staff, and ledger-line burden. Now includes `statistics.black_key_rate` and `metadata.key_signature` as compact pitch-class predictors. |
| Expression and written control | 7 Expression/control demand; partial proxy for 9 Performance/interpretive | Written control only; demand direction not ranked. Aspect 9 remains caveated. |
| Statistics (promoted) | 1 Rhythmic (duration), 2 Pitch/movement, 3 Hand-shape, 4 Texture, 6 Notation | Compact Yan-style score-native aggregates promoted to runtime: `statistics.pitch_mean`, `pitch_std`, `pitch_entropy`, `deviation_from_c4`, `duration_mean`, `duration_std`, `pitch_variability`, `duration_variability`, `black_key_rate`, `polyphony_rate`, `triad/seventh/ninth` counts. Direct contracts reused from `tests/harness/yan2023/extractor.py`. Blocked Yan features (`pressing_velocity_*`, `melodic_*`, ergonomic `hand_stretch` beyond `pitch_geometry`, performance/MIDI-dependent) remain excluded. |

`difficulty_overview.v1` remains a frozen 5-factor composite (`rhythm.attack_density`, `leaps.max_melodic_leap`, `pitch_geometry.max_simultaneity_span`, `coordination.subdivision_mismatch_proxy`, `notation.accidental_density`). Promoted `statistics.*` and compact `metadata.*` descriptors are available as raw descriptors and aspect traces, not automatically weighted into the overview score. Structural/pattern demand (Aspect 8) beyond `metadata.length_quarters` and performance/interpretive demand (Aspect 9) have no dedicated raw family in this registry yet. Aspect 8 remains the primary extraction gap beyond length context; Aspect 9 is intentionally caveated as partially observable and learner-dependent.

## Direct feature families for v0

### Metadata and score context

- measure count
- note count
- pitch range
- tempo change count
- key change count
- meter change count
- length in quarter notes (`metadata.length_quarters`)
- primary tempo (`metadata.primary_tempo`, first tempo or measure `tempo_bpm`, fallback 0 with diagnostic)
- key signature fifths (`metadata.key_signature`, first `key_fifths`, fallback 0)

### Rhythm

- note density
- attack density
- shortest written duration
- tuplet count

### Pitch geometry

- per-hand maximum simultaneity span
- mean simultaneity span
- per-hand register range

### Leaps

- mean melodic leap by hand
- maximum melodic leap by hand
- leap threshold counts

### Texture

- notes per onset
- simultaneity density
- vertical density proxy

### Coordination

- aligned versus asynchronous hand onsets
- simple subdivision mismatch proxy

### Notation and reading

- accidental density
- clef change count
- cross-staff note count
- ledger-line burden

### Expression and written control

- articulated-note ratio
- common articulation ratios such as staccato, accent, and tenuto
- explicit dynamic-mark counts and changes
- crescendo and diminuendo wedge counts

### Hand shape and hand position (Gradus experimental / Yan-adjacent)

Gradus experimental features in `src/piano_difficulty/features/hand_shape.py`. Not Yan-derived; Yan-adjacent — related to Yan `hand_stretch`/`chord_number` families but formulas are Gradus-defined. Do not infer fingering, actual hand repositioning, independent voices, or voice-leading; chord-tone comparisons are sorted-pitch comparisons only. Hand-position features report likely hand-position shift (center shift), not literal repositioning.

- Thresholds: `large_span_threshold=12` semitones, `comfortable_span_threshold=9` semitones, `large_center_shift_threshold=7` semitones
- Span / chord size: `hand_shape.octave_onset_rate`, `hand_shape.large_span_onset_rate`, `hand_shape.mean_large_span_burden`, `hand_shape.wide_chord_density`, `hand_shape.repeated_octave_texture_rate`
- Chord-shape variability: `hand_shape.chord_shape_change_rate`, `hand_shape.chord_shape_entropy`, `hand_shape.chord_shape_edit_distance_mean` (unmatched penalty 6 semitones per extra tone, normalized by max chord size), `hand_shape.chord_size_change_rate`, `hand_shape.repeated_shape_ratio`
- Chord-tone motion (same-size chordal transitions only, sorted pitches): `hand_shape.chord_tone_motion_variability`, `hand_shape.nonparallel_chord_tone_motion_rate`, `hand_shape.inner_chord_tone_change_rate`
- Hand position (all hand onsets, likely center shift): `hand_position.max_center_shift`, `hand_position.mean_center_shift`, `hand_position.large_center_shift_rate`, `hand_position.timed_center_shift` (ignores transitions with onset gap ≤0)
- All are per-hand (`scope=hand`, `scope_ref=left|right`); inapplicable chord-transition features emit `0.0` with an explicit insufficient-eligibility diagnostic rather than implying stability/ease.

### Statistics (promoted from Yan harness, score-native)

Promoted compact predictors (see `src/piano_difficulty/features/statistics.py`):

- `statistics.pitch_mean` (midi), `statistics.pitch_std` (midi, population std)
- `statistics.pitch_entropy` (bits, Shannon over exact MIDI pitches)
- `statistics.deviation_from_c4` (semitones, mean |MIDI-60|)
- `statistics.duration_mean` / `statistics.duration_std` (quarter_notes)
- `statistics.pitch_variability` / `statistics.duration_variability` (ratio, adjacent-normalized)
- `statistics.black_key_rate` (ratio, written-note ratio)
- `statistics.polyphony_rate` (ratio, polyphonic onset ratio)
- `statistics.triad_count` / `seventh_chord_count` / `ninth_chord_count` (chords, distinct pitch-class set sizes per global onset group)

All reuse Yan-harness math only where score-native and regression-checked on `tests/fixtures/feature_fixture.musicxml` vs `tests/harness/yan2023/implementation_audit.py:90`. Blocked features (`pressing_velocity_entropy/variability`, `melodic_complexity/originality`, `degree_of_melodiousness`, ergonomic `hand_stretch` beyond `pitch_geometry`, performance/MIDI-only or ambiguous proxies) remain excluded.

## Feature contract

Each feature should eventually be emitted with:

- `feature_id`
- `scope`
- `scope_ref`
- `value`
- `units`
- `reliability`
- `source_span`
- `diagnostics`

This registry should stay focused on directly observable descriptors. Any
aspect grouping, practice recommendation, weighted scoring, or interpretive
proxy layer should be added on top of these facts rather than mixed into them.
