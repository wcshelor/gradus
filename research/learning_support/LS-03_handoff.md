# LS-03 review handoff — minimal investigation and learner contracts

Date: 2026-09-05. Implementer: muse-spark. Branch: codex/passage-diagnosis-planning
(working tree; nothing committed). Design authority D-013 accepted
(passage-first); pending-review blocker resolved before this run.

## Outcome

- **LS-03a (done, verified before LS-03b started):** shared
  `PassageInvestigation` envelope implemented over the existing `Passage`.
  Both entries use one contract; origin is a validated `SelectionOrigin`
  field; difficulty context is an optional validated collection (empty valid);
  enrichment preserves origin/identity; no hotspot IDs, scores, or
  contributions are manufactured.
- **LS-03b (done):** learner request/journal/context contracts implemented in
  a new documented boundary `research/learning_support/learner_context/`.
  Request intent is separate from history; unresolved requests are valid;
  journal text is verbatim with revision chains; permissions enforce
  session-only/exclusion rules; summaries carry source-entry IDs for LS-04
  invalidation; results reference score evidence and self-reports separately
  and require rationale plus limitations.

## Reuse analysis (why new modules, what was reused)

- Reused unchanged: `Passage`, `ScorePosition`/`ScoreInterval`,
  `SourceRef`, `Diagnostic` (`passage_practice/models/`); score-time stays
  exact rational, floats only at the model-boundary score fields.
- Considered: putting learner records in `passage_practice` (rejected —
  learner concepts upstream of score facts violate dependency direction);
  `piano_difficulty` (rejected — score-only, no learner concepts);
  a second region model (rejected per D-012/D-013).
- Missing responsibility justifying new code: LS-03a envelope binding passage
  + structured origin + optional validated difficulty context with
  source/coverage checks; LS-03b learner-side records with no score-object
  embedding (passages by ID reference only).

## Changed files

- `research/learning_support/passage_practice/src/passage_practice/models/investigation.py`
  (new), `models/__init__.py` (exports).
- `research/learning_support/passage_practice/tests/unit/test_investigation.py`
  (new, 24 tests).
- `research/learning_support/passage_practice/docs/contracts.md` (one-line
  LS-03a implementation note; no semantic change).
- `research/learning_support/learner_context/README.md`,
  `src/learner_context/{__init__,models}.py`,
  `tests/unit/test_learner_contracts.py` (all new; 20 tests).
- `pytest.ini` (learner_context testpaths/pythonpath added).
- `docs/Task_list_2026-09-05_flexible_piano_learning_support.md` (LS-03a,
  LS-03b log rows).

## Commands and results (repo root, `piano-difficulty` env)

- Baseline: `conda run -n piano-difficulty python -m pytest -q` →
  217 passed, 7 skipped (verified; matches latest record).
- After LS-03a: focused learning-support suites 123 passed; full suite
  241 passed, 7 skipped.
- After LS-03b: new file 20 passed; full suite **261 passed, 7 skipped**.
- Skips unchanged: optional local-corpus/ScoreAnalyzer fixtures only.
- `git diff --check` clean. Two test-side mistakes fixed during the run
  (constructor TypeError vs. payload ValueError for bad origin; convoluted
  exclusion assertion rewritten); no behavior test weakened, no snapshot
  regenerated.

## Accepted vs. implemented vs. unimplemented

- Accepted design: D-013 passage-first envelope (this run did not re-decide it).
- Implemented: LS-03a/LS-03b contracts + contract tests + frozen payloads.
- Explicitly unimplemented: selection adapters (T02.5/T05.2/T05.3), journal
  storage/selection/invalidation (LS-04), full diagnosis/attribution trees,
  UI, pedagogical algorithms. Contract fixtures imply no runtime adapter
  equivalence; behavioral equivalence tests remain T05.3 work.

## Limitations and remaining dependencies

- `window_score`/contributions require a `hotspot_id`, but container
  validation cannot prove the analysis was real; producer trust stays with
  the T05.2 adapter and method metadata.
- `ContextPermission` deletion state is removal (no tombstone contract);
  LS-04 storage must guarantee deleted entries leave no hidden memory.
- No real learner data, no external calls; synthetic fixtures only.
- Next: LS-04 (context operations/provenance). T05.3 additionally needs
  T02.5. No WP gate is released by this contract task.
