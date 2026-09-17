# Scripts — CEO demo

Thin backend helpers for the CEO demo catalog (11 curated pieces). Deterministic, scoped to the catalog. The demo presents one consistent model: the 9-aspect difficulty taxonomy.

## Implemented

- **`build_demo_piece.py`** — Reusable backend package generator. Reads a single MusicXML score from `data/source_scores/` and runs the existing `piano_difficulty` pipeline (`analyze_score` + `write_analysis_outputs`), writing frontend-ready artifacts under `artifacts/<piece_id>/`:
  - `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv` (via `research/piano_difficulty/src/piano_difficulty/output/overview.py:157`)
  - `demo_manifest.json` — compact manifest for the mini-GUI: supporting feature traces for the timeline/hotspots plus the 9-aspect taxonomy payload (`difficulty_aspects` / `aspects`, 9 aspects), caveats, and snippet placeholders. The manifest is the single source of truth for the frontend.

  The script builds the manifest from the 9-aspect taxonomy as the user-facing model. Chart/hotspot traces are supporting feature signals inside that model (backend provenance includes feature traces; see manifest `chart.series` provenance). It does not present a competing taxonomy to the user.

  Technical: the script requests both `difficulty_aspects` and supporting feature traces via `analyze_score(..., profile_ids=("difficulty_aspects","difficulty_overview"))`. The `difficulty_overview` profile is a backend provenance detail only (feature-trace source for the timeline) and is not a user-facing taxonomy; the frontend describes all traces as supporting signals inside the 9-aspect model.

  Usage (from repo root):

  ```bash
  # Single piece — explicit catalog identity
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py \
    --piece-id debussy_arabesque_1 \
    --score research/learning_support/ceo_demo/data/source_scores/debussy_arabesque-no-1.musicxml \
    --title "Arabesque No. 1" \
    --composer "Claude Debussy" \
    --dataset cipi \
    --dataset-id x-336 \
    --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml \
    --out-dir research/learning_support/ceo_demo/artifacts/debussy_arabesque_1

  # All 11 catalog pieces — run the above for each piece_id/score pair
  # (see hub README.md for the full catalog)
  ```

  Reruns deterministically overwrite the artifact directory in place. Missing source files are reported clearly (exit 2) without breaking other pieces.

- **`build_debussy_demo.py`** — Thin compatibility wrapper for the original Debussy-only command. Delegates to `build_demo_piece.py` with Debussy defaults (`debussy_arabesque_1`, CIPI x-336). Existing documented commands keep working:

  ```bash
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_debussy_demo.py
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_debussy_demo.py --score <path> --out-dir <dir>
  ```

- **`render_demo_snippets.py`** — Generic offline snippet renderer. Reads hotspot measure ranges from any `demo_manifest.json`, extracts those ranges from the given MusicXML via `music21`, renders each snippet ahead of time using MuseScore → PDF → `pdftoppm`/`gs` → PNG (Pillow stitching for multi-page), and updates the manifest in place:
  - per-hotspot: `snippet_image: snippets/hotspot_001.png`, `snippet_status: rendered` (or `render_failed`), `snippet_diagnostic: null`/concise error
  - top-level: `snippet_status`/`snippet_diagnostic` aggregated
  - output dir: `artifacts/<piece_id>/snippets/hotspot_*.png` (stable rank-based filenames)

  Usage (from repo root, piano-difficulty env with `music21`):

  ```bash
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/render_demo_snippets.py \
    --score research/learning_support/ceo_demo/data/source_scores/debussy_arabesque-no-1.musicxml \
    --manifest research/learning_support/ceo_demo/artifacts/debussy_arabesque_1/demo_manifest.json \
    --snippets-dir research/learning_support/ceo_demo/artifacts/debussy_arabesque_1/snippets

  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/render_demo_snippets.py \
    --score research/learning_support/ceo_demo/data/source_scores/oktav_le-onde_OK00027.xml \
    --manifest research/learning_support/ceo_demo/artifacts/oktav_le_onde/demo_manifest.json \
    --snippets-dir research/learning_support/ceo_demo/artifacts/oktav_le_onde/snippets --dpi 150
  ```

  Requires `music21`, MuseScore 4 (`mscore`), and `pdftoppm` (poppler) or `gs`. Failures are explicit per hotspot (`snippet_status: "render_failed"` with concise diagnostic; manifest remains loadable) and re-runs without `--overwrite` reuse existing valid PNGs. Deterministic, offline/pre-rendered.

