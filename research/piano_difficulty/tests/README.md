# Tests

The repository should eventually include:

- `fixtures/`: tiny handcrafted score examples used for deterministic checks
- `unit/`: focused tests for helpers and extractors
- `integration/`: end-to-end extractor tests
- `regression/`: frozen output baselines for representative fixtures

Current implemented coverage:

- import bootstrap for the `src/` layout in `tests/conftest.py`
- CLI shape smoke test
- MusicXML / MXL loader boundary tests

The broader normalization, integration, and regression layers are still pending.

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
