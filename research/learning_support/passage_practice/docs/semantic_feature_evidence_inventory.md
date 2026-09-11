# S0.2 — Piano-difficulty feature evidence inventory

Status: inventory only. No feature formulas altered (per task limit).

Sources inspected:

- `research/piano_difficulty/src/piano_difficulty/features/__init__.py` — extractor registry (`metadata, rhythm, pitch_geometry, leaps, texture, coordination, notation, expression`).
- `research/piano_difficulty/src/piano_difficulty/features/{metadata,rhythm,pitch_geometry,leaps,texture,coordination,notation,expression}.py` — per-family `extract(score)`.
- `research/piano_difficulty/src/piano_difficulty/features/base.py` — `FeatureRecord{feature_id, scope, scope_ref, value, units, reliability, source_span, diagnostics}`.
- `research/piano_difficulty/src/piano_difficulty/features/_common.py` — `feature_record()`, `score_duration_quarters()`, `rate_per_quarter()`, `mean()`.
- `research/piano_difficulty/src/piano_difficulty/analysis/source_map.py` — `build_source_span()` (measure-index span only).
- `research/piano_difficulty/src/piano_difficulty/features/registry.py` — promoted overview subset (`difficulty_factors.v1`, 5 factors).
- `research/piano_difficulty/src/piano_difficulty/output/json_export.py` — `score_payload.v1` export.
- `research/piano_difficulty/src/piano_difficulty/difficulty_analysis/models.py` — `AnalysisDimensionResult` (source_span + notable_measures, no note IDs).
- `research/piano_difficulty/src/piano_difficulty/difficulty_analysis/dynamics/models.py` — `TemporalFeatureSeries`, `DifficultyPassage`, `FeatureContribution`, `DifficultyHotspot`, `DifficultyProfile` (windowed hotspot lane).
- `research/piano_difficulty/src/piano_difficulty/temporal/windows.py` — `ScoreRegion{measure_start/end, window_index, offsets, hand}` (measure/beat windows, no note IDs).

Ownership reminder: feature extraction, `ScoreIR`, windows, and hotspots
belong to `research/piano_difficulty/`. Passage practice may consume their
payloads as optional difficulty context (`DifficultyEvidence`, D-013) but
must not redefine formulas or import pedagogical concepts upstream.

## Cross-cutting traceability finding (applies to every row below)

- **Event-level trace: NOT available.** Every record is built by
  `feature_record()`, whose only provenance is
  `source_span = {measure_start, measure_end}` derived from
  `event.measure_index` (`source_map.py:19-31`). No note/rest/direction IDs,
  no onset Fractions, no observation lists, no aggregation rule, no threshold
  relationship, no per-event values.
- `reliability` is always the default `"direct"`; `diagnostics` is
  `list[str]` (plain strings, not `Diagnostic` objects with source refs).
- Empty inputs silently become zero (`mean([]) -> 0.0`, `rate_per_quarter`
  guard `-> 0.0`, `max(..., default=0)`). There is no missingness state;
  "missing" is indistinguishable from "measured zero". Semantic consumers
  must treat unmeasured as unavailable, never as zero (cf. S0.1 rule).
- This falls short of `contracts.md` `FeatureEvidence` (ordered
  observations + aggregation rule + missingness + resolvable source refs).
  Closing that gap is WP-04 work, not this inventory.
- Region scope of the base extractors is **piece-level** (`scope="piece"`,
  `scope_ref="all"`) except for the hand/measure/duration_value variants
  noted per row. Finer regions (measure/beat windows, hotspot regions) exist
  only in the Difficulty Dynamics lane (`ScoreRegion` + `TemporalFeatureSeries`
  per window), still at measure granularity — see "Exported payloads" below.

## Feature table