- **`render_debussy_snippets.py`** — Debussy-only compatibility wrapper (keeps original defaults). For new pieces, use `render_demo_snippets.py` directly.

  ```bash
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/render_debussy_snippets.py
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/render_debussy_snippets.py --manifest <path> --snippets-dir <dir> --dpi 150
  ```

- **`validate_demo_readiness.py`** — Thin deterministic readiness check for the static 11-piece walkthrough. No recompute, no analysis-semantics change, stdlib only. Validates:
  - `artifacts/pieces.json` exists and contains exactly the 11 expected `ready` pieces with correct `manifest_url`/`artifact_base` and Oktav labels phrased as original dataset labels only.
  - each `artifacts/<piece_id>/demo_manifest.json` exists and exposes frontend-required fields: `piece` metadata, `chart`/`series` (exactly 9 aspect series), `hotspots`, 9-aspect taxonomy payload via `difficulty_aspects`/`aspects` (exactly 9 aspects), `caveats`/`diagnostics`.
  - hotspot snippet references are either `rendered` with an existing image file under `artifacts/<piece_id>/snippets/` or explicitly `not_rendered`/`render_failed` with diagnostic text; top-level `snippet_status`/`snippet_diagnostic` consistent.

  Usage (from repo root):

  ```bash
  # Human-readable report — prints 11/11 pieces ready or actionable failures
  python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py

  # JSON output for CI
  python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py --json

  # Custom catalog path
  python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py --pieces research/learning_support/ceo_demo/artifacts/pieces.json
  ```

  Exit 0 when `11/11 pieces ready`; non-zero with specific field-level errors. Existing demo artifacts remain compatible with the static frontend (`web/app.js` reads the same `pieces.json` → `demo_manifest.json` contract). See also `research/learning_support/tests/unit/test_validate_demo_readiness.py`.

- **`run_live_demo_server.py`** — Local live-demo server for on-demand analysis. Keeps the 11-piece static catalog working exactly as before and adds a search/analyze flow over the full CIPI and Oktav corpora (no bulk corpus mirror, no notation PNG rendering live).

  ```bash
  conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/run_live_demo_server.py --port 8000
  # then open http://127.0.0.1:8000/research/learning_support/ceo_demo/web/
  ```

  Serves existing static web files and `artifacts/` plus JSON API:
  - `GET /api/datasets`
  - `GET /api/pieces?dataset=<cipi|oktav>&q=<query>` — substring search over composer/title/id/path
  - `POST /api/analyze` — `{dataset, piece_id|dataset_relative_path|piece_uid}` for a selected result (async job)
  - `GET /api/jobs/<job_id>` — poll `queued → running → succeeded|failed`; on success returns `manifest_url` under `artifacts/live/<safe_piece_id>/demo_manifest.json` that the existing frontend loads into the chart/hotspot UI

  Analysis is delegated to `build_demo_piece.py` as a subprocess (same 9-aspect pipeline) and writes under `artifacts/live/<safe_piece_id>/` with at least `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv`, `demo_manifest.json`. Indexes are built lazily on startup/first request (CIPI from `evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` against the CIPI root; Oktav from `tests/artifacts/oktav_dataset/python_analysis/full_run/load_report.json` against the Oktav root; fallback to directory scan). `safe_piece_id` is stable, e.g. `live_cipi_…`, `live_oktav_…`. Missing source files or failed analysis yield `failed` job with `error`/`log`. Claim boundaries preserved: labels are provenance only, output is symbolic-score evidence, no calibrated learner grade, Oktav labels are not Gradus grades.

## Intended future scripts

- **Rebuild catalog `artifacts/pieces.json`** — helper to regenerate the pieces catalog from the set of built artifact folders (currently maintained by hand for the 11 curated entries).

Future scripts should remain thin, deterministic, and scoped to the catalog demo. Claim boundaries: symbolic-score evidence only; no calibrated learner grade, no measured learning benefit, no production score-viewer claim.

## Manifest interpretation

The manifest is consumed by `web/app.js` as a 9-aspect taxonomy artifact. `chart.series`/`chart.composite`/`hotspots` are supporting signals for visualization; `difficulty_aspects`/`aspects` is the 9-aspect taxonomy coverage. Do not document or present these as two competing taxonomies. `difficulty_overview` appears only as technical provenance for the supporting traces in scripts/docs, never as visible UI copy.
