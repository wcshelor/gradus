# piano-difficulty

`piano-difficulty` is a Python package for extracting symbolic, traceable piano
score descriptors from `MusicXML`-family files.

It is not yet a single-number difficulty predictor. The repository is organized
around the idea:

> extract first, model later

The goal is to build a pipeline that:

- loads symbolic piano scores,
- normalizes them into a parser-independent IR,
- extracts direct descriptors,
- aggregates them into stable summaries,
- exports explainable structured outputs for later pedagogy, heuristics, and
  machine-learning work.

## Project status

The repository is partially implemented. The codebase now has its core data
contracts and a working `MusicXML` / `MXL` loading boundary, but the end-to-end
extractor is not finished yet.

Implemented today:

- package metadata and console-script registration in `pyproject.toml`
- typed IR dataclasses in `src/piano_difficulty/normalize/schema.py`
- feature record contract in `src/piano_difficulty/features/base.py`
- `MusicXML`, `.xml`, and `MXL` loading in
  `src/piano_difficulty/io/musicxml.py`
- MXL archive resolution through `META-INF/container.xml`
- lightweight parser-level support diagnostics with
  `validate_supported_score(...)`
- CLI parser shape for `piano-difficulty extract <path>`
- unit tests for the CLI parser and MusicXML / MXL loading

Not implemented yet:

- score normalization into `ScoreIR`
- tie collapsing
- hand assignment and reusable analysis views
- feature extraction families
- piece-level and measure-level aggregation
- JSON export
- end-to-end pipeline orchestration
- CLI execution
- MIDI loading, which is explicitly deferred

## What works right now

The stable boundary you can use today is the `MusicXML` loader:

```python
from piano_difficulty.io.musicxml import load_musicxml, validate_supported_score

parsed_score = load_musicxml("tests/fixtures/minimal_piano.musicxml")
diagnostics = validate_supported_score(parsed_score)
```

For the included minimal piano fixture, `diagnostics` should be empty.

Supported input suffixes today:

- `.musicxml`
- `.xml`
- `.mxl`

The planned higher-level entry points already exist as scaffolding:

- `piano_difficulty.extract_score(...)`
- `piano-difficulty extract <path>`

Those interfaces are not wired up yet and currently raise
`NotImplementedError`.

## Parser backend

The active `MusicXML` parser backend is `partitura`.

This repository currently calls
`partitura.io.importmusicxml.load_musicxml(...)` at the loader boundary and
keeps parser-native objects confined to the IO layer until normalization is
implemented.

## Development

Requirements:

- Python 3.12+
- `pip`

Install in editable mode with dev dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run the test suite:

```bash
pytest -q
```

Current automated coverage is intentionally narrow. The tests focus on:

- import/bootstrap behavior for the `src/` layout
- CLI parser shape
- `MusicXML` / `MXL` loading and lightweight score validation

## Repository layout

- `src/piano_difficulty/io/`: parser-facing input boundaries
- `src/piano_difficulty/normalize/`: IR schema and future converters
- `src/piano_difficulty/analysis/`: future shared helpers such as hand
  assignment, onset grouping, and windows
- `src/piano_difficulty/features/`: feature contracts and extractor modules
- `src/piano_difficulty/aggregation/`: piece-level and measure-level summaries
- `src/piano_difficulty/output/`: export helpers
- `src/piano_difficulty/validation/`: structural sanity checks and diagnostics
- `tests/`: fixtures and test scaffolding
- `docs/`: design notes and roadmap material

## Key docs

- [Data model](docs/data_model.md)
- [Core feature registry](docs/core_feature_registry.md)
- [Roadmap](docs/roadmap.md)
- [Working extraction plan](piano_difficulty_extractor_plan.md)

## Near-term focus

The next meaningful milestone is a minimal end-to-end path:

1. normalize parsed scores into `ScoreIR`
2. collapse ties and assign hands conservatively
3. build shared analysis views
4. extract the first descriptor families
5. aggregate summaries and emit JSON
