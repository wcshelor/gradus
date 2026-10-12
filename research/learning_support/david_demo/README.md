# David demo — small catalog mini-GUI (6 learner-facing graph dimensions + 9-aspect backend)

Status: historical presentation/demo lane. This workspace is not the current
semantic-token or practice-chunk evidence path. For current Clair de Lune
practice chunking, start with
`research/piano_difficulty/docs/current_practice_chunking.md` and
`research/piano_difficulty/tests/artifacts/practice_chunk_review/`.

This is a thesis/company David demo workspace, not a general product app and not a new difficulty-analysis lane.

It provides a self-contained hub for the David demo: canonical source scores, generated backend assets, and the mini-GUI. The demo presents a 6 learner-facing graph taxonomy (`gradus.front_graph_taxonomy.v2`) for the visible difficulty chart — Finger Dexterity, Hand Position / Movement, Coordination / Layers, Rhythm & Timing, Control / Expression, Notation / Reading. The 9-aspect backend taxonomy (`difficulty_aspects.v1`) remains available in `difficulty_aspects` / `aspects` for coverage/provenance (evidence, diagnostics, not the graph). Chart traces are graph-dimension signals (weighted means of normalized raw feature traces); hotspot traces remain supporting evidence. Difficulty-analysis runtime code stays in `research/piano_difficulty/`; learning-support passage-practice code stays in `research/learning_support/passage_practice/`.

## David demo feature set

The David demo intentionally uses a compact, score-native feature set. The goal is
to show a credible learner-facing experience: a score becomes a readable
difficulty map, high-demand passages are visible, and the system can explain
why a passage may need attention. This is not the place to settle every Yan et
al. feature ambiguity.

Included for the demo (visible graph is 6 learner-facing dimensions; 9-aspect backend is provenance):

| Feature family | Graph dimension(s) | Backend aspect(s) | Demo role |
|---|---|---|---|
| Note / attack density | Rhythm & Timing, Finger Dexterity | 1. Rhythmic demand | Shows how much is happening per unit of notated time. |
| Rhythmic variety | Rhythm & Timing, Finger Dexterity | 1. Rhythmic demand | Uses available duration, tuplet, shortest-value, and related rhythm traces to show local rhythmic complexity. |
| Leaps / displacement | Hand Position / Movement, Finger Dexterity | 2. Pitch / movement demand | Highlights large pitch transitions and relocation demands. |
| Hand span / chord size | Hand Position / Movement, Finger Dexterity, Coordination / Layers | 3. Hand-shape / span demand | Shows physical extension and simultaneous hand-shape pressure. |
| Polyphony / chord density | Coordination / Layers, Control / Expression | 4. Texture / polyphony demand | Shows vertical density, chordal writing, and multi-note texture. |
| Hand coordination | Coordination / Layers, Rhythm & Timing | 5. Coordination demand | Shows aligned vs. asynchronous hand activity and timing mismatch proxies. |
| Accidentals / reading load | Notation / Reading, Finger Dexterity / Hand Position | 6. Notation / reading demand | Gives a visible notation-demand signal that is easy to explain from the score. |
| Articulation / dynamics, descriptive only | Control / Expression, Finger Dexterity | 7. Expression / control demand | Provides color about written control demands without ranking expression as harder by default. |
| Hotspot timeline / candidate sections | Composite of 6 graph dimensions | Ranked from 9-aspect composite (provenance) but chart is 6-way | Makes demand visible over the piece and anchors the walkthrough in concrete measures. |

Visible chart uses 6 graph dimensions: `finger_dexterity`, `hand_movement_position`, `layers_coordination`, `rhythm_timing`, `expression_sound_control`, `notation_reading` (`gradus.front_graph_taxonomy.v2`). 9-aspect taxonomy (`difficulty_aspects.v1`) is backend coverage.

Deferred from the David demo:

- `distinct_stroke_rate`: unresolved Yan et al. definition; do not guess.
- `playing_speed_variation`: useful in MIDI/performance contexts, but weakly
  defined for sheet music unless tempo-change and rubato handling are made
  explicit.
