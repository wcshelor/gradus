# Difficulty Aspect Feature Gap Audit

Status: gap audit for the canonical 9-aspect taxonomy. No formula, weight, or
stable overview/demo change.
Scope: maps `core_feature_registry.md` runtime descriptors and `yan2023_feature_inventory.md` / `yan2023_feature_plan.md` Yan lane onto `difficulty_aspect_taxonomy.md` v1.
Date: 2026-09-14
Invariant: `src/piano_difficulty/features/registry.py` (`difficulty_factors.v1`)
and the stable `difficulty_overview.v1` payload are unchanged.

## 1. Status summary

The 9-aspect taxonomy is the main Gradus framing; the 5-factor `difficulty_overview.v1` is a deliberate, stable subset retained for compatibility/timeline output. Runtime already covers aspects 1-7 with directly observable score descriptors. The minimal `difficulty_aspects.v1` grouping is built from existing formulas alone — no new extraction required except to fill honest gaps.

- **Ready now (grouping only):** Aspects 1, 2, 4, 5, 6 — runtime descriptors exist and are safe to surface as unweighted, grouped traces.
- **Partial (descriptors exist, ranking not safe):** Aspects 3 and 7 — span/texture descriptors exist; hand-shape needs `hand_stretch` for ergonomic cost, expression needs an explicit demand-direction rule before any ordering.
- **Blocked / caveated (do not rank from score alone):** Aspect 8 structural/pattern is the primary extractor gap (only length/count context exists); Aspect 9 performance/interpretive is intentionally caveated and partly blocked on performance data.

Yan candidates inform coverage but stay in `tests/harness/yan2023/` until a promotion decision per `yan2023_feature_plan.md` Pass 5. No Yan feature is auto-promoted here.

## 2. Per-aspect audit (one row per aspect)

