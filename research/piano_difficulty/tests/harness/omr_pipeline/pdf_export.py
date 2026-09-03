from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from tests.harness.oktav_dataset.pdf_export import (
    DEFAULT_TIMEOUT_SECONDS,
    PdfExportInput,
    build_pdf_export_inputs as _build_pdf_export_inputs,
    discover_score_files,
    resolve_musescore_binary,
    run_oktav_pdf_export as _run_oktav_pdf_export,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "omr_pipeline" / "pdf_export" / "full_run"
DEFAULT_PDF_DIR = DEFAULT_OUT_DIR / "pdfs"
DEFAULT_LOG_DIR = DEFAULT_OUT_DIR / "logs"
DEFAULT_MANIFEST_CSV = DEFAULT_OUT_DIR / "pdf_manifest.csv"
DEFAULT_SUMMARY_JSON = DEFAULT_OUT_DIR / "corpus_summary.json"
DEFAULT_ERRORS_CSV = DEFAULT_OUT_DIR / "errors.csv"

__all__ = [
    "DEFAULT_DATASET_ROOT",
    "DEFAULT_ERRORS_CSV",
    "DEFAULT_LOG_DIR",
    "DEFAULT_MANIFEST_CSV",
    "DEFAULT_OUT_DIR",
    "DEFAULT_PDF_DIR",
    "DEFAULT_SUMMARY_JSON",
    "DEFAULT_TIMEOUT_SECONDS",
    "PdfExportInput",
    "build_pdf_export_inputs",
    "discover_score_files",
    "main",
    "resolve_musescore_binary",
    "run_oktav_pdf_export",
    "run_omr_pdf_export",
]


def build_pdf_export_inputs(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    suffixes: Sequence[str] = (".mxl",),
    repo_root: str | Path | None = None,
) -> list[PdfExportInput]:
    return _build_pdf_export_inputs(
        dataset_root=dataset_root,
        out_dir=out_dir,
        suffixes=suffixes,
        repo_root=repo_root,
    )


def run_omr_pdf_export(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    musescore_bin: str | Path | None = None,
    suffixes: Sequence[str] = (".mxl",),
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    force: bool = False,
) -> dict[str, Any]:
    out_dir_path = Path(out_dir).expanduser().resolve()
    summary = _run_oktav_pdf_export(
        dataset_root=dataset_root,
        out_dir=out_dir_path,
        musescore_bin=musescore_bin,
        suffixes=suffixes,
        timeout_seconds=timeout_seconds,
        force=force,
    )

    summary_path = Path(summary["summary_json_path"])
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "omr_pdf_export_summary.v1"
    payload["lane"] = "omr_pipeline"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    summary["summary_json_path"] = str(summary_path)
    summary["schema_version"] = payload["schema_version"]
    summary["lane"] = payload["lane"]
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_omr_pdf_export",
        description=(
            "Render Oktav .mxl scores to PDF for a small OMR prototyping lane "
            "and write a manifest under tests/artifacts/omr_pipeline."
        ),
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--musescore-bin", type=Path, default=None)
    parser.add_argument(
        "--suffix",
        action="append",
        dest="suffixes",
        default=None,
        help="Score file suffix to include. Repeat to include multiple suffixes. Defaults to .mxl.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-file MuseScore timeout in seconds.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass MuseScore's -f flag to ignore corruption and version mismatch warnings.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_omr_pdf_export(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        musescore_bin=args.musescore_bin,
        suffixes=tuple(args.suffixes or (".mxl",)),
        timeout_seconds=args.timeout_seconds,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failure_count"] else 0


run_oktav_pdf_export = run_omr_pdf_export
