# Difficulty Aspect Taxonomy

Version: target taxonomy v1 (conceptual, not yet validated)
Status: canonical conceptual vocabulary. Runtime exposes descriptive grouped
traces through the primary `difficulty_aspects.v1` profile; validated
weights, grades, and learner-specific interpretation are not claimed.
Related: `core_feature_registry.md` (raw descriptors), `feature_registry.md` (reviewed overview), `front_facing_graph_taxonomy.md` (learner-facing graph layer), `yan2023_feature_inventory.md` / `yan2023_feature_plan.md` (Yan reconstruction lane), `difficulty_theory_matrix.md` (survey-dimension theory map)

## Purpose and distinctions

This document makes the 9-aspect taxonomy explicit as the thesis/product
target framing for score-derived piano difficulty and practice demand.
`difficulty_aspects.v1` is the primary Gradus analysis profile and exposes all
9 aspects as descriptive traces. The older `difficulty_overview.v1` profile
remains as the conservative 5-factor timeline/export slice.

Four layers are kept distinct:

| Layer | Meaning | Where it lives |
| --- | --- | --- |
| **Taxonomy** | Canonical target model: 9 aspects of difficulty/practice demand that scores can plausibly signal. Unweighted framework, not a validated grade. | This document. |
| **Extractable subfeatures** | Measurable score descriptors that operationalize an aspect. Each has a `feature_id`, scope, units, and reliability. | `core_feature_registry.md` and `src/piano_difficulty/features/*`. |
| **Overview profile** | Selected, conservative subset retained for compatibility, timeline exports, and older demo surfaces. | `feature_registry.md` / `src/piano_difficulty/features/registry.py` (`difficulty_overview.v1`, `difficulty_factors.v1`). |
| **Practice payload** | Learner-facing Gradus payload for hotspots, cards, routines, feedback, and recommendations. It should map back to the 9 aspects and preserve evidence/provenance. | `src/piano_difficulty/pedagogy/*` (`gradus.practice_payload.v1`). |
| **Graph presentation layer** | Compact learner-visible graph dimensions derived from raw features and backend aspects. This is a many-to-many presentation mapping, not a replacement taxonomy. | `front_facing_graph_taxonomy.md` (documentation only for now). |
| **Validation** | Future empirical / teacher / learner evidence that would justify weights, promotion, or learner-specific interpretation. Not claimed here. | `evaluation.md`, lane artifacts, and future study reports. |

The 9 aspects are the feature-framework hypothesis. They are not implied to be
orthogonal, equally weighted, or empirically validated in this step.

Language shown to learners may remain musically precise rather than simplified
plain language. "Teacher-language" should mean vocabulary a learner can grow
into, not a separate teacher-only model.

## The 9 aspects

### 1. Rhythmic demand

**Definition:** How much temporal precision, subdivision variety, and density the
score asks of the player, independent of pitch or hand span.

**Scope:** Score-notated time structure as written, not performed tempo.

**Current implemented subfeatures (score-derived, runtime):**

| feature_id | Units | Notes |
| --- | --- | --- |
| `rhythm.note_density` | notes_per_quarter | Logical-note rate; correlated with attack density — not both in composite. |
| `rhythm.attack_density` | attacks_per_quarter | Selected in `difficulty_overview.v1` (conservative onset rate). |
| `rhythm.shortest_written_duration` | quarter_notes | Floor of written values. |
| `rhythm.tuplet_count` | notes | Written tuplet notes. |
| `rhythm.duration_value_ratio` | ratio | Per-duration-class share (hand-agnostic). |
| `rhythm.significant_shortest_value` | whole_note_denominator | Smallest duration that is not a rare outlier. |
| `rhythm.asymmetric_tuplet_measure_ratio` | ratio | Measures with irregular tuplets. |
| `rhythm.polyrhythm_measure_ratio` | ratio | Measures with cross-hand polyrhythmic content. |
| `rhythm.polyrhythm_flag` | flag | Per-measure polyrhythm marker. |
| `metadata.tempo_change_count` | changes | Score-level tempo direction changes. |
| `metadata.meter_change_count` | changes | Score-level meter changes. |
| `statistics.duration_mean` | quarter_notes | Promoted: mean logical duration (Yan-harness). |
| `statistics.duration_std` | quarter_notes | Promoted: population std of logical durations. |
| `statistics.duration_variability` | ratio | Promoted: adjacent-normalized variability over written durations. |
| `metadata.primary_tempo` | bpm | Promoted: first tempo direction / measure `tempo_bpm`. |
| `metadata.length_quarters` | quarter_notes | Promoted: score duration in quarter notes. |

