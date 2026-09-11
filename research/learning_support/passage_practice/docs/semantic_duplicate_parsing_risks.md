# S0.4 — Duplicate-parsing risks

Status: risk list only. No parser changes (per task limit); no runtime changes.

Sources inspected:

- `research/piano_difficulty/src/piano_difficulty/normalize/converters.py` —
  `build_score_ir`, `_parse_document`/`_parse_part`, `_parse_written_note`,
  `_duration_from_child`/`_note_duration`/`_time_modification`,
  `_tie_flags`/`_merge_tie_type`, `_collapse_ties_with_diagnostics`
  (`unmatched_tie_stop`, `overlapping_tie_start`, `unclosed_tie`),
  `_logical_from_chain`, `_assign_staff_hands` (`unknown_staff_hand`),
  `_build_onset_groups`, `_normalize_note_context`, `_select_part`,
  `_update_attributes`, `_parse_clefs`, `_parse_direction`, `_articulations`.
- `research/piano_difficulty/src/piano_difficulty/normalize/schema.py` —
  `MeasureIR`, `WrittenNoteIR`, `RestEventIR`, `LogicalNoteIR`,
  `DirectionIR`, `ClefIR`, `OnsetGroupIR`, `ScoreIR`, `DiagnosticIR`.
- `research/learning_support/passage_practice/src/passage_practice/models/source.py` —
  `SourceRef`/`SourceKind` resolver (existing correct-consumption pattern).
- `research/learning_support/passage_practice/src/passage_practice/passages/selection.py` —
  `select_passage` (half-open selection, sustaining boundary context,
  inherited `PassageContext`).
- `research/learning_support/passage_practice/src/passage_practice/observations/__init__.py` —
  LS-06 pitch transitions (existing correct-consumption pattern: resolves
  logical-note refs, never touches XML).
- Plan §Layer 3 view families (`attack_stream`, `written_stream`,
  `hand_stream`, `voice_stream`, `onset_slices`, `rhythm_grid`,
  `texture_grid`, `harmony_view`, `salience_view`, `role_stream`).

## Rule

Semantic views, observations, and detectors consume `ScoreIR` collections
(and, inside a passage, `SourceRef`-resolved events plus passage views).
Only `research/piano_difficulty/io/` + `normalize/` may read MusicXML
elements. Any semantic helper that opens XML, recomputes a normalized field,
or mints its own event identity is a duplicate parser even if its output
"looks the same" on one fixture — it will drift on ties, tuplets, part
selection, cross-staff notation, or enharmonics, and it silently forks
provenance from the difficulty features (S0.2), which read the same `ScoreIR`.

Deriving new projections *from* `ScoreIR`/passage data (the planned S2
views) is the job, not the risk. The risks below are specifically about
reaching past `ScoreIR` or recomputing what it already normalizes.

## Risk list

- [ ] **R1 — Quarter durations from `divisions` + `time-modification`.**
  Tempting when a rhythm detector wants "the written length" of a note.
  Correct source: `WrittenNoteIR.duration` / `LogicalNoteIR.duration`
  (`Fraction`, owner: `piano_difficulty/normalize`). The parser already folds
  per-measure `divisions`, dot multipliers, and tuplet `actual/normal`
  (`_duration_from_child`, `_note_duration`, `_time_modification`) and keeps
  the raw `tuplet_actual/tuplet_normal` flags for explicit unsupported-case
  diagnostics. Recomputing from XML reintroduces tuplet-ratio and
  divisions-change bugs and float time. Future consumer: `rhythm_grid` view
  (S2.6); unsupported-tuplet policy belongs there, reading the flags, not
  the XML.