| ID | Aspect | Current runtime coverage (`src/`, via `core_feature_registry.md` + taxonomy) | Yan candidate coverage (`yan2023_feature_inventory.md`) | Missing / future extractors | Confidence | Recommended next action |
|---|---|---|---|---|---|---|
| 1 | Rhythmic demand | `rhythm.note_density`, `rhythm.attack_density` (selected), `rhythm.shortest_written_duration`, `rhythm.tuplet_count`, `rhythm.duration_value_ratio`, `rhythm.significant_shortest_value`, `rhythm.asymmetric_tuplet_measure_ratio`, `rhythm.polyrhythm_measure_ratio`, `rhythm.polyrhythm_flag`, `metadata.tempo_change_count`, `metadata.meter_change_count` | `note_duration_variability` implemented, `playing_speed` proxyable, `playing_speed_variation` / `duration_mean` / `duration_std` implemented, `dotted_note_rate` / `irregular_rhythm` / `distinct_stroke_rate` proxyable | Syncopation/off-beat stress, nested subdivisions, hemiola typing, duration-entropy summary | **ready** | Keep `attack_density` as reviewed factor; surface remaining rhythm descriptors only as grouped traces in `difficulty_aspects.v1`. No new extractor before grouping. |
| 2 | Pitch / movement demand | `leaps.mean_melodic_leap`, `leaps.max_melodic_leap` (selected), `leaps.count_ge_5`/`_8`/`_12`, `leaps.timed_difficult_displacement_ratio`, `leaps.max_timed_difficult_displacement`, `leaps.timed_difficult_displacement_count`, `metadata.pitch_range` | `pitch_mean`/`pitch_std`/`pitch_range`/`pitch_entropy`/`deviation_of_pitch_from_C4`/`pitch_variability` implemented, `hand_displacement_rate` proxyable | Direction-aware leap cost, fingering-conditioned cost, register-specific penalty | **ready** | Keep `max_melodic_leap`; add other leaps as grouped traces. Defer fingering model. `hand_displacement_rate` stays Yan-proxyable until geometry vs `playing_speed` disambiguated. |
| 3 | Hand-shape / span demand | `pitch_geometry.max_simultaneity_span` (selected), `pitch_geometry.mean_simultaneity_span`, `pitch_geometry.register_range` | `black_key_rate`/`chord_number`/`triad`/`seventh_chord`/`ninth_chord` implemented, `hand_stretch` proxyable | Interval-specific span cost, sustained-span burden (held notes), hand-size-ergonomic weighting | **partial** | Surface existing span/register as grouped traces. Do not promote `hand_stretch` (needs hand model) or chord-type counts as span difficulty without ergonomic rule. |
| 4 | Texture / polyphony demand | `texture.notes_per_onset`, `texture.simultaneity_density`, `texture.vertical_density_proxy`, `texture.chord_count` (incl. per-measure), `texture.chord_ratio`, `texture.octave_chord_ratio` | `polyphony_rate` implemented, `chord_number`/`triad`/`seventh_chord`/`ninth_chord` implemented (overlap with 3) | Voice-count trajectory, independent voice-leading vs block-chord distinction | **ready** | Expose as grouped traces in `difficulty_aspects.v1`. Exclusion from `difficulty_overview.v1` remains correct (avoids correlated span/density signal); no formula change needed. |
| 5 | Coordination demand | `coordination.aligned_hand_onset_count`, `coordination.asynchronous_hand_onset_count`, `coordination.aligned_hand_onset_ratio`, `coordination.subdivision_mismatch_proxy` (selected, combined view only) | None uniquely mapped (Yan `playing_speed` stays under Aspect 1) | Hand-role complexity, antiphase/canonic timing typing | **ready** | Keep `subdivision_mismatch_proxy` as reviewed proxy with limitation note. Surface remaining coordination counts/ratios as grouped traces only. |
| 6 | Notation / reading demand | `notation.accidental_density` (selected), `notation.accidental_count`/`accidental_ratio` (per-hand, per-measure), `notation.clef_change_count`, `notation.cross_staff_note_count`, `notation.ledger_line_burden` | `key_signature` implemented, `black_key_rate` implemented | Key-signature distance/enharmonic cost, ornament/grace-note load, 8va/8vb shorthand cost | **ready** | Keep `accidental_density` as reviewed factor; surface other notation descriptors as grouped traces with diagnostics (`cross_staff` = explicit conflicts only, `ledger_line_burden` assumes piano clefs if absent). |
| 7 | Expression / control demand | `expression.articulated_note_ratio` (global+per-hand), `expression.articulation_density`, `expression.staccato/accent/strong_accent/tenuto_note_ratio`, `expression.dynamic_marking_count`/`dynamic_marking_rate`/`dynamic_change_count`/`dynamic_range_span`, `expression.wedge_start_count`/`crescendo_start_count`/`diminuendo_start_count`, `expression.staff_specific_dynamic_ratio` | `staccato_rate` implemented, `dotted_note_rate` proxyable | Pedal demand, phrase-level legato/slur burden, voicing/balance indications | **partial** | **Do not rank.** Surface as unweighted descriptive bucket in `difficulty_aspects.v1` only. Adding a demand direction (more markings = harder) requires explicit pedagogical rule and validation — the taxonomy intentionally leaves it unranked. |
| 8 | Structural / pattern demand | Only context: `metadata.measure_count`, `metadata.note_count` (and Yan `length` in quarters outside `src/`) | `length`/`tempo` implemented in Yan lane only; no structural Yan feature beyond `length` | Repetition/recurrence rate, sequence/n-gram regularity, formal-boundary complexity (`key_change_count`/`meter_change_count` exist but not as form model), harmonic/pitch predictability, length-normalized novelty, structural pacing (`playing_speed_variation` reinterpreted) | **blocked** | **Primary extractor gap.** Do not surface as ranked difficulty. In `difficulty_aspects.v1` expose only `measure_count`/`note_count` as contextual metadata with `availability: contextual` and mark bucket `experimental / missing`. New extractors require pattern-detection and operational definitions before any ranking. |
| 9 | Performance / interpretive demand | No direct runtime quantification; indirect written proxies only: Aspect 7 descriptors + `metadata.tempo_change_count` + `expression.dynamic_range_span` | `pressing_velocity_entropy` blocked, `pressing_velocity_variability` blocked, `melodic_complexity`/`melodic_originality`/`degree_of_melodiousness` blocked (MC family, formulas unrecovered) | Score→performance mappings (timing micro-variation, voicing, pedal realization), learner moderators (hand size, experience, reading fluency) | **caveated** | **Do not quantify from score.** In `difficulty_aspects.v1` include only as labeled caveated bucket: list written proxies, enumerate 5 blocked Yan candidates, require disclaimer "partially observable, learner-dependent; needs performance/MIDI or teacher/learner evidence." No promotion path without external data. |

