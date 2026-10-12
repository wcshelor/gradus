# PracticeChunk Design

## Purpose

`PracticeChunk` is the general hierarchical grouping model for score understanding. It answers:

> “How would a pianist mentally divide this passage in order to understand and practice it?”

not merely:

> “Which special feature did we detect here?”

Every non-empty selected passage must yield at least one musically coherent `PracticeChunk` — something a pianist could notice, name, isolate, subdivide, and practice. Detected difficulty features (octave doubling, leaps, rolled chords, dynamics, phrase marks, scalar runs) contribute traits, boundaries, subchunks, context, and practice affordances *inside* that hierarchy, rather than defining the hierarchy itself.

## Core Concepts

### ScoreEvent vs DetectedFeature/MusicalObject vs PracticeChunk vs PracticeTransform

- **ScoreEvent** — One normalized row per note/rest with provenance (pitch, onset/end, hand/staff, measure, dynamics hint, articulation). Ground truth for all higher layers. Never inferred.
- **DerivedToken / Gesture** — Low-level derived facts (e.g., `melodic_interval`, `chord_shape`, `leap`, `arpeggio`). Evidence providers.
- **MusicalObject** — Typed, catalog-level grouping of tokens/gestures into musically named objects (`ascending_scalar_run`, `octave_doubled_melody`, `single_hand_multi_voice_texture`, etc.). Conservative, catalog-constrained, difficulty-adjacent.
- **PracticeChunk** — The pianist-facing hierarchical unit. Musically coherent, overlap allowed, subdivisible, with traits and affordances. Built from *all* available evidence, not only salient difficulty objects. Always produced for a non-empty passage (with caveats when inferred).
- **PracticeTransform** (future / out-of-scope) — An operation applied to a chunk for practice (e.g., “block chords”, “hands separate”). Chunks declare *affordances*; transforms enact them.

```
ScoreEvent → DerivedToken/Gesture → MusicalObject → PracticeChunk → PracticeTransform
   ground        evidence           named object      pianist unit        operation
```

### Primary vs Context Evidence

- **primary_event_ids** — Notes that define the chunk’s musical identity. Highlighted strongly in review artifacts (blue).
- **context_event_ids** — Notes that belong to the same temporal window but are not the chunk’s focus (e.g., inner voices inside an octave-doubled melody, accompaniment around a melody). Shown softly (grey). Enables `ghost_accompaniment`, `layer_back`, `add_context` affordances.

A passage with overlapping hands or layered texture will produce overlapping chunks where the same events are primary in one chunk and context in another — this is intentional.

### Traits vs Subchunks

- **traits** — Flat, searchable tags describing the chunk (`scalar`, `ascending`, `rolled_chords`, `chord_sequence`, `decrescendo`, `octave_shift`, `mixed_with_inner_voices`). Traits drive affordance selection and UI filtering.
- **subchunks (child_chunk_ids)** — Structural decomposition. A parent chunk (e.g., `arpeggio_sweep`) declares children (`ascent`, `descent`, `turn`, `landing`) that partition its span. Children have `parent_chunk_id` pointing back and carry payload explaining boundary reasons (contour reset, leap drop, repeated interval pattern, phrase mark, etc.).

Traits describe *what* it is; subchunks describe *how* to split it for practice.

### Parent / Child Hierarchy

- Hierarchical grouping via `child_chunk_ids` / `parent_chunk_id`.
- Phrase parents group nearby same-hand chunks when gap ≤ 1.5 quarters and no rest separates them; span ≤ 8 quarters.
- Coordination parents group overlapping left/right chunks when an `onset_alignment` token exists.
- Arpeggio/scalar parents own contour-segment children.
- Overlap is allowed at every level (no single-winner constraint). A chord can be primary in a `chord_shape` chunk and context in an `octave_doubled_melody` chunk.

### Overlap Allowed

Chunks are not a segmentation. They are overlapping, selectable lenses over the same notes. Review artifacts allow click-to-highlight per chunk; the same event may be primary in one chunk and context or unhighlighted in another.

### Why Every Passage Should Produce at Least One Chunk

A selected passage is, by definition, musically interesting enough to inspect (flagged hotspot or user selection). Returning zero chunks signals missing general grouping machinery, not an uninteresting passage.

Fallback grouping uses general evidence that is always available:

- measure span
- hand / staff streams
- rhythmic continuity (onset density, duration pattern)
- repeated texture / pattern repetition tokens
- chordal continuity (`harmonic_simultaneity` / `chord_shape`)
- simultaneities / onset alignments
- phrase marks (slur / phrase)
- dynamics and hairpins
- arpeggiation / rolled-chord marks
- register / pitch-band gap

If no salient detector fires, a conservative fallback is emitted (`passage_chunk`, `chordal_texture_chunk`, `hand_stream_chunk`, `phrase_chunk`) with trait `fallback` / `inferred` and caveat `fallback_chunk`. Specific traits (`rolled_chords`, `decrescendo`) are added when evidence supports them; otherwise the label stays generic but musically coherent.

## How Notation Markings Contribute

Markings are treated as evidence that can attach to chunks as traits, boundary priors, context, practice affordances, and payload metadata — never as hard-coded detectors.