**Remaining Yan-inspired subfeatures (still Yan lane, not promoted):**

| Yan feature | Status | Candidate math |
| --- | --- | --- |
| `playing_speed` | proxyable | Attacks per quarter (current proxy) — not promoted (overlaps `rhythm.attack_density`). |
| `playing_speed_variation` | implemented (Yan lane) | Tempo-variation ratio — deferred (needs per-score variation definition). |
| `dotted_note_rate` | proxyable | Shared rate bank (written/logical/onset/duration-weighted) — not promoted (ambiguous duration_type convention). |
| `irregular_rhythm` | proxyable | Formula ambiguous — keep candidates explicit. |
| `distinct_stroke_rate` | proxyable | Stroke identity rule unpublished. |

**Missing / future subfeatures:**
- Syncopation / off-beat stress beyond current polyrhythm/tuplet flags.
- Nested or changing subdivisions within a measure (e.g., 3-against-4 against changing meter).
- Explicit hemiola or cross-rhythm typing.
- Duration-distribution entropy as a distinct descriptor (partially covered by `rhythm.duration_value_ratio` but not summarized).

**Evidence limitations:**
- Written durations only; no performed timing, rubato, or tempo realization.
- Tuplet and polyrhythm heuristics depend on MusicXML encoding quality.
- Duration variability candidates are score-native proxies until compared to Yan release matrices.

**Safe for demo/runtime:** `rhythm.attack_density` is reviewed and safe (in `difficulty_overview.v1`). Other rhythm descriptors are available raw but not ranked in the conservative overview.

---

### 2. Pitch / movement demand

**Definition:** How far and how often the hands must relocate between pitch
regions, measured as melodic leaps between successive onsets.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `leaps.mean_melodic_leap` | semitones | Per hand, closest-pitch distance between onset groups. |
| `leaps.max_melodic_leap` | semitones | Selected in `difficulty_overview.v1` (per hand). |
| `leaps.count_ge_5` / `count_ge_8` / `count_ge_12` | leaps | Threshold exceedances per hand. |
| `leaps.timed_difficult_displacement_ratio` | percent | Gap-weighted difficult displacement share (from reference metrics). |
| `leaps.max_timed_difficult_displacement` | semitones | Largest gap-weighted displacement. |
| `leaps.timed_difficult_displacement_count` | events | Per-measure difficult displacement events. |
| `metadata.pitch_range` | semitones | Whole-score pitch span (logical notes). |
| `statistics.pitch_mean` | midi | Promoted: mean MIDI pitch (Yan-harness). |
| `statistics.pitch_std` | midi | Promoted: population std of MIDI pitch. |
| `statistics.pitch_entropy` | bits | Promoted: Shannon entropy over exact MIDI pitches. |
| `statistics.deviation_from_c4` | semitones | Promoted: mean |MIDI-60|. |
| `statistics.pitch_variability` | ratio | Promoted: adjacent-normalized variability over written pitches. |

**Remaining Yan-inspired subfeatures (not promoted):**

| Yan feature | Status |
| --- | --- |
| `hand_displacement_rate` | proxyable (gap-weighted same-hand attack proxy) — not promoted (ambiguous grouping) |

**Missing / future:**
- Direction-aware leap cost (e.g., repeated large outward leaps vs. stepwise return).
- Fingering-conditioned movement cost (needs fingering annotation; not score-derivable alone).
- Register-specific movement penalty (leaps high in the register vs. mid-range).

**Evidence limitations:**
- Closest pitch-set distance is a proxy, not physical hand travel.
- Gap-weighted displacement uses an onset-gap model, not key-to-key kinematics.
- Pitch variability candidates share a score-sequence bank; the best formulation is still to be selected empirically.

**Safe for demo/runtime:** `leaps.max_melodic_leap` is reviewed and safe (in `difficulty_overview.v1`). Mean/threshold variants and displacement ratios are available raw but excluded from the initial composite to avoid correlated movement signals.

---

### 3. Hand-shape / span demand

