from __future__ import annotations

from pathlib import Path

import pytest

from tests.harness.ceo_walkthrough import artifacts


def test_fixed_root_and_demo_id_produce_expected_paths(tmp_path: Path) -> None:
    paths = artifacts.piece_artifact_paths(tmp_path / "out", "mozart_k545")
    assert paths["dir"] == tmp_path / "out" / "mozart_k545"
    for name in (
        "analysis.json", "analysis.md", "analysis.html", "analysis.csv",
        "piece_context.json", "demo_notes.md",
    ):
        assert paths[name] == tmp_path / "out" / "mozart_k545" / name


def test_top_level_paths_use_fixed_names(tmp_path: Path) -> None:
    top = artifacts.top_level_paths(tmp_path / "out")
    assert top["index.json"] == tmp_path / "out" / "index.json"
    assert top["index.md"] == tmp_path / "out" / "index.md"
    assert top["failures.csv"] == tmp_path / "out" / "failures.csv"


@pytest.mark.parametrize("bad_id", ["../escape", "a/b", "", "UPPER", "has space"])
def test_unsafe_ids_cannot_escape_artifact_root(tmp_path: Path, bad_id: str) -> None:
    with pytest.raises(ValueError):
        artifacts.piece_dir(tmp_path / "out", bad_id)
    # Nothing escaped even if the error path differs.
    if bad_id.strip():
        assert not (tmp_path / bad_id).exists()


def test_rerun_cannot_silently_mix_old_and_new_outputs(tmp_path: Path) -> None:
    root = tmp_path / "out"
    stale_piece = root / "mozart_k545"
    stale_piece.mkdir(parents=True)
    (stale_piece / "analysis.json").write_text("{}")
    (stale_piece / "stale.txt").write_text("old")
    (root / "index.md").write_text("old index")
    (root / "unrelated.txt").write_text("keep me")

    artifacts.clean_planned_outputs(root, ["mozart_k545"])

    assert not stale_piece.exists()
    assert not (root / "index.md").exists()
    assert (root / "unrelated.txt").read_text() == "keep me"


def test_clean_is_safe_on_missing_root(tmp_path: Path) -> None:
    artifacts.clean_planned_outputs(tmp_path / "nope", ["mozart_k545"])
