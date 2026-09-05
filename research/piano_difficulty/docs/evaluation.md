# Consolidated analyzer evaluation

Run from the Gradus root:

```bash
conda run -n piano-difficulty python -m pytest -q
```

The automated suite includes the existing extraction, Dynamics, prediction,
clustering, dataset, legacy comparison, and passage-contract checks. New
overview tests cover an isolated density/leap spike, a flat negative, exact
beat boundaries, hand selection, unknown-hand abstention, source immutability,
contribution sums, deterministic serialization and output files.

The existing Dynamics integration tests still exercise JSON/CSV/report/plot
exports and the manifest piece lab through promoted runtime imports. The
legacy difficulty-profile results are preserved under explicit profile IDs.

No expert or learner agreement is claimed by passing these tests. The five
overview factors and their equal weights remain descriptive choices. A
teacher review should assess factor relevance, usefulness of merged sections,
false positives, omitted sustained demands and sensitivity to window settings.

Small local-score checks and the latest verification counts are recorded in
tests/artifacts/difficulty_dynamics/consolidation_validation.md.
