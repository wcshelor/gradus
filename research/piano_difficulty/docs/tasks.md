# Piano Difficulty - Implementation Task Breakdown

> Historical task proposal, retained for research context. Superseded by
> [roadmap.md](roadmap.md) and [consolidation.md](consolidation.md).
> Many tasks below describe behavior that already exists. Do not use this file
> as an active implementation queue or a completion record.

> Each task below is designed to be carried out one at a time by a coding agent. Every task is small, testable, and contains enough context for an agent to understand what to build and how to verify it.

---

## Long-Term Goals

The project exists to build a **symbolic piano score descriptor extraction engine** following the principle **"extract first, model later."** The long-term arc is:

1. **Ingest** symbolic piano scores (MusicXML / MXL) and normalize them into a parser-independent intermediate representation (`ScoreIR`).
2. **Extract** direct, localizable, interpretable descriptors (the v0 feature families) with full traceability back to source regions.
3. **Aggregate** those descriptors into stable piece-level and measure-level summaries, with diagnostics at every stage.
4. **Export** explainable structured outputs (JSON payloads) that downstream pedagogy, heuristics, and ML work can consume.
5. **Harden** the pipeline with fixtures, regression baselines, edge-case handling, and face-validity checks.
6. **Enrich** with richer musical features (articulation, dynamics, pedaling, harmony, structure) and local-difficulty summaries (windows, hotspots).
7. **Add research layers** on top: pedagogy-weighted scoring, repertoire-level corpus statistics, personalized ergonomic scaling, and optional learned models.
8. **Become a platform** for difficulty research — not just a direct descriptor engine — supporting both direct descriptors and higher-level analysis.

---

## Phase 0: Scaffold and Contracts (Complete — Reference Only)

These were the foundational tasks already completed:

- Package layout under `src/piano_difficulty/` with `io/`, `normalize/`, `analysis/`, `features/`, `aggregation/`, `output/`, `validation/`, `cli/`
- IR schema in `src/piano_difficulty/normalize/schema.py` (`ScoreIR`, `MeasureIR`, `WrittenNoteIR`, `LogicalNoteIR`, `DirectionIR`, `ClefIR`, `OnsetGroupIR`, `DiagnosticIR`)
- Feature record contract in `src/piano_difficulty/features/base.py` (`feature_id`, `scope`, `scope_ref`, `value`, `units`, `reliability`, `source_span`, `diagnostics`)
- `MusicXML` / `MXL` loading in `src/piano_difficulty/io/musicxml.py`
- Parser-level support checks in `validate_supported_score`
- Feature registry in `docs/core_feature_registry.md`
- IR design doc in `docs/data_model.md`
- CLI shape in `src/piano_difficulty/cli/main.py`
- Console entry point in `pyproject.toml`
- Test bootstrap in `tests/conftest.py`

---

## Phase 1: Complete Normalization and Helper Layer

### 1.1 Implement Normalization Functions

- **Task 1.1.1**: Implement `normalize_measures` in `src/piano_difficulty/normalize/converters.py`
  - **Description**: Convert raw parsed score-partwise XML into a list of `MeasureIR` objects with stable indices and printed numbering. Preserve active meter, key, and tempo context per measure.
  - **Files**: `src/piano_difficulty/normalize/converters.py`, `src/piano_difficulty/normalize/schema.py`
  - **Test**: Unit test in `tests/unit/test_normalize.py` that verifies measure count, index stability, and context preservation on a fixture with multiple measures

- **Task 1.1.2**: Implement `normalize_written_notes` in `src/piano_difficulty/normalize/converters.py`
  - **Description**: Extract `WrittenNoteIR` objects from the parsed XML. Preserve exact time using `Fraction`. Store pitch, duration, onset, staff, voice, and notational ornaments (accidentals, articulations). Keep written and logical note views separate.
  - **Files**: `src/piano_difficulty/normalize/converters.py`
  - **Test**: Unit test verifying that written notes retain notational details (accidentals, tuplet markers) that logical notes would not

- **Task 1.1.3**: Implement `normalize_directions` in `src/piano_difficulty/normalize/converters.py`
  - **Description**: Extract `DirectionIR` objects for dynamics, tempo changes, pedal markings, and other symbolic directions. Each direction must include its type, value, source span, and associated measure/staff.
  - **Files**: `src/piano_difficulty/normalize/converters.py`
  - **Test**: Unit test verifying that dynamics markings, tempo changes, and pedal markings are captured with correct types and source spans

- **Task 1.1.4**: Implement `collapse_ties` in `src/piano_difficulty/normalize/converters.py`
  - **Description**: Collapse tied written notes into single `LogicalNoteIR` events. Preserve exact duration using `Fraction`. Handle ties across measures. Ensure the logical note view has correct onset times and durations.
  - **Files**: `src/piano_difficulty/normalize/converters.py`
  - **Test**: Unit test with a fixture containing ties across measures, verifying that tied durations sum correctly and onset times are preserved

