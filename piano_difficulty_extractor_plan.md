# Piano Difficulty Descriptor Extraction Repo - Updated Plan

Updated for the current repository state on 2026-04-22.

## Purpose

This repository is still best understood as a symbolic piano score descriptor
extractor, not as a single-number difficulty predictor.

The immediate job of the codebase is to:

- ingest symbolic piano scores,
- normalize them into a parser-independent IR,
- extract direct, localizable descriptors,
- aggregate those descriptors into stable summaries,
- export explainable outputs that later support pedagogy, heuristics, and ML.

The guiding principle remains:

> extract first, model later

## What Changed In This Plan

The earlier plan described an aspirational pre-implementation architecture. That
was no longer aligned with the repository. This version is a working plan tied
to the files and contracts that actually exist today.

In particular:

- the repo already has a concrete IR schema,
- the repo already has a feature record contract,
- the repo already has design docs and a CLI shape,
- most runtime behavior is still stubbed and needs implementation,
- some previously proposed file names do not match the actual tree.

## Current Repository State

### Foundations already in place

- package layout under `src/piano_difficulty/`
- parser-independent IR in `src/piano_difficulty/normalize/schema.py`
- feature contract in `src/piano_difficulty/features/base.py`
- `MusicXML` / `MXL` loading in `src/piano_difficulty/io/musicxml.py`
- lightweight parser-level support checks in `validate_supported_score`
- initial feature registry in `docs/core_feature_registry.md`
- IR design doc in `docs/data_model.md`
- short roadmap in `docs/roadmap.md`
- research-notes placeholder in `docs/research_notes.md`
- CLI parser shape in `src/piano_difficulty/cli/main.py`
- console entry point in `pyproject.toml`
- clean test bootstrap in `tests/conftest.py`
- loader fixture and unit tests in `tests/unit/test_musicxml_io.py`

### Major implementation still pending

- score normalization and tie collapsing
- hand assignment
- onset grouping and source-span helpers
- sanity checks
- all feature extraction modules
- piece-level and measure-level aggregation
- JSON export
- pipeline orchestration
- CLI dispatch
- real fixtures, integration tests, and regression baselines

### Important repo-specific corrections

- `docs/feature_ontology.md` does not exist in this repo. The current canonical
  feature-planning document is `docs/core_feature_registry.md`.
- the chosen MusicXML parser backend is now explicitly `partitura`
- feature families live in flat modules such as
  `features/metadata.py` and `features/rhythm.py`, not in nested subpackages.
- the hand-assignment module is `analysis/hands.py`, not
  `analysis/hand_assignment.py`.
- the output boundary currently targets JSON only. CSV should stay deferred
  until the JSON payload is stable.
- MIDI support is explicitly deferred. The boundary exists in `io/midi.py`, but
  it is not part of the first implementation milestone.

## Stable Design Commitments

These should remain true as implementation proceeds.

### 1. Descriptor extraction comes before scoring

The repo should produce direct, interpretable descriptors first. Weighted
difficulty scores, pedagogical ratings, or learned models belong on top of that
layer, not inside it.

### 2. Parser-native objects stop at the IO and normalization boundary

Feature extractors should operate on repository IR objects, not on parser
objects.

### 3. Traceability is mandatory

Each feature should be able to point back to the score region it summarizes.
This is why `FeatureRecord` includes `scope`, `scope_ref`, `source_span`, and
`diagnostics`.

### 4. Conservative hand assignment is better than clever but opaque heuristics

Many later features depend on hand labels. Early logic should prefer explicit
staff-driven rules and confidence flags over aggressive inference.

### 5. Local difficulty matters

The repo should support whole-piece summaries and local views. Measure-level
aggregation is part of the first meaningful end-to-end milestone. Windowed and
hotspot analysis can follow once the core pipeline is stable.

## Current Code Structure

The actual implementation surface today is:

```text
src/piano_difficulty/
  io/
    musicxml.py
    midi.py
  normalize/
    schema.py
    converters.py
  analysis/
    hands.py
    grouping.py
    windows.py
    source_map.py
  features/
    base.py
    metadata.py
    rhythm.py
    pitch_geometry.py
    leaps.py
    texture.py
    coordination.py
    notation.py
  aggregation/
    piece_summary.py
    measure_summary.py
  output/
    json_export.py
  validation/
    sanity_checks.py
  cli/
    main.py
  pipeline.py
```

This plan should follow that structure unless there is a deliberate refactor.

## Canonical v0 Feature Scope

The current first-pass feature scope should stay aligned with
`docs/core_feature_registry.md`.

### Metadata and score context

