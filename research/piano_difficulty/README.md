# Piano difficulty analysis

This research area owns symbolic score extraction, the public difficulty
overview, and the score-derived practice payload for Gradus. Analyze a piece
to inspect the 9-aspect difficulty framework, the conservative overview slice,
local peaks, and candidate high-demand sections.

## Current semantic-token / practice-chunk lane

Current semantic extraction and practice-chunk work lives in
`src/piano_difficulty/semantic_tokens/`, with the design direction documented in
[`docs/practice_chunks.md`](docs/practice_chunks.md). The current Clair de Lune
review artifacts live under:

```text
tests/artifacts/practice_chunk_review/clair_de_lune_25_26/
tests/artifacts/practice_chunk_review/clair_de_lune_27_28/
tests/artifacts/semantic_breakdown/clair_de_lune_current/
```

Use [`docs/current_practice_chunking.md`](docs/current_practice_chunking.md) to
distinguish these current artifacts from older learning-support demo outputs.

## Setup

From the repository root:

```bash
conda env create -f research/piano_difficulty/environment.yml
conda run -n piano-difficulty python -m pip install -e 'research/piano_difficulty[dev]'
conda run -n piano-difficulty python -m pytest -q
```

The explicit editable install also repairs an environment left over from the
repository move. Existing environments need only the last two commands.
For external replication tools, initialize the pinned submodules with
`git submodule update --init --recursive`. The overview itself needs neither
the external corpora nor the research harness.

## Analyze a piece

```bash
conda run -n piano-difficulty piano-difficulty analyze piece.mxl --out-dir analysis
```

The command prints a readable overview and writes:

- `analysis.json`: canonical extraction and versioned overview;
- `analysis.md`: factor summaries, sections, factor peaks, and diagnostics;
- `analysis.html`: standalone timeline with raw values available on hover;
- `analysis.csv`: factor tracks and exact score locations.

Supported inputs: `.musicxml`, `.xml`, and `.mxl`.

Defaults use overlapping two-measure windows with stride one. Scores with a
single or constant window still show raw demands but have no distinct local
peak. The five reviewed overview factors cover onset density, pitch
transitions, simultaneous spans, hand timing mismatch, and accidentals.
All existing raw descriptors remain in the extraction output.

The main Gradus vocabulary is the 9-aspect difficulty taxonomy documented in
[difficulty_aspect_taxonomy.md](docs/difficulty_aspect_taxonomy.md). The default
analysis now emits `difficulty_aspects.v1` first, followed by the smaller
`difficulty_overview.v1` compatibility slice used for timeline exports and
older demo reports.

```bash
piano-difficulty analyze piece.mxl --format json
piano-difficulty analyze piece.mxl --hand right --window-size 1
piano-difficulty analyze piece.mxl --window beat --window-size 4 --stride 1
piano-difficulty analyze-batch scores/ --out-dir analyses/ --write-csv
piano-difficulty extract piece.mxl
piano-difficulty analyze piece.mxl --profile scoreanalyzer_reference --format json
piano-difficulty analyze piece.mxl --profile difficulty_aspects --format json
piano-difficulty analyze piece.mxl --gradus --format json
piano-difficulty analyze piece.mxl --explain-events --format json  # post-process flagged passages into difficulty events
```

Beat units are quarter notes. Regions use exact rational half-open intervals.
Explicit `--profile` choices replace the default; repeat the flag to compare
profiles. Batch runs continue after individual input failures and return a
nonzero exit code when any score fails.

## Python API

```python
from piano_difficulty import analyze_score, extract_score
from piano_difficulty.difficulty_analysis.overview import OverviewOptions

result = analyze_score("piece.mxl", overview_options=OverviewOptions(window_size=2))
payload = result.to_json_payload()
```

`extract_score` retains the existing direct descriptor contract.
`analyze_score` now defaults to `difficulty_aspects` plus
`difficulty_overview`, with the 9-aspect profile first. Request
`profile_ids=("difficulty_overview",)` for only the older 5-factor overview, or
`profile_ids=("scoreanalyzer_reference",)` to reproduce the legacy analysis.
`AnalysisResult.to_gradus_payload()` builds the opt-in
`gradus.practice_payload.v1` payload for practice cards, hotspots, routines,
feedback-derived recommendations, and learner-visible demand labels.
`analyze_score(..., explain_events=True)` adds `difficulty_events.v1` that
subdivides already-flagged passages into overlapping playable events with
metric evidence, optional note evidence, confidence, and explicit uncertainty
without changing difficulty scores.

## Interpretation

Ranks describe the selected within-piece profile. They are not calibrated
difficulty grades or estimates for an individual learner. Raw units,
normalization, window settings, support windows, source event IDs, and caveats
remain available in JSON. Section contributions refer to a named representative
window; region event IDs identify inputs, not a semantic diagnosis.

The overview uses exact attack selection. Incoming sustains and transitions
across a window start are not counted as new attacks. Hand inference remains
conservative and staff-based. See [difficulty_model.md](docs/difficulty_model.md)
for the complete method and limitations.

Gradus practice output should use musically precise, student-visible language:
not plain-language simplification, but also not teacher-only framing. The
canonical conceptual vocabulary is the 9-aspect taxonomy; any practice-demand
labels should map back to those aspects and preserve limitations/provenance.

## Architecture and research lanes

- [Architecture](docs/architecture.md): module ownership and dependency direction.
- [Factor registry](docs/feature_registry.md): selected factors and retained descriptors.
- [Difficulty aspect taxonomy](docs/difficulty_aspect_taxonomy.md): canonical
  9-aspect framework and validation boundaries.
- [Research lanes](docs/analysis_lanes.md): Yan reconstruction, datasets, OMR,
  Difficulty Dynamics experiments, matrix evaluation, and legacy parity.
- [Dataset adapter cleanup task plan](docs/dataset_adapters_cleanup_task_plan.md):
  focused cleanup tasks after the external dataset adapter implementation.
- [Consolidation record](docs/consolidation.md): preservation map and migration evidence.
- [Evaluation](docs/evaluation.md): automated checks and remaining expert review.
- [Roadmap](docs/roadmap.md): current follow-up work.
- [PracticeChunks](docs/practice_chunks.md): hierarchical grouping model for score understanding and practice (traits, hierarchy, fallback grouping, notation markings).
- [Consolidation task list — 2026-09-05](docs/Task_list_2026-09-05_difficulty_analysis_consolidation.md): detailed implementation handoff and acceptance checks.
- [Legacy workflows](docs/legacy_workflows.md): preserved historical commands.

Runtime code lives in `src/piano_difficulty/`. Configured experiments and
dataset loops live in `tests/harness/`; thin wrappers stay in `tests/scripts/`.
Generated research evidence stays in `tests/artifacts/`. Corpus manifests and
labels stay in `evaluation_scores/`.

Difficulty Dynamics now consumes the promoted runtime engine. Its old imports
remain compatibility wrappers; its experimental defaults retain the legacy
whole-overlapping-measure selection policy, recorded in its metadata.
Prediction, clustering, Yan, dataset and OMR workflows remain research lanes.
