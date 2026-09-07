# Learner context

Experiment boundary for optional learner-provided context, chosen during LS-03
of the repository-wide
[three-area plan](../../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md).
Owner: learner-context experiment (LS-03b contracts; storage and selection in
LS-04). Status: minimal contracts plus in-memory storage/selection operations;
no UI, external processing, or real learner-data integration exists here.

## Why a separate boundary

Reuse considered and rejected or accepted:

- `passage_practice` models (`ScoreInterval`, `Diagnostic`) are **reused** for
  optional exact regions and diagnostics. Passage subjects are referenced by
  stable ID string only, so this boundary never embeds score objects.
- `piano_difficulty` is score-only and carries no learner concepts; not reused.
- Learner records (intent vs. persisted history, verbatim reports, permissions,
  tentative summaries, assistance results) are the **missing responsibility**:
  placing them in passage layers would put learner concepts upstream of score
  facts and violate the `score facts -> views -> ... -> presentation`
  dependency direction. Hence one minimal module here, no new top-level
  application, and nothing moved to `research/shared/`.

Import direction: `learner_context -> passage_practice`; never the reverse.

## Contracts (`src/learner_context/models.py`)

Section 4 of the three-area plan, LS-01 scenarios S3–S5, and LS-03b:

- `AssistanceRequest` (request intent separate from persisted history;
  unresolved requests stay valid).
- `JournalEntry` (verbatim text, scope, revision chain via `supersedes`).
- `ContextPermission` (session-only vs. saved; current/future use; exclusion
  wins; deletion is removal, handled by LS-04 storage).
- `ContextSummary` (source-entry IDs, method/version, tentative
  interpretation, confirmation state; invalidation in LS-04).
- `AssistanceResult` (score evidence and self-reports referenced separately;
  rationale and limitations required; no measured-outcome claims).

All records use synthetic histories in committed tests. Real learner data,
retention, and company boundaries require explicit owner decisions before any
implementation with those data.

## Operations (`src/learner_context/store.py`, LS-04)

In-memory `ContextStore`: create (session-only unless explicitly saved),
read, correct (new revision via `supersedes`), delete (with summary cascade),
exclude, scope-and-permission selection (`SelectedContext`), summary currency,
and explicit JSON file save/load of saved records only. No inference.