**Definition:** How much instantaneous hand extension or awkward vertical shaping
the score asks within a simultaneous onset.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `pitch_geometry.max_simultaneity_span` | semitones | Per hand, largest onset span. Selected in `difficulty_overview.v1`. |
| `pitch_geometry.mean_simultaneity_span` | semitones | All-hand mean span. |
| `pitch_geometry.register_range` | semitones | Per-hand pitch span over the whole score. |

**Current promoted Yan-style subfeatures (runtime-native):**

| Feature | Units | Notes |
| --- | --- | --- |
| `statistics.black_key_rate` | ratio | Promoted: written-note black-key ratio. |
| `statistics.triad_count` / `seventh_chord_count` / `ninth_chord_count` | chords | Promoted: typed chord counts by distinct pitch-class set size. |
| `statistics.polyphony_rate` (also aspect 4) | ratio | Promoted: polyphonic onset ratio (also texture). |

**Remaining Yan-inspired subfeatures (not promoted):**

| Yan feature | Status | Notes |
| --- | --- | --- |
| `hand_stretch` | proxyable | Requires precise hand model; paper-facing inventory collapses to one unsuffixed slot — **blocked** per task (ergonomic beyond existing `pitch_geometry` span). |

**Missing / future:**
- Interval-specific span cost (e.g., octave vs. ninth vs. dense cluster) rather than only max semitone distance.
- Sustained-span burden (notes held while new notes are added — current span is attack-local).
- Ergonomic weighting by hand size (learner-dependent; belongs in validation, not score facts).

**Evidence limitations:**
- Span is hand-local and attack-local; it excludes already-sustaining pitches.
- Hand inference is staff-based and conservative.
- `hand_stretch` and chord-type counts are first-pass score proxies.

**Safe for demo/runtime:** `pitch_geometry.max_simultaneity_span` is reviewed and safe (in `difficulty_overview.v1`). Mean span, register range, and chord-type counts are available raw.

---

### 4. Texture / polyphony demand

**Definition:** How many concurrent voices or notes must be managed per unit
time, and how vertically dense the texture is.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `texture.notes_per_onset` | notes_per_onset | Mean notes per global onset group. |
| `texture.simultaneity_density` | ratio | Share of global onsets with >1 note. |
| `texture.vertical_density_proxy` | average_sounding_notes | Total logical duration / score duration. |
| `texture.chord_count` | onsets | Per hand and per measure. |
| `texture.chord_ratio` | percent | Share of hand onsets that are chords. |
| `texture.octave_chord_ratio` | percent | Share of hand chords at octave span. |

**Current promoted Yan-style subfeatures (runtime-native):**

| Feature | Units | Notes |
| --- | --- | --- |
| `statistics.polyphony_rate` | ratio | Promoted: polyphonic onset ratio. |
| `statistics.triad_count` / `seventh_chord_count` / `ninth_chord_count` | chords | Promoted: typed chord counts (also hand-shape). |

**Missing / future:**
- Voice-count trajectory (e.g., 2-voice vs. 3-voice polyphony changing within a piece).
- Independent voice leading difficulty (counterpoint vs. block chords) beyond note-count density.

**Evidence limitations:**
- Global onset grouping approximates simultaneity; engraving timing variations can blur it.
- Vertical density proxy is a duration-based average, not a per-window polyphony curve.

**Safe for demo/runtime:** Available raw. Intentionally excluded from `difficulty_overview.v1` to avoid correlated chord/density signals alongside the span factor. Eligible for `difficulty_aspects.v1`.

---

### 5. Coordination demand

**Definition:** How independently the two hands must act in time, including
aligned vs. asynchronous attacks and subdivision mismatch between hands.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `coordination.aligned_hand_onset_count` | onsets | Onsets shared by both hands. |
| `coordination.asynchronous_hand_onset_count` | onsets | Onsets unique to one hand. |
| `coordination.aligned_hand_onset_ratio` | ratio | Aligned / union onsets. |
| `coordination.subdivision_mismatch_proxy` | ratio | Selected in `difficulty_overview.v1`. Unaligned measure-offsets / union measure-offsets. |

**Candidate Yan-inspired subfeatures:**
- None uniquely mapped; coordination is covered natively. Yan's `playing_speed` interacts with coordination but is classified under rhythmic demand.

