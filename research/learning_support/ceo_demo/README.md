# CEO demo — small catalog mini-GUI (9-aspect taxonomy)

This is a thesis/company CEO demo workspace, not a general product app and not a new difficulty-analysis lane.

It provides a self-contained hub for the CEO demo: canonical source scores, generated backend assets, and the mini-GUI. The demo presents one consistent model — the 9-aspect difficulty taxonomy (`difficulty_aspects.v1`) — with timeline/hotspots drawn from supporting feature signals inside that model. Chart and hotspot traces are technical visualization signals (provenance: `difficulty_overview` feature traces), not a separate competing taxonomy. Difficulty-analysis runtime code stays in `research/piano_difficulty/`; learning-support passage-practice code stays in `research/learning_support/passage_practice/`.

## CEO demo feature set

The CEO demo intentionally uses a compact, score-native feature set. The goal is
to show a credible learner-facing experience: a score becomes a readable
difficulty map, high-demand passages are visible, and the system can explain
why a passage may need attention. This is not the place to settle every Yan et
al. feature ambiguity.

Included for the demo:

| Feature family | Taxonomy aspect(s) | Demo role |
|---|---|---|
| Note / attack density | 1. Rhythmic demand | Shows how much is happening per unit of notated time. |
| Rhythmic variety | 1. Rhythmic demand | Uses available duration, tuplet, shortest-value, and related rhythm traces to show local rhythmic complexity. |
| Leaps / displacement | 2. Pitch / movement demand | Highlights large pitch transitions and relocation demands. |
| Hand span / chord size | 3. Hand-shape / span demand | Shows physical extension and simultaneous hand-shape pressure. |
| Polyphony / chord density | 4. Texture / polyphony demand | Shows vertical density, chordal writing, and multi-note texture. |
| Hand coordination | 5. Coordination demand | Shows aligned vs. asynchronous hand activity and timing mismatch proxies. |
| Accidentals / reading load | 6. Notation / reading demand | Gives a visible notation-demand signal that is easy to explain from the score. |
| Articulation / dynamics, descriptive only | 7. Expression / control demand | Provides color about written control demands without ranking expression as harder by default. |
| Hotspot timeline / candidate sections | Presentation over the above signals | Makes demand visible over the piece and anchors the walkthrough in concrete measures. |

Deferred from the CEO demo:

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

## Selected demo pieces (11 curated entries)

| piece_id | Composer | Title | Dataset | Notes |
|---|---|---|---|---|
| `beethoven_fur_elise` | Ludwig van Beethoven | Bagatelle "Für Elise" a minor WoO 59 | CIPI | Henle 3 |
| `beethoven_bagatelle_119_10` | Ludwig van Beethoven | Bagatelle A major Op. 119 No. 10 | CIPI | Henle 3 |
| `mozart_k545` | Wolfgang Amadeus Mozart | Piano Sonata "Facile" C major KV 545, 1st movement | CIPI | Henle 4 |
| `chopin_waltz_a_minor_kk_ivb_11` | Frédéric Chopin | Waltz a minor KK IVb,11 | CIPI | Henle 3 |
| `chopin_prelude_e_minor_28_4` | Frédéric Chopin | Prelude e minor Op. 28 No. 4 | CIPI | Henle 4 |
| `chopin_prelude_a_major_28_7` | Frédéric Chopin | Prelude A major Op. 28 No. 7 | CIPI | Henle 4 |
| `debussy_arabesque_1` | Claude Debussy | Arabesque No. 1 | CIPI x-336 | Henle 4 |
| `satie_gymnopedie_1` | Erik Satie | Gymnopédie No. 1 | CIPI | Henle 2 |
| `oktav_le_onde` | Ludovico Einaudi | Le Onde | OKTAV OK00027 | regular piano, difficulty around 43 (original dataset label; not a Gradus grade) |
| `oktav_a_thousand_miles` | Vanessa Carlton | A Thousand Miles | OKTAV OK00016 | PVG-Ac arrangement, difficulty around 53 (original label) |
| `oktav_viva_la_vida` | Coldplay | Viva la Vida | OKTAV OK00009 | PVG-RH arrangement, difficulty around 55 (original label) |

Oktav difficulty numbers are included as provenance only (`difficulty_label` in `pieces.json`); they are not presented as calibrated Gradus grades and are not comparable across pieces.

## Canonical source scores