- [ ] **R2 — Tie chains and sounding durations.** Tempting when an
  attack-stream or salience view wants "notes as heard". Correct source:
  `LogicalNoteIR` (`onset`, summed `duration`, `source_note_ids`) plus the
  collapse diagnostics `unmatched_tie_stop` / `overlapping_tie_start` /
  `unclosed_tie` (owner: `piano_difficulty/normalize`; passage-side consumer:
  `attack_stream` view, S2.4, owned by `passage_practice/views`). The chain
  key is `(pitch_midi, staff, voice)` in onset order; re-collapsing from
  `<tie>` elements risks double attacks, cross-voice chain merges, and
  dropped diagnostics. Sustaining-across-boundary handling additionally
  belongs to `select_passage` (boundary context), never to a re-parse.
- [ ] **R3 — Simultaneity / onset grouping.** Tempting when a texture or
  chord detector wants "notes that sound together". Correct source:
  `OnsetGroupIR` (`onset`, `hand`, `note_ids`) for score-wide groups and the
  planned `onset_slices` / `texture_grid` passage views for in-passage
  slices (owners: `piano_difficulty/normalize` + `analysis/grouping` for the
  facts; `passage_practice/views` for the slices). Regrouping from raw
  onsets risks chord-vs-arpeggiation drift against the difficulty texture
  features (S0.2), which read the same groups.
- [ ] **R4 — Hand from staff numbers.** Tempting when a hand-scoped
  observation wants a quick `staff == 1 → right` rule. Correct source:
  `hand` + `hand_confidence` on every note/rest event, assigned once by
  `_assign_staff_hands` with the `unknown_staff_hand` diagnostic for
  non-piano staves (owner: `piano_difficulty/normalize`; passage-side
  consumer: `hand_stream` view, S2, owned by `passage_practice/views`).
  Re-inferring inline (as distinct from *consuming* the field with an
  explicit `INFERENCE` basis + diagnostic, the LS-06 pattern) forks hand
  identity from every difficulty hand-scoped feature and mishandles
  cross-staff notation. Staff, encoded voice, inferred hand, and inferred
  role stay four separate concepts end to end.
- [ ] **R5 — Musical role from encoded voice.** Tempting when a melody
  detector sees `voice == "1"` and treats it as the tune. Correct source
  for the *fact*: the encoded `voice` field via the planned `voice_stream`
  view (owners: `piano_difficulty/normalize` for the fact;
  `passage_practice/views` for the stream). Role (melody/bass/accompaniment)
  is a later *inference* (`role_stream`, `salience_view`, S2.8/S3.2) that
  must carry method, evidence, confidence, and diagnostics — never a re-read
  of `<voice>` elements with role semantics baked in. Two encoded voices do
  not imply two musical roles (S0.1 non-claim).
- [ ] **R6 — Pitch spelling, MIDI numbers, and accidentals.** Tempting when
  a contour/interval observation wants `step + alter + octave → MIDI`.
  Correct source: `pitch_midi`, `pitch_step`, `pitch_octave`, `alter`,
  `accidental` as already normalized (`_normalize_note_context`, `_parse_written_note`;
  owner: `piano_difficulty/normalize`). Key-signature interaction, courtesy
  accidentals, and enharmonic spelling live in the parser; recomputing MIDI
  in semantic code risks off-by-semitone drift that would silently disagree
  with LS-06 transition values and every pitch feature.
- [ ] **R7 — Measure boundaries and key/meter/tempo context.** Tempting
  when a phrase or harmony heuristic wants "the time signature in bar 12".
  Correct source: `MeasureIR` (`start`/`end`, `time_signature`,
  `time_beats`/`time_beat_type`, `key_fifths`/`key_mode`/`key_signature`,
  `tempo_bpm`/`tempo_text`) plus passage-side `PassageContext` inheritance
  at the passage start (owners: `piano_difficulty/normalize` for the facts;
  `passage_practice/passages` for inheritance). Re-deriving measure timing
  from `<attributes>` divisions risks off-by-divisions errors; mid-passage
  changes are future-view work (`harmony_view`, S6), not re-parse work.