- Pressing-velocity entropy / variability: performance/MIDI features, not
  score-only features.
- Melodic complexity, melodic originality, and degree of melodiousness:
  promising research targets, but formula recovery and score-native candidate
  experiments remain future work.
- Deep structural / pattern modeling: repetition, recurrence, motif reuse,
  novelty, and form-aware difficulty are deferred.
- Final feature weights or calibrated Gradus grades: prediction against
  difficulty labels is a validity target, but the demo does not claim a
  validated weighting model.

After the demo, the research track should return to the deferred set by building
candidate feature banks for dotted-note ratio / rhythmic variety, local and
global pitch entropy, melodic-complexity proxies, and structural-pattern
features, then testing them against available difficulty labels as one measure
of validity.

## Selected demo pieces (12 curated entries)

| piece_id | Composer | Title | Dataset | Notes |
|---|---|---|---|---|
| `beethoven_fur_elise` | Ludwig van Beethoven | Bagatelle "Für Elise" a minor WoO 59 | CIPI | Henle 3 |
| `beethoven_bagatelle_119_10` | Ludwig van Beethoven | Bagatelle A major Op. 119 No. 10 | CIPI | Henle 3 |
| `mozart_k545` | Wolfgang Amadeus Mozart | Piano Sonata "Facile" C major KV 545, 1st movement | CIPI | Henle 4 |
| `chopin_waltz_a_minor_kk_ivb_11` | Frédéric Chopin | Waltz a minor KK IVb,11 | CIPI | Henle 3 |
| `chopin_prelude_e_minor_28_4` | Frédéric Chopin | Prelude e minor Op. 28 No. 4 | CIPI | Henle 4 |
| `chopin_prelude_a_major_28_7` | Frédéric Chopin | Prelude A major Op. 28 No. 7 | CIPI | Henle 4 |
| `debussy_arabesque_1` | Claude Debussy | Arabesque No. 1 | CIPI x-336 | Henle 4 |
| `debussy_clair_de_lune` | Claude Debussy | Clair de Lune | CIPI x-190 | Henle 5 |
| `satie_gymnopedie_1` | Erik Satie | Gymnopédie No. 1 | CIPI | Henle 2 |
| `oktav_le_onde` | Ludovico Einaudi | Le Onde | OKTAV OK00027 | regular piano, difficulty around 43 (original dataset label; not a Gradus grade) |
| `oktav_a_thousand_miles` | Vanessa Carlton | A Thousand Miles | OKTAV OK00016 | PVG-Ac arrangement, difficulty around 53 (original label) |
| `oktav_viva_la_vida` | Coldplay | Viva la Vida | OKTAV OK00009 | PVG-RH arrangement, difficulty around 55 (original label) |

Oktav difficulty numbers are included as provenance only (`difficulty_label` in `pieces.json`); they are not presented as calibrated Gradus grades and are not comparable across pieces.

## Canonical source scores

```
research/learning_support/david_demo/data/source_scores/
  beethoven_fur-elise.musicxml
  beethoven_bagatelle-a-major-op-119-no-10.musicxml
  mozart_k545_mvt1.musicxml
  chopin_waltz-a-minor-kk-ivb-11.musicxml
  chopin_prelude-e-minor-op-28-no-4.musicxml
  chopin_prelude-a-major-op-28-no-7.musicxml
  debussy_arabesque-no-1.musicxml
  debussy_clair-de-lune.musicxml
  satie_gymnopedie-no-1.musicxml
  oktav_le-onde_OK00027.xml
  oktav_a-thousand-miles_OK00016.xml
  oktav_viva-la-vida_OK00009.xml
```

Each file is a single copied score for the demo catalog (not a bulk corpus copy). See `data/source_scores/README.md` for provenance per piece.

## Layout

```
research/learning_support/david_demo/
  README.md
  AGENTS.md
  data/source_scores/            # 12 canonical source scores
  data/source_scores/README.md
  artifacts/pieces.json          # catalog of pre-analyzed pieces
  artifacts/<piece_id>/          # generated demo artifacts per piece (analysis.* + demo_manifest.json + snippets/)
  scripts/README.md              # backend helpers (manifest + snippet rendering)
  web/README.md                  # mini-GUI (static, 6 learner-facing graph dimensions + 9-aspect backend, catalog-driven)
```

