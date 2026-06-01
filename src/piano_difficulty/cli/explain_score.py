"""Verbose score explanation command."""

from __future__ import annotations

import argparse

from piano_difficulty.output.verbose_report import render_verbose_report
from piano_difficulty.pipeline import analyze_score, extract_score


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="explain_score",
        description=(
            "Analyze one MusicXML-family score and print a verbose explanation of "
            "the extracted values."
        ),
    )
    parser.add_argument("path", help="Path to a .xml, .musicxml, or .mxl score.")
    parser.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        default=["scoreanalyzer_reference"],
        help="Difficulty profile id. Repeat to analyze with multiple profiles.",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Skip difficulty profiles and explain extraction output only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.extract_only:
        payload = extract_score(args.path).to_json_payload()
    else:
        profiles = tuple(dict.fromkeys(args.profiles))
        payload = analyze_score(args.path, profile_ids=profiles).to_json_payload()

    print(render_verbose_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