- measure count
- note count
- pitch range
- tempo change count
- key change count
- meter change count

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

## Inputs And Coverage

### Primary input for the first implementation

- `MusicXML`
- `MXL`

These formats preserve the notation needed for the repo's actual goals.

### Deferred input

- MIDI

MIDI should remain a later reduced-coverage path because it lacks much of the
notation and control information needed for meaningful difficulty descriptors.

## Output Contract For The First Working Pipeline

The first end-to-end extractor should output a JSON payload that includes:

- normalized score metadata
- extracted feature records
- piece-level summary
- measure-level summaries
- diagnostics

Window-level summaries and hotspot ranking are valuable, but they can stay out
of the first shipping milestone if they slow down the core path.

## Implementation Plan By Area

### 1. IO

#### Target files

- `src/piano_difficulty/io/musicxml.py`
- `src/piano_difficulty/io/midi.py`

#### Near-term plan

- keep the `partitura` boundary stable for `.musicxml`, `.xml`, and `.mxl`
- preserve explicit `.mxl` container resolution in `read_mxl_archive`
- keep parser-level supportability checks lightweight and explainable
- keep MIDI unimplemented until after the first MusicXML-based pipeline works

#### Deliverable

A parser-native score object for one supported MusicXML-family file plus a
small validation layer for obvious unsupported layouts.

### 2. Normalization

#### Target files

- `src/piano_difficulty/normalize/schema.py`
- `src/piano_difficulty/normalize/converters.py`

#### Current status

The schema is already defined. That is one of the main completed pieces of
foundational work in the repo.

#### Near-term plan

- implement `normalize_measures`
- implement `normalize_written_notes`
- implement `normalize_directions`
- implement `collapse_ties`
- implement `build_score_ir`

#### Requirements

- preserve exact time using `Fraction`
- keep written and logical note views separate
- keep measure indices stable
- store hand labels and confidence separately from staff labels
- keep the IR small and parser-independent

#### Deliverable

A populated `ScoreIR` object for one parsed piano score.

### 3. Analysis Helpers

#### Target files

- `src/piano_difficulty/analysis/hands.py`
- `src/piano_difficulty/analysis/grouping.py`
- `src/piano_difficulty/analysis/source_map.py`
- `src/piano_difficulty/analysis/windows.py`

#### Near-term plan

- implement conservative hand assignment for written and logical notes
- implement measure indexing for written notes
- implement hand indexing for logical notes
- implement onset grouping for logical notes
- implement source-span construction from event collections

#### Deferred-but-reserved plan

- keep fixed-size measure windows in place as the future home for hotspot and
  local-difficulty work
- do not let window support block the first measure-summary pipeline

#### Deliverable

Reusable score views that keep extractor code small and deterministic.

### 4. Feature Extraction

#### Target files

- `src/piano_difficulty/features/base.py`
- `src/piano_difficulty/features/metadata.py`
- `src/piano_difficulty/features/rhythm.py`
- `src/piano_difficulty/features/pitch_geometry.py`
- `src/piano_difficulty/features/leaps.py`
- `src/piano_difficulty/features/texture.py`
- `src/piano_difficulty/features/coordination.py`
- `src/piano_difficulty/features/notation.py`

#### Stable contract

Each extractor should return `list[FeatureRecord]`.

Each record should include:

- `feature_id`
- `scope`
- `scope_ref`
- `value`
- `units`
- `reliability`
- `source_span`
- `diagnostics`

#### Implementation order

1. metadata
2. rhythm
3. pitch geometry
4. leaps
5. texture
6. coordination
7. notation

#### Rationale

This order matches the current docs and keeps the first implementation focused
on direct, observable, low-ambiguity descriptors.

#### Deliverable

A direct descriptor layer that is explainable and testable on tiny fixtures.

### 5. Validation, Aggregation, And Export

#### Target files

- `src/piano_difficulty/validation/sanity_checks.py`
- `src/piano_difficulty/aggregation/piece_summary.py`
- `src/piano_difficulty/aggregation/measure_summary.py`
- `src/piano_difficulty/output/json_export.py`

#### Near-term plan

- run sanity checks after normalization and before extraction
- aggregate raw feature records into piece-level summaries
- aggregate raw feature records into measure-level summaries
- export a canonical JSON payload

#### Current constraint

JSON is enough for the first working version. Do not add CSV or dataframe
exports until the JSON schema stops moving.

#### Deliverable

A stable structured payload suitable for debugging, regression testing, and
downstream experimentation.

### 6. Pipeline And CLI

#### Target files

- `src/piano_difficulty/pipeline.py`
- `src/piano_difficulty/cli/main.py`