```
research/learning_support/ceo_demo/data/source_scores/
  beethoven_fur-elise.musicxml
  beethoven_bagatelle-a-major-op-119-no-10.musicxml
  mozart_k545_mvt1.musicxml
  chopin_waltz-a-minor-kk-ivb-11.musicxml
  chopin_prelude-e-minor-op-28-no-4.musicxml
  chopin_prelude-a-major-op-28-no-7.musicxml
  debussy_arabesque-no-1.musicxml
  satie_gymnopedie-no-1.musicxml
  oktav_le-onde_OK00027.xml
  oktav_a-thousand-miles_OK00016.xml
  oktav_viva-la-vida_OK00009.xml
```

Each file is a single copied score for the demo catalog (not a bulk corpus copy). See `data/source_scores/README.md` for provenance per piece.

## Layout

```
research/learning_support/ceo_demo/
  README.md
  AGENTS.md
  data/source_scores/            # 11 canonical source scores
  data/source_scores/README.md
  artifacts/pieces.json          # catalog of pre-analyzed pieces
  artifacts/<piece_id>/          # generated demo artifacts per piece (analysis.* + demo_manifest.json + snippets/)
  scripts/README.md              # backend helpers (manifest + snippet rendering)
  web/README.md                  # mini-GUI (static, 9-aspect taxonomy, catalog-driven)
```

## Generated artifacts

Generated demo artifacts go under `artifacts/<piece_id>/` plus the catalog `artifacts/pieces.json`.

Each `artifacts/<piece_id>/` contains:

- `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv` (via `research/piano_difficulty/src/piano_difficulty/output/overview.py`)
- `demo_manifest.json` — compact manifest for the mini-GUI: supporting feature traces for the timeline/hotspots plus the 9-aspect taxonomy payload (`difficulty_aspects` / `aspects`, 9 aspects), caveats, and snippet placeholders. The manifest is the single source of truth for the frontend.

`artifacts/pieces.json` lists each available pre-analyzed piece with `id`, `title`, `composer`, `dataset`, `dataset_id`, `manifest_url`, `status: ready`, and optional `difficulty_label` for source-label provenance.

## How to regenerate one piece

```bash
# Example: Chopin Prelude in E minor
conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py \
  --piece-id chopin_prelude_e_minor_28_4 \
  --score research/learning_support/ceo_demo/data/source_scores/chopin_prelude-e-minor-op-28-no-4.musicxml \
  --title "Prelude in E minor Op. 28 No. 4" \
  --composer "Frédéric Chopin" \
  --dataset cipi \
  --dataset-id "chopin_prelude-e-minor-op.-28,4-mvt1" \
  --dataset-relative-path "pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml" \
  --out-dir research/learning_support/ceo_demo/artifacts/chopin_prelude_e_minor_28_4

# Debussy via compatibility wrapper (same output, Debussy defaults):
conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_debussy_demo.py
```

## How to regenerate all available pieces

```bash
# Run the builder for each of the 11 selected scores (from repo root):
conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id debussy_arabesque_1 --score research/learning_support/ceo_demo/data/source_scores/debussy_arabesque-no-1.musicxml --title "Arabesque No. 1" --composer "Claude Debussy" --dataset cipi --dataset-id x-336 --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml --out-dir research/learning_support/ceo_demo/artifacts/debussy_arabesque_1

conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id chopin_prelude_e_minor_28_4 --score research/learning_support/ceo_demo/data/source_scores/chopin_prelude-e-minor-op-28-no-4.musicxml --title "Prelude in E minor Op. 28 No. 4" --composer "Frédéric Chopin" --dataset cipi --dataset-id "chopin_prelude-e-minor-op.-28,4-mvt1" --dataset-relative-path "pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml" --out-dir research/learning_support/ceo_demo/artifacts/chopin_prelude_e_minor_28_4

conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id beethoven_fur_elise --score research/learning_support/ceo_demo/data/source_scores/beethoven_fur-elise.musicxml --title "Für Elise" --composer "Ludwig van Beethoven" --dataset cipi --dataset-id "beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1" --dataset-relative-path "pieces/beethoven/beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1.musicxml" --out-dir research/learning_support/ceo_demo/artifacts/beethoven_fur_elise

conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id oktav_le_onde --score research/learning_support/ceo_demo/data/source_scores/oktav_le-onde_OK00027.xml --title "Le Onde" --composer "Ludovico Einaudi" --dataset oktav --dataset-id OK00027 --dataset-relative-path "Le Onde (Ludovico Einaudi) - piano MSMT OK00027.xml" --out-dir research/learning_support/ceo_demo/artifacts/oktav_le_onde

conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id oktav_a_thousand_miles --score research/learning_support/ceo_demo/data/source_scores/oktav_a-thousand-miles_OK00016.xml --title "A Thousand Miles" --composer "Vanessa Carlton" --dataset oktav --dataset-id OK00016 --dataset-relative-path "A Thousand Miles (Vanessa Carlton) - PVG-Ac MSMT OK00016 - 01.xml" --out-dir research/learning_support/ceo_demo/artifacts/oktav_a_thousand_miles

conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/build_demo_piece.py --piece-id oktav_viva_la_vida --score research/learning_support/ceo_demo/data/source_scores/oktav_viva-la-vida_OK00009.xml --title "Viva la Vida" --composer "Coldplay" --dataset oktav --dataset-id OK00009 --dataset-relative-path "Viva la Vida (Coldplay) - PVG-RH MSMT OK00009-01.xml" --out-dir research/learning_support/ceo_demo/artifacts/oktav_viva_la_vida
```

