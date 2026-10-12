# Local Passage Semantics

## Purpose
The semantic extractor is a local passage inspection tool. Difficulty mapping or user selection provides the passage; this layer explains what the pianist does there.

Selection (from difficulty analysis or user interaction) answers "where"; local semantics answers "what".

## Non-Goals
- No exhaustive whole-piece analysis.
- No first-occurrence claims ("first time in the piece") — requires piece-global tracking not yet implemented.
- No teacher-quality prose or LLM polishing.
- No exercise generation — that is a downstream consumer, not part of the extractor contract.
- No whole-piece difficulty rating or ranking.

## Layers
```
ScoreIR
  -> events (ScoreEvent table, one row per note/rest with provenance)
  -> derived tokens (leap, chord_shape, pattern_repetition, etc.)
  -> gestures (bass_to_chord, melody_with_accompaniment, scalar_run, etc.)
  -> musical objects (catalog IDs: leap_to_chord, broken_chord_accompaniment, etc.)
  -> object components (internal traits: leap_interval, target_chord, interval_path, register_separation, etc.)
  -> instruction units (local, playable action objects with anatomy)
```

Each layer is deterministic and retains `evidence_event_ids`. No object or component may be emitted without evidence.

## Instruction Units
Instruction units are the promoted, reader-facing output of a local inspection.

- **Local:** derived from overlap with the selected report span (e.g., measures 8–11 for a hotspot at 9–10 with context 1).
- **Playable:** describes an action the pianist performs, not an abstract statistic.
- **Action object with anatomy:** each unit has a stable object family (e.g., `leap_to_chord`) plus structured anatomy fields.
- **Capped:** at most 3 per report, ranked by local relevance.
- **Descriptive, not prescriptive:** states what is present ("The left hand moves from a single note into a 2-note chord landing") rather than prescribing practice ("practice as block chord at 50% tempo").

Supporting local objects are grouped and secondary; broad piece-global objects are separated as context.

## Object Anatomy
Minimum fields per core family (omit if not detected; say "not detected yet" rather than invent):

### leap_to_chord
- hand
- source shape if available: single note / chord / unknown
- destination shape: chord
- movement size/direction if available (semitones, direction)
- destination chord note count if available
- destination span if available (semitones)
- time to land or beat relation if available
- evidence / caveats

### scalar_run (ascending/descending)
- hand
- direction (up/down)
- steps / note count
- span (semitones)

### arpeggio / broken-chord (alberti_bass, broken_chord_accompaniment, arpeggiated_accompaniment, wide_broken_chord)
- hand
- pattern / pcs (pitch classes)
- interval path
- span

### chord / voicing (chord_landing, chordal_homophonic_texture, melody_embedded_in_chords)
- hand
- shape: note count, span
- landing beat

### syncopation / rhythm cell (syncopation, repeated_rhythm_cell, rhythm_pattern_break, polyrhythm)
- hand
- texture/rhythm character
- local measures

All anatomy derives from instance-specific components attached via evidence overlap, not from family-wide pooling.

## Component Attachment
Components are attached to a specific object *instance*, not to the object family.

A component belongs to an object instance only if:
- `parent_object_id` matches, **and** at least one of:
  - `evidence_event_ids` intersect,
  - onset span overlaps the object onset span,
  - token/gesture IDs intersect.

This prevents anatomy from mixing components of unrelated instances (e.g., a RH chord voicing title with LH hand data).

## Ranking & Selection
Within a local span, promotion prefers:
1. Local span overlap (higher overlap ratio first)
2. Actionable object families
3. Tighter object span (smaller width)
4. Confidence
5. Diversity by family + hand

Actionable families (promoted as instruction units):
`leap_to_chord`, `chord_landing`, `hand_shift`, `hand_expansion_contraction`,
`ascending_scalar_run`, `descending_scalar_run`, `broken_chord_accompaniment`,
`arpeggiated_accompaniment`, `wide_broken_chord`, `alberti_bass`,
`melody_with_accompaniment`, `melody_embedded_in_chords`,
`melody_voicing_over_accompaniment`, `syncopation`, `repeated_rhythm_cell`,
`rhythm_pattern_break`, `polyrhythm`.