## Generated artifacts

Generated demo artifacts go under `artifacts/<piece_id>/` plus the catalog `artifacts/pieces.json`.

Each `artifacts/<piece_id>/` contains:

- `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv` (via `research/piano_difficulty/src/piano_difficulty/output/overview.py`)
- `demo_manifest.json` — compact manifest for the mini-GUI: 6 learner-facing graph dimensions drive the visible chart (`chart.series` / `chart.graph_dimension_ids` / `chart.composite`, `gradus.front_graph_taxonomy.v2`), plus the 9-aspect taxonomy payload (`difficulty_aspects` / `aspects`, 9 aspects) for backend coverage/provenance, caveats, snippet placeholders, and grouped practice targets (`hard_bits`/`practice_regions` with `core_region` + buffered `display_region` and `supporting_windows`/`supporting_resolutions` provenance). The manifest is the single source of truth for the frontend.

`artifacts/pieces.json` lists each available pre-analyzed piece with `id`, `title`, `composer`, `dataset`, `dataset_id`, `manifest_url`, `status: ready`, and optional `difficulty_label` for source-label provenance.

## How to regenerate one piece

```bash
# Example: Chopin Prelude in E minor
conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py \
  --piece-id chopin_prelude_e_minor_28_4 \
  --score research/learning_support/david_demo/data/source_scores/chopin_prelude-e-minor-op-28-no-4.musicxml \
  --title "Prelude in E minor Op. 28 No. 4" \
  --composer "Frédéric Chopin" \
  --dataset cipi \
  --dataset-id "chopin_prelude-e-minor-op.-28,4-mvt1" \
  --dataset-relative-path "pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml" \
  --out-dir research/learning_support/david_demo/artifacts/chopin_prelude_e_minor_28_4

# Debussy via compatibility wrapper (same output, Debussy defaults):
conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_debussy_demo.py
```

## How to regenerate all available pieces

```bash
# Run the builder for each of the 12 selected scores (from repo root):
conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id debussy_arabesque_1 --score research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml --title "Arabesque No. 1" --composer "Claude Debussy" --dataset cipi --dataset-id x-336 --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml --out-dir research/learning_support/david_demo/artifacts/debussy_arabesque_1

conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id chopin_prelude_e_minor_28_4 --score research/learning_support/david_demo/data/source_scores/chopin_prelude-e-minor-op-28-no-4.musicxml --title "Prelude in E minor Op. 28 No. 4" --composer "Frédéric Chopin" --dataset cipi --dataset-id "chopin_prelude-e-minor-op.-28,4-mvt1" --dataset-relative-path "pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml" --out-dir research/learning_support/david_demo/artifacts/chopin_prelude_e_minor_28_4

conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id beethoven_fur_elise --score research/learning_support/david_demo/data/source_scores/beethoven_fur-elise.musicxml --title "Für Elise" --composer "Ludwig van Beethoven" --dataset cipi --dataset-id "beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1" --dataset-relative-path "pieces/beethoven/beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1.musicxml" --out-dir research/learning_support/david_demo/artifacts/beethoven_fur_elise

conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id oktav_le_onde --score research/learning_support/david_demo/data/source_scores/oktav_le-onde_OK00027.xml --title "Le Onde" --composer "Ludovico Einaudi" --dataset oktav --dataset-id OK00027 --dataset-relative-path "Le Onde (Ludovico Einaudi) - piano MSMT OK00027.xml" --out-dir research/learning_support/david_demo/artifacts/oktav_le_onde

conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id oktav_a_thousand_miles --score research/learning_support/david_demo/data/source_scores/oktav_a-thousand-miles_OK00016.xml --title "A Thousand Miles" --composer "Vanessa Carlton" --dataset oktav --dataset-id OK00016 --dataset-relative-path "A Thousand Miles (Vanessa Carlton) - PVG-Ac MSMT OK00016 - 01.xml" --out-dir research/learning_support/david_demo/artifacts/oktav_a_thousand_miles

conda run -n piano-difficulty python research/learning_support/david_demo/scripts/build_demo_piece.py --piece-id oktav_viva_la_vida --score research/learning_support/david_demo/data/source_scores/oktav_viva-la-vida_OK00009.xml --title "Viva la Vida" --composer "Coldplay" --dataset oktav --dataset-id OK00009 --dataset-relative-path "Viva la Vida (Coldplay) - PVG-RH MSMT OK00009-01.xml" --out-dir research/learning_support/david_demo/artifacts/oktav_viva_la_vida
```