| Marking | Extraction | Chunk attachment |
|---|---|---|
| **Dynamics** (`p`, `pp`, `mp`, `mf`, `f`, `ff`) | `DirectionIR.kind == "dynamics"` parsed from `<dynamics>` | Payload `dynamics`, trait `has_dynamics`, affordance `shape_dynamics` when span shows shape |
| **Hairpins / crescendo / decrescendo spans** | `DirectionIR.kind == "wedge"` with `value` `crescendo`/`diminuendo`/`crescendo_stop`/`diminuendo_stop` → hairpin span token | Trait `crescendo` / `decrescendo` / `dynamic_shape`, payload `hairpin_span`, affordance `shape_dynamics` |
| **Octave shift** (`8va`, `8vb`, `15ma`) | `DirectionIR.kind == "octave_shift"` from `<octave-shift type="up|down" size="8">` | Trait `octave_shift`, payload `octave_shift`, caveat about sounding vs written pitch |
| **Phrase marks** (distinct from slurs/ties) | `<slur>` in `<notations>` distinguished where musicxml encodes type; treated as boundary prior for `phrase_chunk` | Boundary prior, payload `phrase_mark`, prefer `phrase_chunk` grouping |
| **Arpeggiation / rolled chord** | `<arpeggiate>` in `<notations>` on `WrittenNoteIR` | Trait `rolled_chord` / `rolled_chords`, affordance `block_then_roll` / `roll_evenly` |

If full MusicXML extraction is unavailable, the system documents the unsupported status rather than silently ignoring it. The normalization layer exposes a thin representation for markings already accessible from parsed data; full extraction is incremental.

### Guidance: Avoid Patchwork

> Use passage observations to improve general chunking machinery, not to add one-off fixes.

- Do not branch on measure numbers or piece titles.
- Do not add a detector that fires only on a single passage’s note pattern.
- Prefer generic boundary cues (contour reset, leap drop after ascent, repeated interval / pitch-class pattern, rhythmic grouping, register reset, phrase mark) that explain *why* a boundary was chosen via `payload`.
- Gate any new heuristic on evidence density, confidence, and caveats; label `fallback` / `inferred` when conservative.

## Examples

### Rolled chordal phrase with decrescendo (e.g., mm. 25–26)

- Evidence: repeated chordal simultaneities across onsets, `<arpeggiate>` marks if present, wedge `diminuendo` across the span.
- Chunk: `chordal_texture_chunk` / `phrase_chunk` covering mm. 25–26, `hand` maybe `both` if hands overlap.
- Traits: `rolled_chords`, `chord_sequence`, `hand_overlap` (if both-hand sonority), `decrescendo` / `dynamic_shape`.
- Subchunks: individual chord onsets (`chord_shape` / `landing` per onset) if useful.
- Affordances: `block_chords`, `roll_evenly`, `shape_dynamics`, `isolate_hands`, `add_context`.
- Payload notes `hairpin_span`, `chord_count`, `rolling` and caveats `inferred_roll_if_no_marking`.

### LH arpeggiating figure split into repeated ascending cells (e.g., mm. 27–28)

- Evidence: long LH run with contour ascent → large drop → ascent → drop (leap reset), repeated interval pattern (e.g., `7,5,4` or thirds stack), high onset density.
- Chunk: parent `arpeggio_sweep` / `run` covering whole figure.
- Subchunks: repeated `ascent` cells (3–4 notes each), `turn` at peak, `landing` on final chord, `reset` on downward leap.
- Traits on parent: `arpeggiated`, `repeated_cells`, `register_reset`.
- Payload per child: `segment_intervals`, `boundary_reason` (`contour_reset`, `leap_drop`, `repeated_pattern`, `phrase_mark`), `cell_index`.

### Octave-doubled melody inside chordal context

- Evidence: `octave_doubled_melody` object where outer octave spans 12 semitones but inner tones exist at same onsets.
- Chunk: `octave_doubled_melody` with `primary_event_ids` = outer octaves, `context_event_ids` = inner voices, trait `mixed_with_inner_voices`.
- Affordances: `skeletonize`, `ghost_accompaniment`, `layer_back`.

### Same-hand layered texture (sustained low + moving upper)

- Evidence: low pitch band sustained, upper band moving, gap ≥ 12 semitones.
- Chunk: `layered_texture` parent with two `layer` children (`low`, `high`).
- Traits: `layered`, `same_hand_multi_voice`; payload `pitch_band_gap_semitones`.

## Design Direction

- Keep chunk formation deterministic and evidence-driven.
- Preserve provenance: every chunk cites `source_object_ids` / `source_feature_refs` and `evidence_event_ids`.
- Be conservative and caveated when inferred: `caveats` like `fallback_chunk`, `inferred_roll_if_no_marking`, `no_explicit_marking`, `heuristic_only`.
- Prefer small, explicit experiments over fixing the thesis to one generation method or learner workflow.
- Document what remains unsupported (e.g., full MusicXML wedge span recovery across part breaks, distinct phrase vs slur encoding) with clear “no-data” messages in artifacts and code comments.

## References

- `src/piano_difficulty/semantic_tokens/models.py` — `PracticeChunk`, `CHUNK_KINDS`, `PRACTICE_AFFORDANCES`.
- `src/piano_difficulty/semantic_tokens/practice_chunks.py` — builder with hierarchy and fallback layer.
- `src/piano_difficulty/semantic_tokens/notation_markings.py` — thin marking extraction → chunk evidence.
- `src/piano_difficulty/normalize/schema.py` — `ScoreIR`, `DirectionIR`, `WrittenNoteIR` extended for markings.
- `docs/local_passage_semantics.md` — upstream semantic layers feeding chunks.
- `tests/scripts/generate_practice_chunk_review.py` — visual QA displaying traits, markings, hierarchy, primary/context, and notation snippets.