Reruns deterministically overwrite each artifact directory in place. After rebuilding, `artifacts/pieces.json` remains valid (it points to the same manifest paths); rebuild it if piece metadata changes.

## How to launch the static demo

```bash
# from repo root
python3 -m http.server 8000
# then open
open http://localhost:8000/research/learning_support/ceo_demo/web/
```

The load screen fetches `artifacts/pieces.json`, shows the 11 stored/preloaded pieces (Debussy selected by default when present), and loads the selected `demo_manifest.json` on clicking **Load piece**. Missing or unavailable pieces are shown as disabled and do not block other pieces.

## How to launch the live demo mode (local, on-demand analysis)

The live mode keeps the 11-piece static catalog working exactly as before and adds a local search/analyze flow over the full CIPI and Oktav corpora. No notation snippet PNGs are rendered live; the live success path is graph + hotspot manifest generation.

```bash
# from repo root — requires local corpora at:
#   /Users/campshelor/Desktop/oktav-thesis/datasets/cipi
#   /Users/campshelor/Desktop/oktav-thesis/datasets/oktav-starting-dataset
conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/run_live_demo_server.py --port 8000

# then open (server prints the URL and tries to open it)
open http://127.0.0.1:8000/research/learning_support/ceo_demo/web/
```

What the live server does:

- Serves the existing static web files and `artifacts/` (so the 11-piece flow is unchanged).
- Exposes JSON API:
  - `GET /api/datasets` — available datasets and counts
  - `GET /api/pieces?dataset=<cipi|oktav>&q=<query>` — substring search over composer/title/id/path, returns `difficulty_label` when available (provenance only)
  - `POST /api/analyze` — body `{dataset, piece_id|dataset_relative_path|piece_uid}` for the selected result; creates an async job
  - `GET /api/jobs/<job_id>` — poll for `queued → running → succeeded|failed`; on success returns `manifest_url` (e.g. `/research/learning_support/ceo_demo/artifacts/live/<safe_id>/demo_manifest.json`) that the existing frontend loads into the chart/hotspot UI
- Runs analysis asynchronously via `research/learning_support/ceo_demo/scripts/build_demo_piece.py` (same 9-aspect pipeline as the static catalog) and writes generated artifacts under `artifacts/live/<safe_piece_id>/` with at least `analysis.json`, `analysis.md`, `analysis.html`, `analysis.csv`, `demo_manifest.json`.
- Dataset indexes are built lazily on startup/first request: CIPI from `research/piano_difficulty/evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` resolved against the CIPI root; Oktav from `research/piano_difficulty/tests/artifacts/oktav_dataset/python_analysis/full_run/load_report.json` (fallback to directory scan) resolved against the Oktav root. Search is simple case-insensitive substring matching.
- `safe_piece_id` is stable and filesystem-safe, e.g. `live_cipi_pieces_mozart_...` or `live_oktav_le_onde_...`.
- Returning a missing source file or a failed `build_demo_piece` run yields a `failed` job with `error` and `log` fields; the static catalog is never modified.

Live picker in the web UI (below the static catalog) shows a dataset selector (CIPI/Oktav), a search box, a results list (composer/title/dataset id/difficulty label), an **Analyze** button for the selected result, and a status line. When the job succeeds the returned `manifest_url` is fetched and rendered with the same 9-aspect chart, regions, and ranked hotspots. The UI degrades gracefully when the live server is not running (`Live mode requires: python research/learning_support/ceo_demo/scripts/run_live_demo_server.py`).

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

## Claim boundaries

Symbolic-score demo evidence only — 9-aspect taxonomy.

- No calibrated learner grade (and no calibrated Gradus grade for Oktav difficulty labels).
- No measured learning benefit.
- No production score-viewer claim.

The demo shows 9-aspect difficulty taxonomy coverage and supporting score-derived signals plus pre-rendered notation snippets for illustration. Timeline and hotspots are supporting feature traces inside the 9-aspect model, not a separate calibrated score. The demo does not assign a pedagogical grade to a learner, does not measure learning outcomes, and does not claim a production-grade score viewer or engraving pipeline.
