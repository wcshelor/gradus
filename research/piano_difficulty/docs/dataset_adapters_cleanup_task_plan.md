# Dataset Adapter Cleanup Task Plan

Status: small implementation handoff for cleanup after the dataset adapter
implementation review.

This document replaces the earlier dataset-adapter planning handoffs. The main
adapter architecture is now implemented. The remaining work is cleanup: wire the
root resolver into normal entry points, fix one limited-run summary edge case,
and remove duplicated lane documentation.

## Scope

Do:

- keep all changes inside the piano-difficulty harness and docs;
- keep dataset loading out of `src/piano_difficulty/`;
- preserve the shared dataset contract in `tests/harness/shared/`;
- preserve Oktav and CIPI adapter boundaries;
- keep raw corpora outside the repo;
- add or update focused tests for each behavior change.

Do not:

- redesign the adapter architecture;
- copy Oktav or CIPI score files into the repo;
- change prediction or clustering to scan raw corpus roots;
- remove legacy constants unless they are no longer referenced and tests prove
  that removal is safe.

## Review Findings To Resolve

1. Root resolution is implemented but not wired into normal adapter and script
   defaults.
2. CIPI `skipped_missing_count` can overcount when `--limit` is used.
3. `docs/analysis_lanes.md` has two adjacent `Rules:` sections in Lane 2.

## Task 1: Wire Root Resolution Into Oktav Loading

Objective:
Make bare Oktav adapter and script calls honor the documented root precedence:
explicit argument, `GRADUS_OKTAV_ROOT`, `GRADUS_DATASETS_CONFIG`, local
`.local/datasets.toml`, then the adapter's explicit repo fallback.

Files likely touched:

- `tests/harness/oktav_dataset/catalog.py`
- `tests/harness/oktav_dataset/python_analysis.py`
- `tests/scripts/build_oktav_dataset_catalog.py`
- `tests/unit/test_oktav_dataset_catalog.py`
- `tests/unit/test_dataset_scripts.py`

Implementation notes:

- Use `resolve_dataset_root("oktav", explicit_root=..., repo_fallback=...)`.
- Preserve explicit `dataset_root=` behavior for tests and callers.
- Record the selected root source in the load summary, for example
  `dataset_root_source` and `dataset_root_detail`.
- Avoid silently creating the root directory.
- Bare script use should no longer ignore `GRADUS_OKTAV_ROOT` or
  `.local/datasets.toml`.

Tests or validation:

- Add a test where `dataset_root` is omitted and `GRADUS_OKTAV_ROOT` points at
  a temporary fixture root.
- Add a test where a temporary config file supplies the Oktav root.
- Existing explicit-root tests must continue to pass.

Acceptance criteria:

- Oktav root resolution behavior matches the docs.
- Explicit roots still win.
- Load reports identify how the root was resolved.

## Task 2: Wire Root Resolution Into CIPI Loading

Objective:
Make bare CIPI adapter and script calls honor the documented root precedence:
explicit argument, `GRADUS_CIPI_ROOT`, `GRADUS_DATASETS_CONFIG`, local
`.local/datasets.toml`, then the adapter's explicit repo fallback.

Files likely touched:

- `tests/harness/cipi_dataset/catalog.py`
- `tests/harness/cipi_dataset/python_analysis.py`
- `tests/scripts/build_cipi_dataset_catalog.py`
- `tests/scripts/run_cipi_python_analysis.py`
- `tests/unit/test_cipi_dataset_catalog.py`
- `tests/unit/test_cipi_python_analysis.py`
- `tests/unit/test_dataset_scripts.py`

Implementation notes:

- Use `resolve_dataset_root("cipi", explicit_root=..., repo_fallback=...)`.
- Preserve explicit `dataset_root=` behavior.
- Record root resolution source and detail in the CIPI load summary.
- Keep canonical manifest default unchanged:
  `evaluation_scores/manifests/cipi/cipi_movement_manifest.csv`.
- Keep the existing diagnostic for callers that point directly at `pieces/`.

Tests or validation:

- Add a test where `dataset_root` is omitted and `GRADUS_CIPI_ROOT` points at a
  temporary fixture root.
- Add a test where a temporary config file supplies the CIPI root.
- Existing direct-root and direct-`pieces/` diagnostic tests must continue to
  pass.

Acceptance criteria:

- CIPI root resolution behavior matches the docs.
- Explicit roots still win.
- Load reports identify how the root was resolved.

## Task 3: Adjust Script Defaults To Allow Resolver Use

Objective:
Ensure runner scripts do not pre-fill repo defaults in a way that prevents the
shared resolver from seeing environment variables or local config.

Files likely touched:

