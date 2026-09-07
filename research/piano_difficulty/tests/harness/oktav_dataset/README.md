# Oktav Dataset Harness

This is one dataset adapter in the broader dataset-staging lane. It loads the
local Oktav corpus through the shared dataset contract
(`tests/harness/shared/`) without copying raw scores into the repository.

## Corpus shape

- Flat directory of score files (`.xml`, `.musicxml`, `.mxl`).
- File names usually encode title, arrangement token, an `MSMT`/`MSMT2`
  marker, and an `OKxxxxx` identifier, with version suffixes, accents, and
  punctuation variants.
- `OKxxxxx` is useful but not unique: one commercial title can have multiple
  arrangements or difficulty versions. Duplicate IDs are expected.
- A few files have malformed (`OK0357`) or missing IDs; they are reported in
  `nonconforming_ids`, never dropped.

## Identity and labels

- `piece_id` is the valid `OKxxxxx` when present, else the filename stem.
- `piece_uid` is unique and derives from the normalized dataset-relative
  path/filename, never from `OKxxxxx` alone.
- Arrangement tokens (`arrangement_raw`, `arrangement_key`) are best-effort
  metadata parsed before `MSMT`/`MSMT2`; identity and label joins never depend
  on them.
- Difficulty labels come from an explicit CSV source (headers equivalent to
  `Filename`, `ArrID`, `Difficulty`; `difficulty_numeric` accepted as well).
- Join precedence: exact filename, then normalized filename, then
  dataset-relative path. Never join by `OKxxxxx` alone — duplicates can carry
  different difficulty values.
- Raw and numeric labels stay separate (`difficulty_raw` preserves values such
  as `n/a`; `difficulty_numeric` exists only for numeric values).
- A prior generated matrix can still serve as a label source, but only through
  the explicitly named `legacy_label_source_csv` argument. Generated matrices
  are outputs, not canonical labels.

## Runners

- `tests/scripts/build_oktav_dataset_catalog.py`
  - checks dataset loading without extraction (`--dataset-root`,
    `--label-source`, `--out`)
- `tests/scripts/run_oktav_python_analysis.py`
  - runs repo-native `extract_score(...)` over each record via
    `to_runtime_export_input`
  - writes `oktav_labeled_feature_matrix.csv`, `corpus_summary.json`,
    `errors.csv` (on failures), `piece_json/`, and `load_report.json` to
    `tests/artifacts/oktav_dataset/python_analysis/full_run/`
- `tests/scripts/run_oktav_og_export.py`
  - archival ScoreAnalyzer export path (legacy)
- `tests/scripts/run_oktav_pdf_export.py`
  - compatibility alias for the OMR prototyping lane

## Local setup

Resolve the corpus root via `--dataset-root`, `GRADUS_OKTAV_ROOT`, or
`.local/datasets.toml` (see `.local/datasets.example.toml`). Keep corpus
staging, export metadata, and failure diagnostics here. New work should prefer
the shared dataset helpers and matrix-evaluation lanes where possible.
OMR-specific rendering and readback experiments belong in the separate OMR
lane.
