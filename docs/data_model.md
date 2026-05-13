# Data Model

This document defines the parser-independent intermediate representation used by
the repository.

## Design goals

- Preserve enough score detail for both direct descriptor extraction and later
  higher-level analysis.
- Separate written notation facts from logical attack events.
- Keep source locations traceable so features can point back to measures and
  time ranges.
- Avoid coupling feature extractors directly to any parser library.

## Core objects

### `ScoreIR`

Top-level container for one score. It should eventually hold:

- source metadata,
- score metadata,
- measures,
- notes,
- directions,
- onset groups,
- diagnostics.

### `MeasureIR`

Represents a measure with both stable indexing and printed numbering. It should
retain active meter, key, and tempo context when available.

### `WrittenNoteIR`

Represents notated note tokens before tie-collapsing. This is the right object
for notation-sensitive features such as accidentals, tuplets, or ledger-line
burden.

### `LogicalNoteIR`

Represents tie-collapsed attack-level events. This is the right object for
physical and rhythmic analyses such as leap size, hand span, and attack density.

### `DirectionIR`

Represents dynamics, tempo changes, pedal markings, and free-text or symbolic
directions attached to a score region.

### `OnsetGroupIR`

Represents a simultaneity or near-simultaneity grouping used by span, texture,
and coordination features.

### `DiagnosticIR`

Represents warnings, unsupported notation notices, ambiguity markers, and
validation failures.

## Stable design choices

- Time should be represented with exact rational values, not floats.
- Written and logical note views should coexist rather than being derived
  ad hoc inside every extractor.
- Hand labels should be stored separately from staff labels and should support
  confidence levels.