Confidence legend — `ready`: existing runtime descriptors sufficient to group as unweighted traces; `partial`: descriptors exist but ranking or ergonomic interpretation is unsafe; `blocked`: no validated extractor for the aspect; `caveated`: partly unobservable from score, learner-dependent, blocked Yan candidates.

## 3. Minimal `difficulty_aspects.v1` profile shape (runtime-only, no new formulas)

Uses only descriptors that already exist in `src/piano_difficulty/features/*` per `core_feature_registry.md` + `difficulty_aspect_taxonomy.md`. No Yan promotion, no new weights, no ranking. Grouping only, separate from `difficulty_overview.v1`.

| Aspect | Bucket contents (feature_ids, existing runtime) | Notes |
|---|---|---|
| 1 Rhythmic | `rhythm.note_density`, `rhythm.attack_density`, `rhythm.shortest_written_duration`, `rhythm.tuplet_count`, `rhythm.duration_value_ratio` (per duration class), `rhythm.significant_shortest_value`, `rhythm.asymmetric_tuplet_measure_ratio`, `rhythm.polyrhythm_measure_ratio`, `rhythm.polyrhythm_flag` (per measure), `metadata.tempo_change_count`, `metadata.meter_change_count` | `attack_density` retains reviewed status; others are traces. |
| 2 Pitch/movement | `leaps.mean_melodic_leap` (per hand), `leaps.max_melodic_leap` (per hand), `leaps.count_ge_5`/`_8`/`_12` (per hand), `leaps.timed_difficult_displacement_ratio`, `leaps.max_timed_difficult_displacement`, `leaps.timed_difficult_displacement_count` (per measure), `metadata.pitch_range` | Span-independent relocation cost only. |
| 3 Hand-shape/span | `pitch_geometry.max_simultaneity_span` (per hand), `pitch_geometry.mean_simultaneity_span`, `pitch_geometry.register_range` (per hand) | Attack-local span; caveat "excludes sustaining notes; staff-based hand inference." |
| 4 Texture/polyphony | `texture.notes_per_onset`, `texture.simultaneity_density`, `texture.vertical_density_proxy`, `texture.chord_count` (per hand + per measure), `texture.chord_ratio`, `texture.octave_chord_ratio` | Correlated with Aspect 3 but kept separate as descriptive bucket. |
| 5 Coordination | `coordination.aligned_hand_onset_count`, `coordination.asynchronous_hand_onset_count`, `coordination.aligned_hand_onset_ratio`, `coordination.subdivision_mismatch_proxy` | `subdivision_mismatch_proxy` combined-view only; flag `proxy` in payload. |
| 6 Notation/reading | `notation.accidental_density`, `notation.accidental_count`/`accidental_ratio` (per hand, per measure), `notation.clef_change_count`, `notation.cross_staff_note_count`, `notation.ledger_line_burden` | Emit `diagnostics` for `cross_staff_note_count` and `ledger_line_burden` as already defined. |
| 7 Expression/control | `expression.articulated_note_ratio` (global+per hand), `expression.articulation_density`, `expression.staccato_note_ratio`/`accent_note_ratio`/`strong_accent_note_ratio`/`tenuto_note_ratio`, `expression.dynamic_marking_count`/`dynamic_marking_rate`/`dynamic_change_count`/`dynamic_range_span`, `expression.wedge_start_count`/`crescendo_start_count`/`diminuendo_start_count`, `expression.staff_specific_dynamic_ratio` | Bucket marked `ordering: none` — traces only, no contribution ranking. |
| 8 Structural/pattern | `metadata.measure_count`, `metadata.note_count` as contextual metadata only | Bucket marked `availability: contextual`, `status: blocked — no pattern extractor yet`. Do not compute aspect-level score. |
| 9 Performance/interpretive | No quantified runtime feature; references proxies: Aspect 7 descriptors + `metadata.tempo_change_count` + `expression.dynamic_range_span` | Bucket marked `caveated / partially observable`. List 5 blocked Yan candidates (`pressing_velocity_entropy`, `pressing_velocity_variability`, `melodic_complexity`, `melodic_originality`, `degree_of_melodiousness`) as `blocked`. Require disclaimer in any UI. |

