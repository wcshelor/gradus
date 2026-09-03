"""Thin CLI helpers for Yan 2023 experimental-lane inventories."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from tests.harness.yan2023.boundary import build_boundary_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report structural boundaries for the Yan 2023 paper-first "
            "feature lane."
        )
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "summary"),
        default="summary",
        help="Output format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_boundary_report()

    if args.format == "markdown":
        print(report.to_markdown())
        return 0

    if args.format == "json":
        print(
            json.dumps(
                {
                    "lane_id": report.lane_id,
                    "lane_name": report.lane_name,
                    "allowed_artifact_root": report.allowed_artifact_root,
                    "boundary_rules": list(report.boundary_rules),
                    "feature_statuses": report.feature_statuses,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    counts = Counter(report.feature_statuses.values())
    print(f"{report.lane_name} ({report.lane_id})")
    print(f"allowed artifact root: {report.allowed_artifact_root}")
    print(
        "feature status counts: "
        f"implemented={counts['implemented']}, "
        f"proxyable={counts['proxyable']}, "
        f"blocked={counts['blocked']}"
    )
    return 0