- **Task 1.1.5**: Implement `build_score_ir` in `src/piano_difficulty/normalize/converters.py`
  - **Description**: Assemble all normalized components (measures, written notes, logical notes, directions, clefs, onset groups, diagnostics) into a single `ScoreIR` container. This is the final composition step that ties all normalization functions together.
  - **Files**: `src/piano_difficulty/normalize/converters.py`
  - **Test**: Integration test that loads a fixture MusicXML, calls all normalization functions, and verifies `ScoreIR` has all expected top-level fields populated

### 1.2 Implement Analysis Helpers

- **Task 1.2.1**: Implement conservative hand assignment in `src/piano_difficulty/analysis/hands.py`
  - **Description**: Assign hands to written and logical notes using staff-driven rules: `staff=1` → right hand, `staff=2` → left hand. Store hand labels separately from staff labels with confidence levels. Handle grand staff and single-staff scores.
  - **Files**: `src/piano_difficulty/analysis/hands.py`
  - **Test**: Unit test with fixtures for grand staff, single staff, and mixed-staff scores, verifying correct hand assignment and confidence flags

- **Task 1.2.2**: Implement measure indexing for written notes in `src/piano_difficulty/analysis/hands.py`
  - **Description**: Assign each `WrittenNoteIR` to its containing measure index. Handle edge cases like notes at measure boundaries and notes spanning measures via ties.
  - **Files**: `src/piano_difficulty/analysis/hands.py`
  - **Test**: Unit test verifying measure index assignment for notes in normal positions, at boundaries, and within tied sequences

- **Task 1.2.3**: Implement hand indexing for logical notes in `src/piano_difficulty/analysis/hands.py`
  - **Description**: Propagate hand assignment from written notes to their collapsed logical note counterparts. Ensure each `LogicalNoteIR` carries the correct hand label.
  - **Files**: `src/piano_difficulty/analysis/hands.py`
  - **Test**: Unit test verifying that logical notes inherit the correct hand assignment from their source written notes

- **Task 1.2.4**: Implement onset grouping for logical notes in `src/piano_difficulty/analysis/hands.py`
  - **Description**: Group logical notes by onset time and hand to produce `OnsetGroupIR` objects. This supports texture, coordination, and span features. Each group should have a list of note references and a timestamp.
  - **Files**: `src/piano_difficulty/analysis/hands.py`
  - **Test**: Unit test with a fixture containing chords and single notes, verifying correct grouping by onset time and hand

- **Task 1.2.5**: Implement source-span construction in `src/piano_difficulty/analysis/source_map.py`
  - **Description**: Build `source_span` references for feature records pointing back to the measure and time range in the original score. Implement helper functions for constructing spans from event collections, single events, and ranges.
  - **Files**: `src/piano_difficulty/analysis/source_map.py`
  - **Test**: Unit test verifying that source spans correctly reference measure numbers and time ranges for various feature types

### 1.3 Implement Sanity Checks

- **Task 1.3.1**: Implement `validate_supported_score` checks for unsupported tuplets in `src/piano_difficulty/validation/sanity_checks.py`
  - **Description**: Detect nested tuplets and irrational tuplet ratios. Return a diagnostic with code, severity, message, and location for each violation.
  - **Files**: `src/piano_difficulty/validation/sanity_checks.py`
  - **Test**: Unit test with fixtures containing nested tuplets and irrational ratios, verifying diagnostic output

- **Task 1.3.2**: Implement `validate_supported_score` checks for cross-staff beaming in `src/piano_difficulty/validation/sanity_checks.py`
  - **Description**: Detect cross-staff beaming patterns and return diagnostics.
  - **Files**: `src/piano_difficulty/validation/sanity_checks.py`
  - **Test**: Unit test with a fixture containing cross-staff beamed notes

- **Task 1.3.3**: Implement `validate_supported_score` checks for ossia staves and unconventional clefs in `src/piano_difficulty/validation/sanity_checks.py`
  - **Description**: Detect ossia staves and unconventional clef definitions (e.g., clefs not in the standard set). Return diagnostics with codes and locations.
  - **Files**: `src/piano_difficulty/validation/sanity_checks.py`
  - **Test**: Unit test with fixtures containing ossia staves and nonstandard clefs

- **Task 1.3.4**: Implement `validate_supported_score` check for missing required elements in `src/piano_difficulty/validation/sanity_checks.py`
  - **Description**: Verify that the score contains required structural elements (at least one measure, notes, etc.). Return a diagnostic if any are missing.
  - **Files**: `src/piano_difficulty/validation/sanity_checks.py`
  - **Test**: Unit test with empty/minimal score inputs

---

## Phase 2: Ship the First End-to-End Extractor (Complete — Reference Only)

These tasks were completed: metadata, rhythm, pitch geometry, leaps, texture, coordination, notation feature families, piece and measure summaries, JSON export, pipeline orchestration, and CLI dispatch.

---

## Phase 3: Harden and Validate

### 3.1 Expand Fixtures

- **Task 3.1.1**: Create normalization testing fixtures in `tests/fixtures/`
  - **Description**: Add small, legally redistributable MusicXML files covering: simple measures, ties across measures, cross-staff notation, tuplets, clef changes, key changes, meter changes, accidentals, multiple voices. Each fixture file must have a companion README entry documenting what musical construct it isolates.
  - **Files**: `tests/fixtures/`, `tests/fixtures/README.md`
  - **Test**: `pytest tests/unit/test_normalize.py -v` passes with new fixtures