Reruns deterministically overwrite each artifact directory in place. After rebuilding, `artifacts/pieces.json` remains valid (it points to the same manifest paths); rebuild it if piece metadata changes.

## How to launch the demo (one canonical command)

This demo is a coherent local app — start one live server, open one page. No need to understand static vs live server, artifact paths, or API details.

```bash
# from repo root — single canonical command (local-only, no upload/cloud)
conda run -n piano-difficulty python research/learning_support/david_demo/scripts/run_live_demo_server.py --port 8000

# then open (server prints the URL and tries to open it)
open http://127.0.0.1:8000/research/learning_support/david_demo/web/
# hard-refresh after updating artifacts
```

First screen shows two clear sections: **Choose a piece** (always visible at top — 12 curated rows showing title, composer, tag like Henle 3 / Oktav 43; click a row to directly open the same graph/hotspot view; subtle caveat “Source labels are for reference only.”; works even if CIPI/Oktav dataset roots are missing) and **Analyze another piece** (below the catalog — “Search the local CIPI or Oktav library.” — choose from local dataset indexes over CIPI/Oktav roots, Search → **Analyze piece** → same chart; no API/path wording unless error). Footer: “Local symbolic-score demo. Labels are source labels, not Gradus grades.” Optional future: choose a local MusicXML/MXL file as ad-hoc local analysis, labelled separately from the curated catalog.

### Legacy: static server only (artifact inspection fallback)

Static server still works for quick artifact inspection but is **no longer the main path** and is not presented as such in the UI:

```bash
# fallback only
python3 -m http.server 8000
open http://localhost:8000/research/learning_support/david_demo/web/
```

What the live server does:

- Serves the existing static web files and `artifacts/` via one coherent local app (so the 12-piece catalog is impossible to miss on first screen).
- Exposes JSON API:
  - `GET /api/catalog` — convenience wrapper around `artifacts/pieces.json` (one obvious live-server endpoint for the frontend; also confirms catalog availability without reasoning about paths)
  - `GET /api/health` — includes `catalog_exists`, `catalog_count`, `live_artifacts_count`, plus `cipi_root_exists`/`oktav_root_exists`
  - `GET /api/datasets` — available datasets and counts
  - `GET /api/pieces?dataset=<cipi|oktav>&q=<query>` — substring search over composer/title/id/path, returns `difficulty_label` when available (provenance only)
  - `POST /api/analyze` — body `{dataset, piece_id|dataset_relative_path|piece_uid}` for the selected result; creates an async job
  - `GET /api/jobs/<job_id>` — poll for `queued → running → succeeded|failed`; on success returns `manifest_url` (e.g. `/research/learning_support/david_demo/artifacts/live/<safe_id>/demo_manifest.json`) that the existing frontend loads into the same chart/hotspot UI
- Runs analysis asynchronously via `research/learning_support/david_demo/scripts/build_demo_piece.py` (same 6-dimension graph + 9-aspect backend pipeline as the static catalog) and writes generated artifacts under `artifacts/live/<safe_piece_id>/` with at least `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv`, `demo_manifest.json`.
- Dataset indexes are built lazily on startup/first request: CIPI from `research/piano_difficulty/evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` resolved against the CIPI root; Oktav from `research/piano_difficulty/tests/artifacts/oktav_dataset/python_analysis/full_run/load_report.json` (fallback to directory scan) resolved against the Oktav root. Search is simple case-insensitive substring matching.
- `safe_piece_id` is stable and filesystem-safe, e.g. `live_cipi_pieces_mozart_...` or `live_oktav_le_onde_...`.
- Returning a missing source file or a failed `build_demo_piece` run yields a `failed` job with `error` and `log` fields; the static catalog is never modified.

