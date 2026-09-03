from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from piano_difficulty.comparison.scoreanalyzer_parity import _default_artifacts_dir


REQUIRED_BASE_COLUMNS = (
    "piece_relpath",
    "status",
    "error",
    "all_equal",
    "mismatch_count",
)


@dataclass(slots=True)
class PieceReport:
    piece_relpath: str
    status: str
    mismatch_count: int
    mismatching_metrics: list[str]
    error: str


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    if normalized == "":
        return None
    return None


def _is_missing(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip() in {"", "None", "null", "NULL"}


def _discover_metrics(headers: list[str]) -> list[str]:
    metrics = sorted(
        {
            header[len("og_") :]
            for header in headers
            if header.startswith("og_")
        }
    )
    return metrics


def _validate_headers(headers: list[str], metrics: list[str]) -> None:
    missing_base = [name for name in REQUIRED_BASE_COLUMNS if name not in headers]
    if missing_base:
        raise ValueError(f"Missing required base columns: {', '.join(missing_base)}")
    if not metrics:
        raise ValueError("No metric columns found (expected columns prefixed with 'og_').")


def _metric_mismatch(row: dict[str, str], metric: str) -> bool:
    if row.get("status", "").strip().lower() != "ok":
        return True

    equal_value = _parse_bool(row.get(f"equal_{metric}"))
    if equal_value is not None:
        return not equal_value

    og_value = row.get(f"og_{metric}")
    replica_value = row.get(f"replica_{metric}")
    if _is_missing(og_value) != _is_missing(replica_value):
        return True
    if _is_missing(og_value) and _is_missing(replica_value):
        return False
    return og_value != replica_value


def build_report(csv_path: Path, *, top_k: int = 10, show_matches: bool = False) -> dict[str, Any]:
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV is missing a header row.")
        headers = list(reader.fieldnames)
        metrics = _discover_metrics(headers)
        _validate_headers(headers, metrics)
        rows = list(reader)

    metric_mismatch_counts: dict[str, int] = defaultdict(int)
    metric_piece_sets: dict[str, set[str]] = defaultdict(set)
    pieces: list[PieceReport] = []
    errors: list[dict[str, str]] = []

    row_count = len(rows)
    error_count = 0
    success_count = 0
    mismatch_piece_count = 0
    mismatch_metric_instances = 0

    for row in rows:
        piece_relpath = row.get("piece_relpath", "")
        status = row.get("status", "")
        error = row.get("error", "")
        if status.strip().lower() == "ok":
            success_count += 1
        else:
            error_count += 1
            errors.append(
                {
                    "piece_relpath": piece_relpath,
                    "status": status,
                    "error": error,
                }
            )

        mismatching_metrics: list[str] = []
        for metric in metrics:
            if _metric_mismatch(row, metric):
                mismatching_metrics.append(metric)
                metric_mismatch_counts[metric] += 1
                metric_piece_sets[metric].add(piece_relpath)

        mismatch_count = len(mismatching_metrics)
        if mismatch_count > 0:
            mismatch_piece_count += 1
        mismatch_metric_instances += mismatch_count

        if show_matches or mismatch_count > 0 or status.strip().lower() != "ok":
            pieces.append(
                PieceReport(
                    piece_relpath=piece_relpath,
                    status=status,
                    mismatch_count=mismatch_count,
                    mismatching_metrics=mismatching_metrics,
                    error=error,
                )
            )

    denominator = row_count * len(metrics) if row_count and metrics else 0
    overall_rate = (mismatch_metric_instances / denominator) if denominator else 0.0
    has_failures = (mismatch_piece_count > 0) or (error_count > 0)

    metric_rows = [
        {
            "metric": metric,
            "mismatch_count": metric_mismatch_counts.get(metric, 0),
            "affected_pieces": len(metric_piece_sets.get(metric, set())),
            "mismatch_rate": (
                metric_mismatch_counts.get(metric, 0) / row_count if row_count else 0.0
            ),
        }
        for metric in metrics
    ]
    metric_rows.sort(
        key=lambda item: (-item["mismatch_count"], -item["affected_pieces"], item["metric"])
    )

    pieces_sorted = sorted(
        pieces,
        key=lambda item: (-item.mismatch_count, item.piece_relpath),
    )

    return {
        "summary": {
            "row_count": row_count,
            "metric_count": len(metrics),
            "success_count": success_count,
            "error_count": error_count,
            "mismatch_piece_count": mismatch_piece_count,
            "mismatch_metric_instances": mismatch_metric_instances,
            "overall_mismatch_rate": overall_rate,
            "has_failures": has_failures,
        },
        "metrics": metric_rows,
        "top_mismatching_metrics": metric_rows[:top_k],
        "pieces": [
            {
                "piece_relpath": piece.piece_relpath,
                "status": piece.status,
                "mismatch_count": piece.mismatch_count,
                "mismatching_metrics": piece.mismatching_metrics,
                "error": piece.error,
            }
            for piece in pieces_sorted
        ],
        "top_problem_pieces": [
            {
                "piece_relpath": piece.piece_relpath,
                "status": piece.status,
                "mismatch_count": piece.mismatch_count,
                "mismatching_metrics": piece.mismatching_metrics,
                "error": piece.error,
            }
            for piece in pieces_sorted[:top_k]
        ],
        "errors": errors,
    }


def _print_console_summary(report: dict[str, Any], out_json: Path, top_k: int) -> None:
    summary = report["summary"]
    headline = "FAIL" if summary["has_failures"] else "PASS"
    print(f"[{headline}] ScoreAnalyzer parity summary")
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
        print(
            f"- {piece['piece_relpath']}: mismatch_count={piece['mismatch_count']}, status={piece['status']}"
        )
    print(f"JSON report: {out_json}")


def _default_in_csv() -> Path:
    return _default_artifacts_dir() / "comparison.csv"


def _default_out_json() -> Path:
    return _default_artifacts_dir() / "comparison_summary.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="summarize_scoreanalyzer_comparison",
        description="Summarize OG-vs-replica comparison CSV outputs.",
    )
    parser.add_argument("--in-csv", type=Path, default=_default_in_csv(), help="Path to comparison CSV.")
    parser.add_argument("--out-json", type=Path, default=_default_out_json(), help="Path to write JSON summary.")
    parser.add_argument("--top-k", type=int, default=10, help="Top N metrics/pieces to show.")
    parser.add_argument(
        "--show-matches",
        action="store_true",
        help="Include pieces without mismatches in the full JSON piece list.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top_k <= 0:
        print("top-k must be > 0")
        return 2
    try:
        report = build_report(args.in_csv, top_k=args.top_k, show_matches=args.show_matches)
    except (OSError, ValueError) as exc:
        print(f"Malformed or unreadable CSV: {exc}")
        return 2

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    _print_console_summary(report, args.out_json, args.top_k)
    return 1 if report["summary"]["has_failures"] else 0