Profile contract:
- `schema_version: difficulty_aspects.v1` (distinct from `difficulty_overview.v1`).
- One bucket per aspect with `aspect_id`, `label`, `status` (`ready`/`partial`/`blocked`/`caveated`), `subfeatures: [{feature_id, value, units, scope, diagnostics}]`, and `availability`.
- Equal descriptive treatment within each bucket; **no cross-aspect weights** and no composite score.
- `metadata.*` stays contextual, not a difficulty rank.

## 4. True extractor gaps

### 4a. Aspect 8 — Structural/pattern demand (largest gap)

No runtime pattern extractor exists. Only length/count proxies exist.

Future extractors (all score-derived, need new code + operational definitions):
- Repetition / recurrence rate (exact/transposed).
- N-gram / motivic reuse and sequence regularity.
- Formal-boundary complexity (section counts/irregularity; `key_change_count`/`meter_change_count` exist but are not a form model).
- Harmonic / pitch-class and chord-transition predictability.
- Length-normalized novelty (new material per quarter).
- Structural pacing (re-scope Yan `playing_speed_variation` as pacing, not just tempo variation).

Gate: needs clear definition of "reduces vs increases difficulty" for repetition before any ranking; intended as descriptive first.

### 4b. Aspect 9 — Performance/interpretive demand (intentionally blocked)

Five Yan lane candidates are `blocked` per `yan2023_feature_inventory.md:118`:
- `pressing_velocity_entropy`, `pressing_velocity_variability` — likely require performance/MIDI.
- `melodic_complexity`, `melodic_originality`, `degree_of_melodiousness` (MC family) — formulas not yet reconstructed.

Additional gaps: timing micro-variation, voicing/balance, pedal realization, plus all learner-dependent moderators (hand size, experience, practice strategy). No score-only quantification should be promoted here.

### 4c. Notation / expression — available but not yet safe to score

Already extracted and must stay unranked until a rule is validated:
- `notation.cross_staff_note_count` — explicit hand/staff conflicts only (ScoreIR limitation).
- `notation.ledger_line_burden` — assumes standard piano clefs when `ScoreIR.clefs` absent.
- `notation.accidental_density`/`accidental_ratio` — does not model reading familiarity.
- All `expression.*` (articulation shares, dynamics, wedges, `dynamic_range_span` ordinals) — more markings ≠ uniformly harder; coarse ordinal scale. Keep as `partial`/`ready`-as-traces, not ranked factors. `dotted_note_rate` remains `proxyable` due to counting-convention ambiguity.

## 5. Boundary note

- **`difficulty_aspects.v1` is the primary grouped profile.** It groups existing descriptors by the 9 aspects with subfeature traces, as proposed in section 3. It carries no cross-aspect weights and must label Aspect 8 as `blocked` and Aspect 9 as `caveated`.
- **`difficulty_overview.v1` remains the stable 5-factor compatibility/timeline profile.** Authority: `src/piano_difficulty/features/registry.py:27` (`rhythm.attack_density`, `leaps.max_melodic_leap`, `pitch_geometry.max_simultaneity_span`, `coordination.subdivision_mismatch_proxy`, `notation.accidental_density`). Weights stay descriptive equal weights, within-piece ranking only.
- **Yan candidates inform coverage but are not automatically promoted.** Per `yan2023_feature_plan.md:121` and the inventory's `proxyable`/`blocked` statuses, all Yan features stay in `tests/harness/yan2023/` behind the harness boundary. Promotion requires Pass 3 reference comparison and Pass 5 decision — not this docs step.

## 6. Open questions

- Whether downstream consumers should read `difficulty_aspects.v1` directly or receive the same grouping through `gradus.practice_payload.v1`.
- Exact bucket payload shape: per-piece scalars vs per-window/per-measure series (reuse existing `FeatureRecord` contract per `core_feature_registry.md:89`).
- Minimal-set size: whether to emit all per-measure flags (e.g., `rhythm.polyrhythm_flag`, `leaps.timed_difficult_displacement_count`) or only aggregated ratios in the first cut.
- No weighting or validation questions are answered here by design.
