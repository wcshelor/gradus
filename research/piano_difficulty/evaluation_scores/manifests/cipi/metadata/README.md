# CIPI Metadata

Recovered from:

`~/Desktop/oktav-thesis/datasets/cipi/metadata`

This directory stores the upstream CIPI metadata JSON files used for corpus
labels and train/validation/test splits. Keep score files outside this
metadata directory.

## Normalized Files

- `index.normalized.json` is the repository-normalized index. It preserves each
  upstream record, moves the original source paths to `upstream_path`, and uses
  `path` for local dataset-relative paths under `pieces/`.
- `../cipi_movement_manifest.csv` is the flat movement-level manifest derived
  from `index.normalized.json`. Use it when joining Henle labels onto feature
  matrices.
- `cipi_movement_manifest.csv` includes `legacy_dataset_relative_path` and
  `normalized_filename` for compatibility with older generated exports that
  predate the `pieces/` prefix or have different Unicode normalization.

## Count Notes

- `index.json` contains 652 metadata records keyed by IDs such as `c-1`,
  `m-103`, and `x-2`.
- Every `index.json` record has a `path` dictionary. Expanding those movement
  paths yields 744 score-file entries, matching the 744 local CIPI
  `.musicxml` files under `~/Desktop/oktav-thesis/datasets/cipi/pieces`.
- The existing generated Yan CIPI export has 740 successful piece JSON files
  and 4 timeout failures. Its `corpus_summary.json` still reports 744 input
  rows.
- `splits_composers.json`, `splits_lengths.json`, `max_lengths.json`, and
  `index.json` agree on the same 652 metadata IDs.
- `splits.json` references 660 IDs: all 652 IDs from `index.json` plus 8 IDs
  absent from `index.json` (`x-106`, `x-254`, `x-293`, `x-294`, `x-297`,
  `x-304`, `x-309`, `x-357`).
- The reduced split files intentionally cover fewer IDs than `index.json`.

Interpret the apparent piece-count mismatch as work-level metadata
(`index.json`, 652 records) versus movement/file-level corpus entries
(744 `.musicxml` files).
