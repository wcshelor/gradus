# Scripts — David demo

Thin backend helpers for the David demo catalog (12 curated pieces). Deterministic, scoped to the catalog. The demo presents 6 learner-facing graph dimensions for the visible chart (`gradus.front_graph_taxonomy.v2`) and 9-aspect backend taxonomy for provenance.

## Implemented

- **`build_demo_piece.py`** — Reusable backend package generator. Reads a single MusicXML score from `data/source_scores/` and runs the existing `piano_difficulty` pipeline (`analyze_score` + `write_analysis_outputs`), writing frontend-ready artifacts under `artifacts/<piece_id>/`:
  - `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv` (via `research/piano_difficulty/src/piano_difficulty/output/overview.py:157`)
  - `demo_manifest.json` — compact manifest for the mini-GUI: 6 learner-facing graph dimensions drive the visible chart (`chart.series` / `chart.graph_dimension_ids` / `chart.composite`, `gradus.front_graph_taxonomy.v2`), plus the 9-aspect taxonomy payload (`difficulty_aspects` / `aspects`, 9 aspects) for backend coverage/provenance, caveats, and snippet placeholders. The manifest is the single source of truth for the frontend.

  The script builds the visible chart from `front_graph_taxonomy` / `graph_taxonomy` (6 dimensions) inside the `difficulty_aspects` profile. 9-aspect taxonomy stays as backend provenance. Chart/hotspot traces are graph-dimension signals (visible) with feature-level provenance. It does not silently fall back to presenting 9 aspects as the graph.

  Technical: the script requests both `difficulty_aspects` and supporting feature traces via `analyze_score(..., profile_ids=("difficulty_aspects","difficulty_overview"))`. The `difficulty_overview` profile is a backend provenance detail only and is not the visible graph; the visible graph is `front_graph_taxonomy` (6 dimensions) from the `difficulty_aspects` payload.

  Usage (from repo root):

  ```bash
  # Single piece — explicit catalog identity
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py \
    --piece-id debussy_arabesque_1 \
    --score research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml \
    --title "Arabesque No. 1" \
    --composer "Claude Debussy" \
    --dataset cipi \
    --dataset-id x-336 \
    --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml \
    --out-dir research/learning_support/david_demo/artifacts/debussy_arabesque_1

  # All 12 catalog pieces — run the above for each piece_id/score pair
  # (see hub README.md for the full catalog)
  ```

  Reruns deterministically overwrite the artifact directory in place. Missing source files are reported clearly (exit 2) without breaking other pieces.

- **`build_debussy_demo.py`** — Thin compatibility wrapper for the original Debussy-only command. Delegates to `build_demo_piece.py` with Debussy defaults (`debussy_arabesque_1`, CIPI x-336). Existing documented commands keep working:

  ```bash
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_debussy_demo.py
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_debussy_demo.py --score <path> --out-dir <dir>
  ```

- **`rebuild_demo_analysis.py`** — Convenience wrapper for debugging analysis
  changes. Reads `artifacts/pieces.json`, resolves each curated source score,
  and reruns `build_demo_piece.py` in place so current feature extraction,
  taxonomy weights, hotspot logic, and explanation code are reflected in the
  static demo artifacts.

  ```bash
  # List known catalog ids
  python research/learning_support/david_demo/scripts/rebuild_demo_analysis.py --list

  # Rebuild every catalog piece with current defaults
  python research/learning_support/david_demo/scripts/rebuild_demo_analysis.py --validate

  # Rebuild just Clair de Lune while debugging
  python research/learning_support/david_demo/scripts/rebuild_demo_analysis.py debussy_clair_de_lune

  # Try alternate overview windows
  python research/learning_support/david_demo/scripts/rebuild_demo_analysis.py debussy_clair_de_lune --window-sizes 1,2,4

  # Show commands without running
  python research/learning_support/david_demo/scripts/rebuild_demo_analysis.py debussy_clair_de_lune --dry-run
  ```

- **`render_demo_snippets.py`** — Generic offline snippet renderer. Reads hotspot measure ranges from any `demo_manifest.json`, extracts those ranges from the given MusicXML via `music21`, renders each snippet ahead of time using MuseScore → PDF → `pdftoppm`/`gs` → PNG (Pillow stitching for multi-page), and updates the manifest in place:
  - per-hotspot: `snippet_image: snippets/hotspot_001.png`, `snippet_status: rendered` (or `render_failed`), `snippet_diagnostic: null`/concise error
  - top-level: `snippet_status`/`snippet_diagnostic` aggregated
  - output dir: `artifacts/<piece_id>/snippets/hotspot_*.png` (stable rank-based filenames)

  Usage (from repo root, piano-difficulty env with `music21`):

  ```bash
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_demo_snippets.py \
    --score research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml \
    --manifest research/learning_support/david_demo/artifacts/debussy_arabesque_1/demo_manifest.json \
    --snippets-dir research/learning_support/david_demo/artifacts/debussy_arabesque_1/snippets

  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_demo_snippets.py \
    --score research/learning_support/david_demo/data/source_scores/oktav_le-onde_OK00027.xml \
    --manifest research/learning_support/david_demo/artifacts/oktav_le_onde/demo_manifest.json \
    --snippets-dir research/learning_support/david_demo/artifacts/oktav_le_onde/snippets --dpi 150
  ```

  Requires `music21`, MuseScore 4 (`mscore`), and `pdftoppm` (poppler) or `gs`. Failures are explicit per hotspot (`snippet_status: "render_failed"` with concise diagnostic; manifest remains loadable) and re-runs without `--overwrite` reuse existing valid PNGs. Deterministic, offline/pre-rendered.

