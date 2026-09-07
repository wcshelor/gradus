from __future__ import annotations

import os

import pytest

from tests.harness.cipi_dataset.catalog import load_cipi_dataset
from tests.harness.oktav_dataset.catalog import load_oktav_dataset
from tests.harness.shared import resolve_dataset_root


def _root(name: str) -> str | None:
    return os.environ.get(name, "").strip() or None


@pytest.mark.parametrize("dataset_name,env_var", [("oktav", "GRADUS_OKTAV_ROOT"), ("cipi", "GRADUS_CIPI_ROOT")])
def test_local_corpus_smoke_skips_without_configuration(dataset_name: str, env_var: str) -> None:
    if _root(env_var):
        pytest.skip(f"{env_var} is configured; run the configured-root test instead")
    resolution = resolve_dataset_root(dataset_name)
    if resolution.configured and resolution.exists:
        pytest.skip(f"{dataset_name} resolved unexpectedly to {resolution.root}")
    assert resolution.source in {"not_configured", "local_config", "repo_default", "local_config_error"}


def test_local_oktav_corpus_loads_when_configured() -> None:
    root = _root("GRADUS_OKTAV_ROOT")
    if not root:
        pytest.skip("GRADUS_OKTAV_ROOT is not configured")
    result = load_oktav_dataset(dataset_root=root)
    assert result.records, "expected at least one Oktav record from the configured root"


def test_local_cipi_corpus_loads_when_configured() -> None:
    root = _root("GRADUS_CIPI_ROOT")
    if not root:
        pytest.skip("GRADUS_CIPI_ROOT is not configured")
    result = load_cipi_dataset(dataset_root=root)
    assert result.records, "expected at least one CIPI record from the configured root"
