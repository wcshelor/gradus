from __future__ import annotations

import argparse
import json
from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity import (
    _default_artifacts_dir,
    _default_pieces_root,
    _resolve_shim_path,
    run_comparison,
)
from piano_difficulty.comparison.scoreanalyzer_parity_summary import build_report


def _default_out_csv() -> Path:
    return _default_artifacts_dir() / "comparison.csv"


def _default_out_json() -> Path:
    return _default_artifacts_dir() / "comparison_summary.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_scoreanalyzer_parity_pipeline",
        description="Run OG-vs-replica parity from piece sampling through CSV and summary JSON.",
    )
    parser.add_argument("--count", type=int, required=True, help="Number of pieces to process.")
    parser.add_argument("--php-bin", type=Path, required=True, help="Path to php executable.")
    parser.add_argument("--out-csv", type=Path, default=_default_out_csv(), help="Output CSV path.")
    parser.add_argument("--out-json", type=Path, default=_default_out_json(), help="Output summary JSON path.")
    parser.add_argument(
        "--pieces-root",
        type=Path,
        default=_default_pieces_root(),
        help="Pieces root directory.",
    )
    parser.add_argument("--start-offset", type=int, default=0, help="Start index after sorting.")
    parser.add_argument("--strict", action="store_true", help="Stop at first mismatch or error.")
    parser.add_argument(
        "--include-raw-json-dir",
        type=Path,
        default=None,
        help="Optional per-piece OG/replica raw JSON directory.",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Top N metrics/pieces in summary.")
    parser.add_argument(
        "--show-matches",
        action="store_true",
        help="Include clean pieces in summary JSON piece list.",
    )
    return parser


def _print_summary(report: dict[str, object], out_csv: Path, out_json: Path, top_k: int) -> None:
    summary = report["summary"]
    headline = "FAIL" if summary["has_failures"] else "PASS"
    print(f"[{headline}] ScoreAnalyzer parity pipeline")
    print(
        "rows={row_count}, metrics={metric_count}, success={success_count}, errors={error_count}".format(
            **summary
        )
    )
    print(
        "mismatch_pieces={mismatch_piece_count}, mismatch_instances={mismatch_metric_instances}, mismatch_rate={overall_mismatch_rate:.4f}".format(
            **summary
        )
    )
    print(f"Top mismatching metrics (top {top_k}):")
    for item in report["top_mismatching_metrics"]:
        print(
            f"- {item['metric']}: mismatches={item['mismatch_count']}, affected_pieces={item['affected_pieces']}, rate={item['mismatch_rate']:.4f}"
        )
    print(f"Top problematic pieces (top {top_k}):")
    for piece in report["top_problem_pieces"]:
        print(f"- {piece['piece_relpath']}: mismatch_count={piece['mismatch_count']}, status={piece['status']}")
    print(f"CSV output: {out_csv}")
    print(f"JSON report: {out_json}")


def run_pipeline(
    *,
    pieces_root: Path,
    count: int,
    start_offset: int,
    php_bin: Path,
    out_csv: Path,
    out_json: Path,
    strict: bool,
    include_raw_json_dir: Path | None,
    top_k: int,
    show_matches: bool,
) -> int:
    if top_k <= 0:
        print("top-k must be > 0")
        return 2
    shim_path = _resolve_shim_path(pieces_root)
    run_comparison(
        pieces_root=pieces_root,
        count=count,
        start_offset=start_offset,
        php_bin=php_bin,
        shim_path=shim_path,
        out_csv=out_csv,
        strict=strict,
        include_raw_json_dir=include_raw_json_dir,
    )
    try:
        report = build_report(out_csv, top_k=top_k, show_matches=show_matches)
    except (OSError, ValueError) as exc:
        print(f"Malformed or unreadable CSV: {exc}")
        return 2
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    _print_summary(report, out_csv, out_json, top_k)
    return 1 if report["summary"]["has_failures"] else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_pipeline(
        pieces_root=args.pieces_root,
        count=args.count,
        start_offset=args.start_offset,
        php_bin=args.php_bin,
        out_csv=args.out_csv,
        out_json=args.out_json,
        strict=args.strict,
        include_raw_json_dir=args.include_raw_json_dir,
        top_k=args.top_k,
        show_matches=args.show_matches,
    )