**Missing / future:**
- Hand-role complexity (e.g., melody vs. accompaniment independence vs. two equal voices).
- Antiphase or canon-like hand timing (regular offset vs. irregular mismatch).

**Evidence limitations:**
- `subdivision_mismatch_proxy` is explicitly a proxy; different onset patterns are not uniformly difficult across learners.
- Coordination is only computed on the combined view; hand-filtered profiles exclude it.

**Safe for demo/runtime:** `coordination.subdivision_mismatch_proxy` is reviewed and safe (in `difficulty_overview.v1`, combined view only).

---

### 6. Notation / reading demand

**Definition:** How much decoding effort the notation itself imposes, separate
from motor execution: accidentals, clef changes, cross-staff notation, and
ledger-line burden.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `notation.accidental_density` | ratio | Selected in `difficulty_overview.v1`. Explicit accidentals / written notes. |
| `notation.accidental_count` / `notation.accidental_ratio` | notes / percent | Per hand (and per-measure counts). |
| `notation.clef_change_count` | changes | Per staff, sorted by measure. |
| `notation.cross_staff_note_count` | notes | Explicit hand/staff conflicts only. |
| `notation.ledger_line_burden` | ledger_lines | Sum of ledger lines implied by active clef. |

**Current promoted Yan-style subfeatures (runtime-native):**

| Feature | Units | Notes |
| --- | --- | --- |
| `metadata.key_signature` | fifths | Promoted: first key fifths. |
| `statistics.black_key_rate` | ratio | Promoted: written-note black-key ratio (also hand-shape). |

**Missing / future:**
- Key-signature distance / enharmonic spelling cost (beyond raw accidental density).
- Ornament and grace-note reading load (not yet separately modeled).
- 8va/8vb and other staff-shorthand reading cost.

**Evidence limitations:**
- Accidental density does not model learner reading familiarity.
- Cross-staff detection is limited to explicit MusicXML conflicts available in ScoreIR.
- Ledger-line burden assumes standard piano clefs when clef declarations are absent.

**Safe for demo/runtime:** `notation.accidental_density` is reviewed and safe (in `difficulty_overview.v1`). Other notation descriptors are available raw.

---

### 7. Expression / control demand

**Definition:** How much fine control of tone, articulation, and dynamics the
score explicitly asks for through written instructions.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `expression.articulated_note_ratio` | ratio | Share of written notes with any articulation (global and per hand). |
| `expression.articulation_density` | articulated_notes_per_quarter | Articulated notes / score duration. |
| `expression.staccato_note_ratio` / `accent_note_ratio` / `strong_accent_note_ratio` / `tenuto_note_ratio` | ratio | Per-articulation shares (global and per hand). |
| `expression.dynamic_marking_count` | markings | Count of dynamics directions. |
| `expression.dynamic_marking_rate` | markings_per_quarter | Dynamics per quarter note. |
| `expression.dynamic_change_count` | changes | Changes in dynamic level sequence. |
| `expression.dynamic_range_span` | ordinal_steps | Max − min dynamic ordinal. |
| `expression.wedge_start_count` / `crescendo_start_count` / `diminuendo_start_count` | wedges | Hairpin starts. |
| `expression.staff_specific_dynamic_ratio` | ratio | Share of dynamics with explicit staff. |

**Candidate Yan-inspired subfeatures:**

| Yan feature | Status |
| --- | --- |
| `staccato_rate` | implemented (shared rate bank, written-note ratio default) |
| `dotted_note_rate` | proxyable (shared rate bank, dotted-note convention ambiguous) |

**Missing / future:**
- Pedal demand (sustain/una corda) — MusicXML pedal encoding is inconsistent.
- Phrase-level legato / slur burden beyond single-note articulation flags.
- Voicing / balance indications that imply control difficulty (e.g., cantabile over accompaniment).

**Evidence limitations:**
- Only explicitly encoded articulations and dynamics are counted; interpretive nuance beyond the score is not inferred.
- Dynamic ordinals are a coarse symbolic ordering, not loudness prediction.
- The demand direction for expression markings is intentionally left without a ranking claim — more markings do not uniformly mean harder.

**Safe for demo/runtime:** Available raw. Excluded from `difficulty_overview.v1` pending explicit demand-direction interpretation. Eligible for `difficulty_aspects.v1` as an unweighted descriptive bucket.

