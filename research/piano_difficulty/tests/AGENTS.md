# AGENTS

This directory is the parity and validation lab for `piano-difficulty`.

Rules for work here:

- `tests/harness/scoreanalyzer/` is the reusable OG-vs-Python comparison box.
- `tests/harness/yan2023/` is a separate experimental box for Yan-inspired
  work and must not be used for Sebastien parity.
- `tests/harness/difficulty_dynamics/` is the temporal difficulty profiling
  box for windowed score analysis and hotspot ranking.
- `tests/harness/oktav_dataset/` is the thesis-scoped local dataset box for
  Oktav catalog and OG export work and must not be described as parity.
- `tests/harness/omr_pipeline/` is the OMR prototyping box for rendered score
  pages and downstream readback experiments.
- `tests/harness/difficulty_prediction/` is the reusable supervised modeling
  box over exported matrices.
- `tests/harness/difficulty_clustering/` is the reusable unsupervised
  clustering box over exported matrices.
- `tests/scripts/` should only contain thin wrappers that import the harness.
- `tests/artifacts/` is for generated outputs only.
- `music/` is the canonical score library for harness input files.
- `tests/retired/` is for archived probes and wrappers that are no longer part
  of the active workflow.
- Keep pytest-discovered test files separate from harness modules.
- Reserve `scoreanalyzer_*` names for Sebastien parity only and `yan2023_*` or
  `yan_*` names for the Yan experimental lane.
- Reserve `difficulty_dynamics_*` names for the temporal difficulty profiling
  lane.
- Reserve `oktav_*` names for the Oktav thesis lane and keep its raw corpus
  under `evaluation_scores/ad_hoc/`, not inside `tests/`.
- Reserve `omr_*` names for the OMR prototyping lane and keep its rendered
  score evidence under `tests/artifacts/omr_pipeline/`.
