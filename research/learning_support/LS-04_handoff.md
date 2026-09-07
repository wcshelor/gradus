# LS-04 review handoff — optional context operations and provenance

Date: 2026-09-05. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-03 (contracts); owner: learner-context experiment.

## Outcome

Implemented `ContextStore` (`context_store.v1`) and `SelectedContext`
(`selected_context.v1`) in
`research/learning_support/learner_context/src/learner_context/store.py`:

- Create (session-only unless `saved=True` explicitly chosen), read,
  correct (new revision via `supersedes`; original retained dated),
  delete (entry + permission removed; dependent summaries cascaded),
  exclude (permission replaced; exclusion wins).
- Selection by request scope + permission: NONE selects nothing; REFERENCED
  links by piece identity or overlapping exact region; PERMITTED selects all
  permitted active entries. Superseded entries never selected. Only current
  summaries with fully selected sources attached.
- Summary currency: current iff all sources resolve, none superseded, none
  excluded. Corrections stale dependents; deletions remove them.
- Score-version risk surfaced: edition-bound (piece/region) entries selected
  under a versioned request carry a `score_version_unverified` warning (S7).
- Persistence boundary: in-memory store with explicit JSON export/save/load
  of saved records only. Empty history selects empty context without error.
- No habit inference, no external models, no network. Synthetic data only.

## Changed files

- `research/learning_support/learner_context/src/learner_context/store.py`
  (new), `__init__.py` (exports), `README.md` (operations section).
- `research/learning_support/learner_context/tests/unit/test_context_store.py`
  (new, 16 tests).
- `docs/Task_list_2026-09-05_flexible_piano_learning_support.md` (LS-04 log row).
- No passage-practice or difficulty files touched.

## Commands and results (repo root, `piano-difficulty` env)

- Baseline before LS-04: 261 passed, 7 skipped (verified).
- Focused: `research/learning_support/learner_context/tests` → 36 passed.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **277 passed, 7 skipped** (skips unchanged: optional local-corpus fixtures).
- `git diff --check` clean. No behavior test weakened; no snapshots exist or
  were regenerated.

## Acceptance mapping (LS-04 "done when")

- Session-only not persisted: export/save-file/load tests.
- Excluded/deleted uninfluential: selection-omission + summary-stale/cascade tests.
- Version mismatches surfaced: warning tests (present/absent cases).
- Empty history valid: empty-store selection test.

## Limitations and remaining dependencies

- Deletion leaves no tombstone; a re-added same-ID record starts fresh.
  Cross-session "later request" semantics (use_future gating beyond storage)
  deferred to LS-08 interaction work.
- `score_version_unverified` fires whenever an edition-bound entry meets a
  versioned request, since entries carry no edition identity by design
  (LS-03b); true edition matching awaits LS-05+ region/version handling.
- Next: LS-05 (user-selected regions independent of difficulty; needs WP-02
  selection API T02.2–T02.5). No WP gate released by this task.
