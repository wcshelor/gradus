from __future__ import annotations

import csv
import json
from pathlib import Path

from tests.harness.ceo_walkthrough.cipi_selection import plan_batch
from tests.harness.ceo_walkthrough.manifest import CeoWalkthroughEntry
from tests.harness.ceo_walkthrough.runner import (
    analyze_single_piece,
    run_batch,
    run_dry_run,
    run_walkthrough,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SCORE = REPO_ROOT / "tests" / "fixtures" / "minimal_piano.musicxml"
SAFE_KNOWN_SCORE = (
    REPO_ROOT
    / "evaluation_scores"
    / "known_levels"
    / "cipi"
    / "beethoven"
    / "beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml"
)

CANONICAL_COLUMNS = [
    "cipi_id", "movement", "piece_id", "piece_uid", "legacy_piece_uid",
    "composer", "work_name", "book", "henle", "uri",
    "dataset_relative_path", "legacy_dataset_relative_path",
    "upstream_path", "filename", "normalized_filename",
]
FIXTURE_XML_TEXT = FIXTURE_SCORE.read_text()
CURATED_COLUMNS = [
    "demo_id", "composer", "title", "henle", "dataset_relative_path",
    "recognition_tier", "demo_role", "analyzer_led_note", "user_selected_note",
    "disagreement_note", "caveat_note",
]


def _write_canonical(path: Path, rel_paths: list[str]) -> Path:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for index, rel in enumerate(rel_paths):
            writer.writerow({
                "cipi_id": f"c-{index}", "movement": "1", "piece_id": f"p{index}",
                "piece_uid": f"uid{index}", "legacy_piece_uid": "",
                "composer": "C", "work_name": "W", "book": "", "henle": "4",
                "uri": "", "dataset_relative_path": rel,
                "legacy_dataset_relative_path": "", "upstream_path": "",
                "filename": Path(rel).name, "normalized_filename": "",
            })
    return path


def _write_curated(path: Path, demo_ids: list[str], rel: str) -> Path:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CURATED_COLUMNS)
        writer.writeheader()
        for demo_id in demo_ids:
            writer.writerow({
                "demo_id": demo_id, "composer": "C", "title": "T", "henle": "4",
                "dataset_relative_path": rel, "recognition_tier": "familiar",
                "demo_role": "role", "analyzer_led_note": "a",
                "user_selected_note": "u", "disagreement_note": "d",
                "caveat_note": "c",
            })
    return path


def _entry(demo_id: str = "demo_piece") -> CeoWalkthroughEntry:
    return CeoWalkthroughEntry(
        demo_id=demo_id, composer="C", title="T", henle="4",
        dataset_relative_path="pieces/bach/piece.musicxml",
        recognition_tier="familiar", demo_role="role",
        analyzer_led_note="a", user_selected_note="u",
        disagreement_note="d", caveat_note="c",
        metadata={}, source_row_index=0,
    )


def test_single_piece_writes_four_analyzer_artifacts(tmp_path: Path) -> None:
    piece_dir = tmp_path / "piece"
    payload = analyze_single_piece(FIXTURE_SCORE, piece_dir)
    assert payload["analysis_profiles"][0]["profile_id"] == "difficulty_overview"
    for name in ("analysis.json", "analysis.md", "analysis.html", "analysis.csv"):
        assert (piece_dir / name).is_file(), name


def test_single_piece_uses_committed_safe_score(tmp_path: Path) -> None:
    assert SAFE_KNOWN_SCORE.is_file(), "committed CIPI-safe score must exist"
    payload = analyze_single_piece(SAFE_KNOWN_SCORE, tmp_path / "known")
    assert payload["analysis_profiles"]


def test_single_piece_missing_file_raises(tmp_path: Path) -> None:
    try:
        analyze_single_piece(tmp_path / "absent.musicxml", tmp_path / "piece")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")


