# Analysis Lanes

This repository has multiple analysis lanes with different goals. They must
stay separate so humans and agents do not confuse parity work with
experimental work.

## Lane 1: ScoreAnalyzer parity

Purpose:
- reproduce the original PHP `ScoreAnalyzer` behavior as closely as possible
- diagnose mismatches between the OG implementation and the Python port
- preserve OG quirks unless an experiment explicitly opts out

Authoritative locations:
- runtime profile: `src/piano_difficulty/difficulty_analysis/scoreanalyzer_reference.py`
- parity harness: `tests/harness/scoreanalyzer/`
- thin runners: `tests/scripts/run_scoreanalyzer_*.py`
- evidence: `tests/artifacts/scoreanalyzer_parity/`

Rules:
- only `scoreanalyzer_*` names may be used for Sebastien parity modules/scripts
- parity success is defined by OG agreement, not by improved prediction quality

## Lane 2: Yan paper replication

Purpose:
- reproduce Yan et al. (2023) as faithfully as possible
- compare recreated features against the published reference matrices
- document ambiguity in formulas, preprocessing, or source data

Authoritative locations:
- `external/yan-features/`

Rules:
- this lane is self-contained and paper-facing
- this lane does not define or modify the default runtime difficulty profile

## Lane 3: Yan-inspired repo experiments

Purpose:
- explore ideas inspired by Yan et al. using this repository's normalized score
  pipeline and canonical `music/` assets
- produce explicit experimental evidence without affecting parity behavior

Authoritative locations:
- harness: `tests/harness/yan2023/`
- thin runners: `tests/scripts/run_yan2023_*.py`
- evidence: `tests/artifacts/yan2023/`

Rules:
- only `yan2023_*` or `yan_*` names may be used for this lane
- this lane must never be described as OG parity or exact ScoreAnalyzer
  replication

## Lane 4: Oktav thesis dataset operations

Purpose:
- manage the local thesis dataset supplied by Oktav without committing the raw
  score files
- normalize workbook-provided difficulty labels into committed manifest CSVs
- batch-export OG PHP `ScoreAnalyzer` metrics for later downstream modeling

Authoritative locations:
- harness: `tests/harness/oktav_dataset/`
- thin runners:
  `tests/scripts/build_oktav_dataset_catalog.py`,
  `tests/scripts/run_oktav_og_export.py`,
  `tests/scripts/run_cipi_og_export.py`
- local-only raw corpus: `evaluation_scores/ad_hoc/oktav_starting_dataset/`
- committed manifests: `evaluation_scores/manifests/`
- evidence: `tests/artifacts/oktav_dataset/`

Rules:
- this lane is thesis-scoped and dataset-scoped, not runtime code
- reusable modeling code belongs in `tests/harness/difficulty_prediction/`,
  not here
- raw Oktav score files stay git-ignored; committed state lives in manifests
  and generated evidence only

## Lane 5: Difficulty-prediction experiments

Purpose:
- run reusable, config-driven supervised experiments over exported feature
  matrices
- compare feature sets, target transforms, and model families without tying the
  experiment code to corpus staging or label normalization

Authoritative locations:
- harness: `tests/harness/difficulty_prediction/`
- thin runners: `tests/scripts/run_difficulty_prediction.py`
- evidence: `tests/artifacts/difficulty_prediction/`

Rules:
- this lane consumes matrices and explicit configs, not raw score files
- this lane must not stage corpora, normalize labels, or export OG metrics

## Lane 6: Difficulty-clustering experiments

Purpose:
- run reusable, config-driven unsupervised experiments over exported feature
  matrices
- keep PCA and clustering label-free during fitting, then compare the resulting
  clusters to difficulty labels only after the fact
- complement the supervised prediction lane with exploratory structure analysis

Authoritative locations:
- harness: `tests/harness/difficulty_clustering/`
- thin runner: `tests/scripts/run_difficulty_clustering.py`
- evidence: `tests/artifacts/difficulty_clustering/`

Rules:
- this lane consumes exported matrices, not raw score files
- this lane must not use difficulty labels during PCA, scaling, or clustering
- labels may be used only for post-hoc crosstabs, plots, and interpretation

## Lane 7: CIPI external-corpus cataloging

Purpose:
- keep a stable repository-side manifest for the externally stored CIPI corpus
- support downstream survey and baseline experiments without copying the raw
  MusicXML files into the repository

Authoritative locations:
- harness: `tests/harness/cipi_dataset/`
- thin runner: `tests/scripts/build_cipi_dataset_catalog.py`
- committed manifest: `evaluation_scores/manifests/cipi_dataset_catalog.csv`

Rules:
- the raw CIPI corpus remains outside the repository
- downstream experiments should consume the manifest, not the raw JSON

## Promotion Policy

Work may move inward only in this order:

1. experiment in `tests/harness/*`
2. stabilize definitions, outputs, and diagnostics
3. decide whether the behavior belongs in runtime code
4. add a new runtime profile explicitly

Until step 4 happens, the difficulty-prediction and difficulty-clustering lanes
remain test-scoped and consume exported matrices rather than raw corpus files.
