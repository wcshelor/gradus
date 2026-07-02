from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.scoreanalyzer.scoreanalyzer_export import (
    DEFAULT_TIMEOUT_SECONDS,
    ExportInput,
    default_scoreanalyzer_root,
    discover_score_files,
    run_scoreanalyzer_export,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "og_export" / "full_run"


def build_export_inputs(dataset_root: str | Path = DEFAULT_DATASET_ROOT) -> list[ExportInput]:
    source_paths = discover_score_files(dataset_root)
    inputs: list[ExportInput] = []
    for source_path in source_paths:
        inputs.append(
            ExportInput(
                source_path=source_path,
                metadata={
                    "piece_id": _piece_id_from_path(source_path),
                    "piece_uid": _piece_id_from_path(source_path),
                    "title": source_path.stem,
                    "composer": "",
                    "filename": source_path.name,
                    "dataset_relative_path": _relative_path(source_path, Path(dataset_root)),
                    "repo_relative_path": _relative_path(source_path, REPO_ROOT),
                },
            )
        )
    return inputs


def run_oktav_export(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    php_bin: str | Path = "php",
    scoreanalyzer_root: str | Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    inputs = build_export_inputs(dataset_root=dataset_root)
    result = run_scoreanalyzer_export(
        inputs,
        out_dir=out_dir,
        matrix_csv_name="og_full_dataset.csv",
        summary_json_name="corpus_summary.json",
        errors_csv_name="errors.csv",
        php_bin=php_bin,
        scoreanalyzer_root=scoreanalyzer_root or default_scoreanalyzer_root(),
        timeout_seconds=timeout_seconds,
    )
    return {
        "matrix_csv_path": str(result.matrix_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "errors_csv_path": str(result.errors_csv_path) if result.errors_csv_path else None,
        "piece_json_dir": str(result.piece_json_dir),
        "log_dir": str(result.log_dir),
        "input_count": len(result.inputs),
        "success_count": len(result.inputs) - len(result.failures),
        "failure_count": len(result.failures),
        "timeout_seconds": timeout_seconds,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_oktav_og_export",
        description="Run ScoreAnalyzer over the Oktav corpus and export a flat matrix CSV.",
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--php-bin", type=Path, default=Path("php"))
    parser.add_argument("--scoreanalyzer-root", type=Path, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_oktav_export(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        php_bin=args.php_bin,
        scoreanalyzer_root=args.scoreanalyzer_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failure_count"] else 0


def _piece_id_from_path(path: Path) -> str:
    stem = path.stem
    if "OK" in stem:
        marker_index = stem.find("OK")
        candidate = stem[marker_index:]
        candidate = candidate.split()[0]
        return candidate.replace("-", "_")
    return stem


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()

