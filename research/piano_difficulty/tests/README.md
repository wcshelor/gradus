# Tests

The repository should eventually include:

- `fixtures/`: tiny handcrafted score examples used for deterministic checks
- `unit/`: focused tests for helpers and extractors
- `integration/`: end-to-end extractor tests
- `regression/`: frozen output baselines for representative fixtures

Current coverage includes raw MusicXML/MXL parsing, normalization, all runtime
feature families, explicit legacy profile regression, the public overview,
exact temporal selection, CLI/report/batch integration, and research harnesses.
The overview has both musical invariant tests and a compact frozen public
contract example.

Run `conda run -n piano-difficulty python -m pytest -q` from the Gradus root
to include both difficulty and passage-contract suites. The same command from
this subproject runs its own suite. Install the declared dev extra first;
optional PHP/local-corpus checks report skips with explicit reasons.

The test-scoped research lanes currently include:

- `tests/harness/yan2023/`: Yan replication / extension work
- `tests/harness/difficulty_dynamics/`: windowed temporal difficulty
  profiling and hotspot detection
- `tests/harness/oktav_dataset/`: one current dataset adapter for staging and
  export
- `tests/harness/cipi_dataset/`: one current dataset adapter for cataloging and
  export
- `tests/harness/difficulty_prediction/`: supervised matrix evaluation
- `tests/harness/difficulty_clustering/`: unsupervised matrix evaluation

Legacy ScoreAnalyzer parity harnesses remain in the tree only as archive and
compatibility material.
