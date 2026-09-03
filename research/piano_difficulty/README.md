# Piano difficulty research subproject

This directory contains the existing `piano-difficulty` project as a
self-contained research area within the broader `gradus` thesis repository.
Commands and paths in this document are relative to this directory.

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

## Analysis lanes

The active work in this repository is now centered on five areas:

- Yan replication / extension:
  `tests/harness/yan2023/`, `tests/scripts/run_yan2023_*.py`, and
  `tests/artifacts/yan2023/`
- Difficulty Dynamics:
  `tests/harness/difficulty_dynamics/`,
  `tests/scripts/run_difficulty_dynamics.py`, and
  `tests/artifacts/difficulty_dynamics/`
- dataset staging and cataloging:
  `tests/harness/oktav_dataset/`,
  `tests/harness/cipi_dataset/`,
  `evaluation_scores/manifests/`
- OMR prototyping:
  `tests/harness/omr_pipeline/`,
  `tests/scripts/run_omr_pdf_export.py`,
  `tests/artifacts/omr_pipeline/`
- matrix evaluation:
  `tests/harness/difficulty_prediction/`,
  `tests/harness/difficulty_clustering/`,
  `tests/scripts/run_difficulty_prediction.py`,
  `tests/scripts/run_difficulty_clustering.py`,
  `tests/artifacts/difficulty_prediction/`,
  `tests/artifacts/difficulty_clustering/`

The matrix-evaluation lane has two modes, supervised and unsupervised, but
they share the same matrix-loading and feature-selection backbone.

Legacy ScoreAnalyzer parity material is retained only for historical reference
and compatibility checks. It is no longer an active lane.

## Project status

The repository is partially implemented. The codebase now has its core data
contracts, a raw `MusicXML` / `MXL` loading boundary, and a first normalization
layer that preserves the MusicXML details needed to port the legacy
`ScoreAnalyzer` research heuristics.

Implemented today:

- package metadata and console-script registration in `pyproject.toml`
- typed IR dataclasses in `src/piano_difficulty/normalize/schema.py`
- feature record contract in `src/piano_difficulty/features/base.py`
- raw `MusicXML`, `.xml`, and `MXL` loading in
  `src/piano_difficulty/io/musicxml.py`
- MXL archive resolution through `META-INF/container.xml`
- raw `score-partwise` normalization into `ScoreIR`
- written-note, rest-event, and tie-collapsed logical-note views
- conservative staff-based hand assignment (`staff=1` right, `staff=2` left)
- onset grouping for global and hand-specific attack views
- a legacy PHP `ScoreAnalyzer` compatibility view for staff-local streams,
  tuplets by measure, and active measure context
- direct v0 feature families from `docs/core_feature_registry.md`
- coarse source-span mapping for feature records
- piece-level and measure-level summary payloads
- JSON-ready extraction payloads
- `piano_difficulty.extract_score(...)`
- `piano_difficulty.analyze_score(...)`
- resilient batch analysis with `piano_difficulty.difficulty_analysis.batch.analyze_batch(...)`
- per-score batch failure capture with stable summary and CSV reporting
- frozen regression snapshots for representative `MusicXML` and real committed
  `.mxl` fixtures
- a test-scoped Difficulty Dynamics lane for windowed temporal profiles, consensus hotspot ranking, and feature attribution
- CLI dispatch for `piano-difficulty extract <path>`
- CLI dispatch for `piano-difficulty analyze <path>`
- CLI dispatch for `piano-difficulty analyze-batch <source> --out-dir <dir>`
- verbose repo-local explain script for one score file
- lightweight parser-level support diagnostics with
  `validate_supported_score(...)`
- unit tests for the CLI parser, raw MusicXML / MXL loading, normalization,
  feature extraction, analysis payloads, batch failure handling, and regression
  snapshots

Not implemented yet:

- MIDI loading, which is explicitly deferred
- richer local windowing and hotspot ranking in the Difficulty Dynamics lane
- pedagogy-weighted scoring or learned difficulty prediction

## What works right now

The preferred boundary for new research extraction work is the raw MusicXML
loader plus normalization layer:

```python
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.analysis.compatibility import build_php_compatibility_view

document = load_musicxml_document("tests/fixtures/minimal_piano.musicxml")
score = build_score_ir(document)
php_view = build_php_compatibility_view(score)
```

`score` contains normalized measures, written notes, rests, logical notes,
directions, clefs, onset groups, and diagnostics. `php_view` exposes staff-local
streams that make it easier to port the original PHP `ScoreAnalyzer` feature
math.

The single-file extraction path is now wired through the public API:

