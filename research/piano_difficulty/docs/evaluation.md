# Consolidated analyzer evaluation

Run from the Gradus root:

```bash
conda run -n piano-difficulty python -m pytest -q
```

The automated suite includes the existing extraction, Dynamics, prediction,
clustering, dataset, legacy comparison, and passage-contract checks. New
overview tests cover an isolated density/leap spike, a flat negative, exact
beat boundaries, hand selection, unknown-hand abstention, source immutability,
contribution sums, deterministic serialization and output files. The
`difficulty_aspects.v1` checks verify the primary 9-aspect output: exactly 9
aspect buckets, deterministic serialization, honest blocked/caveated status for
structural and performance interpretation, and no leakage into the overview
composite.

The existing Dynamics integration tests still exercise JSON/CSV/report/plot
exports and the manifest piece lab through promoted runtime imports. The
legacy difficulty-profile results are preserved under explicit profile IDs.

No expert or learner agreement is claimed by passing these tests. The five
overview factors and their equal weights remain descriptive choices inside the
conservative compatibility slice. The 9-aspect taxonomy is the main Gradus
system, but it is still unvalidated: it is a shared vocabulary for score-derived
practice demand, not a calibrated grade.
Review should assess factor/aspect relevance, usefulness of merged sections,
false positives, omitted sustained demands, sensitivity to window settings, and
whether the student-visible language is musically precise without becoming
teacher-only.

Gradus practice-payload evaluation should separately check hotspot
determinism, evidence/provenance links, append-only feedback behavior, dismissed
item filtering, card/log aggregation, recommendation priority ordering, and whether
recommendations remain framed as suggestions rather than diagnosis.

Small local-score checks and the latest verification counts are recorded in
tests/artifacts/difficulty_dynamics/consolidation_validation.md.
