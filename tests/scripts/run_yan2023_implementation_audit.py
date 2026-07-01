"""Run the strict Yan 2023 implementation audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.yan2023.implementation_audit import (  # noqa: E402
    build_json_payload,
    build_markdown_report,
    recommended_base_status_counts,
    recommended_status_counts,
    safe_base_features,
    validate_audit_metadata,
    validate_feature_fixture_regression,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit the currently implemented Yan 2023 feature slots."
    )
    parser.add_argument(
        "--format",
        choices=("summary", "json", "markdown"),
        default="summary",
        help="Output format.",
    )
    parser.add_argument(
        "--write-artifact",
        type=Path,
        help="Optional path to write the Markdown audit report.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if audit metadata or fixture regression checks report issues.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    markdown_report = build_markdown_report()
    payload = build_json_payload()
    slot_counts = recommended_status_counts()
    base_counts = recommended_base_status_counts()
    safe_features = safe_base_features()
    metadata_issues = validate_audit_metadata()
    regression_issues = validate_feature_fixture_regression()

    if args.write_artifact:
        args.write_artifact.parent.mkdir(parents=True, exist_ok=True)
        args.write_artifact.write_text(markdown_report, encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(markdown_report, end="")
    else:
        print("Yan 2023 implementation audit")
        print(
            "post-audit slot counts: "
            f"implemented={slot_counts['implemented']}, "
            f"math_drafted={slot_counts['math_drafted']}, "
            f"proxyable={slot_counts['proxyable']}, "
            f"blocked={slot_counts['blocked']}"
        )
        print(
            "post-audit base counts: "
            f"implemented={base_counts['implemented']}, "
            f"math_drafted={base_counts['math_drafted']}, "
            f"proxyable={base_counts['proxyable']}, "
            f"blocked={base_counts['blocked']}"
        )
        print("safe base features: " + ", ".join(safe_features))
        print(f"metadata issues: {len(metadata_issues)}")
        print(f"fixture regression issues: {len(regression_issues)}")

    if args.check:
        issues = [*metadata_issues, *regression_issues]
        if issues:
            for issue in issues:
                print(f"[FAIL] {issue}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