```python
from piano_difficulty import extract_score

result = extract_score("tests/fixtures/minimal_piano.musicxml")
payload = result.to_json_payload()
```

The legacy parser-backed loader still exists:

```python
from piano_difficulty.io.musicxml import load_musicxml, validate_supported_score

parsed_score = load_musicxml("tests/fixtures/minimal_piano.musicxml")
diagnostics = validate_supported_score(parsed_score)
```

This path uses `partitura` and is useful for validation or comparison, but raw
MusicXML is now the source of truth for normalization.

Supported input suffixes today:

- `.musicxml`
- `.xml`
- `.mxl`

The CLI emits the same JSON-ready payload:

```bash
piano-difficulty extract tests/fixtures/minimal_piano.musicxml
```

The single-file analysis path layers difficulty profiles on top of extraction:

```bash
piano-difficulty analyze tests/fixtures/feature_fixture.musicxml
```

The currently wired runtime profile is the legacy
`scoreanalyzer_reference`. Additional profiles can be requested with repeated
`--profile` flags.

## Verbose explain script

For inspection and debugging, the repo now includes a verbose explain script
that accepts `.xml`, `.musicxml`, and `.mxl` inputs and prints a plain-text
walkthrough of the extracted values.

Run it from the repository root:

```bash
PYTHONPATH=src python scripts/explain_score.py tests/fixtures/feature_fixture.musicxml
```

It can also explain a real compressed MusicXML file:

```bash
PYTHONPATH=src python scripts/explain_score.py tests/fixtures/real_mxl_basic_grand_staff.mxl
```

If you want only extraction output and do not want difficulty-profile analysis:

```bash
PYTHONPATH=src python scripts/explain_score.py tests/fixtures/real_mxl_basic_grand_staff.mxl --extract-only
```

The verbose report includes:

- source metadata and score-level counts
- aggregated piece-summary feature values
- every extracted feature record with value, units, scope, reliability, and
  source span
- per-measure summary records
- difficulty-profile dimensions, raw values, labels, marks, summaries, and
  notable measures when profile analysis is enabled
- top-level diagnostics

## Batch analysis

Batch analysis accepts either one score file or a directory tree and writes one
JSON payload per successful score:

```bash
piano-difficulty analyze-batch tests/fixtures --out-dir out
```

Current batch behavior is intentionally strict about reporting and intentionally
lenient about per-file continuation:

- input discovery includes `.musicxml`, `.xml`, and `.mxl`
- setup errors still fail immediately, for example a missing source path or an
  output directory creation failure
- score-level analysis errors are isolated to the individual score that failed
- one malformed or unsupported file does not stop the rest of the directory
- the command exits `0` only when every discovered score succeeds
- the command exits `1` when any score fails, even if other scores complete and
  write outputs

For a batch run, the output directory may contain:

- one `<slug>.json` file per successfully analyzed score
- `corpus_summary.json` for the whole batch
- `errors.csv` whenever at least one score fails
- `features.csv` and `analysis_dimensions.csv` only when `--write-csv` is set,
  and only for successful scores

`corpus_summary.json` currently uses `schema_version: "batch_summary.v2"` and
includes:

- `file_count`: number of discovered inputs
- `success_count`: number of scores that produced JSON payloads
- `failure_count`: number of scores that failed analysis
- `profile_ids`: requested analysis profiles
- `scores`: one entry per discovered input with a stable `status`

Each `scores` entry is shaped as one of:

- success: `source_path`, `status: "success"`, `json_path`
- failure: `source_path`, `status: "failure"`, `error_type`, `message`

`errors.csv` is written independently of `--write-csv` whenever there is at
least one failure. Its columns are stable:

- `source_path`
- `error_type`
- `message`

Per-file error JSON artifacts are intentionally not written. Failures are
reported only through `corpus_summary.json` and `errors.csv`.

## Parser backend

The raw normalization layer uses Python's standard XML parser and does not
require `partitura`.

`partitura` remains the optional backend for `load_musicxml(...)`, which returns
parser-native objects for validation and future cross-checking. Parser-native
objects should stay out of feature extractors.

## Development

Requirements:

- Conda or Miniconda
- Python 3.12+

Use the project conda environment for all Python commands. From this directory:

```bash
conda env create -f environment.yml
conda activate piano-difficulty
```

From the repository root, use the equivalent path:

```bash
conda env create -f research/piano_difficulty/environment.yml
```

Fresh clones must initialize submodules (MIDI toolbox `1.1` and `mxl-predict`):

