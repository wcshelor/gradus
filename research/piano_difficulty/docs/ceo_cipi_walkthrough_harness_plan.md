# CEO CIPI Walkthrough Harness Plan

Status: implementation handoff, planning only. No code is implemented by this
document.

This plan defines a small, reproducible harness for running a curated set of
familiar CIPI pieces through the existing piano-difficulty analysis pipeline and
turning the outputs into CEO-walkthrough evidence. The harness is a demo and
review surface over existing analysis behavior, not a new difficulty model and
not a product-runtime feature.

## Scope

Do:

- create a curated CIPI walkthrough manifest for familiar, relatively
  approachable repertoire;
- resolve rows against the canonical CIPI movement manifest;
- reuse existing CIPI root resolution and existing difficulty analysis/export
  code;
- produce stable per-piece artifacts that can be opened during a walkthrough;
- preserve score facts, system rankings, learner reports, and caveats as
  separate concepts;
- make adding another piece a one-row manifest change;
- add focused unit and smoke tests for each behavior.

Do not:

- add new difficulty factors, weights, or musical inference;
- copy raw CIPI files into the repository;
- make learning-support code parse CIPI directly;
- treat relative within-piece difficulty as a calibrated learner difficulty
  claim;
- claim pedagogical effectiveness;
- build a polished production UI in this harness.

## Proposed Locations

- Harness code:
  `research/piano_difficulty/tests/harness/ceo_walkthrough/`
- Thin runner:
  `research/piano_difficulty/tests/scripts/run_ceo_cipi_walkthrough.py`
- Curated manifest:
  `research/piano_difficulty/evaluation_scores/manifests/ceo_walkthrough/cipi_familiar_v1.csv`
- Generated artifacts:
  `research/piano_difficulty/tests/artifacts/ceo_walkthrough/cipi_familiar_v1/`
- Learning-support reference:
  `research/learning_support/ceo_demo_milestone_2026-09-06.md`

The harness belongs in piano difficulty because it resolves CIPI rows and runs
score analysis. Learning support consumes the resulting evidence for product
walkthrough scenarios.

## Initial Piece Set

The first manifest should include these eight pieces. Keep `demo_id` stable
after the first successful run because generated reports and walkthrough notes
will reference it.

| demo_id | composer | title | henle | dataset_relative_path | demo_role |
| --- | --- | ---: | ---: | --- | --- |
| beethoven_fur_elise | Ludwig van Beethoven | Bagatelle "Fur Elise" a minor WoO 59 | 3 | `pieces/beethoven/beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1.musicxml` | famous_easy |
| beethoven_bagatelle_119_10 | Ludwig van Beethoven | Bagatelle A major op. 119 no. 10 | 3 | `pieces/beethoven/beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml` | existing_preview_anchor |
| mozart_k545 | Wolfgang Amadeus Mozart | Piano Sonata "Facile" C major KV 545 | 4 | `pieces/mozart/mozart_1st-movement-allegro-from-piano-sonata-facile-c-major-kv-545-mvt1.musicxml` | classical_texture |
| chopin_waltz_a_minor_kk_ivb_11 | Frederic Chopin | Waltz a minor KK IVb,11 | 3 | `pieces/chopin/chopin_waltz-a-minor-kk-ivb,11-mvt1.musicxml` | easy_chopin |
| chopin_prelude_e_minor_28_4 | Frederic Chopin | Prelude e minor op. 28 no. 4 | 4 | `pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml` | expressive_simple |
| chopin_prelude_a_major_28_7 | Frederic Chopin | Prelude A major op. 28 no. 7 | 4 | `pieces/chopin/chopin_prelude-a-major-op.-28,7-mvt1.musicxml` | short_control |
| debussy_arabesque_1 | Claude Debussy | Arabesque no. 1 | 4 | `pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml` | flowing_arpeggiation |
| satie_gymnopedie_1 | Erik Satie | Gymnopedie no. 1 | 2 | `pieces/satie/satie_gymnopédie-no.-1-mvt1.musicxml` | sparse_baseline |

## Manifest Schema

Required columns:

- `demo_id`: stable unique identifier used for output directory names.
- `composer`: display composer name.
- `title`: display piece title.
- `henle`: CIPI/Henle label copied from the canonical manifest.
- `dataset_relative_path`: CIPI path, including the `pieces/` prefix.
- `recognition_tier`: short reviewer-facing familiarity estimate, for example
  `very_familiar`, `familiar`, or `useful_control`.
- `demo_role`: why this piece is in the walkthrough set.
- `analyzer_led_note`: what to inspect in the automatically selected sections.
- `user_selected_note`: suggested manual passage walkthrough framing.
- `disagreement_note`: learner-report-vs-ranking scenario framing.
- `caveat_note`: piece-specific warning or interpretation boundary.

Optional columns may be preserved as metadata, but the first version should
avoid open-ended schema growth unless the generated reports consume the fields.

## Output Contract

Each piece directory should be:

```text
tests/artifacts/ceo_walkthrough/cipi_familiar_v1/<demo_id>/
```

Required per-piece files:

- `analysis.json`: canonical analyzer payload.
- `analysis.md`: readable score-analysis overview.
- `analysis.html`: standalone timeline preview.
- `analysis.csv`: factor tracks and score locations.
- `piece_context.json`: manifest metadata, CIPI row identity, resolved local
  source path, status, runtime versions where available, and timestamps.
- `demo_notes.md`: short walkthrough notes generated from manifest fields and
  the top analysis result.

Required top-level files:

- `index.json`: machine-readable run summary.
- `index.md`: CEO-walkthrough entry point with links to every piece artifact,
  success/failure status, and reviewer checklist.
- `failures.csv`: present when any piece cannot be resolved or analyzed.

## Atomic Tasks

### CEO-CIPI-01: Create Harness README

Objective:
Add `tests/harness/ceo_walkthrough/README.md` explaining that this is a curated
demo-evidence harness over existing analysis code.

Likely files:

- `tests/harness/ceo_walkthrough/README.md`

Tests or validation:

- Documentation review only.

Acceptance criteria:

- README states that no new difficulty math is owned here.
- README states that raw CIPI files stay outside the repo.
- README points to the generated artifact root and the curated manifest.

### CEO-CIPI-02: Add Curated Manifest

Objective:
Create `evaluation_scores/manifests/ceo_walkthrough/cipi_familiar_v1.csv` with
the eight initial pieces and required fields.

Likely files:

- `evaluation_scores/manifests/ceo_walkthrough/cipi_familiar_v1.csv`

Tests or validation:

- A manifest-loader test later in CEO-CIPI-04 should prove all eight rows load
  in order.

Acceptance criteria:

- Every row has stable `demo_id`, `dataset_relative_path`, `demo_role`, and
  scenario notes.
- No absolute local paths appear in the manifest.

### CEO-CIPI-03: Define Manifest Schema

Objective:
Add a small schema definition for required columns and optional metadata
preservation.

Likely files:

- `tests/harness/ceo_walkthrough/manifest.py`
- `tests/unit/test_ceo_walkthrough_manifest.py`

Tests or validation:

- Missing required columns produce a clear validation error.
- Extra columns are preserved as metadata or rejected according to the chosen
  documented policy.

Acceptance criteria:

- Required columns are defined in one place.
- Error messages name the missing columns and source CSV.

### CEO-CIPI-04: Implement Manifest Loader

Objective:
Load the curated CSV into typed records or simple validated dataclasses.

Likely files:

- `tests/harness/ceo_walkthrough/manifest.py`
- `tests/unit/test_ceo_walkthrough_manifest.py`

Tests or validation:

- Loads the eight initial rows in manifest order.
- Trims blank string cells consistently.
- Preserves scenario-note fields.

Acceptance criteria:

- Loading a valid manifest returns deterministic records.
- Empty manifests and empty `dataset_relative_path` values are rejected.

### CEO-CIPI-05: Validate Stable IDs

Objective:
Reject duplicate or unsafe `demo_id` values before any analysis runs.

Likely files:

- `tests/harness/ceo_walkthrough/manifest.py`
- `tests/unit/test_ceo_walkthrough_manifest.py`

Tests or validation:

- Duplicate `demo_id` rows fail.
- IDs with path separators or blank values fail.
- Valid lowercase slug-style IDs pass.

Acceptance criteria:

- Output directories cannot collide or escape the artifact root.

### CEO-CIPI-06: Match Rows To Canonical CIPI Manifest

Objective:
Resolve each curated row against
`evaluation_scores/manifests/cipi/cipi_movement_manifest.csv`.

Likely files:

- `tests/harness/ceo_walkthrough/cipi_selection.py`
- `tests/unit/test_ceo_walkthrough_cipi_selection.py`

Tests or validation:

- Each initial curated `dataset_relative_path` matches exactly one CIPI movement
  row.
- Unknown paths fail with a structured missing-catalog-match result.
- Duplicate canonical matches fail loudly if ever encountered.

Acceptance criteria:

- The harness never trusts copied composer/title/Henle values without checking
  the canonical manifest.

### CEO-CIPI-07: Reuse CIPI Root Resolution

Objective:
Use the existing dataset-root behavior for local CIPI files:
explicit `--dataset-root`, `GRADUS_CIPI_ROOT`, config, then documented fallback.

Likely files:

- `tests/harness/ceo_walkthrough/cipi_selection.py`
- `tests/unit/test_ceo_walkthrough_cipi_selection.py`

Tests or validation:

- Explicit dataset root wins.
- Missing root is represented as a structured unresolved status.
- The harness does not create dataset roots.

Acceptance criteria:

- Root resolution logic is not duplicated if the shared resolver already covers
  the behavior.

### CEO-CIPI-08: Resolve Local Score Files

Objective:
Combine the resolved CIPI root and canonical `dataset_relative_path` to locate
each score file.

Likely files:

- `tests/harness/ceo_walkthrough/cipi_selection.py`
- `tests/unit/test_ceo_walkthrough_cipi_selection.py`

Tests or validation:

- Existing files resolve to absolute paths.
- Missing files produce per-piece failures and do not stop batch planning.
- Paths pointing directly at `pieces/` receive the existing CIPI diagnostic if
  that behavior is already exposed by the adapter.

Acceptance criteria:

- Every unresolved piece has a reason suitable for `failures.csv`.

### CEO-CIPI-09: Define Artifact Layout

Objective:
Add deterministic path planning for per-piece and top-level artifact files.

Likely files:

- `tests/harness/ceo_walkthrough/artifacts.py`
- `tests/unit/test_ceo_walkthrough_artifacts.py`

Tests or validation:

- A fixed output root and `demo_id` produce the expected paths.
- Unsafe IDs cannot create paths outside the output root.

Acceptance criteria:

- No timestamp is required for the default `cipi_familiar_v1` walkthrough root
  unless the CLI explicitly asks for a run-specific directory.

### CEO-CIPI-10: Run One Piece Through Existing Analysis

Objective:
Add a one-piece runner that calls the existing runtime analysis/export path and
writes the standard four analyzer artifacts.

Likely files:

- `tests/harness/ceo_walkthrough/runner.py`
- `tests/unit/test_ceo_walkthrough_runner.py`

Tests or validation:

- A committed safe score or tiny fixture writes `analysis.json`,
  `analysis.md`, `analysis.html`, and `analysis.csv`.
- Analyzer exceptions become structured per-piece errors.

Acceptance criteria:

- The implementation reuses existing analysis/export functions or the public
  CLI-equivalent code path.
- No new feature calculations are introduced.

### CEO-CIPI-11: Run Batch Without Global Failure

Objective:
Run all manifest rows and continue when individual rows fail.

Likely files:

- `tests/harness/ceo_walkthrough/runner.py`
- `tests/unit/test_ceo_walkthrough_runner.py`

Tests or validation:

- One intentionally bad row yields one failure while other rows still succeed.
- Batch summary includes attempted, success, and failure counts.

Acceptance criteria:

- The harness can produce partial demo evidence instead of failing all-or-nothing.

### CEO-CIPI-12: Write `piece_context.json`

Objective:
Write per-piece context containing manifest fields, canonical CIPI row fields,
resolution status, source path, generated artifact paths, and run metadata.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Required keys are present for successful pieces.
- Failed pieces include status and error reason.