On the same page, the **Choose a piece** section is always at top with each row showing title, composer, and tag like Henle 3 / Oktav 43 — clicking a row directly opens the same graph/hotspot view without a separate Load step. Subtle caveat: “Source labels are for reference only.” The **Analyze another piece** section below offers dataset selector + search box backed by `/api/pieces`, results from allowlisted local indexes, and **Analyze piece** that loads the returned manifest into the same 6-way graph/hotspot view. Missing dataset roots do not hide or break the catalog. No API/path wording appears in the main UI unless there is an error; the footer shows “Local symbolic-score demo. Labels are source labels, not Gradus grades.”

Smoke test (after starting the live server):

```bash
curl "http://127.0.0.1:8000/api/pieces?dataset=cipi&q=mozart" | python -m json.tool
curl "http://127.0.0.1:8000/api/pieces?dataset=cipi&q=arabesque" | python -m json.tool
curl "http://127.0.0.1:8000/api/pieces?dataset=oktav&q=Le%20Onde" | python -m json.tool
# pick one dataset_relative_path from above and analyze
curl -X POST http://127.0.0.1:8000/api/analyze -H "Content-Type: application/json" -d '{"dataset":"cipi","dataset_relative_path":"pieces/mozart/mozart_1st-movement-allegro-from-piano-sonata-facile-c-major-kv-545-mvt1.musicxml"}'
# then poll GET /api/jobs/<job_id> until succeeded and open the returned manifest_url in the chart UI
```

Snippet PNGs are not rendered as part of live analysis (opt-in only). Live manifests use `snippet_status: not_rendered` with diagnostic `Snippet rendering deferred…` and load directly into the existing chart/hotspot flow.

## Explanation layers — Phase 1 (passage-card cleanup)

- **User-facing explanations describe musical demands.** The visible passage summary and “Why it feels hard” use plain language such as “the hands do not always land together,” “several notes need to line up cleanly,” “the hand has to move across a wider shape,” “timing has less room for adjustment,” “dynamic or articulation control has to stay consistent while the notes change,” and “reading load may be higher because of accidentals or dense notation.”
- **Provenance/debug explains selection and scoring.** The collapsed “Evidence (deterministic)” / “Why this was flagged (debug / provenance)” section retains the winning taxonomy label, raw/normalized feature contributors, relative-within-piece caveat, and selection reason (score-derived evidence, normalized, relative within this piece).
- **Phase 1 uses conservative mappings from existing signals and does not claim full semantic understanding.** Observations are derived only from the existing 6-dimension contributors and feature contributors already present in the manifest; no contour, hand, arpeggio, or voice claims are invented.

Implementation: `research/learning_support/david_demo/scripts/hotspot_explanation.py` (observation builder + learner summary v2, provenance preserved), `research/learning_support/david_demo/web/app.js` (JS parity, main card = learner, drawer = provenance).

## Explanation layers — Phase 2 (targeted semantic observations)

Phase 2 enriches `learner_observations` with concrete, evidence-backed window-level observations when the existing manifest data supports them. No new “musical object” framework is introduced; detectors reuse the 6-dimension contributors and micro-feature contributors already present in `demo_manifest.json` / the evidence brief.