Broad/global objects (e.g., `two_voice_counterpoint`, `pedal_point_accompaniment`,
`dynamic_swell_across_phrase`, `left_hand_stride_like_motion`) are excluded
from promotion and appear only as broad context with compressed measure spans.

## Local vs Broad Context
- **Local:** objects whose measure span fits inside or overlaps tightly with the report span; grouped as supporting objects with compact summary (top 8 groups visible, full rows in `<details>`).
- **Broad:** objects whose span exceeds the local span by >2 measures or ≥8 measures, or whose family is known to be piece-global; shown separately with compressed span notation (e.g., `1-72 (72 measures)` or `1,3,9,26,29,34-38,...`).

Measure compression: `1,2,3,4,5` → `1-5`; `1..72` contiguous → `1-72 (72 measures)`; mixed → `1,3,9,26,29,34-38,51,53-54,57-59,67,69-71`; non-numeric labels preserved.

## Rendering Contract
Markdown is readable first; raw JSON is inside `<details>` and truncated for display (>12k chars). Full machine-readable payload is written to a sibling `.json` file when generated via harness scripts. Both harnesses share the same builder:

- `src/piano_difficulty/semantic_tokens/local_inspection.py` — `build_local_inspection()` + `render_markdown()`
- `tests/scripts/generate_local_inspection.py` — single passage wrapper (writes `.md` + `.json` siblings)
- `tests/scripts/generate_semantic_breakdown_reports.py` — multi-span wrapper with `--context-measures` (default 1), merging overlapping/adjacent expanded spans, and `--no-merge-spans` opt-out; each span delegates to `build_local_inspection`.

Flagged source measures and expanded report span are both recorded in every report.

## Consistency Diagnostics

Surface rendering must keep note names, chord counts, spans, intervals, beats, and durations tied to the same evidence group. The local inspection JSON includes consistency warnings when rendered fields appear to mix components from different object instances or when written and logical duration disagree.

Diagnostics are produced by `diagnose_instruction_unit_consistency()` / `surface_consistency_checks()` in `local_inspection.py`. Each instruction unit records `selected_surface_fields` with provenance (`event_ids`, `component_id`, `measure_numbers`) so tests can prove that landing chord, count, and span came from the same event group or component family.

Warning classes:

- `component_instance_mismatch` — selected components for one unit come from different likely object instances (no shared evidence/token/gesture; attached by onset overlap only; hand conflicts; measure outside object span).
- `pitch_count_mismatch` — rendered chord name implies N pitches but `chord_note_count` says M (e.g., `Db3-Gb3-Bb3-Db4` implies 4 but count=2).
- `pitch_span_mismatch` — rendered chord pitches imply a span different from `target_span_semitones` (e.g., `Db3-Gb3-Bb3-Db4` spans 12, not 4).
- `interval_direction_mismatch` — source→destination pitch movement contradicts interval direction/sign (compares source pitch to lowest and median destination pitch; method reported as `lowest_and_median_both_disagree`).
- `duration_representation_mismatch` — `duration_type` says eighth but logical/tie-merged duration is 7/2 quarters; written and logical durations disagree (severity `info`, not fatal; renderer should not present as a single simple duration without caveat).

Markdown shows a compact per-unit line `Consistency: N warning(s)` with a `<details>` list; the sibling `.json` contains the full `instruction_unit_diagnostics` section with `selected_surface_fields` and `consistency_warnings` for programmatic inspection.

## Future Integration
- The difficulty system or the learner's selection chooses *where* (report span).
- This extractor produces instruction units that describe *what* the pianist does.
- A downstream chatbot consumes instruction units to explain, ask follow-ups, or generate practice material without re-deriving semantics from scratch.
- First-occurrence claims and teacher-quality exercise prose remain future work.

## Relation to Other Docs
- `semantic_narration.md` — deterministic narration templates and guardrails (phase 5).
- `musical_object_catalog.md` — full 54-object catalog definitions.
- `docs/templates/local_semantic_inspection.md` — Markdown template for a local report.