| Feature ID(s) | Units | Region scope (base extractor) | Event-level trace available? | Missing event references / gaps for semantic use |
|---|---|---|---|---|
| `metadata.page_count`, `metadata.measure_count`, `metadata.note_count`, `metadata.pitch_range` | pages / measures / notes / semitones | piece | No — measure-index span only | No per-event data; `pitch_range` is max-min over logical notes with no contributing-note IDs or region |
| `metadata.tempo_change_count`, `metadata.key_change_count`, `metadata.meter_change_count` | changes | piece | No — span over `score.directions or score.measures` / `score.measures` | Change counts with no change-point locations, no before/after values, no direction/measure IDs |
| `rhythm.note_density` | notes_per_quarter | piece | No — span over logical notes | Numerator (note count) and denominator (score duration from measure span) not separately exposed; no per-onset breakdown |
| `rhythm.attack_density` (promoted overview factor, `selected_hand_or_score`) | attacks_per_quarter | piece | No — span over logical notes | Distinct-onset count collapsed to one float; onset times/IDs unavailable; windowed recomputation only via Dynamics lane |
| `rhythm.shortest_written_duration` | quarter_notes | piece | No — span over written notes | Minimum with no arg-min note ID; `0` default when empty is ambiguous with a real zero |
| `rhythm.tuplet_count` | notes | piece | No — span over written notes | Count only; which notes/measures are tuplets unavailable at record level (measure-level ratios exist separately) |
| `rhythm.duration_value_ratio` (one record per duration value) | ratio | `duration_value` / value label | No — span over that value's notes | Group membership (which notes) not exported; ratios per value, not per region |
| `rhythm.significant_shortest_value` | whole_note_denominator | piece | No — span over written notes | Derived judgement value, no supporting-note IDs |
| `rhythm.asymmetric_tuplet_measure_ratio`, `rhythm.polyrhythm_measure_ratio` | ratio | piece | No — span over implicated measures | Measure-index sets (`asymmetric_tuplet_measures`, `polyrhythm_measures`) exist inside `reference_metrics` but only the ratio + span are exported |
| `rhythm.polyrhythm_flag` (one record per implicated measure) | flag (=1) | measure / index | No — single-measure span | Presence flag only; the conflicting subdivisions are not identified by note ID |
| `pitch_geometry.mean_simultaneity_span` | semitones | piece | No — span over onset-group member notes | Group spans averaged; neither the groups nor the extremal notes are identified |
| `pitch_geometry.max_simultaneity_span` (promoted overview factor, `hand`) | semitones | hand / right, left | No — span over that hand's group notes | Maximum with no arg-max group/note IDs; already-sustaining notes excluded per limitation, silently |
| `pitch_geometry.register_range` | semitones | hand / right, left | No — span over that hand's notes | Range with no extremal note IDs |
| `leaps.mean_melodic_leap`, `leaps.max_melodic_leap` (`max` promoted in overview as "Largest pitch transition", `hand`) | semitones | hand / right, left | No — span over that hand's notes | Closest-pitch-set distance between successive onset groups, collapsed; the transition pair(s) driving the value are not identified; differs from passage-practice LS-06 consecutive-attack intervals by construction (onset-grouped, unsigned, closest-set) |
| `leaps.count_ge_5`, `leaps.count_ge_8`, `leaps.count_ge_12` | leaps | hand / right, left | No — span over that hand's notes | Threshold counts with no per-leap values, locations, or note-pair IDs |
| `leaps.timed_difficult_displacement_ratio` | percent | hand / right, left | No — span over hand-metric notes | Reference-metric derived; contributing events not identified |
| `leaps.max_timed_difficult_displacement` | semitones | hand / right, left | No — span over hand-metric notes | Maximum with no arg-max note IDs |
| `leaps.timed_difficult_displacement_count` (one record per implicated measure) | events | measure / index | No — single-measure span of that hand's notes | Count per measure; the displacements themselves carry no note-pair IDs |
| `texture.notes_per_onset`, `texture.simultaneity_density`, `texture.vertical_density_proxy` | notes_per_onset / ratio / average_sounding_notes | piece | No — span over logical notes (global onset groups with `hand is None` for the first two) | Group sizes and sounding durations collapsed; no per-onset sizes, no group IDs |
| `texture.chord_count` (per hand, plus one record per implicated measure) | onsets | hand / right, left; measure / index | No — span over that hand's (or measure's) notes | Counts only; chord member note IDs and onset times unavailable |
| `texture.chord_ratio`, `texture.octave_chord_ratio` | percent | hand / right, left | No — span over that hand's notes | Ratios only; no chord member IDs |
| `coordination.aligned_hand_onset_count`, `coordination.asynchronous_hand_onset_count`, `coordination.aligned_hand_onset_ratio` | onsets / ratio | piece | No — span over both-hands notes | Aligned vs async onset sets collapsed to counts/ratio; the onset times driving them are not exported |
| `coordination.subdivision_mismatch_proxy` (promoted overview factor, `coordination`) | ratio | piece | No — span over both-hands notes | Unaligned-offset proportion over measures active in both hands; per-measure offsets and the mismatching onsets are not identified |
| `notation.accidental_density` (promoted overview factor, `selected_hand_or_score`) | ratio | piece | No — span over written notes | Explicit-accidental ratio; which notes carry accidentals unavailable (per-hand/measure counts below are the only refinement) |
| `notation.clef_change_count` | changes | piece | No — span over `score.clefs` | Count with no change locations or clef IDs |
| `notation.cross_staff_note_count` | notes | piece | No — span over written notes | Counts only explicit staff/hand conflicts; member note IDs unavailable; heuristic limitation carried as plain-string diagnostic |
| `notation.ledger_line_burden` | ledger_lines | piece | No — span over written notes | Summed burden with no per-note ledger counts; assumed-default-clef fallback carried as plain-string diagnostic |
| `notation.accidental_count` (per hand, plus per implicated measure), `notation.accidental_ratio` (per hand) | notes / percent | hand / right, left; measure / index | No — span over that hand's (or measure's) notes | Counts/ratios only; accidental-bearing note IDs unavailable at record level |
| `expression.articulated_note_ratio` (piece + per hand), `expression.articulation_density` (piece) | ratio / articulated_notes_per_quarter | piece; hand / right, left | No — span over written notes (or articulated subset) | Which notes are articulated unavailable; per-type ratios below are the only refinement |
| `expression.staccato_note_ratio`, `expression.accent_note_ratio`, `expression.strong_accent_note_ratio`, `expression.tenuto_note_ratio` (piece + per hand) | ratio | piece; hand / right, left | No — span over matching-or-all written notes (fallback keeps span coarse when no matches) | Matching-note IDs unavailable; empty-match fallback reuses the full note list for the span, so the span does not prove any match exists |
| `expression.dynamic_marking_count`, `expression.dynamic_marking_rate`, `expression.dynamic_change_count`, `expression.dynamic_range_span` | markings / markings_per_quarter / changes / ordinal_steps | piece | No — span over dynamic directions (or all directions as fallback) | Dynamic levels collapsed; the marking sequence, change points, and direction IDs are not exported; unknown level tokens silently ignored in level parsing |
| `expression.wedge_start_count`, `expression.crescendo_start_count`, `expression.diminuendo_start_count`, `expression.staff_specific_dynamic_ratio` | wedges / ratio | piece | No — span over wedge/direction subsets (with fallbacks as above) | Start events carry no measure/onset export at record level; staff-specific ratio has no per-marking staff breakdown |