- **What can become more specific:**
  - Hand/staff movement — wider movement/span, repeated position changes, large leaps; hand attribution (“left/right hand…”) only if the source micro-feature carries `scope_ref == left/right`, otherwise the generic “one hand … while the other …” is used.
  - Coordination — “the hands do not always land together, so coordination has to stay steady between layers” when `layers_coordination` is elevated and async-onset features are present.
  - Simultaneity / texture layers — “several notes need to line up cleanly,” “one part sustains while another part moves, so balance and coordination matter” when texture features (`notes_per_onset`, `simultaneity_density`, `vertical_density_proxy`, chord ratios) and async evidence co-occur.
  - Expression-over-motion — “dynamic shaping happens while the notes are changing, so control has to stay consistent through the motion” when `expression_sound_control` is elevated together with movement/rhythm; says “crescendo” only if wedge/hairpin data (`crescendo_start_count`, `wedge_start_count` raw > 0) is present.
  - Movement + timing — “the passage combines wider hand movement with timing precision” when both `hand_movement_position` and `rhythm_timing` are elevated with supporting leap and rhythm micro-features.
  - Reading load — accidentals/dense notation/clef changes if present (falls back to Phase 1 generic when threshold not met).

- **Conservative and evidence-backed:**
  - Semantic observations are generated only when dimension normalized values and micro-feature normalized values meet thresholds (e.g. `hand_movement_position >= 0.45` + leap `>= 0.55`, `rhythm_timing >= 0.40`, `layers_coordination + async >= 0.45`). Unsupported specifics are not generated.
  - Contour claims (ascending/descending, arpeggio, melody in right hand) are **not** emitted — no pitch-sequence data is plumbed into the brief, so the detector is disabled and Phase 1 generic observations are used instead.
  - Hand/staff claims require `scope_ref`/`hand` on the micro-feature; otherwise the generic “one hand …” phrasing is used or Phase 1 fallback is kept.

- **Integration with Phase 1:**
  - Specific semantic observations take precedence (up to 2) over generic mapped observations; generic Phase 1 observations remain fallback when specificity is not supported.
  - Learner-facing summary remains concise (2–3 sentences): concrete demand first, then why, then taxonomy label; debug/provenance copy remains separate except for an appended “Semantic observations (evidence-backed): …” line in the drawer.

- **Minimal plumbing:**
  - `research/piano_difficulty/src/piano_difficulty/difficulty_analysis/front_graph_taxonomy.py` unchanged; window-level signals continue to come from normalized feature traces.
  - `scripts/build_demo_piece.py` now preserves `scope`/`scope_ref`/`hand` on `feature_contributors` so hand attribution can be evidenced when the pipeline emits it.
  - `scripts/hotspot_explanation.py` adds `_build_semantic_observations(...)` returning structured `{kind, text, confidence, support_level, evidence}` and `semantic_observations` in the heuristic payload (`david_heuristic.v3`).

- **JS parity:** `web/app.js` mirrors the same thresholds (`buildSemanticObservations`) for the browser fallback; when manifest lacks note-level scope data the fallback stays conservative and documents that full hand/contour extraction is Python-only. Version is `david_heuristic.v3` in both layers.

Implementation: `scripts/hotspot_explanation.py` (`_build_semantic_observations`, extended `_build_observations`/`_build_learner_summary`, `OBSERVATION_REASON`), `scripts/build_demo_piece.py` (scope passthrough), `web/app.js` (JS parity + provenance annotation).

## Grouped hard bits / practice regions — Phase 3 (compact practice targets)

Phase 3 makes the grouped hard bit the learner-facing object. Raw 1-measure and 2-measure hotspot windows remain internal evidence only; nearby detections are merged into compact practice regions whose buffered rendering is shown to the learner.

