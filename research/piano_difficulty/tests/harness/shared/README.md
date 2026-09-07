# Shared Dataset Harness

Dataset-agnostic primitives for loading local score corpora. Dataset-specific
parsing lives in `tests/harness/oktav_dataset/` and
`tests/harness/cipi_dataset/`; this layer must stay free of Oktav/CIPI names.

## Concepts

- `DatasetSpec` (`dataset_config.py`): configured inputs before loading —
  dataset name, local root, optional manifest/label paths, score globs,
  expected suffixes, path mode, adapter metadata. Reading files is out of
  scope; it never touches the filesystem.
- `DatasetRecord` / `DatasetLoadResult` (`dataset_records.py`): one analyzable
  score file, and a full adapter load with JSON-serializable diagnostics
  (`missing_files`, `extra_files`, `duplicate_piece_ids`,
  `duplicate_piece_uids`, `nonconforming_ids`, `unsupported_files`,
  `warnings`, `summary`). `piece_uid` is unique within a load; `piece_id` may
  repeat (duplicate arrangements, multi-movement works).
- `to_runtime_export_input(record)`: the single bridge from dataset records to
  the existing `RuntimeExportInput` used by `runtime_matrix_export.py`. Maps
  `difficulty_numeric`, `overallDifficulty`, and `henle` labels and preserves
  stable adapter-metadata columns.
- Discovery/normalization (`dataset_discovery.py`): Unicode-aware
  `normalize_filename`, dataset-relative and repo-relative path helpers,
  suffix-filtered `discover_score_files` (recursive or flat, sorted,
  `.DS_Store`-ignoring).
- Validation (`dataset_validation.py`): duplicate-value helpers and
  manifest-vs-discovered comparison. Duplicate `piece_id` is a diagnostic, not
  fatal; duplicate `piece_uid` is serious.

## Root resolution

`resolve_dataset_root(dataset_name, explicit_root=None, config_path=None)`
precedence:

1. explicit CLI root (`--dataset-root`)
2. dataset environment variable (`GRADUS_OKTAV_ROOT`, `GRADUS_CIPI_ROOT`)
3. config from `GRADUS_DATASETS_CONFIG`, else `.local/datasets.toml`
   (see `.local/datasets.example.toml`; real configs stay git-ignored)
4. adapter repo-relative fallback (fixtures / ignored staging only)

The result reports its source (`cli`, `env`, `local_config`, `repo_default`,
`not_configured`, `local_config_error`) and distinguishes "not configured"
from "configured path does not exist". Roots are never created automatically.

## Flow

```text
external raw corpus
  -> dataset-specific adapter (DatasetSpec -> DatasetLoadResult)
  -> to_runtime_export_input
  -> run_runtime_matrix_export
  -> tests/artifacts/<dataset>_dataset/<export_kind>/<run_name>/
  -> matrix-evaluation harnesses (matrices only)
```

Prediction and clustering harnesses consume matrices, never raw corpus roots.
The one exception is the Yan-lane cross-dataset comparison helper, which may
re-run Yan exports from raw roots only when explicitly asked.
