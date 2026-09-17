# CIPI Dataset Harness

This is one dataset adapter in the broader dataset-staging lane. It loads the
local CIPI corpus through the shared dataset contract
(`tests/harness/shared/`) without copying raw scores into the repository.

## Work versus movement identity

- Upstream `metadata/index.json` holds 652 work-level records; expanding each
  work's movement paths yields 744 movement/file rows.
- The canonical catalog is the committed movement-level manifest
  `evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` (744 rows).
- `cipi_id` is work-level and repeats across movements; `piece_uid` is
  movement-level and unique. Score extraction always uses movement rows.
- `henle` is the primary label, attached at work level and inherited by each
  movement record.

## Paths

- The expected local root is the CIPI dataset root containing `metadata/` and
  `pieces/` (configure via `--dataset-root`, `GRADUS_CIPI_ROOT`, or
  `.local/datasets.toml`).
- Manifest `dataset_relative_path` values (with the `pieces/` prefix) resolve
  under that root. Pointing directly at `pieces/` produces a clear diagnostic
  instead of silently resolving.
- `legacy_dataset_relative_path`, `legacy_piece_uid`, and
  `normalized_filename` are preserved in adapter metadata so older generated
  exports stay joinable. New identity is `piece_uid`, not `legacy_piece_uid`.

## Splits and diagnostics

- Split files (`metadata/splits*.json`) are optional and diagnostic-only.
  Split IDs are validated against `index.json`; the 8 known split IDs absent
  from the index are reported, not dropped.
- Load reports include work-level and movement-level Henle distributions,
  missing/extra files, duplicate diagnostics, and split mismatch details.

## Runners

- `tests/scripts/build_cipi_dataset_catalog.py`
  - validates the committed movement manifest against a local root and writes
    a load report (`--dataset-root`, `--manifest-csv`, `--out`); it never
    rewrites the canonical manifest
- `tests/scripts/run_cipi_python_analysis.py`
  - active repo-native runtime export: loads movement records, converts via
    `to_runtime_export_input`, and writes `cipi_labeled_feature_matrix.csv`,
    `corpus_summary.json`, `errors.csv` (on failures), `piece_json/`,
    `load_report.json`, and `label_pairing_audit.json` to
    `tests/artifacts/cipi_dataset/python_analysis/full_run/`
  - `label_pairing_audit.json` is the quick validation preflight: it reports
    matrix row count, Henle-labeled row count, missing files, duplicate
    movement IDs, Henle distribution, and whether the matrix is ready for
    Henle validation
- `tests/scripts/run_cipi_og_export.py`
  - archival ScoreAnalyzer export; evidence stays under
    `tests/artifacts/retired/cipi_og_export/`

## Related demo surface

- The CEO CIPI walkthrough (`tests/harness/ceo_walkthrough/`) resolves a
  curated eight-piece manifest against the canonical movement manifest above
  and runs each piece through the existing difficulty overview. It reuses the
  dataset-root behavior documented here and owns no difficulty math; see its
  README for the rerun policy and claim boundaries.

Raw score files stay outside the repository unless they are explicitly safe to
commit.