- **Both resolutions as support evidence.** `build_demo_piece.py:main` now runs a companion 1-measure `difficulty_aspects` analysis (`OverviewOptions(window_size=1)`) alongside the primary 2-measure analysis and feeds both sets of graph hotspots (`1_measures` + `2_measures`) into the grouping step. When a real 1-measure run is available, its graph hotspots are merged directly; when not, each 2-measure core measure is kept as synthetic `1_measures` provenance so `supporting_resolutions` always lists both `1_measures`/`2_measures` as considered.
- **Merging.** Detection windows that overlap, touch, or are separated by only 1–2 measures (`gap ≤2`, i.e. `next.measure_start ≤ cur_end + 3`) are merged into one hard bit. Core span before buffer is continuous from `min(measure_start)` to `max(measure_end)` (gaps filled), so a chain like `12–13`, `13–14`, `17–18` with a 2-measure gap (15, 16) becomes one core `12–18` → in practice the Chopin e-minor example merges to core `9–20` because both 1m and 2m detections bridge the gap.
- **Buffered display/practice region.** `core_region` (merged difficulty span) is buffered ±1 measure, bounded by score edges (`max(1, core_start−1)` … `min(measure_count, core_end+1)`). Visible labels, snippet rendering, and the evidence brief all target `display_region`/`practice_region` (also aliased `hard_bits`/`practice_regions`/`grouped_hard_bits` in the manifest), not raw two-measure windows. `hard_bits` are capped to 5 (same `top_sections` as hotspots) and ranked by `max(score_value)` of the group.
- **Provenance preserved.** Raw windows stay inspectable as `supporting_windows` / `supporting_resolutions` / `supporting_section_ids` / `supporting_window_indices` (plus `supporting_windows_synthetic_1m` when synthetic). `core_region` vs `display_region` are both stored, so the debug drawer can show exactly which 1m/2m windows triggered the group and how the buffer was applied.
- **Semantic explanation targets the grouped region.** `build_evidence_brief(hard_bit, chart, piece, caveats)` is called on the buffered `hard_bit` (not individual windows) so `learner_observations`, `heuristic_explanation`/`summary`, snippet `measure_numbers`, and the visible measure label all describe the grouped buffered excerpt. Phase 2 precedence still holds: up to 2 evidence-backed semantic observations take precedence over generic Phase 1 wording; learner summary stays compact (2–3 sentences); no unsupported contour/arpeggio/hand-specific/crescendo claims are re-introduced.
- **UI.** `web/app.js:getPrimaryHotspots()` prefers `hard_bits`/`practice_regions` over `hotspots`; chart stars, the chip list, and the detail pane all render hard bits. Raw `hotspots` remain in the manifest for provenance/debug only.
- **Validation.** `scripts/validate_demo_readiness.py:_validate_hard_bits` checks `core_region` + `display_region` existence, buffered ±1 invariant, non-empty `supporting_windows`/`supporting_resolutions`, and that semantic artifacts are attached to the grouped bit.

Manifest additive fields (existing tests/consumers stay compatible, `hotspots`/`candidate_sections` remain):

```json
hard_bits: [{ id:"hard_bit:73:77", rank:1, core_region:{measure_numbers:["74","75","76"], measure_range:"74-76"}, display_region:{measure_numbers:["73","74","75","76","77"], measure_range:"73-77"}, supporting_windows:[{id, resolution_key:"2_measures", measure_range:"74-75"}, …], supporting_resolutions:["1_measures","2_measures"], supporting_section_ids:["graph_section:both:292:304", …], evidence:{…}, heuristic_explanation:{…} }]
practice_regions / grouped_hard_bits  (aliases)
hard_bits_version: "david_hard_bits.v1", hard_bits_method: "grouped_detections.v1"
```

Implementation: `scripts/build_demo_piece.py` (`_group_hotspots_into_hard_bits`, `HARD_BITS_GAP_TOLERANCE=2`, `HARD_BITS_BUFFER_MEASURES=1`, `build_demo_manifest(extra_hotspots, score_path)`), `scripts/hotspot_explanation.py` (unchanged thresholds, brief built from grouped region), `web/app.js` (hard-bit–first rendering + `core/display` provenance drawer), `scripts/validate_demo_readiness.py` (hard-bit checks).

## Claim boundaries

Symbolic-score demo evidence only — 6 learner-facing graph dimensions + 9-aspect backend.

- No calibrated learner grade (and no calibrated Gradus grade for Oktav difficulty labels).
- No measured learning benefit.
- No production score-viewer claim.

The demo shows a 6-dimension learner-facing graph (visible chart) plus 9-aspect backend taxonomy coverage and supporting score-derived signals plus pre-rendered notation snippets for illustration. Timeline and hotspots are descriptive evidence, not a calibrated score. The demo does not assign a pedagogical grade to a learner, does not measure learning outcomes, and does not claim a production-grade score viewer or engraving pipeline.
