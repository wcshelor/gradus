from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.cipi_dataset.catalog import (
    DEFAULT_CATALOG_CSV,
    REPO_ROOT,
    load_catalog_dataframe,
    resolve_score_path,
)
from tests.harness.scoreanalyzer.scoreanalyzer_export import (
    DEFAULT_TIMEOUT_SECONDS,
    ExportInput,
    default_scoreanalyzer_root,
    run_scoreanalyzer_export,
)

DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "retired" / "cipi_og_export" / "full_cipi_run"


def build_export_inputs(
    *,
    catalog_csv: str | Path = DEFAULT_CATALOG_CSV,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    repo_root: str | Path | None = REPO_ROOT,
) -> list[ExportInput]:
    frame = load_catalog_dataframe(catalog_csv)
    dataset_root_path = Path(dataset_root).expanduser()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser()

    inputs: list[ExportInput] = []
    for record in frame.fillna("").to_dict(orient="records"):
        piece_id = str(record.get("cipi_id", "") or record.get("score_id", "")).strip()
        piece_uid = str(
            record.get("piece_uid", "") or record.get("legacy_piece_uid", "") or piece_id
        ).strip() or str(record.get("filename", "")).strip()
        metadata = {
            "piece_id": piece_id,
            "piece_uid": piece_uid,
            "title": str(record.get("work_name", "") or record.get("title", "")).strip(),
            "composer": str(record.get("composer", "")).strip(),
            "filename": str(record.get("filename", "")).strip(),
            "dataset_relative_path": str(record.get("dataset_relative_path", "")).strip(),
            "repo_relative_path": str(record.get("repo_relative_path", "")).strip(),
            "henle": record.get("henle", ""),
        }
        source_path = _resolve_catalog_source_path(
            record,
            dataset_root=dataset_root_path,
            repo_root=repo_root_path,
        )
        inputs.append(ExportInput(source_path=source_path, metadata=metadata))
    return inputs


def run_cipi_export(
    *,
    catalog_csv: str | Path = DEFAULT_CATALOG_CSV,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    php_bin: str | Path = "php",
    scoreanalyzer_root: str | Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    inputs = build_export_inputs(catalog_csv=catalog_csv, dataset_root=dataset_root)
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
        prog="run_cipi_og_export",
        description="Run ScoreAnalyzer over the CIPI catalog and export a flat matrix CSV.",
    )
    parser.add_argument("--catalog-csv", type=Path, default=DEFAULT_CATALOG_CSV)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--php-bin", type=Path, default=Path("php"))
    parser.add_argument("--scoreanalyzer-root", type=Path, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_cipi_export(
        catalog_csv=args.catalog_csv,
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        php_bin=args.php_bin,
        scoreanalyzer_root=args.scoreanalyzer_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failure_count"] else 0


def _resolve_catalog_source_path(
    record: dict[str, Any],
    *,
    dataset_root: Path,
    repo_root: Path,
) -> Path:
    resolved = resolve_score_path(record, dataset_root=dataset_root, repo_root=repo_root)
    if resolved is not None:
        return resolved

    dataset_relative_path = str(record.get("dataset_relative_path", "")).strip()
    if dataset_relative_path:
        direct = (dataset_root / dataset_relative_path).expanduser()
        if direct.is_file():
            return direct
        legacy_rel = str(record.get("legacy_dataset_relative_path", "") or "").strip()
        if legacy_rel:
            legacy_direct = (dataset_root / legacy_rel).expanduser()
            if legacy_direct.is_file():
                return legacy_direct
        return direct

    repo_relative_path = str(record.get("repo_relative_path", "")).strip()
    if repo_relative_path:
        return (repo_root / repo_relative_path).expanduser()

    filename = str(record.get("filename", "")).strip()
    if filename:
        return (dataset_root / filename).expanduser()

    score_id = str(record.get("score_id", "")).strip() or "cipi-piece"
    return (dataset_root / f"{score_id}.xml").expanduser()

