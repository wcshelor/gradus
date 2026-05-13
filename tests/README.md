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