Acceptance criteria:

- The context file is sufficient to audit which CIPI row produced each demo
  artifact.

### CEO-CIPI-13: Write `demo_notes.md`

Objective:
Generate a concise per-piece walkthrough note from manifest scenario fields and
the top analyzer section when available.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Notes include piece identity, demo role, analyzer-led note, user-selected
  note, disagreement note, caveats, and top section if analysis succeeded.
- Failed pieces still produce a clear note explaining why they are unavailable.

Acceptance criteria:

- Notes do not add pedagogical claims beyond the provided scenario framing and
  computed analysis evidence.

### CEO-CIPI-14: Generate `index.json`

Objective:
Create a machine-readable top-level summary for the walkthrough run.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Summary includes manifest path, output root, piece count, success count,
  failure count, and artifact paths.

Acceptance criteria:

- A later UI can consume `index.json` without reading the filesystem ad hoc.

### CEO-CIPI-15: Generate `index.md`

Objective:
Create a human-readable entry point for the CEO walkthrough.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Snapshot-style test verifies all eight initial pieces are listed.
- Links to per-piece `analysis.html`, `analysis.md`, and `demo_notes.md` are
  present for successful pieces.

Acceptance criteria:

- `index.md` includes a reviewer checklist that separates score facts, system
  ranking, learner report, and limitations.

### CEO-CIPI-16: Add Thin CLI Script

Objective:
Add a thin script entry point under `tests/scripts/`.

Likely files:

- `tests/scripts/run_ceo_cipi_walkthrough.py`
- `tests/unit/test_dataset_scripts.py` or a new script test file

Tests or validation:

- CLI help exposes `--dataset-root`, `--manifest-csv`, `--out-dir`, `--limit`,
  and `--dry-run`.
- The script delegates to harness code and stays thin.

Acceptance criteria:

- The script is runnable with:

```bash
conda run -n piano-difficulty python -m tests.scripts.run_ceo_cipi_walkthrough --dry-run
```

### CEO-CIPI-17: Add Dry-Run Mode

Objective:
Validate manifest rows, CIPI catalog matches, root resolution, and local file
availability without running score analysis.

Likely files:

- `tests/harness/ceo_walkthrough/runner.py`
- `tests/scripts/run_ceo_cipi_walkthrough.py`
- `tests/unit/test_ceo_walkthrough_runner.py`

Tests or validation:

- Dry run reports which pieces would run.
- Dry run writes or prints validation summary without `analysis.*` files.

Acceptance criteria:

- Users can check local CIPI setup quickly before the full demo run.

### CEO-CIPI-18: Add Failure Report CSV

Objective:
Write `failures.csv` when any piece fails at manifest validation, catalog match,
local file resolution, or analyzer execution.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Injected bad rows produce rows with `demo_id`, phase, reason, and source path
  where available.

Acceptance criteria:

- Failure reporting is explicit enough for non-technical walkthrough prep.

### CEO-CIPI-19: Define Rerun Freshness Policy

Objective:
Choose and document one policy for reruns: either cleanly overwrite an explicit
output directory or allocate timestamped run directories.

Likely files:

- `tests/harness/ceo_walkthrough/README.md`
- `tests/harness/ceo_walkthrough/artifacts.py`
- `tests/unit/test_ceo_walkthrough_artifacts.py`

Tests or validation:

- Rerunning cannot silently mix old and new per-piece outputs.

Acceptance criteria:

- The policy is clear in the README and enforced by code.

### CEO-CIPI-20: Validate Product Scenario Fields

Objective:
Require each manifest row to include at least one useful scenario note and a
caveat note.

Likely files:

- `tests/harness/ceo_walkthrough/manifest.py`
- `tests/unit/test_ceo_walkthrough_manifest.py`

Tests or validation:

- Blank scenario-note rows fail.
- The initial manifest passes.

Acceptance criteria:

- The harness cannot produce a walkthrough index that has analysis artifacts but
  no product framing.

### CEO-CIPI-21: Add Reviewer Checklist To Index

Objective:
Render the core CEO-review prompts in `index.md`.

Likely files:

- `tests/harness/ceo_walkthrough/reports.py`
- `tests/unit/test_ceo_walkthrough_reports.py`

