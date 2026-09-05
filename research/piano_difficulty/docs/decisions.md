# Difficulty-analysis decisions

## 2026-09-05 — Promote Difficulty Dynamics

The user selected consolidation of difficulty analysis as the active milestone.
Promote the existing dynamics core/models and artifact exporters into runtime;
retain harness import wrappers, configs, piece labs and plotting experiments.
Keep shared temporal primitives in temporal/. Preserve all other research lanes.

## 2026-09-05 — Version and qualify the overview

The default API/CLI profile becomes difficulty_overview, schema
difficulty_overview.v1. Explicit scoreanalyzer_reference preserves its historical
profile. CLI analyze defaults to readable Markdown; --format json retains
machine-readable output. Explicit profile flags replace, rather than append to,
the implicit default.

The initial five-factor selection is descriptive and within-piece. Raw values,
hand views, exact locations, methods, original support windows and input
provenance accompany rankings. Constant tracks abstain from local peaks.

## 2026-09-05 — Exact selection as an explicit adaptation

The old Dynamics beat windows selected all notes in overlapping measures.
The overview now uses exact attack intervals with clipped rate denominators.
The legacy experimental mode preserves its computations and labels the
selection policy in metadata. This distinction allows old results to be
reproduced without misrepresenting their temporal precision.

## 2026-09-05 — Preserve compatibility during migration

Existing import shims and comparison modules remain until downstream consumers
have migrated. We do not remove them simply to achieve a cleaner directory tree.
The detailed earlier task breakdown is historical; roadmap.md is authoritative.