#### Near-term plan

- implement `extract_score(path)`
- have the pipeline call IO, normalization, validation, analysis helpers,
  feature extraction, aggregation, and export shaping in that order
- wire the CLI to the pipeline
- keep the CLI narrow: `piano-difficulty extract <path> --format json`

#### Deliverable

A minimal but real end-to-end command for one score file.

## Validation Strategy

The validation plan should now match the current test layout.

### Unit tests

Use tiny purpose-built excerpts to verify exact values for:

- spans
- leap counts
- tie collapsing
- accidentals
- clef changes
- cross-staff notation
- tuplets
- simple hand assignment

### Integration tests

Add end-to-end tests that:

- load a real fixture score,
- build `ScoreIR`,
- run selected extractor families,
- verify JSON shape and diagnostics.

### Regression tests

Freeze JSON outputs for a small stable fixture set so later changes are
intentional and reviewable.

### Face-validity checks

Once the core extractor exists, compare outputs on clearly easier and harder
repertoire to catch obviously misleading descriptors.

## Immediate Repo Hygiene Tasks

These are not feature work, but they should be handled early because they slow
down iteration.

### 1. Add real fixtures beyond the loader smoke tests

The repo now has one minimal MusicXML fixture for the loader boundary. The next
step is to add small purpose-built score files for normalization and feature
tests.

### 2. Keep docs synchronized with code

`README.md`, package docstrings, and this plan now reflect the implemented
loader milestone. Keep them updated as normalization and extraction land.

## Phased Roadmap

### Phase 0 - Foundations already done

#### Completed or mostly completed

- package structure
- IR schema
- feature record contract
- feature registry
- CLI shape
- roadmap and research-note placeholders

#### Exit condition

The repo has stable module boundaries and stable data contracts.

### Phase 1 - Finish the normalization and helper layer

#### Work

- implement MusicXML / MXL loading
- build `ScoreIR`
- implement tie collapsing
- assign hands conservatively
- create onset groups
- add sanity checks
- add source-span helpers

#### Exit condition

One input score can be loaded and normalized into a populated `ScoreIR` with
diagnostics.

### Phase 2 - Ship the first end-to-end extractor

#### Work

- implement the seven direct feature families in the current registry
- implement piece and measure summaries
- implement JSON export
- implement pipeline orchestration
- implement CLI dispatch
- add one integration test

#### Exit condition

The repo can process one MusicXML-family score and emit structured JSON with
piece-level and measure-level direct descriptors.

### Phase 3 - Harden and validate

#### Work

- expand handcrafted fixtures
- add regression baselines
- handle parser edge cases
- improve diagnostics
- check outputs against musically obvious examples

#### Exit condition

Changes to core extraction behavior are testable, reviewable, and explainable.

### Phase 4 - Add richer musical features

#### Work

- articulation burden
- dynamics
- pedaling
- harmony and tonality
- structure and repetition
- better local-difficulty summaries

#### Exit condition

The repo supports a meaningfully broader multidimensional difficulty profile
beyond the direct v0 feature set.

### Phase 5 - Research-driven layers

#### Work

- pedagogy-weighted summaries
- repertoire-level comparisons
- personalized ergonomic scaling
- optional learned models

#### Exit condition

The repo becomes a platform for difficulty research rather than only a direct
descriptor engine.

## Concrete Next Milestones

### Milestone 1 - Completed

- make test execution reliable in a clean environment
- choose and wire the MusicXML parser backend
- implement `load_musicxml`
- implement `read_mxl_archive`
- implement lightweight parser-level support checks

### Milestone 2 - Build normalized score objects

- implement measure, written-note, and direction normalization
- implement tie collapsing
- return a populated `ScoreIR`

### Milestone 3 - Build shared analysis views

- assign hands
- group onsets
- build source spans
- add sanity checks

### Milestone 4 - Implement the direct feature slice

- metadata
- rhythm
- pitch geometry
- leaps
- texture
- coordination
- notation

### Milestone 5 - Finish the first public extractor path

- piece summary
- measure summary
- JSON payload
- CLI dispatch
- integration test

## Definition Of Success For The First Real Release

The first meaningful release is successful if the repo can:

- load one `MusicXML` or `MXL` piano score,
- normalize it into the current IR,
- run the direct feature families listed in `docs/core_feature_registry.md`,
- emit a JSON payload with traceable feature records and diagnostics,
- summarize results at piece and measure level,
- pass unit and integration tests in a documented setup.

That is the right target for the current repository state. It is ambitious
enough to be useful, but still grounded in the code that already exists.