Tests or validation:

- Snapshot checks for:
  - score facts;
  - system ranking;
  - learner self-report;
  - system hypothesis;
  - limitations.

Acceptance criteria:

- A reviewer can use the generated index to evaluate claim boundaries without
  reading source docs first.

### CEO-CIPI-22: Add Safe Local Smoke Test

Objective:
Use the committed small CIPI-safe subset or tiny fixtures so normal tests do not
require a full local CIPI root.

Likely files:

- `tests/unit/test_ceo_walkthrough_runner.py`
- `tests/integration/test_ceo_walkthrough_local_smoke.py` if an integration
  split is preferred

Tests or validation:

- Smoke test writes the expected artifact set for at least one available score.
- Full-corpus-only behavior skips cleanly when local CIPI is absent.

Acceptance criteria:

- The ordinary local suite remains runnable without private datasets.

### CEO-CIPI-23: Add Optional Full-CIPI Integration Test

Objective:
Run the full eight-piece manifest when `GRADUS_CIPI_ROOT` or an explicit local
config is available.

Likely files:

- `tests/integration/test_ceo_walkthrough_local_smoke.py`

Tests or validation:

- Test skips when CIPI is not configured.
- Test succeeds and produces all eight pieces when CIPI is configured.

Acceptance criteria:

- The CEO prep machine can verify the exact demo set end to end.

### CEO-CIPI-24: Link From Piano-Difficulty Docs

Objective:
Document the new harness from the relevant piano-difficulty docs.

Likely files:

- `tests/harness/ceo_walkthrough/README.md`
- `tests/harness/cipi_dataset/README.md`
- `tests/harness/difficulty_dynamics/README.md`
- `docs/analysis_lanes.md` if a demo-harness note is needed

Tests or validation:

- Documentation review only.

Acceptance criteria:

- The harness is discoverable without being mistaken for a new research lane.

### CEO-CIPI-25: Link From Learning-Support CEO Milestone

Objective:
Update the existing CEO milestone plan to point to the walkthrough harness and
generated artifact index.

Likely files:

- `research/learning_support/ceo_demo_milestone_2026-09-06.md`

Tests or validation:

- Documentation review only.

Acceptance criteria:

- The milestone doc continues to bound claims and notes that the harness
  produces computed evidence for the walkthrough.

## Implementation Order

1. Manifest and validation: CEO-CIPI-01 through CEO-CIPI-08.
2. Artifact layout and single-piece run: CEO-CIPI-09 through CEO-CIPI-13.
3. Batch, CLI, index, and dry run: CEO-CIPI-14 through CEO-CIPI-18.
4. Demo reliability and scenario checks: CEO-CIPI-19 through CEO-CIPI-23.
5. Documentation handoff: CEO-CIPI-24 through CEO-CIPI-25.

## Suggested Validation Commands

Use targeted tests while implementing:

```bash
conda run -n piano-difficulty python -m pytest research/piano_difficulty/tests/unit/test_ceo_walkthrough_manifest.py -q
conda run -n piano-difficulty python -m pytest research/piano_difficulty/tests/unit/test_ceo_walkthrough_cipi_selection.py -q
conda run -n piano-difficulty python -m pytest research/piano_difficulty/tests/unit/test_ceo_walkthrough_artifacts.py -q
conda run -n piano-difficulty python -m pytest research/piano_difficulty/tests/unit/test_ceo_walkthrough_reports.py -q
conda run -n piano-difficulty python -m pytest research/piano_difficulty/tests/unit/test_ceo_walkthrough_runner.py -q
```

Before handoff, run the narrow harness group and any existing adjacent tests
that were touched. Do not require private CIPI data for default unit tests.

## Claim Boundary

The generated walkthrough may show:

- analysis computed from symbolic scores;
- relative within-piece factor profiles;
- candidate high-demand sections;
- manual passage-selection scenarios;
- learner-report framing that does not overrule the learner.

The generated walkthrough must not claim:

- calibrated difficulty grades from the analyzer;
- measured learning benefit;
- personalized diagnosis;
- fingering, biomechanics, or performance feedback;
- production readiness.