- **Task 3.1.2**: Create feature extraction fixtures for each feature family in `tests/fixtures/`
  - **Description**: Add purpose-built MusicXML fixtures covering each v0 feature family with positive, negative, and ambiguous cases:
    - Rhythm: density, tuplets, short durations
    - Pitch geometry: spans, register extremes
    - Leaps: melodic intervals across threshold boundaries
    - Texture: simultaneities, notes-per-onset variation
    - Coordination: aligned vs asynchronous hand onsets
    - Notation: accidentals, clef changes, cross-staff, ledger lines
  - **Files**: `tests/fixtures/`, `tests/fixtures/README.md`
  - **Test**: `pytest tests/unit/test_features.py -v` passes with new fixtures

- **Task 3.1.3**: Add integration test fixtures (complete scores) in `tests/fixtures/`
  - **Description**: Add 3-5 small complete pieces (public domain or synthetic) that exercise the full pipeline from loading through JSON export. Each fixture should exercise multiple feature families.
  - **Files**: `tests/fixtures/integration/`
  - **Test**: `pytest tests/integration/test_pipeline.py -v` passes

### 3.2 Add Regression Baselines

- **Task 3.2.1**: Freeze JSON outputs for the fixture set in `tests/artifacts/regression/`
  - **Description**: Run `piano-difficulty extract` on all fixtures and save outputs to `tests/artifacts/regression/`. Each baseline file must include producer version, schema version, and timestamp as metadata. Use `conda run -n piano-difficulty python -m pytest` to generate.
  - **Files**: `tests/artifacts/regression/`
  - **Test**: Verify all baseline files exist and contain required metadata fields

- **Task 3.2.2**: Implement regression test runner `tests/regression/test_json_baselines.py`
  - **Description**: Create a test that loads baselines and compares semantic equivalence (not exact string match). Normalize `payload["source"]["path"]` to repo-relative paths before comparison. Test should fail on semantic changes and pass on formatting-only changes.
  - **Files**: `tests/regression/test_json_baselines.py`
  - **Test**: `pytest tests/regression/ -v` passes; verify it fails when a feature value changes and passes when only formatting differs

### 3.3 Handle Parser Edge Cases

- **Task 3.3.1**: Improve `load_musicxml` robustness in `src/piano_difficulty/io/musicxml.py`
  - **Description**: Handle edge cases: missing divisions element, implicit measure numbering, compressed MXL with nested containers, malformed XML recovery. The loader should return structured diagnostics instead of crashing. Unsupported constructs must be flagged with diagnostic codes.
  - **Files**: `src/piano_difficulty/io/musicxml.py`
  - **Test**: Unit tests in `tests/unit/test_musicxml_io.py` covering each edge case, verifying diagnostics are returned rather than exceptions

- **Task 3.3.2**: Improve `read_mxl_archive` robustness in `src/piano_difficulty/io/musicxml.py`
  - **Description**: Handle MXL archives with unusual compression structures, missing `META-INF/container.xml`, and nested score resources. Add graceful degradation with diagnostics.
  - **Files**: `src/piano_difficulty/io/musicxml.py`
  - **Test**: Unit tests covering malformed MXL archives and missing container files

### 3.4 Improve Diagnostics

- **Task 3.4.1**: Ensure every `FeatureRecord` has complete diagnostic fields in `src/piano_difficulty/features/base.py`
  - **Description**: Verify each `FeatureRecord` includes: `feature_id`, `scope`, `scope_ref`, `value`, `units`, `reliability`, `source_span`, `diagnostics` (list of structured diagnostic objects with `code`, `severity`, `message`, `location`). No feature record should have empty diagnostics when edge cases are encountered.
  - **Files**: `src/piano_difficulty/features/base.py`
  - **Test**: Contract test `tests/contract/test_feature_record.py` verifying all required fields are present and non-empty

- **Task 3.4.2**: Add pipeline-level diagnostic aggregation in `src/piano_difficulty/pipeline.py`
  - **Description**: Collect all diagnostics from IO, normalization, validation, feature extraction, and aggregation into the final JSON payload under a top-level `diagnostics` array. Each diagnostic must include stage, code, severity, message, and location.
  - **Files**: `src/piano_difficulty/pipeline.py`
  - **Test**: Integration test verifying the final JSON payload has a complete `diagnostics` array with all stage diagnostics

- **Task 3.4.3**: Add validation diagnostic collection in `src/piano_difficulty/validation/sanity_checks.py`
  - **Description**: Ensure all sanity check results are collected into `DiagnosticIR` objects and returned in a structured list. Each diagnostic must have a unique code, severity level, human-readable message, and source location.
  - **Files**: `src/piano_difficulty/validation/sanity_checks.py`
  - **Test**: Unit tests verifying diagnostic completeness for each check category

### 3.5 Face-Validity Checks

