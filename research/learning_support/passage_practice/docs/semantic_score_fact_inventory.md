# S0.1 — Score facts currently exposed to passage practice

Status: inventory only. No runtime changes (per `semantic_music_extraction_tasks.md` S0.1 limit).

Sources inspected (2026-09-09):

- `research/piano_difficulty/src/piano_difficulty/normalize/schema.py` — `ScoreIR` and event IRs (owner: piano-difficulty).
- `research/learning_support/passage_practice/src/passage_practice/models/source.py` — `SourceRef`, `SourceKind`, resolver (D-011).
- `research/learning_support/passage_practice/src/passage_practice/models/time.py` — `ScorePosition`, `ScoreInterval`, exact fractions.
- `research/learning_support/passage_practice/src/passage_practice/models/passage.py` — `Passage`, `ViewType`, `PassagePurpose`.
- `research/learning_support/passage_practice/src/passage_practice/passages/selection.py` — `select_passage`, `PassageContext`, boundary policy (D-014 proposal).
- `research/learning_support/passage_practice/src/passage_practice/passages/investigate.py` — LS-05 manual entry, `PassageInvestigation` envelope (D-013).
- `research/learning_support/passage_practice/src/passage_practice/models/investigation.py` — `PassageInvestigation`, `DifficultyEvidence` (LS-03a).
- `research/learning_support/passage_practice/src/passage_practice/models/observations.py` + `observations/__init__.py` — LS-06 pitch-transition observations only.
- `research/learning_support/passage_practice/src/passage_practice/models/diagnostics.py` — `Diagnostic`.
- `research/learning_support/passage_practice/tests/unit/test_selection.py`, `test_observations.py` — implemented selection/observation behavior.

Boundary reminder: `ScoreIR`, loading, generic descriptors, windows, and
hotspots belong to `research/piano_difficulty/`. Passage selection, views,
observations, and later semantic hypotheses belong to passage practice.
Passage practice depends on `ScoreIR` at selection/observation time; it does
not re-parse MusicXML and `piano_difficulty` never imports passage practice
(D-012).

## Fact inventory

