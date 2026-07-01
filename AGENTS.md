# AGENTS

Repository-level working rules:

- Treat `src/` as runtime code only.
- Treat `tests/harness/scoreanalyzer/` as the OG-parity lab.
- Treat `tests/harness/yan2023/` as the Yan-inspired experimental lab.
- Treat `tests/harness/oktav_dataset/` as the thesis-scoped Oktav dataset lab.
- Treat `tests/harness/difficulty_prediction/` as the reusable prediction lab.
- Treat `tests/harness/difficulty_clustering/` as the reusable unsupervised
  clustering lab.
- Keep runner scripts thin and located in `tests/scripts/`.
- Keep generated evidence under `tests/artifacts/`.
- Treat `music/` as the canonical score asset library and prefer it over the
  legacy `external/ScoreAnalyzer/pieces` tree.
- Treat `evaluation_scores/` as the corpus-and-label area:
  - `known_levels/` for commit-safe labeled corpora
  - `ad_hoc/` for local-only ignored corpora
  - `manifests/` for committed catalog and label tables
- Do not reintroduce parity or probe machinery into `src/` unless the runtime
  genuinely needs it.
- Prefer explicit, test-scoped diagnostics over hidden behavior changes.
- Keep lane boundaries explicit:
  - Sebastien parity code belongs in `tests/harness/scoreanalyzer/`
  - Yan-inspired work belongs in `tests/harness/yan2023/`
  - Oktav thesis dataset mechanics belong in `tests/harness/oktav_dataset/`
  - reusable difficulty-prediction experiments belong in
    `tests/harness/difficulty_prediction/`
  - reusable unsupervised difficulty-clustering experiments belong in
    `tests/harness/difficulty_clustering/`
- If a change adds, removes, or repurposes a research lane, update the lane
  roadmap in `README.md`, `docs/analysis_lanes.md`, this file, and the
  affected directory README files in the same change.

## Repo Roadmap

- `src/piano_difficulty/`
  - reusable runtime extraction, normalization, analysis, and CLI code
- `tests/harness/scoreanalyzer/`
  - OG PHP `ScoreAnalyzer` parity harness and probes
- `tests/harness/yan2023/`
  - Yan-inspired experiments that stay out of runtime until intentionally
    promoted
- `tests/harness/oktav_dataset/`
  - thesis-scoped local dataset tooling for catalog building and OG batch
    export over the Oktav corpus
- `tests/harness/difficulty_prediction/`
  - reusable modeling experiments over exported feature matrices
- `tests/harness/difficulty_clustering/`
  - reusable unsupervised clustering experiments over exported feature matrices
- `tests/scripts/`
  - thin runnable wrappers only; no heavy logic
- `tests/artifacts/`
  - generated evidence only, grouped by lane
- `tests/artifacts/difficulty_prediction/`
  - run outputs, metrics, fold predictions, and comparison tables
- `tests/artifacts/difficulty_clustering/`
  - clustering run outputs, PCA tables, cluster assignments, and reports
- `evaluation_scores/`
  - real corpora, local-only corpora, and manifest tables
- `music/`
  - canonical score asset library for committed reference material
- `docs/`
  - lane definitions, findings logs, and methodology notes