- `tests/scripts/build_oktav_dataset_catalog.py`
- `tests/scripts/build_cipi_dataset_catalog.py`
- `tests/scripts/run_cipi_python_analysis.py`
- `tests/harness/oktav_dataset/python_analysis.py`
- `tests/harness/cipi_dataset/python_analysis.py`

Implementation notes:

- Prefer parser defaults of `None` for `--dataset-root` on scripts that should
  use resolver precedence.
- Let harness functions decide fallback behavior.
- Keep `--out-dir`, `--manifest-csv`, and label-source defaults stable unless
  there is a direct reason to change them.

Tests or validation:

- Existing script thinness tests should cover parser entry points.
- Add or update tests to prove environment variables are honored by script
  `main(argv)` when no `--dataset-root` is supplied.

Acceptance criteria:

- Bare scripts can use configured local roots.
- Explicit `--dataset-root` remains the highest precedence.

## Task 4: Fix CIPI Limited-Run Missing Count

Objective:
Make `skipped_missing_count` describe missing-file skips only, not records
excluded by `--limit`.

Files likely touched:

- `tests/harness/cipi_dataset/python_analysis.py`
- `tests/unit/test_cipi_python_analysis.py`

Implementation notes:

- Compute exportable records before applying `limit`.
- Compute missing-file skips as:
  `len(load_result.records) - len(exportable_before_limit)`.
- If useful, add separate summary fields for limited runs, such as
  `limited_input_count` or keep existing `limited` / `limit`.
- Preserve existing `failure_count` semantics.

Tests or validation:

- Fixture with two existing CIPI records and `limit=1` should report
  `skipped_missing_count == 0`.
- Fixture with one existing and one missing CIPI record should report
  `skipped_missing_count == 1`, both with and without `limit=1`.

Acceptance criteria:

- `--limit` does not inflate missing-file counts.
- `--fail-on-missing` still fails only when source files are missing.

## Task 5: Clean Lane Documentation Duplication

Objective:
Remove the duplicated Lane 2 `Rules:` block in `docs/analysis_lanes.md`.

Files likely touched:

- `docs/analysis_lanes.md`
- maybe `tests/unit/test_analysis_lanes.py` if it checks exact text.

Implementation notes:

- Keep the richer new Rules block that mentions shared `DatasetRecord` loads,
  JSON load reports, and configured roots.
- Remove the shorter duplicate block.
- Do not change lane boundaries.

Tests or validation:

- Run `tests/unit/test_analysis_lanes.py`.

Acceptance criteria:

- Lane 2 has one `Rules:` section.
- Existing analysis-lane tests pass.

## Task 6: Run Focused Verification

Objective:
Verify the cleanup did not disturb adapter behavior or matrix consumers.

Files likely touched:

- none.

Suggested commands:

```bash
conda run -n piano-difficulty python -m pytest -q \
  research/piano_difficulty/tests/unit/test_dataset_config.py \
  research/piano_difficulty/tests/unit/test_dataset_discovery.py \
  research/piano_difficulty/tests/unit/test_dataset_records.py \
  research/piano_difficulty/tests/unit/test_dataset_validation.py \
  research/piano_difficulty/tests/unit/test_oktav_dataset_catalog.py \
  research/piano_difficulty/tests/unit/test_cipi_dataset_catalog.py \
  research/piano_difficulty/tests/unit/test_cipi_python_analysis.py \
  research/piano_difficulty/tests/unit/test_dataset_scripts.py \
  research/piano_difficulty/tests/unit/test_analysis_lanes.py \
  research/piano_difficulty/tests/integration/test_dataset_local_smoke.py
```

Acceptance criteria:

- Focused dataset and docs tests pass.
- Local-corpus smoke tests skip cleanly when roots are not configured.

## Task 7: Run Full Piano-Difficulty Verification

Objective:
Confirm the cleanup did not regress unrelated piano-difficulty harnesses.

Files likely touched:

- none.

Suggested command:

```bash
conda run -n piano-difficulty python -m pytest -q research/piano_difficulty/tests
```

Acceptance criteria:

- Full piano-difficulty test suite passes, or any failure is clearly documented
  as pre-existing and unrelated.

## Final Review Checklist

Before finishing, confirm:

- no raw corpus files were added;
- no generated bulk artifacts were added;
- no real local absolute dataset paths were committed;
- `rg "resolve_dataset_root\\(" research/piano_difficulty/tests/harness
  research/piano_difficulty/tests/scripts` shows active adapter/script usage,
  not only tests;
- `rg "cipi_dataset_catalog.csv" research/piano_difficulty` shows only legacy
  or historical references;
- `docs/analysis_lanes.md` has no duplicated Lane 2 Rules block;
- `git diff` shows only scoped cleanup changes.
