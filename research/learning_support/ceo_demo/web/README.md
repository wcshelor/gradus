# Web — CEO demo mini-GUI (9-aspect taxonomy, catalog-driven)

Polished, lightweight static wrapper over the pre-analyzed catalog at `artifacts/pieces.json` and each `artifacts/<piece_id>/demo_manifest.json`. No backend, no snippet rendering, no new analysis math. Presents one consistent model: the 9-aspect difficulty taxonomy. Chart/hotspot traces are supporting signals inside that model, not a competing taxonomy.

## What this demo does

- **Load screen** — Fetches `artifacts/pieces.json` as the catalog, shows the 11 stored/preloaded pieces as selectable rows (Debussy pre-selected when present), and loads the selected `demo_manifest.json` on clicking **Load piece**. Missing or unavailable pieces are shown as disabled and do not block others. The manifest is the only data contract after selection.
- **After loading** — shows piece metadata (title, composer, dataset provenance, measure counts, window config, generation time) and transitions to the **Difficulty Chart** screen.
- **Difficulty Chart** — SVG with stable `960×340` dimensions (no layout shift):
  - supporting-signal toggles/checkboxes from `factors` / `chart.factor_ids` — default: all supporting signals enabled; toggles are display-only and reflect traces inside the 9-aspect model
  - traces from `chart.series[].normalized_values` (fallback `smoothed_values`) — toggles affect display only, not data
  - optional composite dashed line from `chart.composite.normalized_values`
  - clickable hotspot star markers from `hotspots` (placed at `representative_region.window_index` / `score_value`)
- **Right detail panel** — on hotspot click shows:
  - measure range (`measure_range` / `measure_numbers`), `score_value`, `section_id`, offsets, `score_position`, `method`
  - top contributors (`top_contributors[]` with share/normalized/raw/weighted + peak badge)
  - supporting `supporting_factor_ids` and `supporting_window_indices`
  - caveats/diagnostics (from `caveats` / `diagnostics`)
  - snippet image when `snippet_status: rendered` (`artifacts/<piece_id>/snippets/hotspot_*.png`), or explicit `not_rendered`/`render_failed` state from `snippet_status` / `snippet_diagnostic` (`snippet_image` is `null` when not yet rendered; failed snippets do not block the manifest)
- **9-aspect taxonomy panel** — grouped coverage from `difficulty_aspects` / `aspects` (9 aspects, readiness, included feature IDs, missing/limitations). No temporal series, no cross-aspect weights, not a calibrated score. Displayed as descriptive coverage inside the same 9-aspect model; timeline & hotspots are supporting signals, not a separate taxonomy.

Frontend consumes only `artifacts/pieces.json` (catalog) and the selected `demo_manifest.json`. It does not fetch or parse `analysis.json` / `analysis.csv`; `chart.references` is ignored. Chart signals are backend feature traces (technical provenance: `difficulty_aspects.v1` for aspects; chart series are supporting traces) — not presented as a competing user-facing taxonomy.

## Files

```
web/
  index.html   # load screen + metadata + chart + detail layout (9-aspect copy)
  styles.css   # restrained, demo-ready styling
  app.js       # catalog-driven manifest loading; SVG chart; hotspot interaction; 9-aspect panel
  README.md    # this file
```

Relative paths (from `web/`):

```
../artifacts/pieces.json
../artifacts/<piece_id>/demo_manifest.json
../artifacts/<piece_id>/snippets/hotspot_*.png
```

Catalog shape (`artifacts/pieces.json`): `{ pieces: [{ id, title, composer, dataset, dataset_id, manifest_url, artifact_base, status: "ready", difficulty_label? }] }`. `difficulty_label` for Oktav entries is the original dataset label only (“Oktav 43” etc.) and is not a Gradus grade.

## Run locally

Browser `fetch` is blocked on `file://`. Use a local static server:

```bash
# from repo root
python3 -m http.server 8000
# then open
open http://localhost:8000/research/learning_support/ceo_demo/web/
# or: http://localhost:8000/research/learning_support/ceo_demo/web/index.html
```

Alternatives (any static server works):

```bash
npx serve research/learning_support/ceo_demo/web
# or
python3 -m http.server 8000 --directory research/learning_support/ceo_demo/web
# but then manifest path must be served from repo root; prefer the first command
```

## Verification checklist

- [ ] Catalog `artifacts/pieces.json` contains all successfully built pieces (11) with correct `manifest_url` and `status: ready`
- [ ] Load screen shows piece list from catalog; Debussy is pre-selected when present; clicking rows changes selection
- [ ] Click **Load piece** — metadata appears and Difficulty Chart renders for the selected piece
- [ ] Switch back to load screen and load each additional ready piece — each loads without error
- [ ] Missing or not-ready piece appears disabled and does not block loading other pieces
- [ ] Supporting-signal checkboxes toggle traces only (data unchanged); composite toggle works independently
- [ ] Default: all supporting signals on, composite on
- [ ] Hotspot stars on chart are clickable; detail panel updates (measure range, score value, contributors, caveats, snippet image or placeholder)
- [ ] Hotspot list chips below chart also clickable and reflect selection
- [ ] Snippet area shows `not_rendered`/`render_failed`/`rendered` with diagnostic text appropriately; failed snippets do not break the manifest
- [ ] Aspects panel shows 9 aspects with readiness/coverage; no calibrated score claim
- [ ] No frontend reference to `analysis.json` / `analysis.csv` (check `app.js`/`index.html`)
- [ ] Chart has stable dimensions; no layout shift on toggle/hotspot
- [ ] Visible copy consistently says 9-aspect taxonomy; no competing taxonomy or layer framing (verify via search for legacy taxonomy terms per project brief)
- [ ] Overview profile name does not appear in visible UI copy (only as technical provenance in scripts/docs if at all)

## Constraints kept

- Static frontend only. No backend.
- No new analysis math, no generic multi-piece upload, no company/product integration claims, not a marketing landing page.
- Plain HTML/CSS/JS, no broad dependencies.
- Symbolic-score evidence only; no calibrated learner grade, no measured learning benefit, no production score-viewer claim.
- Aspect 8/9 caveated material only as present in manifest (`caveats` shown in detail + aspects panel).

## Claim boundaries

- Not a calibrated score / no learner grade / symbolic-score evidence only.
- Oktav `difficulty_label` is the original dataset label, not a Gradus grade; not comparable across pieces.
- Aspects are unweighted descriptive buckets; timeline shows relative demands within this piece.