---

### 8. Structural / pattern demand

**Definition:** How much the piece's larger organization — repetition, pattern
regularity, formal boundaries, and predictability — helps or hinders learning
and memorability. Higher pattern regularity reduces demand; higher structural
irregularity increases it.

**Current implemented subfeatures:**

| feature_id | Units | Notes |
| --- | --- | --- |
| `metadata.measure_count` | measures | Whole-score length. |
| `metadata.note_count` | notes | Whole-score logical-note count. |
| `metadata.length_quarters` | quarter_notes | Promoted: total quarter-note score length (Yan-harness). |

Remaining structural/pattern descriptors are **missing** from runtime beyond this length context.

**Remaining Yan-inspired subfeatures (not separately classified):**
- Yan's variability/entropy features (`pitch_variability`, `note_duration_variability`, `pitch_entropy`) are now promoted runtime-native but classified under pitch and rhythmic demand here, not structural demand, to keep the aspect distinct.

**Missing / future (primary gap):**

| Subfeature idea | Description | Observable in score? |
| --- | --- | --- |
| Repetition / recurrence rate | Share of material that repeats exactly or with transposition | Score-derived, needs pattern detection |
| Sequence / pattern regularity | N-gram repetition, motivic reuse | Score-derived, needs sequence model |
| Formal boundary complexity | Number and irregularity of section boundaries, key/meter changes as form signals | Partially via `metadata.key_change_count` / `metadata.meter_change_count` but not as a structural model |
| Harmonic / pitch predictability | Entropy over pitch classes, chord transitions | Score-derived, future work |
| Length-normalized novelty | New material introduced per unit duration | Score-derived |
| Variation of playing speed (structural sense) | Tempo/length interaction at the piece level | Via Yan `playing_speed_variation` but reinterpreted as structural pacing |

**Evidence limitations:**
- This is the largest gap in the current runtime. No validated repetition or form extractor is promoted yet.
- Any structural descriptor will need a clear operational definition before ranking — repetition helps some learners and may not reduce demand in all pedagogical frames.

**Safe for demo/runtime:** Not safe to surface as a ranked factor yet. In `difficulty_aspects.v1`, keep this bucket explicitly blocked/contextual. The `metadata` length counts may be shown as context but not as a difficulty aspect until structural extractors exist.

---

### 9. Performance / interpretive demand — partially observable / learner-dependent

**Definition:** Demands that are only partly encoded in the score and depend
heavily on the performer and learner: tone production, velocity control,
voicing, timing nuance, and artistic interpretation beyond explicit notation.

This aspect is **intentionally caveated**. The score is an incomplete proxy
for performed difficulty here.

**Current implemented subfeatures (indirect, score-only proxies):**
- Expression/control descriptors listed in Aspect 7 (articulations, dynamics, wedges) are the closest score-native signals for this aspect, but they record what is *written*, not how it must be *performed*.
- `metadata.tempo_change_count` and `expression.dynamic_range_span` are contextual proxies for interpretive range.

**Candidate Yan-inspired subfeatures:**

| Yan feature | Status | Caveat |
| --- | --- | --- |
| `pressing_velocity_entropy` | blocked | Likely needs performance/MIDI data (whole-score distribution per Table 3). |
| `pressing_velocity_variability` | blocked | Likely needs performance/MIDI data. |
| `melodic_complexity` | blocked | MC-family dimension; formula not yet reconstructed. |
| `melodic_originality` | blocked | MC-family dimension; formula not yet reconstructed. |
| `degree_of_melodiousness` | blocked | MC-family dimension; formula not yet reconstructed. |

**Missing / future:**
- All score-to-performance mappings (timing micro-variation, voicing balance, pedal realization).
- Learner-dependent moderators: hand size, experience, practice strategy, reading fluency.
- Any weighting that claims "interpretive difficulty = N" from notation alone.

**Evidence limitations:**
- Score data alone cannot determine pressing velocity or interpretive nuance.
- MC-family features are still blocked; their paper formulas need reconstruction before any interpretation.
- Learner dependence means population-average rankings will mislead for individual learners.

**Safe for demo/runtime:** Not safe to quantify as a ranked difficulty factor from score data alone. Keep caveated:

- In `difficulty_overview.v1`: **excluded** as a ranked factor.
- In `difficulty_aspects.v1`: include as a **labeled caveated bucket** that lists only written proxies, marks blocked candidates, and warns that learner-specific inference requires additional data (performance capture, teacher assessment, or learner history).
- Any UI that surfaces this aspect must carry the disclaimer that the score signal is partial and learner-dependent.

---

## Mapping summary

### From existing runtime families to aspects

| Existing family / module | Primary aspect(s) | Selected in `difficulty_overview.v1`? |
| --- | --- | --- |
| `metadata` | 1 (Rhythmic), 6 (Notation), 8 (Structural, contextual only) | No — contextual descriptors retained outside the composite. Now includes `metadata.length_quarters`, `metadata.primary_tempo`, `metadata.key_signature` as compact promoted predictors. |
| `rhythm` | 1 (Rhythmic) | `rhythm.attack_density` only. |
| `statistics` (promoted) | 1 Rhythmic (duration), 2 Pitch/movement, 3 Hand-shape, 4 Texture, 6 Notation | No — not in overview; available as raw descriptors and aspect traces. Includes `statistics.pitch_*`, `duration_*`, `variability`, `black_key_rate`, `polyphony_rate`, `triad/seventh/ninth`. |
| `leaps` | 2 (Pitch/movement) | `leaps.max_melodic_leap` only. |
| `pitch_geometry` | 3 (Hand-shape/span) | `pitch_geometry.max_simultaneity_span` only. |
| `texture` | 4 (Texture/polyphony) | No — excluded from initial composite to avoid correlated signals. |
| `coordination` | 5 (Coordination) | `coordination.subdivision_mismatch_proxy` only (combined view). |
| `notation` | 6 (Notation/reading) | `notation.accidental_density` only. |
| `expression` | 7 (Expression/control), 9 (Performance, as written proxy) | No — needs demand-direction interpretation before ranking. |

See `core_feature_registry.md` for the full raw descriptor inventory and
`feature_registry.md` for the reviewed 5-factor selection rationale.

### From Yan lane to aspects (post-promotion)

| Yan feature | Aspect | Status |
| --- | --- | --- |
| `note_density` | 1 | runtime-native (`rhythm.note_density`) |
| `duration_mean` / `duration_std` | 1 | **promoted to runtime** (`statistics.duration_mean` / `duration_std`) |
| `playing_speed` / `playing_speed_variation` | 1 / 8 | proxyable / Yan-only (not promoted) |
| `note_duration_variability` | 1 | **promoted** (`statistics.duration_variability`) |
| `irregular_rhythm` / `distinct_stroke_rate` / `dotted_note_rate` | 1 | proxyable — not promoted (ambiguous) |
| `pitch_mean` / `pitch_std` / `pitch_range` / `pitch_entropy` / `deviation_of_pitch_from_C4` / `pitch_variability` | 2 | **promoted** (`statistics.pitch_*`, `deviation_from_c4`, `pitch_variability`; `pitch_range` via `metadata.pitch_range`) |
| `hand_displacement_rate` | 2 | proxyable — not promoted |
| `black_key_rate` / `triad` / `seventh_chord` / `ninth_chord` / `chord_number` | 3, 4 | **promoted** (`statistics.black_key_rate`, `triad/seventh/ninth` counts; `chord_number` via `texture.chord_*`) |
| `hand_stretch` | 3 | blocked — not promoted (ergonomic beyond `pitch_geometry` span) |
| `polyphony_rate` / `chord_number` | 4 | **promoted** (`statistics.polyphony_rate`) |
| `black_key_rate` / `key_signature` | 6 | **promoted** (`statistics.black_key_rate` / `metadata.key_signature`) |
| `staccato_rate` | 7 | runtime-native (`expression.staccato_*`) |
| `pressing_velocity_entropy` / `pressing_velocity_variability` | 9 | blocked — not promoted (needs MIDI/performance) |
| `melodic_complexity` / `melodic_originality` / `degree_of_melodiousness` | 9 | blocked — not promoted (MC family) |
| `length` / `tempo` / `key_signature` | 8 / 1 / 6 | **promoted** (`metadata.length_quarters`, `metadata.primary_tempo`, `metadata.key_signature`) |

