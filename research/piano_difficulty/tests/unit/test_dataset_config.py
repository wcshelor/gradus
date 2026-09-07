from __future__ import annotations

from pathlib import Path

import pytest

from tests.harness.shared import (
    DatasetSpec,
    parse_dataset_config_file,
    resolve_dataset_root,
)


def test_dataset_spec_normalizes_name_and_keeps_optional_paths() -> None:
    spec = DatasetSpec(dataset_name="Oktav")
    assert spec.dataset_name == "oktav"
    assert spec.manifest_path is None
    assert spec.label_source_path is None
    assert ".musicxml" in "".join(spec.score_globs).lower()

    cipi = DatasetSpec(
        dataset_name="cipi",
        root=Path("/tmp/cipi"),
        manifest_path=Path("/tmp/manifest.csv"),
    )
    assert cipi.normalized_name == "cipi"
    assert cipi.expected_suffixes


def test_explicit_root_wins_over_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    env_root = tmp_path / "env"
    env_root.mkdir()
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(env_root))
    resolution = resolve_dataset_root("oktav", explicit_root=explicit)
    assert resolution.source == "cli"
    assert resolution.root == explicit
    assert resolution.exists


def test_env_wins_over_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_root = tmp_path / "env"
    env_root.mkdir()
    config_root = tmp_path / "config"
    config_root.mkdir()
    config_path = tmp_path / "datasets.toml"
    config_path.write_text(f'[oktav]\nroot = "{config_root}"\n')
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(env_root))
    monkeypatch.setenv("GRADUS_DATASETS_CONFIG", str(config_path))
    resolution = resolve_dataset_root("oktav")
    assert resolution.source == "env"


def test_explicit_config_path_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRADUS_OKTAV_ROOT", raising=False)
    first = tmp_path / "first"
    first.mkdir()
    second = tmp_path / "second"
    second.mkdir()
    first_config = tmp_path / "first.toml"
    first_config.write_text(f'[oktav]\nroot = "{first}"\n')
    monkeypatch.setenv("GRADUS_DATASETS_CONFIG", str(tmp_path / "second.toml"))
    (tmp_path / "second.toml").write_text(f'[oktav]\nroot = "{second}"\n')
    resolution = resolve_dataset_root("oktav", config_path=first_config)
    assert resolution.root == first
    assert resolution.source == "local_config"


def test_missing_configured_path_reports_clearly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRADUS_OKTAV_ROOT", raising=False)
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv("GRADUS_CIPI_ROOT", str(missing))
    resolution = resolve_dataset_root("cipi")
    assert resolution.configured
    assert not resolution.exists
    assert "does not exist" in resolution.detail


def test_not_configured_reports_clearly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GRADUS_CIPI_ROOT", raising=False)
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    monkeypatch.setattr("tests.harness.shared.dataset_config.DEFAULT_LOCAL_CONFIG_PATH", tmp_path / "absent.toml")
    resolution = resolve_dataset_root("cipi")
    assert resolution.source == "not_configured"
    assert not resolution.configured


def test_parse_valid_and_missing_section(tmp_path: Path) -> None:
    config_path = tmp_path / "datasets.toml"
    config_path.write_text('[oktav]\nroot = "/tmp/oktav"\n\n[cipi]\nroot = "/tmp/cipi"\n')
    sections = parse_dataset_config_file(config_path)
    assert sections["oktav"]["root"] == "/tmp/oktav"
    assert "unknown" not in sections


def test_parse_malformed_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "datasets.toml"
    config_path.write_text("[oktav\nroot = \n")
    with pytest.raises(ValueError, match="Malformed dataset config"):
        parse_dataset_config_file(config_path)


def test_parse_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_dataset_config_file(tmp_path / "absent.toml")