def test_batch_continues_after_one_bad_row(tmp_path: Path, monkeypatch) -> None:
    import tests.harness.ceo_walkthrough.runner as runner_module

    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_SCORE.read_text())
    canonical = _write_canonical(
        tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"]
    )
    # Both rows resolve to the same existing file; the mock fails one of them.
    planned = plan_batch(
        [_entry("good"), _entry("bad")], dataset_root=root,
        canonical_manifest_csv=canonical,
    )
    assert [item.status for item in planned] == ["ready", "ready"]

    real_single = runner_module.analyze_single_piece

    def flaky(source_path, piece_dir):
        if "bad" in str(piece_dir):
            raise RuntimeError("boom")
        return real_single(source_path, piece_dir)

    monkeypatch.setattr(runner_module, "analyze_single_piece", flaky)
    results = run_batch(planned, tmp_path / "out")
    by_id = {item["demo_id"]: item for item in results}
    assert by_id["good"]["status"] == "success"
    assert by_id["bad"]["status"] == "analysis_failed"
    assert "boom" in by_id["bad"]["reason"]
    assert (tmp_path / "out" / "good" / "analysis.json").is_file()
    assert (tmp_path / "out" / "bad" / "piece_context.json").is_file()


def test_batch_summary_counts(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_SCORE.read_text())
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    planned = plan_batch([_entry("good")], dataset_root=root, canonical_manifest_csv=canonical)
    results = run_batch(planned, tmp_path / "out")
    assert len(results) == 1
    assert results[0]["status"] == "success"


def test_dry_run_reports_without_analysis_files(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_XML_TEXT)
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    curated = _write_curated(tmp_path / "curated.csv", ["demo_piece"], "pieces/bach/piece.musicxml")
    summary = run_dry_run(
        manifest_csv=curated, dataset_root=root, canonical_manifest_csv=canonical
    )
    assert summary["would_run"] == ["demo_piece"]
    assert summary["blocked"] == []
    assert not (tmp_path / "analysis.json").exists()


def test_dry_run_lists_blocked_pieces(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    root.mkdir()
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/other.musicxml"])
    curated = _write_curated(tmp_path / "curated.csv", ["demo_piece"], "pieces/bach/piece.musicxml")
    summary = run_dry_run(
        manifest_csv=curated, dataset_root=root, canonical_manifest_csv=canonical
    )
    assert summary["would_run"] == []
    assert len(summary["blocked"]) == 1
    assert summary["blocked"][0]["demo_id"] == "demo_piece"


def test_walkthrough_writes_top_level_reports(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_SCORE.read_text())
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    curated = _write_curated(tmp_path / "curated.csv", ["demo_piece"], "pieces/bach/piece.musicxml")
    summary = run_walkthrough(
        manifest_csv=curated, out_dir=tmp_path / "out", dataset_root=root,
        canonical_manifest_csv=canonical,
    )
    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0
    assert (tmp_path / "out" / "index.json").is_file()
    assert (tmp_path / "out" / "index.md").is_file()
    index = json.loads((tmp_path / "out" / "index.json").read_text())
    assert index["piece_count"] == 1


def test_cli_help_exposes_required_flags(capsys) -> None:
    import tests.scripts.run_ceo_cipi_walkthrough as script

    with __import__("pytest").raises(SystemExit) as exc:
        script.main(["--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    for flag in ("--dataset-root", "--manifest-csv", "--out-dir", "--limit", "--dry-run"):
        assert flag in help_text, flag


def test_cli_script_stays_thin() -> None:
    import inspect

    import tests.scripts.run_ceo_cipi_walkthrough as script

    source = inspect.getsource(script)
    assert "run_walkthrough" in source
    # Heavy lifting lives in the harness, not the script.
    assert "analyze_score" not in source
    assert "write_analysis_outputs" not in source


def test_cli_dry_run_delegates_to_harness(tmp_path: Path, capsys) -> None:
    import tests.scripts.run_ceo_cipi_walkthrough as script

    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_XML_TEXT)
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    curated = _write_curated(tmp_path / "curated.csv", ["demo_piece"], "pieces/bach/piece.musicxml")
    code = script.main([
        "--dataset-root", str(root),
        "--manifest-csv", str(curated),
        "--canonical-manifest-csv", str(canonical),
        "--out-dir", str(tmp_path / "out"),
        "--dry-run",
    ])
    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["mode"] == "dry_run"
    assert summary["would_run"] == ["demo_piece"]