```bash
git clone --recurse-submodules git@github.com:wcshelor/gradus.git
# or if already cloned:
git submodule update --init --recursive
```

If the environment already exists, update it from the YAML:

```bash
conda env update -n piano-difficulty -f environment.yml --prune
```

Coding agents and non-interactive scripts should avoid relying on shell
activation. Use `conda run` explicitly:

```bash
conda run -n piano-difficulty python -m pytest -q
conda run -n piano-difficulty python -m compileall -q src tests
```

The environment installs this package in editable mode with dev dependencies via
`environment.yml`, which delegates Python package dependencies to
`pyproject.toml`.

Run the test suite:

```bash
conda run -n piano-difficulty python -m pytest -q
```

Current automated coverage is intentionally narrow. The tests focus on:

- import/bootstrap behavior for the `src/` layout
- CLI parser shape
- raw `MusicXML` / `MXL` loading
- normalization of measures, written notes, rests, ties, tuplets, metadata, and
  PHP-compatible staff streams
- direct feature extraction across the v0 registry families
- single-file extraction and analysis payload shape
- verbose explain-script rendering for `.musicxml` and `.mxl`
- resilient batch processing with partial failures
- committed real `.mxl` fixture coverage in addition to synthetic archive tests
- regression snapshots with machine-independent source-path normalization
- lightweight parser-level score validation when `partitura` is installed

### Dependency maintenance

Keep `README.md` and `environment.yml` current whenever development practices or
dependencies change. In particular, coding agents should update:

- `pyproject.toml` when Python package requirements change
- `environment.yml` when the conda environment needs new system-level or pip
  dependencies
- `README.md` when setup, verification, or workflow instructions change

## Repository layout

- `src/piano_difficulty/io/`: raw and optional parser-backed input boundaries
- `src/piano_difficulty/normalize/`: IR schema and raw MusicXML converters
- `src/piano_difficulty/analysis/`: hand assignment, onset grouping,
  PHP-compatible views, and future window helpers
- `src/piano_difficulty/difficulty_analysis/`: batch orchestration, profile
  registry, and report rendering
- `src/piano_difficulty/features/`: feature contracts and extractor modules
- `src/piano_difficulty/aggregation/`: piece-level and measure-level summaries
- `src/piano_difficulty/output/`: export helpers
- `src/piano_difficulty/validation/`: structural sanity checks and diagnostics
- `evaluation_scores/`: real repertoire for labeled evaluation and manual
  inspection, kept separate from strict test fixtures
- `tests/`: fixtures, regression snapshots, and test scaffolding
- `docs/`: design notes, roadmap material, and recovery lists

## Fixtures and regression coverage

The repository now keeps both source-like XML fixtures and a real committed
compressed MusicXML archive:

- `tests/fixtures/minimal_piano.musicxml`: smallest useful piano loader fixture
- `tests/fixtures/feature_fixture.musicxml`: hand-authored analysis fixture used
  for stable reference-profile expectations
- `tests/fixtures/real_mxl_basic_grand_staff.mxl`: self-authored compressed
  MusicXML fixture for end-to-end `.mxl` regression coverage

The committed `.mxl` fixture is intentionally small but still exercises the
compressed input boundary with piano-specific content:

- grand staff
- title and composer metadata
- explicit tempo
- at least one chord
- at least one accidental
- ordinary rests and notes across two measures

Regression snapshots live in `tests/regression/`. Snapshot helpers normalize
`payload["source"]["path"]` to a repo-relative path before comparison so frozen
outputs remain stable across machines and workspace locations.

## Evaluation corpora

Use `evaluation_scores/` for real score files you want to inspect or benchmark.
That directory now includes:

- `known_levels/abrsm/`
- `known_levels/henle/`
- `known_levels/rcm/`
- `ad_hoc/` for local-only exploratory files ignored by git
- `manifests/score_catalog.template.csv` as a starter catalog format

Keep `tests/fixtures/` reserved for tiny deterministic automated-test assets.

## Key docs

- [Data model](docs/data_model.md)
- [Core feature registry](docs/core_feature_registry.md)
- [Roadmap](docs/roadmap.md)
- [Recovery list](docs/recovery_list.md)
- [Working extraction plan](piano_difficulty_extractor_plan.md)

## Near-term focus

The next meaningful milestone is hardening the first end-to-end path:

1. expand measure-scoped descriptors instead of relying only on piece spans
2. refine notation edge cases such as cross-staff writing and nonstandard clefs
3. add richer sanity checks for unsupported score layouts
4. compare outputs on easy and difficult reference pieces for face validity
5. broaden the committed fixture corpus beyond the first representative `.mxl`