- [ ] **R8 — Clefs, directions, dynamics, articulations.** Tempting when a
  readability or salience observation wants "the dynamic here" or "the
  clef". Correct source: `ClefIR` (`sign`, `line`, `staff`,
  `measure_index`), `DirectionIR` (`kind`, `value`, `start`, `end`,
  `staff`), `WrittenNoteIR.articulations` (tuple), `MeasureIR.tempo_*`
  (owner: `piano_difficulty/normalize`; passage-side consumer:
  `PassageContext.clefs`/`direction_refs`, owners `passage_practice/passages`).
  Re-scanning `<direction>`/`<notations>` elements risks dropping kinds
  (dynamics vs wedge vs tempo vs pedal), misattributing staff, and inventing
  dynamic trajectories the parser deliberately leaves as discrete marks.
  Dynamic *interpretation* (e.g. salience weighting) belongs in observations
  with missingness kept explicit, never in a shadow parser.
- [ ] **R9 — Event identity and ordering.** Tempting when a new view wants
  stable keys and reaches for XPath, document position, or pitch+onset
  tuples. Correct source: `note_id` / `rest_id` / `direction_id` /
  `clef_id` with `xml_order` / `measure_staff_order` for deterministic
  ordering, referenced passage-side through `SourceRef(id, kind)` and
  `resolve_ref` (owners: `piano_difficulty/normalize` for ID minting;
  `passage_practice/models` for references). Parallel ID schemes break
  provenance joins with difficulty evidence and with `region_evidence`
  note-ID lists from CIPI runs (S0.3). Generated-exercise IDs, when they
  arrive, belong to the generated artifact and never replace canonical IDs.
- [ ] **R10 — Rests and "silence".** Tempting when a phrase-boundary
  heuristic computes gaps from note end-times. Correct source:
  `RestEventIR` (`rest_id`, `onset`, `duration`, `staff`, `voice`) for
  notated rests; gap-vs-rest semantics belong to the future
  phrase-boundary heuristic with explicit policy (owners:
  `piano_difficulty/normalize` for the facts; `passage_practice/semantics`
  for the heuristic). A computed inter-onset gap is not a notated rest;
  conflating them corrupts both the planned S2.12 readability observations
  and any rest-based phrase evidence.
- [ ] **R11 — Grace notes, chord tones, and tuplet flags.** Tempting to
  treat every `<note>` as a full attack. Correct source: `is_grace`,
  `is_chord_continuation`, `duration_type`, `tuplet_actual`/`tuplet_normal`
  (owner: `piano_difficulty/normalize`). Counting grace notes as
  full-duration attacks, or expanding chord continuations into sequential
  onsets, inflates every density measure and breaks attack ordering against
  `LogicalNoteIR`. Tuplet handling beyond the supported subset must be an
  explicit diagnostic in the consuming view, not a silent re-read.
- [ ] **R12 — Part selection (which piano part).** Tempting when a corpus
  piece has several parts and a semantic loader picks "the piano one".
  Correct source: the loader's part resolution (`_select_part`,
  `_part_names`; owner: `piano_difficulty/io` + `normalize`). A second,
  independent part picker in semantic code risks analyzing a different
  instrument than the difficulty pipeline analyzed for the same file,
  invalidating every cross-area comparison (S0.3 handoff included).

## What S0.4 does not claim

- No view, observation, or detector is specified here; S2 owns view
  construction on top of these sources.
- No upstream promotion list is proposed (that is S2.2 / S-Q004); where a
  needed projection does not exist yet (e.g. `written_stream`,
  `rhythm_grid`), the gap is recorded in S0.1/S0.5, not filled by re-parsing.
- No parser defect is alleged; diagnostics quoted above are the parser's own
  codes, and the limit (no parser changes) was honored — this file is the
  only change.

## Next task

S0.4 completes the four S0 inventories. **S0.5 (readiness matrix)** is now
unblocked: combine S0.1–S0.4 with columns for source, available now, needed
for phase, owner, test fixture, and blocking decision (documentation only).
S1.1 (S-Q001 decision) remains behind S0.5.
