# Source scores — CEO demo (11-piece catalog)

This folder holds the canonical source scores for the 11-piece CEO demo catalog. It is not a general score corpus; do not add additional pieces here without an explicit scope change and do not bulk-copy corpora.

## Canonical files

| Local filename | Piece | Source |
|---|---|---|
| `beethoven_fur-elise.musicxml` | Ludwig van Beethoven — Bagatelle "Für Elise" a minor WoO 59 | CIPI — `pieces/beethoven/beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1.musicxml` |
| `beethoven_bagatelle-a-major-op-119-no-10.musicxml` | Ludwig van Beethoven — Bagatelle A major Op. 119 No. 10 | CIPI — `pieces/beethoven/beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml` |
| `mozart_k545_mvt1.musicxml` | Wolfgang Amadeus Mozart — Piano Sonata "Facile" C major KV 545, 1st movement | CIPI — `pieces/mozart/mozart_1st-movement-allegro-from-piano-sonata-facile-c-major-kv-545-mvt1.musicxml` |
| `chopin_waltz-a-minor-kk-ivb-11.musicxml` | Frédéric Chopin — Waltz a minor KK IVb,11 | CIPI — `pieces/chopin/chopin_waltz-a-minor-kk-ivb,11-mvt1.musicxml` |
| `chopin_prelude-e-minor-op-28-no-4.musicxml` | Frédéric Chopin — Prelude e minor Op. 28 No. 4 | CIPI — `pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml` |
| `chopin_prelude-a-major-op-28-no-7.musicxml` | Frédéric Chopin — Prelude A major Op. 28 No. 7 | CIPI — `pieces/chopin/chopin_prelude-a-major-op.-28,7-mvt1.musicxml` |
| `debussy_arabesque-no-1.musicxml` | Claude Debussy — Arabesque No. 1 | CIPI `x-336` — `pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml` |
| `satie_gymnopedie-no-1.musicxml` | Erik Satie — Gymnopédie No. 1 | CIPI — `pieces/satie/satie_gymnopédie-no.-1-mvt1.musicxml` |
| `oktav_le-onde_OK00027.xml` | Ludovico Einaudi — Le Onde | OKTAV OK00027 — `Le Onde (Ludovico Einaudi) - piano MSMT OK00027.xml` (regular piano, difficulty around 43) |
| `oktav_a-thousand-miles_OK00016.xml` | Vanessa Carlton — A Thousand Miles | OKTAV OK00016 — `A Thousand Miles (Vanessa Carlton) - PVG-Ac MSMT OK00016 - 01.xml` (PVG-Ac, difficulty around 53) |
| `oktav_viva-la-vida_OK00009.xml` | Coldplay — Viva la Vida | OKTAV OK00009 — `Viva la Vida (Coldplay) - PVG-RH MSMT OK00009-01.xml` (PVG-RH, difficulty around 55) |

Full canonical paths: `research/learning_support/ceo_demo/data/source_scores/<filename>`

Catalog piece IDs map to filenames:

- `beethoven_fur_elise` → `beethoven_fur-elise.musicxml`
- `beethoven_bagatelle_119_10` → `beethoven_bagatelle-a-major-op-119-no-10.musicxml`
- `mozart_k545` → `mozart_k545_mvt1.musicxml`
- `chopin_waltz_a_minor_kk_ivb_11` → `chopin_waltz-a-minor-kk-ivb-11.musicxml`
- `chopin_prelude_e_minor_28_4` → `chopin_prelude-e-minor-op-28-no-4.musicxml`
- `chopin_prelude_a_major_28_7` → `chopin_prelude-a-major-op-28-no-7.musicxml`
- `debussy_arabesque_1` → `debussy_arabesque-no-1.musicxml`
- `satie_gymnopedie_1` → `satie_gymnopedie-no-1.musicxml`
- `oktav_le_onde` → `oktav_le-onde_OK00027.xml`
- `oktav_a_thousand_miles` → `oktav_a-thousand-miles_OK00016.xml`
- `oktav_viva_la_vida` → `oktav_viva-la-vida_OK00009.xml`

## Source identity details

- Debussy: CIPI id `x-336`, id `debussy_arabesque_1` (CEO manifest demo id), CIPI movement manifest row `research/piano_difficulty/evaluation_scores/manifests/cipi/cipi_movement_manifest.csv` (`x-336`).
- Chopin Prelude: CIPI relative path `pieces/chopin/chopin_prelude-e-minor-op.-28,4-mvt1.musicxml`, CE0 walkthrough manifest `research/piano_difficulty/evaluation_scores/manifests/ceo_walkthrough/cipi_familiar_v1.csv` (`chopin_prelude_e_minor_28_4`).
- Beethoven Für Elise: CIPI relative path `pieces/beethoven/beethoven_bagatelle-für-elise-a-minor-woo-59-mvt1.musicxml`, walkthrough manifest `beethoven_fur_elise`.
- Oktav pieces: source paths in `research/piano_difficulty/tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv` (`source_path` column) at `/Users/campshelor/desktop/oktav-thesis/datasets/oktav-starting-dataset/`. Filenames preserve the original `OK00027`/`OK00016`/`OK00009` ids.

## Provenance

- Debussy source copied from the local CIPI dataset at `/Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml` (MuseScore 3.2.3 export, `Arabesque No. 1 in E Major`, encoding date 2021-12-06, source `http://musescore.com/user/33901052/scores/6308406`). Original filename `debussy_arabesque-no.-1-mvt1.musicxml` normalized to `debussy_arabesque-no-1.musicxml`.
- CIPI selections copied from `/Users/campshelor/Desktop/oktav-thesis/datasets/cipi/pieces/...` with stable local filenames as above. The CIPI Henle numbers are retained as catalog provenance labels only.
- Oktav pieces copied from `/Users/campshelor/desktop/oktav-thesis/datasets/oktav-starting-dataset/` (original MusicXML/XML exports). Filenames include the OKTAV id for stable provenance (`_OK00027` etc.). The Oktav difficulty numbers (43, 53, 55) are original dataset labels retained as `difficulty_label` in `artifacts/pieces.json` only for reference; they are not Gradus grades.
- License/provenance is safe to commit per project owner. No additional redistribution restriction applies to these demo sources; provenance is preserved here and in the hub `README.md`.

## Notes

- Do not treat this folder as a CIPI or OKTAV corpus mirror. Only the 11 selected scores belong here.
- Generated artifacts derived from these scores belong under `../../artifacts/<piece_id>/` and are cataloged in `../../artifacts/pieces.json`.