| Fact family (S0.1 request) | Available to passage practice now? | Canonical source | How passage practice accesses it | Limitation / gap for semantic phases |
|---|---|---|---|---|
| Event IDs | Yes, subset | `WrittenNoteIR.note_id` (`@id` or `n{xml_order}`), `LogicalNoteIR.note_id` (first written id + `source_note_ids`), `RestEventIR.rest_id` (`r{xml_order}`), `DirectionIR.direction_id`, `ClefIR.clef_id`, `MeasureIR.measure_index` | `SourceRef(id, kind)` with `SourceKind` in `{written_note, logical_note, rest, measure, direction, clef}`; `resolve_ref()` pure lookup; `refs_for_score()` inventory; `Passage.event_refs` are `LOGICAL_NOTE` only; `SelectedPassage.boundary_context` are `WRITTEN_NOTE` only | `ONSET_GROUP` refs explicitly unresolvable (`resolve_ref` returns `None`) until derived views define stable grouping; rests are declared omissions (`omissions=("rests",)`), not selected attacks; generated-exercise IDs do not exist yet |
| Timing (exact) | Yes | `onset: Fraction`, `duration: Fraction` on written/logical/rest; `MeasureIR.start/end: Fraction`; `DirectionIR.start/end` | `ScorePosition.quarters: Fraction` + `offset_in_measure: Fraction`; `ScoreInterval` strict half-open `[start, end)` with `start.quarters < end.quarters`; `select_passage` selects `start <= onset < end`; serialization via `{numerator, denominator}`, floats rejected | Tempo is `float` (`tempo_bpm`) at presentation/model boundary only; no beat grid, subdivision, or `rhythm_grid` view yet (planned S2.6); simultaneous pairs get `region=None` + `simultaneous_pair` diagnostic, never padded |
| Staff (encoded) | Yes | `WrittenNoteIR.staff`, `LogicalNoteIR.staff`, `RestEventIR.staff` (`int`, 1-indexed, or `None`) | `ScorePosition.staff`; `Observation.staff` set only when both transition endpoints share staff, else `None`; staff never conflated with hand | Staff-scoped views (`hand_stream`, `voice_stream`) exist as `ViewType` enum values only; no view builder consumes staff grouping yet beyond observation filtering |
| Encoded voice | Yes | `WrittenNoteIR.voice`, `LogicalNoteIR.voice`, `RestEventIR.voice` (`str`, or `None`) | `ScorePosition.voice`; `Observation.voice` set only when pair agrees; two-voice fixture (`selection_two_voices.musicxml`) proves `{"1","2"}` survives selection | `ViewType.VOICE_STREAM` is contract-only; no `voice_stream` builder; voice is kept separate from staff/hand/role per architecture rule, but no semantic `role_stream` exists yet |
| Inferred hand | Partial (low-confidence inference) | `hand: str \| None` + `hand_confidence` on written/logical/rest (staff-inferred upstream) | `ScorePosition.hand` (`left`/`right`/`None`); `Observation.hand` when pair agrees; hand-scoped `observe_pitch_transitions(hand=...)` marks `basis=INFERENCE` + `hand_scoped_inference` diagnostic with kept/excluded/ambiguous counts | Hand is not authoritative: upstream `hand_confidence` is a string flag, not consumed by passage practice; no `hand_stream` builder yet; staff/hand/role separation is contractual, not yet exercised by a salience or rhythm-layer detector |
| Tie | Partial (collapsed, not modeled as chain) | `WrittenNoteIR.tie_start/tie_stop`; `LogicalNoteIR.source_note_ids`, `duration` (tie-collapsed) | Selection operates on tie-collapsed `logical_notes`; written notes sustaining across either boundary become `boundary_context` (written refs), never new attacks; tie fixture (`selection_ties.musicxml`) asserts `{"n4","n5"} -> one logical at `4/1` | No tie-chain object in `Passage`; provenance from logical back to written requires second lookup via `source_note_ids`; tie-over-boundary and tie-over-beat rhythm behavior has no dedicated view/observation yet (needed by S2.4–S2.6) |
| Articulation | Upstream only, not projected | `WrittenNoteIR.articulations: tuple[str,...]`, `accidental`, `is_grace`, `duration_type`, `is_chord_continuation` | Reachable only by resolving `SourceRef` back to `ScoreIR` and reading the written note; `Passage`/`Observation` carry no articulation fields; no observation consumes it | `LogicalNoteIR` drops articulations entirely; semantic `salience_view` (S2.8) and notation-readability observations (S2.12) will need an explicit `written_stream` projection (planned S2.5) instead of silent best-effort reads |
| Dynamic | Upstream only, context-thin | `DirectionIR.kind/value/start/end/staff/measure_index`; `MeasureIR.tempo_text/tempo_bpm` | `PassageContext.direction_refs` = directions active at passage `start` only (`_active_directions`); `tempo_bpm/tempo_text` inherited at start; `DifficultyEvidence` may reference dynamics only via validated external evidence refs | No per-event or in-passage dynamic trajectory; dynamics inside `(start, end]` but not active at `start` are invisible to `PassageContext`; no observation family for dynamics/articulation yet |
| Measure identity | Yes | `MeasureIR.measure_index` (stable 0-based), `measure_number` (printed), `start/end` | `ScorePosition.measure_index/measure_number/offset_in_measure`; `PassageContext.measure_index/measure_number`; `locate_measure_by_number` with `unknown_measure` / `ambiguous_measure` diagnostics; `whole_piece_range()` covers full measure span | Printed numbers are not unique keys (ambiguity is explicit error); `offset_in_measure = quarters - measure.start` only; no measure-scoped harmonic or phrase grouping yet |
| Key | Context-thin | `MeasureIR.key_fifths/key_mode/key_signature` | `PassageContext.key_fifths/key_mode` inherited from the measure active at `start` | No key-change tracking inside the passage; no local-key candidate heuristic (planned S6.2); key is context, not an observation |
| Meter | Context-thin | `MeasureIR.time_signature/time_beats/time_beat_type/divisions` | `PassageContext.time_signature` inherited at `start` | No meter-change tracking, no beat-position or subdivision relation, no `rhythm_grid` (planned S2.6); tuplets recorded as `tuplet_actual/tuplet_normal` on written notes but have no passage-level policy yet beyond the planned "simple triplet → explicit diagnostic" fixture row |
| Clef | Context-thin | `ClefIR.clef_id/sign/line/staff/measure_index` | `SourceKind.CLEF` resolvable; `PassageContext.clefs: tuple[ClefState,...]` = clefs with `measure_index <= start measure`; `ClefState{staff, sign, line}` round-trips | No clef-change-inside-passage observation; ledger-line burden, clef-change presence, and other readability proxies (planned S2.12) do not exist yet |
| Pitch | Yes (direct) | `pitch_midi`, `pitch_step/pitch_octave/alter` on written + logical | LS-06 `pitch_transition` observations: signed `value: int`, `units="semitones"`, ordered `source_refs` (two logical notes), exact `region` when `pos_a < pos_b`; `basis=FACT` unscoped | Only consecutive-attack intervals; no range, contour, leap-frequency, or registral-extreme observations yet (planned S2.9); absolute pitch changes under transposition are not yet covered by a metamorphic test in this area |
| Onset grouping / simultaneity | Minimal | `OnsetGroupIR{onset, hand, note_ids, measure_index}` in `ScoreIR` | Not consumed: `SourceKind.ONSET_GROUP` intentionally unresolvable; `ViewType.ONSET_SLICES` is contract-only; simultaneous transition pairs diagnosed, not grouped | `onset_slices` and `texture_grid` views (planned S2.7) are missing; chord-vs-arpeggiation disambiguation is not yet possible here |
| Notation details (grace, tuplet, chord continuation, accidental) | Upstream only | Written-note flags listed above | Not projected into `Passage`/`View`/`Observation`; accessible only via direct `ScoreIR` reads | Needed by S2.12 notation-readability observations; missing-layout must stay "unavailable, not zero" — no helper enforces that yet |
| Diagnostics / provenance | Yes | `DiagnosticIR` upstream; `Diagnostic{code, severity, context, source_refs}` + `SourceRef` here | Selection: `UnresolvableRegion` reasons `empty_interval/out_of_range/no_measures/unknown_measure/ambiguous_measure/outside_parent` + `empty_selection` info; observations: `unresolvable_attack_ref/non_logical_refs_skipped/hand_scoped_inference/insufficient_attacks/unlocatable_pair/simultaneous_pair`; every inference carries method/version (`exact_region_selection/v1`, `pitch_transition_observation/v1`, `manual_region_selection/v1`) | No semantic diagnostic registry yet (planned S-X1); confidence bands/helpers do not exist yet (planned S1.4–S1.5); learner-feedback and annotation provenance do not exist yet (planned S5/S7) |

## What S0.1 does not claim

- No `SemanticHypothesis` / `SemanticBundle` contracts exist (blocked on S-Q001, task S1.1).
- No `attack_stream` / `written_stream` / `rhythm_grid` / `texture_grid` / `salience_view` builders exist; `ViewType` enum names are contracts only.
- No direct rhythm, texture, notation-readability, harmony, or motor-proxy observations exist beyond pitch transitions.
- No difficulty-feature inventory is attempted here (that is S0.2); no CIPI mapping (S0.3); no duplicate-parsing risk list (S0.4).
- No conclusion is drawn about which facts *should* be promoted from `ScoreIR` (that is S2.2 / S-Q004).

## Next task unblocked

S0.1 alone unblocks nothing downstream. The S0 gate (`S0.5 readiness
matrix`) still requires S0.2 (difficulty feature evidence), S0.3 (CIPI
handoff note), and S0.4 (duplicate-parsing risks) before S1 contracts
(S1.1 decision on S-Q001) can safely proceed.
