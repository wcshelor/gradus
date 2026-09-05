# Consolidation record — 2026-09-05

Starting revision: 4a1e948 (clean codex/passage-diagnosis-planning checkout).
The branch had advanced beyond the earlier conversation's T01.1 inventory:
passage contracts and the generic-region ownership decision already existed.
This change preserves that work and consolidates difficulty analysis within
research/piano_difficulty.

## Inventory and preservation map

| Existing component | Consolidation disposition |
| --- | --- |
| io / normalize / features / aggregation | Existing formulas and extraction contracts preserved |
| analysis/windows.py | Compatibility re-export; temporal/windows.py stays canonical |
| temporal/transform.py | Canonical normalization/smoothing configs and functions |
| Dynamics core.py | Moved to difficulty_analysis/dynamics/core.py; shared extraction per region |
| Dynamics models.py | Moved to difficulty_analysis/dynamics/models.py; transform configs reused |
| Dynamics exports.py | Moved to output/dynamics.py |
| Dynamics configs, runner, piece_lab | Retained in harness; import promoted computations |
| Feature/measure raw reports | Retained; overview selects a documented five-factor subset |
| ScoreAnalyzer profile and comparison tools | Retained with explicit legacy profile selection |
| Yan, prediction, clustering, datasets, OMR | Retained in existing research lanes |
| Old analyzer README | Preserved under docs/legacy_workflows.md |
| Old task breakdown | Marked historical; roadmap.md is authoritative |
| Generated corpora and ad hoc runs | Left in place; existing ignore policy retained |
| Passage-practice implementation | Preserved; no dependency introduced from analyzer |

## Package outcomes

| Package | Implemented outcome |
| --- | --- |
| DC-00 | Environment repair, repo-root test config, path repairs, legacy snapshot audit |
| DC-01 | difficulty_overview.v1 payload and documented terminology |
| DC-02 | Executable reviewed factor registry; raw family disposition |
| DC-03 | Canonical temporal helpers; exact non-mutating analysis selection |
| DC-04 | Dynamics core/contracts promoted; harness wrappers retain imports |
| DC-05 | Existing peak/contribution algorithms reused; constant overview peaks suppressed |
| DC-06 | Overlap/touching union with support windows and representative contributions |
| DC-07 | Default overview and explicit legacy profile via existing pipeline |
| DC-08 | Canonical JSON, Markdown, CSV, standalone HTML timeline |
| DC-09 | CLI options, output directory, batch reports and failure continuation |
| DC-10 | Updated root direction, lane rules, analyzer guide and current roadmap |
| DC-11 | Synthetic semantics, compatibility tests and local score smoke runs; see evaluation.md |

## Baseline and migration repairs

The initial repo-root command produced 76 passed, 12 failed, 3 skipped and
7 collection errors. Collection errors included missing PyYAML/scikit-learn
and passage_practice import paths. Failures included old relative fixture paths,
an absent optional Alla Turca corpus, and stale expression snapshots.

Development dependencies are declared in pyproject.toml. environment.yml creates
the Python environment; a documented explicit editable install avoids ambiguous
working-directory resolution after the repository move. Root pytest.ini discovers
both research suites and sets their import roots.

The two legacy snapshots had 24 additional expression feature records each,
already present in runtime before consolidation. The audit found zero changed
existing feature values, zero removed features, and identical legacy profile
results. The snapshots were refreshed for those pre-existing additions. Named
legacy tests now request their profile explicitly.

Optional local-corpus tests now report a skip when their score is absent.
Committed fixture tests use paths relative to their test files and still run.
No score files, private corpus data or existing research runs were deleted.

## Compatibility choices

The normal CLI now prints Markdown; scripts consuming stdout should use
--format json. Explicit --profile flags replace the implicit default.
The legacy dynamics CLI remains a repository-only experiment entry point;
tests/scripts/run_difficulty_dynamics.py is its direct harness equivalent.
All normal extract/analyze/analyze-batch operations work through installed
runtime modules without the harness.

Legacy Dynamics keeps whole-overlapping-measure selection and records that
policy. The overview opts into exact attack intervals, stronger-hand maxima,
missing-hand diagnostics and constant-track abstention. These changes are
versioned as the new overview rather than changing the meaning of old runs.

Full semantic diagnosis, calibrated difficulty, expert validation and
event-by-event causal attribution are follow-up research, not consolidation
claims.
