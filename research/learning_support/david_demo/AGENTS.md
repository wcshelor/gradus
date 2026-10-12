# AGENTS — David demo hub

Scope: `research/learning_support/david_demo/`

- This is a historical presentation/demo lane. Do not use it as evidence for
  current semantic-token or practice-chunk behavior; use
  `research/piano_difficulty/docs/current_practice_chunking.md` and
  `research/piano_difficulty/tests/artifacts/practice_chunk_review/` for that.
- Hub is scoped to a small catalog of pre-analyzed demo pieces (12 curated entries), not an open-ended corpus mirror. The catalog is:
  - `beethoven_fur_elise` — Ludwig van Beethoven — Für Elise (CIPI)
  - `beethoven_bagatelle_119_10` — Ludwig van Beethoven — Bagatelle A major Op. 119 No. 10 (CIPI)
  - `mozart_k545` — Wolfgang Amadeus Mozart — Piano Sonata "Facile" C major KV 545, 1st movement (CIPI)
  - `chopin_waltz_a_minor_kk_ivb_11` — Frédéric Chopin — Waltz a minor KK IVb,11 (CIPI)
  - `chopin_prelude_e_minor_28_4` — Frédéric Chopin — Prelude in E minor Op. 28 No. 4 (CIPI)
  - `chopin_prelude_a_major_28_7` — Frédéric Chopin — Prelude A major Op. 28 No. 7 (CIPI)
  - `debussy_arabesque_1` — Claude Debussy — Arabesque No. 1 (CIPI x-336)
  - `debussy_clair_de_lune` — Claude Debussy — Clair de Lune (CIPI x-190, Henle 5)
  - `satie_gymnopedie_1` — Erik Satie — Gymnopédie No. 1 (CIPI)
  - `oktav_le_onde` — Ludovico Einaudi — Le Onde (OKTAV OK00027, piano, difficulty around 43)
  - `oktav_a_thousand_miles` — Vanessa Carlton — A Thousand Miles (OKTAV OK00016, PVG-Ac, difficulty around 53)
  - `oktav_viva_la_vida` — Coldplay — Viva la Vida (OKTAV OK00009, PVG-RH, difficulty around 55)
  Do not add further pieces without an explicit scope change; do not bulk-copy corpora.
- Do not move reusable difficulty-analysis code here. Runtime analysis, feature extraction, and temporal profiling belong in `research/piano_difficulty/`; import or reuse from there instead of duplicating.
- Do not make this a general CIPI or OKTAV corpus mirror. Only the selected source scores listed above belong in `data/source_scores/`; do not bulk-copy additional pieces. Each copied file preserves provenance notes in `data/source_scores/README.md`.
- Treat `data/source_scores/` as the canonical demo inputs (stable filenames, see README). All backend scripts and the mini-GUI should read these paths.
- Put generated files under `artifacts/<piece_id>/` (one folder per catalog entry) plus the catalog `artifacts/pieces.json`. This includes `demo_manifest.json`, rendered snippet images (when added), and any derived analysis payloads. Do not write generated artifacts outside these directories.
- Keep frontend code under `web/`. The mini-GUI and any static assets for the demo belong there; do not place app code at the hub root. The frontend loads `artifacts/pieces.json` as the catalog and then the selected `demo_manifest.json`; it does not assume only Debussy.
- Keep backend helper scripts under `scripts/`. One-off build, render, and validation helpers for the demo belong there; keep them thin and deterministic. `build_demo_piece.py` is the reusable builder; `build_debussy_demo.py` is a thin compatibility wrapper.
- Preserve score provenance and license notes for every selected piece. Keep the record in `README.md` and `data/source_scores/README.md` when editing. License/provenance is safe to commit per project owner.
- The user-facing visible graph is the 6 learner-facing difficulty dimensions (`gradus.front_graph_taxonomy.v2`: finger_dexterity, hand_movement_position, layers_coordination, rhythm_timing, expression_sound_control, notation_reading). The 9-aspect difficulty taxonomy (`difficulty_aspects.v1`) remains as backend coverage/provenance — not the graph. Chart traces are graph-dimension signals; aspect traces are provenance only, not a competing visible taxonomy.