- **`render_debussy_snippets.py`** — Debussy-only compatibility wrapper (keeps original defaults). For new pieces, use `render_demo_snippets.py` directly.

  ```bash
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_debussy_snippets.py
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_debussy_snippets.py --manifest <path> --snippets-dir <dir> --dpi 150
  ```

- **`validate_demo_readiness.py`** — Thin deterministic readiness check for the static 12-piece walkthrough. No recompute, no analysis-semantics change, stdlib only. Validates:
  - `artifacts/pieces.json` exists and contains exactly the 12 expected `ready` pieces with correct `manifest_url`/`artifact_base` and Oktav labels phrased as original dataset labels only.
  - each `artifacts/<piece_id>/demo_manifest.json` exists and exposes frontend-required fields: `piece` metadata, `chart`/`series` (exactly 6 graph dimension series with `graph_dimension_ids`), `chart.taxonomy_version`, `hotspots`, 9-aspect backend taxonomy payload via `difficulty_aspects`/`aspects` (exactly 9 aspects), `caveats`/`diagnostics`.
  - hotspot snippet references are either `rendered` with an existing image file under `artifacts/<piece_id>/snippets/` or explicitly `not_rendered`/`render_failed` with diagnostic text; top-level `snippet_status`/`snippet_diagnostic` consistent.

  Usage (from repo root):

  ```bash
  # Human-readable report — prints 12/12 pieces ready or actionable failures
  python research/learning_support/david_demo/scripts/validate_demo_readiness.py

  # JSON output for CI
  python research/learning_support/david_demo/scripts/validate_demo_readiness.py --json

  # Custom catalog path
  python research/learning_support/david_demo/scripts/validate_demo_readiness.py --pieces research/learning_support/david_demo/artifacts/pieces.json
  ```

  Exit 0 when `12/12 pieces ready`; non-zero with specific field-level errors. Existing demo artifacts remain compatible with the static frontend (`web/app.js` reads the same `pieces.json` → `demo_manifest.json` contract). See also `research/learning_support/tests/unit/test_validate_demo_readiness.py`.

- **`run_live_demo_server.py`** — Local live-demo server for on-demand analysis. Keeps the 12-piece static catalog working exactly as before and adds a search/analyze flow over the full CIPI and Oktav corpora (no bulk corpus mirror, no notation PNG rendering live).

  ```bash
  conda run -n piano-difficulty python research/learning_support/david_demo/scripts/run_live_demo_server.py --port 8000
  # then open http://127.0.0.1:8000/research/learning_support/david_demo/web/
  ```

  Serves existing static web files and `artifacts/` plus JSON API:
  - `GET /api/datasets`
  - `GET /api/pieces?dataset=<cipi|oktav>&q=<query>` — substring search over composer/title/id/path
  - `POST /api/analyze` — `{dataset, piece_id|dataset_relative_path|piece_uid}` for a selected result (async job)
  - `GET /api/jobs/<job_id>` — poll `queued → running → succeeded|failed`; on success returns `manifest_url` under `artifacts/live/<safe_piece_id>/demo_manifest.json` that the existing frontend loads into the chart/hotspot UI

  Analysis is delegated to `build_demo_piece.py` as a subprocess (same 6-dimension graph + 9-aspect backend pipeline) and writes under `artifacts/live/<safe_piece_id>/` with at least `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv`, `demo_manifest.json`. Indexes are built lazily on startup/first request (CIPI from `evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` against the CIPI root; Oktav from `tests/artifacts/oktav_dataset/python_analysis/full_run/load_report.json` against the Oktav root; fallback to directory scan). `safe_piece_id` is stable, e.g. `live_cipi_…`, `live_oktav_…`. Missing source files or failed analysis yield `failed` job with `error`/`log`. Claim boundaries preserved: labels are provenance only, output is symbolic-score evidence, no calibrated learner grade, Oktav labels are not Gradus grades.

## Intended future scripts

- **Rebuild catalog `artifacts/pieces.json`** — helper to regenerate the pieces catalog from the set of built artifact folders (currently maintained by hand for the 12 curated entries).

Future scripts should remain thin, deterministic, and scoped to the catalog demo. Claim boundaries: symbolic-score evidence only; no calibrated learner grade, no measured learning benefit, no production score-viewer claim.

## Manifest interpretation

The manifest is consumed by `web/app.js` as a 6-dimension graph artifact for the visible chart. `chart.series`/`chart.composite` are 6 graph-dimension signals (`graph_dimension_ids`, `taxonomy_version`); `difficulty_aspects`/`aspects` is the 9-aspect backend coverage/provenance (not the graph). `hotspots` are supporting evidence. Do not present 9 aspects as the graph — visible chart is 6 learner-facing dimensions. `difficulty_overview` appears only as technical provenance, never as visible UI copy.
