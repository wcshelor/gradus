"""Thin runner for the David CIPI walkthrough harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from tests.harness.david_walkthrough.cipi_selection import (
    DEFAULT_CANONICAL_MANIFEST_CSV,
    DEFAULT_CURATION_MANIFEST_CSV,
)
from tests.harness.david_walkthrough.runner import run_walkthrough

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "david_walkthrough" / "cipi_familiar_v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_david_cipi_walkthrough",
        description=(
            "Run the curated CIPI walkthrough manifest through the existing "
            "difficulty analysis and write David demo evidence."
        ),
    )
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--manifest-csv", type=Path, default=DEFAULT_CURATION_MANIFEST_CSV)
    parser.add_argument(
        "--canonical-manifest-csv", type=Path, default=DEFAULT_CANONICAL_MANIFEST_CSV
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--fresh-run-dir",
        action="store_true",
        help="Allocate a timestamped run directory under the output parent.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_walkthrough(
        manifest_csv=args.manifest_csv,
        out_dir=args.out_dir,
        dataset_root=args.dataset_root,
        canonical_manifest_csv=args.canonical_manifest_csv,
        limit=args.limit,
        dry_run=args.dry_run,
        fresh_run_dir=args.fresh_run_dir,
    )
    import json

    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    if summary.get("mode") == "dry_run":
        return 0 if not summary.get("blocked") else 1
    return 0 if not summary.get("failure_count") else 1


if __name__ == "__main__":
    raise SystemExit(main())
