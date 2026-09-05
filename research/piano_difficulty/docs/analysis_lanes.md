# Analysis Lanes

Active work in this repository is centered on Yan feature reconstruction,
dataset staging, OMR prototyping, windowed temporal difficulty profiling, and
matrix-based evaluation. Legacy ScoreAnalyzer parity material remains in the
tree for historical reference, but it is no longer the main lane.

## Lane 1: Yan replication / extension

Purpose:
- reconstruct Yan et al. (2023) feature math from repo-native score data
- treat the paper as the source of intent while allowing the implementation to
  be rebuilt from scratch when the published math is incomplete
- keep ambiguous formulas explicit so they can be compared, refined, or
  blocked instead of silently guessed

Authoritative locations:
- paper-facing reference: `external/yan-features/`
- repo-native harness: `tests/harness/yan2023/`
- thin runners: `tests/scripts/run_yan2023_*.py`
- evidence: `tests/artifacts/yan2023/`

Rules:
- this lane is not OG parity and must never be described that way
- Yan feature names and math should be tracked explicitly in the harness docs
  and inventories
- proxy features are allowed only when the exact paper math is unavailable

## Lane 2: Dataset staging and cataloging

Purpose:
- keep corpus manifests explicit and repo-local without copying raw corpora
- support dataset-specific metadata normalization for downstream matrix runs
- provide score-file discovery, catalog helpers, and export adapters for any
  dataset we choose to stage locally

Authoritative locations:
- generic dataset support: `tests/harness/shared/`
- current dataset adapters: `tests/harness/oktav_dataset/`,
  `tests/harness/cipi_dataset/`
- committed manifests: `evaluation_scores/manifests/`
- evidence: `tests/artifacts/oktav_dataset/`
  - `og_export/full_run/` for legacy matrix export
- retired CIPI export evidence: `tests/artifacts/retired/cipi_og_export/`

Rules:
- raw corpus files stay outside the repository unless they are explicitly safe
  to commit
- dataset helpers should stay dataset-agnostic where possible and should feed
  the shared matrix loader rather than re-implementing staging logic
- Oktav and CIPI are current examples, not the boundary of the lane

## Lane 3: OMR pipeline prototyping

Purpose:
- render source score files into page-oriented PDFs that a small OMR setup can
  ingest
- keep the source-to-rendered boundary explicit so imperfect recognition can be
  evaluated without changing the runtime feature extraction code
- preserve manifest, log, and rendered-page evidence separately from dataset
  staging and matrix experiments

Authoritative locations:
- repo-native harness: `tests/harness/omr_pipeline/`
- thin runner: `tests/scripts/run_omr_pdf_export.py`
- evidence: `tests/artifacts/omr_pipeline/`

Rules:
- this lane is about OMR-readback prototyping, not canonical dataset staging
- the current implementation uses MuseScore as a rendering step before any
  future recognizer is introduced
- rendered PDFs should stay under the OMR artifact root even when the source
  corpus is Oktav

## Lane 4: Difficulty Dynamics

Promotion status (2026-09-05): the core/models are now owned by
`src/piano_difficulty/difficulty_analysis/dynamics/`; export helpers are in
`src/piano_difficulty/output/dynamics.py`. Existing harness imports delegate
to runtime. The public `difficulty_overview` profile adds exact selection,
reviewed factors and merged candidate sections.

Purpose:
- generate time-varying difficulty profiles from symbolic piano scores
- reuse the existing score feature extractors over bounded regions
- keep raw, normalized, smoothed, and composite lines separate in the output
- support consensus hotspot detection that combines feature-track peaks with the composite line for future product visualization
- rank the strongest feature contributors inside hotspot regions as scaffolding for later explanations

Authoritative locations:
- repo-native harness: `tests/harness/difficulty_dynamics/`
- thin runner: `tests/scripts/run_difficulty_dynamics.py`
- evidence: `tests/artifacts/difficulty_dynamics/`

Rules:
- configs, runners, piece labs and plotting experiments stay test-scoped;
  stabilized computations are promoted as recorded in docs/decisions.md
- regional feature computation must be represented as a temporal adaptation of
  existing feature definitions, not as a silent rewrite of the original math
- within-piece normalization is descriptive inside one score only and does not
  imply cross-piece comparability

## Lane 5: Matrix evaluation

Purpose:
- run reusable, config-driven analyses over exported feature matrices
- use the same data-loading backbone for supervised and unsupervised runs
- treat prediction metrics and clustering metrics as diagnostics for feature
  behavior, not as separate research silos

Authoritative locations:
- supervised harness: `tests/harness/difficulty_prediction/`
- unsupervised harness: `tests/harness/difficulty_clustering/`
- thin runners: `tests/scripts/run_difficulty_prediction.py`,
  `tests/scripts/run_difficulty_clustering.py`
- evidence: `tests/artifacts/difficulty_prediction/`,
  `tests/artifacts/difficulty_clustering/`

Rules:
- both modes consume matrices, not raw score files
- labels may be used for supervised targets or post-hoc interpretation, but
  clustering must remain label-free during fitting
- feature selection and matrix loading should be shared wherever possible

## Legacy archive: ScoreAnalyzer parity

Purpose:
- preserve old comparison evidence and compatibility artifacts for reference

Authoritative locations:
- legacy harness: `tests/harness/scoreanalyzer/`
- legacy comparison tools: `src/piano_difficulty/comparison/`
- archived evidence: `tests/artifacts/scoreanalyzer_parity/`

Rules:
- this is archival material, not an active lane
- new work should not add parity assumptions or parity-only probes unless a
  migration task explicitly requires it

## Promotion Policy

Work may move inward only in this order:

1. experiment in `tests/harness/*`
2. stabilize definitions, outputs, and diagnostics
3. decide whether the behavior belongs in runtime code
4. add a new runtime profile explicitly (difficulty_overview is the first
   promoted temporal overview)

Until step 4 happens, the matrix-evaluation lanes remain test-scoped and
consume exported matrices rather than raw corpus files.