Promoted features now have runtime-native `statistics.*` / `metadata.*` `FeatureRecord`s in `src/piano_difficulty/features/statistics.py` and `metadata.py`, selectable via `runtime_statistical` and included in `runtime_yan_overlap`. Blocked features remain in the Yan lab only. Detailed status and formula-variant policy remain in `yan2023_feature_inventory.md` and `yan2023_feature_plan.md`.

## What changed in the promotion (2026-09-16)

- New runtime feature module `src/piano_difficulty/features/statistics.py` emits 13 compact score-native descriptors reusing Yan-harness math (`pitch_mean`, `pitch_std`, `pitch_entropy`, `deviation_from_c4`, `duration_mean/std`, `pitch/duration_variability`, `black_key_rate`, `polyphony_rate`, `triad/seventh/ninth` counts).
- `src/piano_difficulty/features/metadata.py` now emits `metadata.length_quarters`, `metadata.primary_tempo`, `metadata.key_signature` as compact predictors.
- `tests/harness/shared/matrix_features.py` adds `runtime_statistical` and updates `runtime_yan_overlap` to use the new runtime-native columns.
- `src/piano_difficulty/difficulty_analysis/aspects.py` groups the promoted features into their target aspects (rhythmic, pitch/movement, hand-shape, texture, notation, structural).
- `difficulty_overview.v1` (`src/piano_difficulty/features/registry.py`) remains frozen — promoted descriptors are available as raw descriptors / aspect traces, not weighted into the overview score. History: no prior extraction formulas were changed; the 5-factor composite is unchanged.

## What did not change beyond the promotion

- No existing feature formulas were changed except reuse of proven Yan-harness logic for the new descriptors.
- No `difficulty_overview.v1` payload shape, weights, or demo behavior was changed except additional raw descriptors appear alongside the overview.
- `feature_registry.md` remains the 5-factor selection rationale.

## Implementation guidance

### Step A — already extractable, merely not surfaced

These subfeatures exist in `src/` and can be grouped under aspects without new
extraction:

- All remaining `rhythm.*`, `leaps.*`, `pitch_geometry.*`, `texture.*`,
  `coordination.*` (other than the 5 selected), `notation.*`, `expression.*`
  listed in the tables above.
- `metadata.*` as contextual descriptors (not difficulty ranks).

The `difficulty_aspects.v1` primary profile should group the existing raw
descriptors by the 9 aspects, with subfeature traces, separate from
`difficulty_overview.v1`. Frontend and practice consumers should treat these
aspect groups as the main score-derived demand vocabulary. No weight or ranking
is implied by the grouping.

### Step B — needs new extraction

- **Structural/pattern demand (Aspect 8):** repetition/recurrence detection,
  sequence regularity, formal-boundary modeling. Requires new score-analysis
  extractors and a clear operational definition before any ranking.
- **Performance/interpretive demand (Aspect 9):** keep blocked Yan candidates
  as blocked; only written proxies are score-observable. Full quantification
  requires performance/MIDI data or external learner/teacher evidence.

### Step C — profile design decision

Recommended:

| Profile | Purpose | Stability | Weights |
| --- | --- | --- | --- |
| `difficulty_aspects.v1` | Primary Gradus difficulty output. 9 aspect buckets with subfeature traces. | Primary profile output; schema should change only intentionally. | No implied cross-aspect weights. Each bucket lists its subfeature `feature_id`s, units, and availability. Aspect 9 carries the caveated disclaimer. |
| `difficulty_overview.v1` | Compatibility/timeline output. 5 reviewed factors. | Frozen unless explicitly migrated. | Descriptive equal weights; within-piece ranking only. |

Design decision: keep `difficulty_aspects.v1` separate from the existing
overview payload. Separate output minimizes risk to CEO stability.

## Validation disclaimer

- The 9 aspects are a **feature framework**, not a validated weighting model.
- Aspect boundaries are conceptual; empirical work may show overlap or a better
  grouping (e.g., harmonic complexity spans Aspects 3, 4, and 6).
- Weights, cross-aspect comparisons, and learner-specific difficulty claims
  require teacher review, learner studies, or prediction evidence on labeled
  corpora. See `evaluation.md` for the current test-vs.-claim boundary.
- The established difficulty-analysis lanes (`scoreanalyzer`, `yan2023`,
  `difficulty_dynamics`, dataset, OMR, prediction, clustering) remain
  authoritative for their own evidence; this taxonomy only organizes their
  subfeatures.