- **Task 3.5.1**: Create reference piece comparison script `scripts/face_validity_check.py`
  - **Description**: Write a script that loads clearly easier/harder pieces from `evaluation_scores/known_levels/` and compares descriptor values. Output a comparison table showing expected relationships (e.g., harder piece has higher note density, larger leap counts, more accidentals).
  - **Files**: `scripts/face_validity_check.py`
  - **Test**: Script runs without errors on the committed reference corpora; output shows expected monotonic relationships

- **Task 3.5.2**: Document face-validity findings in `docs/face_validity_notes.md`
  - **Description**: Record observations from reference piece comparisons. Note any misleading descriptors (e.g., a feature that doesn't correlate with musical difficulty as expected) and flag them for future improvement.
  - **Files**: `docs/face_validity_notes.md`
  - **Test**: File exists, is readable, and documents at least one observation per feature family

---

## Phase 4: Add Richer Musical Features

### 4.1 Articulation and Dynamics Features

- **Task 4.1.1**: Implement articulation feature family in `src/piano_difficulty/features/articulation.py`
  - **Description**: Create a new feature module extracting: articulated-note ratio, staccato ratio, accent ratio, tenuto ratio, marcato ratio. Each feature must return `list[FeatureRecord]` with proper scope (piece/measure), hand attribution, and source spans. Use the v0 feature contract from `docs/core_feature_registry.md`.
  - **Files**: `src/piano_difficulty/features/articulation.py`
  - **Test**: Unit tests in `tests/unit/test_articulation.py` covering each articulation type with fixtures

- **Task 4.1.2**: Implement dynamics feature family in `src/piano_difficulty/features/dynamics.py`
  - **Description**: Create a new feature module extracting: explicit dynamic mark counts, dynamic change counts, crescendo/diminuendo wedge counts, dynamic range (min/max dynamic marking). Return `list[FeatureRecord]` with proper scope and source spans.
  - **Files**: `src/piano_difficulty/features/dynamics.py`
  - **Test**: Unit tests in `tests/unit/test_dynamics.py` covering dynamic markings

- **Task 4.1.3**: Register articulation and dynamics in the feature pipeline
  - **Description**: Add imports and registration for the new `articulation` and `dynamics` modules in the pipeline. Ensure they are called during `extract_score()`.
  - **Files**: `src/piano_difficulty/pipeline.py`
  - **Test**: Integration test verifying new features appear in the JSON output

### 4.2 Pedaling Features

- **Task 4.2.1**: Implement pedaling feature family in `src/piano_difficulty/features/pedaling.py`
  - **Description**: Create a new feature module extracting: pedal mark count, pedal change frequency, sustained pedal duration ratio, half-pedal indications. Return `list[FeatureRecord]` with proper scope and source spans. Parse pedal markings from `DirectionIR` objects.
  - **Files**: `src/piano_difficulty/features/pedaling.py`
  - **Test**: Unit tests in `tests/unit/test_pedaling.py` covering pedal markings

### 4.3 Harmony and Tonality Features

- **Task 4.3.1**: Implement harmony feature family in `src/piano_difficulty/features/harmony.py`
  - **Description**: Create a new feature module extracting: chord density, harmonic rhythm (rate of harmonic change), modulation count, key stability measure. Return `list[FeatureRecord]` with proper scope and source spans.
  - **Files**: `src/piano_difficulty/features/harmony.py`
  - **Test**: Unit tests in `tests/unit/test_harmony.py` covering harmonic changes

- **Task 4.3.2**: Implement tonality features in `src/piano_difficulty/features/harmony.py`
  - **Description**: Extend the harmony module with: black key rate, pitch entropy, deviation from middle C, and accidental density. These support the tonal instability dimension from the difficulty theory matrix.
  - **Files**: `src/piano_difficulty/features/harmony.py`
  - **Test**: Unit tests verifying tonality features on fixture scores with known harmonic content

### 4.4 Structure and Repetition Features

- **Task 4.4.1**: Implement structure feature family in `src/piano_difficulty/features/structure.py`
  - **Description**: Create a new feature module extracting: repeat section count, measure-level self-similarity, phrase boundary indicators. Return `list[FeatureRecord]` with proper scope and source spans.
  - **Files**: `src/piano_difficulty/features/structure.py`
  - **Test**: Unit tests in `tests/unit/test_structure.py` covering repeated sections

### 4.5 Better Local-Difficulty Summaries

- **Task 4.5.1**: Enhance windowed feature aggregation in `src/piano_difficulty/analysis/windows.py`
  - **Description**: Add sliding/fixed window support with configurable size and stride parameters. Window summaries should include per-window feature averages, min, max, and standard deviation. Integrate with the JSON export.
  - **Files**: `src/piano_difficulty/analysis/windows.py`
  - **Test**: Integration test verifying window summaries match manual calculation on a synthetic score

- **Task 4.5.2**: Implement hotspot detection (basic) in `src/piano_difficulty/analysis/hotspots.py`
  - **Description**: Add hotspot detection that identifies measures or windows exceeding configurable thresholds on key dimensions (leap size, note density, simultaneity span). Return hotspots with dimension contributions and evidence region.
  - **Files**: `src/piano_difficulty/analysis/hotspots.py`
  - **Test**: Unit tests in `tests/unit/test_hotspots.py` with synthetic scores having known hotspots

- **Task 4.5.3**: Wire hotspots and windows into the pipeline in `src/piano_difficulty/pipeline.py`
  - **Description**: Add optional `--windows` and `--hotspots` CLI flags. Include window summaries and hotspot results in the JSON output when requested.
  - **Files**: `src/piano_difficulty/pipeline.py`, `src/piano_difficulty/cli/main.py`
  - **Test**: Integration test verifying CLI flags produce the expected output sections

---

## Phase 5: Research-Driven Layers

### 5.1 Pedagogy-Weighted Summaries

- **Task 5.1.1**: Design weighted scoring schema in `src/piano_difficulty/scoring/weights.py`
  - **Description**: Create a configurable weight schema based on pedagogical literature. Support per-dimension weights, hand-specific weights, and profile presets (e.g., `beginner`, `intermediate`, `advanced`). Weights should map difficulty theory matrix dimensions to numeric values.
  - **Files**: `src/piano_difficulty/scoring/weights.py`
  - **Test**: Unit tests in `tests/unit/test_weights.py` verifying weight application, profile switching, and hand-specific scaling

- **Task 5.1.2**: Implement pedagogy-weighted aggregator in `src/piano_difficulty/aggregation/weighted_summary.py`
  - **Description**: Add a weighted summary module producing difficulty scores with confidence intervals. Output must include raw descriptors, weighted scores, and weight provenance (which weights were applied and from which profile).
  - **Files**: `src/piano_difficulty/aggregation/weighted_summary.py`
  - **Test**: Integration test in `tests/integration/test_weighted_summary.py` comparing weighted vs unweighted outputs

- **Task 5.1.3**: Wire weighted scoring into the pipeline
  - **Description**: Add `--weighted` CLI flag to enable pedagogy-weighted scoring. Ensure the JSON payload includes weighted scores when enabled.
  - **Files**: `src/piano_difficulty/pipeline.py`, `src/piano_difficulty/cli/main.py`
  - **Test**: Integration test verifying `--weighted` produces additional score fields in JSON output

### 5.2 Repertoire-Level Comparisons

- **Task 5.2.1**: Implement corpus statistics module in `src/piano_difficulty/analysis/corpus.py`
  - **Description**: Create a module that loads multiple scores and computes population statistics for each descriptor: percentiles (p25, p50, p75, p90), mean, standard deviation, min, max. Support filtering by feature family and hand.
  - **Files**: `src/piano_difficulty/analysis/corpus.py`
  - **Test**: Integration test in `tests/integration/test_corpus_stats.py` with a small corpus of fixture scores, verifying statistical correctness

- **Task 5.2.2**: Implement corpus CLI command in `src/piano_difficulty/cli/main.py`
  - **Description**: Add a `piano-difficulty corpus <dir>` command that computes and outputs corpus statistics across all scores in a directory. Output should be JSON with per-descriptor statistics.
  - **Files**: `src/piano_difficulty/cli/main.py`
  - **Test**: Integration test verifying the corpus command produces valid statistics output

### 5.3 Personalized Ergonomic Scaling

- **Task 5.3.1**: Add hand-size parameter to leap/span features in `src/piano_difficulty/features/leaps.py` and `src/piano_difficulty/features/pitch_geometry.py`
  - **Description**: Modify leap and span features to accept an optional `hand_span_semitones` parameter. When provided, scale the outputs to reflect whether intervals exceed the given hand span. Default behavior must preserve current behavior when no parameter is given.
  - **Files**: `src/piano_difficulty/features/leaps.py`, `src/piano_difficulty/features/pitch_geometry.py`
  - **Test**: Unit tests verifying scaling behavior with and without the hand span parameter

- **Task 5.3.2**: Add hand-size parameter to coordination features in `src/piano_difficulty/features/coordination.py`
  - **Description**: Extend coordination features to account for hand span when assessing subdivision mismatch and asynchronous onset difficulty.
  - **Files**: `src/piano_difficulty/features/coordination.py`
  - **Test**: Unit tests verifying coordination scaling with hand span parameter

### 5.4 Optional Learned Models

- **Task 5.4.1**: Create model interface contract in `src/piano_difficulty/models/base.py`
  - **Description**: Define an abstract base class with `predict_difficulty(features)` interface. Include versioning, metadata, and a `fit(features, labels)` method signature. The contract must support loading and saving model artifacts.
  - **Files**: `src/piano_difficulty/models/base.py`
  - **Test**: Contract test `tests/contract/test_model_interface.py` verifying interface compliance

- **Task 5.4.2**: Create a reference linear model implementation in `src/piano_difficulty/models/linear.py`
  - **Description**: Implement a simple linear regression model as a reference baseline. This provides a concrete, dependency-light model that can be used before any ML library integration.
  - **Files**: `src/piano_difficulty/models/linear.py`
  - **Test**: Unit tests verifying prediction outputs and that the model conforms to the base interface

- **Task 5.4.3**: Wire model inference into the pipeline
  - **Description**: Add `--model <path>` CLI flag to enable model-based difficulty prediction. Ensure the pipeline can load a model and produce predictions alongside extracted features.
  - **Files**: `src/piano_difficulty/pipeline.py`, `src/piano_difficulty/cli/main.py`
  - **Test**: Integration test verifying model inference produces valid output

---

## Phase 6: Research Lane Integration

### 6.1 Difficulty Dynamics Lane

- **Task 6.1.1**: Implement windowed temporal difficulty profiles in `src/piano_difficulty/analysis/windows.py`
  - **Description**: Enhance the window module to produce time-varying difficulty profiles. Support configurable window size, stride, and smoothing method. Output should include raw, smoothed, and composite lines.
  - **Files**: `src/piano_difficulty/analysis/windows.py`
  - **Test**: Integration test verifying temporal profiles are produced correctly

- **Task 6.1.2**: Implement consensus hotspot ranking in `src/piano_difficulty/analysis/hotspots.py`
  - **Description**: Add consensus-based hotspot detection that combines feature-track peaks with the composite difficulty line. Rank the strongest feature contributors inside hotspot regions.
  - **Files**: `src/piano_difficulty/analysis/hotspots.py`
  - **Test**: Unit tests with synthetic scores having known hotspot regions

- **Task 6.1.3**: Wire Difficulty Dynamics into the CLI
  - **Description**: Add `piano-difficulty analyze <path>` command with `--profile difficulty_dynamics` support. Output should include temporal profiles, hotspot rankings, and feature attributions.
  - **Files**: `src/piano_difficulty/cli/main.py`
  - **Test**: Integration test verifying the analyze command produces valid Difficulty Dynamics output

### 6.2 Yan Feature Reconstruction

- **Task 6.2.1**: Implement `note_density` in `tests/harness/yan2023/extractor.py`
  - **Description**: Reconstruct the note_density feature from repo-native score data. This is a direct score-density primitive that should already have a repo-native equivalent.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify the reconstructed value matches the expected Yan feature table shape

- **Task 6.2.2**: Implement `pitch_variability` in `tests/harness/yan2023/extractor.py`
  - **Description**: Reconstruct the pitch_variability feature using the Table 3 adjacent-note normalized variability formula. Wire the score-native version from the repo compatibility layer.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify the reconstructed value produces the expected variability profile

- **Task 6.2.3**: Implement `note_duration_variability` in `tests/harness/yan2023/extractor.py`
  - **Description**: Reconstruct the note_duration_variability feature using the Table 3 adjacent-note normalized variability formula for durations.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify the reconstructed value produces the expected duration variability profile

- **Task 6.2.4**: Implement `playing_speed_variation` in `tests/harness/yan2023/extractor.py`
  - **Description**: Reconstruct the playing_speed_variation feature using the Table 3 tempo-variation ratio.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify the reconstructed value matches the expected variation metric

- **Task 6.2.5**: Implement remaining implemented features (`chord_number`, `pitch_mean`, `pitch_std`, `pitch_range`, `duration_mean`, `duration_std`, `tempo`, `key_signature`, `black_key_rate`, `length`, `pitch_entropy`, `deviation_of_pitch_from_C4`, `polyphony_rate`, `triad`, `seventh_chord`, `ninth_chord`, `staccato_rate`) in `tests/harness/yan2023/extractor.py`
  - **Description**: Reconstruct each implemented feature from repo-native score data. Use the existing repo feature extractors as the source of truth. Each feature must be trackable to its paper definition.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify each feature produces values with the expected shape and range against a sample corpus

- **Task 6.2.6**: Mark proxyable features (`dotted_note_rate`, `playing_speed`, `hand_displacement_rate`, `hand_stretch`, `distinct_stroke_rate`, `irregular_rhythm`) with candidate formulas in `tests/harness/yan2023/extractor.py`
  - **Description**: For each proxyable feature, expose several explicit counting conventions as named candidates. Do not bake in one hidden convention. Each candidate must be labeled and selectable.
  - **Files**: `tests/harness/yan2023/extractor.py`
  - **Test**: Verify each proxyable feature exposes multiple candidates and the selection mechanism works

- **Task 6.2.7**: Implement reference comparison runner in `tests/harness/yan2023/`
  - **Description**: Create a runner that compares extracted feature vectors against any released Yan feature tables or matrices. Label each mismatch by failure class (preprocessing, scope, formula ambiguity).
  - **Files**: `tests/harness/yan2023/`, `tests/scripts/run_yan2023_reference_compare.py`
  - **Test**: Runner produces a mismatch report with labeled failure classes

- **Task 6.2.8**: Update the 73-slot paper inventory and slot ledger
  - **Description**: Synchronize `tests/harness/yan2023/paper_inventory.py` and `tests/harness/yan2023/slot_inventory.py` with any new paper evidence. Ensure every paper feature has a tracked status (`implemented`, `proxyable`, or `blocked`).
  - **Files**: `tests/harness/yan2023/paper_inventory.py`, `tests/harness/yan2023/slot_inventory.py`
  - **Test**: Verify all 73 slots have status and notes; verify no slot is untracked

### 6.3 Dataset Staging and Cataloging

- **Task 6.3.1**: Implement corpus manifest format in `evaluation_scores/manifests/`
  - **Description**: Define and commit a manifest format specification. Create the template `score_catalog.template.csv` with columns for file path, composer, title, difficulty level, source corpus, and metadata fields.
  - **Files**: `evaluation_scores/manifests/score_catalog.template.csv`
  - **Test**: Verify the template loads correctly and all required columns are present

- **Task 6.3.2**: Implement dataset catalog helpers in `tests/harness/shared/`
  - **Description**: Create dataset-agnostic catalog helpers for score-file discovery, metadata normalization, and catalog loading. These should feed the shared matrix loader.
  - **Files**: `tests/harness/shared/matrix_data.py`, `tests/harness/shared/matrix_features.py`
  - **Test**: Unit tests verifying catalog helpers load manifests and discover scores correctly

- **Task 6.3.3**: Implement Oktav dataset export adapter in `tests/harness/oktav_dataset/`
  - **Description**: Create an export adapter that processes the Oktav corpus, runs extraction on each score, and produces feature matrices. Support OG batch export and local dataset tooling.
  - **Files**: `tests/harness/oktav_dataset/`
  - **Test**: Verify the export adapter produces valid feature matrices for a sample of Oktav scores

---

## Phase 7: Evaluation and Testing Infrastructure

### 7.1 Property-Based and Metamorphic Tests

- **Task 7.1.1**: Add property-based tests for fraction arithmetic in `tests/unit/test_fractions.py`
  - **Description**: Use a property-based testing library to verify that `Fraction`-based time arithmetic is associative, commutative for addition, and preserves exact rational values through all normalization steps.
  - **Files**: `tests/unit/test_fractions.py`
  - **Test**: Run with property-based test runner; verify no counterexamples found

- **Task 7.1.2**: Add metamorphic tests for transposition invariance in `tests/unit/test_metamorphic.py`
  - **Description**: Verify that transposing a score by N semitones changes pitch features by exactly N but leaves rhythm, density, and coordination features unchanged. Similarly verify that duration scaling invariance holds for rhythm features.
  - **Files**: `tests/unit/test_metamorphic.py`
  - **Test**: Verify metamorphic properties hold on fixture scores

### 7.2 CI Integration

- **Task 7.2.1**: Set up CI to run the full test suite on PR
  - **Description**: Configure CI (GitHub Actions or equivalent) to run `conda run -n piano-difficulty python -m pytest` on every PR. Include linting (`ruff check .`), type checking (`mypy src/`), and test execution.
  - **Files**: `.github/workflows/test.yml` or equivalent
  - **Test**: Verify CI runs successfully on a test PR

### 7.3 Code Quality

- **Task 7.3.1**: Run `ruff check .` and fix all violations in `src/` and `tests/`
  - **Description**: Run the linter and fix all style violations. Ensure consistent formatting across all Python files.
  - **Files**: All `.py` files in `src/` and `tests/`
  - **Test**: `ruff check .` passes with zero violations

- **Task 7.3.2**: Run `mypy src/` and fix all type errors
  - **Description**: Run the type checker and fix all type annotations and errors. Ensure all public functions have proper type hints.
  - **Files**: All `.py` files in `src/`
  - **Test**: `mypy src/` passes with zero errors

- **Task 7.3.3**: Ensure all public functions have docstrings in `src/`
  - **Description**: Add docstrings to every public function and module in `src/piano_difficulty/`. Docstrings should describe the purpose, parameters, return values, and any side effects.
  - **Files**: All `.py` files in `src/piano_difficulty/`
  - **Test**: `pytest tests/contract/test_docstrings.py` passes

---

## Ongoing Maintenance Tasks

### M.1 Documentation Synchronization

- **Task M.1.1**: Update `README.md` when new features are added
  - **Description**: Add new feature modules, CLI commands, and usage examples to the README. Keep the "What works" and "Not implemented yet" sections current.
  - **Files**: `README.md`
  - **Test**: Verify all documented features match actual implementation

- **Task M.1.2**: Update `docs/core_feature_registry.md` when feature families change
  - **Description**: Add new feature families to the registry with their IDs, descriptions, and contracts. Mark deprecated features.
  - **Files**: `docs/core_feature_registry.md`
  - **Test**: Verify registry matches actual feature modules

- **Task M.1.3**: Update `docs/data_model.md` when IR schema changes
  - **Description**: Update `ScoreIR`, `MeasureIR`, `WrittenNoteIR`, `LogicalNoteIR`, `DirectionIR`, and other IR types when new fields are added.
  - **Files**: `docs/data_model.md`
  - **Test**: Verify documentation matches actual dataclass definitions

- **Task M.1.4**: Update CLI help text when commands/options change
  - **Description**: Ensure every new CLI command and option has help text. Run `piano-difficulty --help` and `piano-difficulty <command> --help` to verify.
  - **Files**: `src/piano_difficulty/cli/main.py`
  - **Test**: Verify all commands have help text; no missing or empty help strings

### M.2 Test Infrastructure

- **Task M.2.1**: Add property-based tests for fraction arithmetic
  - See Task 7.1.1

- **Task M.2.2**: Add metamorphic tests (transposition, duration scaling invariance)
  - See Task 7.1.2

- **Task M.2.3**: Set up CI to run full test suite on PR
  - See Task 7.2.1

### M.3 Code Quality

- **Task M.3.1**: Run `ruff check .` and fix violations
  - See Task 7.3.1

- **Task M.3.2**: Run `mypy src/` and fix type errors
  - See Task 7.3.2

- **Task M.3.3**: Ensure all public functions have docstrings
  - See Task 7.3.3

---

## Phase 8: Long-Term Vision Tasks

### 8.1 Explanation and Scaffolding Output

- **Task 8.1.1**: Implement feature attribution for hotspots in `src/piano_difficulty/analysis/hotspots.py`
  - **Description**: For each detected hotspot, rank the strongest feature contributors. Output a ranked list of feature IDs, their values, and their contribution to the hotspot score. This scaffolds later product visualization and explanation.
  - **Files**: `src/piano_difficulty/analysis/hotspots.py`
  - **Test**: Unit test with a synthetic score having a known hotspot, verifying attribution ranking

- **Task 8.1.2**: Implement practice exercise generation in `src/piano_difficulty/practice/`
  - **Description**: Based on hotspot regions, generate deterministic, source-derived practice exercises. Exercises should target the difficult passages identified by the pipeline.
  - **Files**: `src/piano_difficulty/practice/`
  - **Test**: Integration test verifying exercise generation targets correct hotspot regions

### 8.2 Multi-Format Output

- **Task 8.2.1**: Implement CSV export in `src/piano_difficulty/output/csv_export.py`
  - **Description**: Add CSV export of feature records for downstream analysis. Each row should be a feature record with all contract fields. Deferred until JSON payload is stable.
  - **Files**: `src/piano_difficulty/output/csv_export.py`
  - **Test**: Verify CSV output has all expected columns and matches JSON output values

- **Task 8.2.2**: Implement batch analysis output formatting in `src/piano_difficulty/difficulty_analysis/batch.py`
  - **Description**: Format batch analysis output with `corpus_summary.json`, `errors.csv`, and per-score JSON files. Support `--write-csv` flag for feature and analysis dimension CSVs.
  - **Files**: `src/piano_difficulty/difficulty_analysis/batch.py`
  - **Test**: Integration test verifying batch output format and content

### 8.3 Model Integration

- **Task 8.3.1**: Evaluate learned models against corpus in `tests/harness/difficulty_prediction/`
  - **Description**: Using the feature matrices from corpus analysis, train and evaluate learned difficulty prediction models. Compare against the linear baseline from Task 5.4.2.
  - **Files**: `tests/harness/difficulty_prediction/`
  - **Test**: Verify model evaluation produces metrics (RMSE, MAE, R²) and comparison tables

- **Task 8.3.2**: Implement clustering analysis in `tests/harness/difficulty_clustering/`
  - **Description**: Run unsupervised clustering on exported feature matrices to discover natural groupings in the repertoire. Produce cluster assignments, PCA visualizations, and reports.
  - **Files**: `tests/harness/difficulty_clustering/`
  - **Test**: Verify clustering produces stable, interpretable clusters

### 8.4 Product Exploration

- **Task 8.4.1**: Build a verbose explain script `scripts/explain_score.py`
  - **Description**: Create a script that accepts a score file and prints a plain-text walkthrough of extracted values, difficulty profiles, hotspots, and diagnostic information. Support `--extract-only` flag for extraction-only mode.
  - **Files**: `scripts/explain_score.py`
  - **Test**: Verify script runs correctly on fixture and real MXL files

- **Task 8.4.2**: Prototype OMR pipeline in `tests/harness/omr_pipeline/`
  - **Description**: Render source score files into page-oriented PDFs using MuseScore as a rendering step. Keep the source-to-rendered boundary explicit for future recognizer evaluation. Preserve manifest, log, and rendered-page evidence separately.
  - **Files**: `tests/harness/omr_pipeline/`, `tests/scripts/run_omr_pdf_export.py`
  - **Test**: Verify rendered PDFs are produced and manifests/log evidence are saved

---

## Task Prioritization Notes

- **Critical path**: Tasks in Phases 1-3 are prerequisites for everything else. Do not start Phase 4+ until Phase 3 passes cleanly.
- **Test-first policy**: For every feature task, write the test before or alongside the implementation. No feature is complete without passing tests.
- **Contract compliance**: Every new feature must conform to the `FeatureRecord` contract in `src/piano_difficulty/features/base.py`.
- **Source spans**: Every feature record must have a valid `source_span`. This is non-negotiable.
- **Yan lane separation**: Yan feature work stays in `tests/harness/yan2023/` until explicitly promoted to `src/`. Do not mix Yan code with runtime code.
- **Diffusion of work**: The analysis lanes (Yan, Difficulty Dynamics, Matrix evaluation) are test-scoped until a promotion decision is made. Do not add runtime code for lane experiments.