## Promoted overview subset (the only features with reviewed ranking status)

`difficulty_factors.v1` (`features/registry.py`) promotes exactly five, with
stated limitations:

- `rhythm.attack_density` (attacks_per_quarter, selected_hand_or_score) — "Does not incorporate performance tempo."
- `leaps.max_melodic_leap` (semitones, hand) — "A pitch-set proxy, not an estimate of physical hand travel."
- `pitch_geometry.max_simultaneity_span` (semitones, hand) — "Staff-based hand inference; excludes already-sustaining notes."
- `coordination.subdivision_mismatch_proxy` (ratio, coordination) — "Different onset patterns need not be difficult for a given learner."
- `notation.accidental_density` (ratio, selected_hand_or_score) — "Does not model the learner's reading familiarity."

No other feature ID carries reviewed ranking status. Semantic detectors must
not treat unpromoted IDs as ranked difficulty claims.

## Exported payloads that can describe a selected CIPI passage

- **`score_payload.v1`** (`output/json_export.py:to_json_payload`): score
  identity (path/title/composer/counts), `features[]` (records as above),
  `piece_summary`, `measure_summaries[]`, `analysis_profiles[]`,
  `diagnostics[]` (measure ranges only). No note-level evidence anywhere.
- **Difficulty Dynamics profile** (`difficulty_analysis/dynamics/models.py`):
  `regions[]` (`ScoreRegion`: `window_index`, `measure_start/end`,
  `measure_numbers`, quarter/beat offsets as strings, `hand`, float
  `position`), per-feature `series` (`TemporalFeatureSeries`: raw,
  normalized, smoothed value per region + `missing_region_indices` +
  `availability_notes`), `passages[]` (peaks: region + value + contributing
  feature + rank + method), `hard_spots[]` (`DifficultyHotspot`: region,
  `support_count`, `supporting_feature_ids`, `best_feature_id/value`,
  `feature_contributions[]` with raw/normalized/smoothed/attribution/weight/
  share/rank). Region granularity is measures/beats, never notes; hotspot
  references are real analyzer outputs consumable as `DifficultyEvidence`
  context (D-013), not passage identity.
- **`AnalysisDimensionResult`** (`difficulty_analysis/models.py`):
  `dimension_id`, mark/label, raw value + units, summary,
  `source_span{measure_start/end}`, plain-string diagnostics,
  `notable_measures[]`. Same measure-granularity ceiling.

## What S0.2 does not claim

- No formula was read as a quality claim; limitations quoted above are the
  extractors' own stated strings, not new review findings.
- No observation breakdown is imputed where none is exported: every
  "event-level trace" cell above is "No" by construction of
  `feature_record()` + `build_source_span()`.
- No CIPI run is mapped here (that is S0.3); no duplicate-parsing risk list
  is attempted (that is S0.4); no readiness judgement is made (that is S0.5).
- No conclusion is drawn about which features *should* gain event traces
  (that is WP-04 / S2.2 / S-Q004 territory).

## Next task

S0.3 (CIPI walkthrough-to-semantic handoff note) is still missing, as is
S0.4 (duplicate-parsing risks). S0.5 readiness matrix stays blocked until
S0.1–S0.4 all exist.
