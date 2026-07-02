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

- `tests/harness/scoreanalyzer/`: parity and forensic harnesses
- `tests/harness/yan2023/`: Yan-inspired experiments
- `tests/harness/oktav_dataset/`: thesis-scoped dataset operations and
  ScoreAnalyzer OG export
- `tests/harness/cipi_dataset/`: CIPI catalog and ScoreAnalyzer export helpers
- `tests/harness/difficulty_prediction/`: supervised experiments over exported
  feature matrices
- `tests/harness/difficulty_clustering/`: unsupervised PCA-plus-clustering
  experiments over exported feature matrices
