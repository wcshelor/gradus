# David CIPI Walkthrough Harness

Curated demo-evidence harness over existing piano-difficulty analysis code.
It runs a small set of familiar CIPI pieces through the current
`difficulty_overview` pipeline and writes stable per-piece artifacts for a
David/company walkthrough.

## What this is not

- **No new difficulty math is owned here.** Single-piece analysis calls the
  existing runtime path (`piano_difficulty.pipeline.analyze_score` plus
  `piano_difficulty.output.overview.write_analysis_outputs`).
- **Raw CIPI score files stay outside the repo.** Rows resolve against the
  committed canonical movement manifest
  (`evaluation_scores/manifests/cipi/cipi_movement_manifest.csv`) and locate
  files under a local dataset root (`--dataset-root`, `GRADUS_CIPI_ROOT`, or
  `.local/datasets.toml`). Only the curated manifest and generated reports
  are committed.
- **Not a research lane.** This is a demo/review surface, not a new analysis
  method. Do not add lane-style experiments here.
- **No learning-support parsing of CIPI.** Learning support consumes the
  generated evidence; all CIPI resolution lives in this harness.

## Layout

- Curated manifest:
  `evaluation_scores/manifests/david_walkthrough/cipi_familiar_v1.csv`
  (eight familiar pieces; adding another demo piece is a one-row change —
  keep `demo_id` stable once a run has been shared).
- Harness code: `tests/harness/david_walkthrough/`
  (`manifest.py`, `cipi_selection.py`, `artifacts.py`, `runner.py`,
  `reports.py`).
- Thin runner: `tests/scripts/run_david_cipi_walkthrough.py`.
- Generated artifact root:
  `tests/artifacts/david_walkthrough/cipi_familiar_v1/<demo_id>/`
  with `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv`,
  `piece_context.json`, and `demo_notes.md` per piece, plus top-level
  `index.json`, `index.md`, and `failures.csv` (when any piece fails).

## Usage

Check local CIPI setup without running analysis:

```bash
conda run -n piano-difficulty python -m tests.scripts.run_david_cipi_walkthrough --dry-run
```

Full demo run (requires a local CIPI root for all eight pieces):

```bash
conda run -n piano-difficulty python -m tests.scripts.run_david_cipi_walkthrough
```

Options: `--dataset-root`, `--manifest-csv`, `--canonical-manifest-csv`,
`--out-dir`, `--limit`, `--dry-run`, `--fresh-run-dir`.

## Rerun policy (David-CIPI-19)

Reruns overwrite the explicit output directory in place: before writing,
the harness removes previously generated per-piece directories for the
planned `demo_id` values and stale top-level `index.json`/`index.md`/
`failures.csv` files, so old and new evidence can never silently mix.
Pass `--fresh-run-dir` to allocate a timestamped run directory under the
output parent instead. Outputs for `demo_id` values no longer in the
manifest are left untouched.

## Claim boundaries

Generated walkthrough notes show analysis computed from symbolic scores,
relative within-piece factor profiles, candidate high-demand sections, and
manual passage-selection framing. They must not claim calibrated difficulty
grades, measured learning benefit, personalized diagnosis, fingering or
performance feedback, or production readiness. Within-piece ranks are
descriptive inside one score only.
