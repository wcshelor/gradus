# Web — David demo mini-GUI (6 learner-facing graph dimensions + 9-aspect backend, catalog-driven)

Polished, lightweight wrapper that feels like one coherent local app: first screen shows the 12 pre-analyzed catalog clearly at top, plus a choose/analyze flow for local CIPI/Oktav files on the same page. 6 learner-facing graph dimensions (`gradus.front_graph_taxonomy.v2`) for the visible chart; 9-aspect backend taxonomy (`difficulty_aspects.v1`) is coverage/provenance only (not the graph).

## What this demo does

- **Screen 1 — two clear sections (same page):**
  - **Choose a piece (always visible at top)** — Fetches catalog via `/api/catalog` (live server) with fallback to `../artifacts/pieces.json`, shows all 12 curated pieces as clickable rows (title, composer, tag like Henle 3 / Oktav 43); clicking a row directly opens the same graph/hotspot view. Subtle caveat: “Source labels are for reference only.” Works even if CIPI/Oktav live dataset roots are missing; catalog is impossible to miss (accent-left card, badge count). Missing/unavailable pieces are disabled and do not block others.
  - **Analyze another piece (below catalog)** — Title “Analyze another piece”, copy “Search the local CIPI or Oktav library.” Dataset selector CIPI/Oktav + search box backed by `GET /api/pieces` over local dataset indexes (allowlisted paths; no upload/cloud). Results list from local folder/index; **Analyze piece** → `POST /api/analyze` → poll `/api/jobs/<id>` → on success load returned manifest into **the same** 6-way graph/hotspot UI. No API/path wording in the main UI unless there is an error. Optional future: choose local MusicXML/MXL file as local ad-hoc analysis, labelled separately from curated/dataset-backed analysis.
- **After loading** — shows piece title/composer with small source label (e.g. CIPI · Henle 4) and **Difficulty overview** immediately below — no metadata cards above the graph. A secondary “Open in MuseScore” action lives near the title when the live server is available.
- **Difficulty overview** — SVG with stable `960×340` dimensions (no layout shift), titled “Difficulty overview”:
  - graph-dimension toggles **below** the graph labeled “Show dimensions” with user-facing names: Finger Dexterity, Hand Movement, Coordination, Rhythm & Timing, Expression, Reading (composite as “Overall”)
  - traces from `chart.series[].normalized_values` — 6 dimensions
  - optional overall dashed line (mean of dimensions)
  - clickable star markers for key passages
- **Key passages** — list below the graph and detail panel beside it; selecting a passage shows plain-language explanation and snippet image when available.
- **Provenance** — caveats and analysis details are inside a collapsed “About this analysis” disclosure at the bottom, not in the hero area. Footer reads “Local symbolic-score demo. Source labels are for reference only.”

Frontend consumes catalog via `GET /api/catalog` when live server runs (fallback `artifacts/pieces.json`) and the selected `demo_manifest.json` (pre-analyzed or live `artifacts/live/<safe_id>/demo_manifest.json`). It does not fetch or parse `analysis.json` / `analysis.csv`; `chart.references` is ignored. Chart signals are 6 graph-dimension traces (`gradus.front_graph_taxonomy.v2`); 9-aspect taxonomy is backend coverage/provenance — not the visible graph.

## Files

```
web/
  index.html   # two-section Screen 1 (catalog top + live picker) + chart/detail layout
  styles.css   # restrained, demo-ready styling (catalog card elevated)
  app.js       # catalog via /api/catalog → fallback, unified applyManifest/onLoaded for catalog+live
  README.md    # this file
```

Relative paths (from `web/`):

```
../artifacts/pieces.json                # static fallback
/artifacts/pieces.json via /api/catalog # live convenience wrapper
../artifacts/<piece_id>/demo_manifest.json
../artifacts/live/<safe_id>/demo_manifest.json  # live-analyzed
../artifacts/<piece_id>/snippets/hotspot_*.png
```

Catalog shape (`artifacts/pieces.json`): `{ pieces: [{ id, title, composer, dataset, dataset_id, manifest_url, artifact_base, status: "ready", difficulty_label? }] }`. `difficulty_label` for Oktav entries is the original dataset label only (“Oktav 43” etc.) and is not a Gradus grade.

## Run locally — one canonical command

This demo feels like one coherent local app — start one live server, browser opens one page.

```bash
# from repo root — single canonical command (local-only)
conda run -n piano-difficulty python research/learning_support/david_demo/scripts/run_live_demo_server.py --port 8000
# then open (server prints the URL and tries to open it)
open http://127.0.0.1:8000/research/learning_support/david_demo/web/
# hard-refresh after updating artifacts
```

The live server serves static web + `artifacts/` and exposes `GET /api/catalog`, `GET /api/health` (with `catalog_exists`/`catalog_count`), `GET /api/datasets`, `GET /api/pieces`, `POST /api/analyze`, `GET /api/jobs/<id>`. Missing CIPI/Oktav roots do not hide or break the pre-analyzed catalog. Catalog and live analysis use the same final chart view.

**Legacy static fallback only** (artifact inspection, not main path):

```bash
python3 -m http.server 8000
open http://localhost:8000/research/learning_support/david_demo/web/
```

## Verification checklist

- [ ] Open `web/index.html` — first viewport visibly shows 12 catalog rows (Choose a piece) without needing to scroll past technical text
- [ ] Click a catalog row (Debussy/Satie/etc.) directly opens difficulty overview — no separate Load button step
- [ ] Start only `run_live_demo_server.py` — hard refresh — catalog shows 12 pieces (Satie, Debussy, etc. open without relying on static server)
- [ ] `GET /api/health` confirms `catalog_exists:true` + `catalog_count:12`
- [ ] Missing live dataset roots do not hide or break catalog (catalog via `/api/catalog` still 12)
- [ ] Search CIPI/Oktav in live picker → Analyze one small score → returned live manifest loads into same 6-way graph/hotspot view (applyManifest/onLoaded shared)
- [ ] UI copy avoids “upload”; uses “choose local dataset score” / “analyze local score”
- [ ] Docs say one canonical live command; static-server-only wording no longer main path
- [ ] Catalog `artifacts/pieces.json` contains 12 with correct `manifest_url` and `status: ready`
- [ ] Graph-dimension checkboxes (6) toggle traces only; composite toggle independent; default all on
- [ ] Hotspot stars + list chips clickable; detail panel updates; snippet states `not_rendered`/`render_failed`/`rendered` appropriate
- [ ] Aspects panel shows 9 backend aspects with readiness/provenance; chart is 6 dimensions; no calibrated score claim
- [ ] No frontend reference to `analysis.json` / `analysis.csv`
- [ ] Chart has stable dimensions; no layout shift

## Constraints kept

- Local-only; no product/upload/cloud claim. No true arbitrary upload — “choose from local dataset indexes” over CIPI/Oktav roots; allowlisted paths only. If raw `.mxl/.musicxml` file picker added later, label as local ad-hoc analysis, not curated catalog.
- No new analysis math, no company/product integration claims, not a marketing landing page.
- Plain HTML/CSS/JS, no broad dependencies.
- Symbolic-score evidence only; no calibrated learner grade, no measured learning benefit, no production score-viewer claim.
- Aspect 8/9 caveated material only as present in manifest (`caveats` shown in detail + aspects panel).

## Claim boundaries

- Not a calibrated score / no learner grade / symbolic-score evidence only.
- Oktav `difficulty_label` is the original dataset label, not a Gradus grade; not comparable across pieces.
- Aspects are unweighted descriptive buckets; timeline shows relative demands within this piece.
