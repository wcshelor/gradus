"""Command-line entrypoint for the extraction pipeline.

The first command should remain narrow and predictable:

`piano-difficulty extract <path>`

As the repository grows, this module can add options for output format, measure
detail, debug diagnostics, and eventually windowed summaries.
"""

from __future__ import annotations

import argparse
import json

from piano_difficulty.difficulty_analysis.batch import analyze_batch
from piano_difficulty.difficulty_analysis.markdown import render_markdown_report
from piano_difficulty.pipeline import analyze_score, extract_score


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="piano-difficulty",
        description="Extract symbolic piano difficulty descriptors from score files.",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract_parser = subparsers.add_parser(
        "extract",
        help="Load one supported score and emit structured descriptors.",
    )
    extract_parser.add_argument("path", help="Path to a MusicXML or MXL file.")
    extract_parser.add_argument(
        "--format",
        default="json",
        choices=["json"],
        help="Output format. JSON is the canonical format in early versions.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Load one score, then run one or more difficulty profiles.",
    )
    analyze_parser.add_argument("path", help="Path to a MusicXML or MXL file.")
    analyze_parser.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        default=["scoreanalyzer_reference"],
        help="Difficulty profile id. Repeat to analyze with multiple profiles.",
    )
    analyze_parser.add_argument(
        "--format",
        default="json",
        choices=["json", "markdown"],
        help="Output format for analyzed scores.",
    )

    batch_parser = subparsers.add_parser(
        "analyze-batch",
        help="Analyze one score file or a directory of score files.",
    )
    batch_parser.add_argument("source", help="Score file or directory.")
    batch_parser.add_argument("--out-dir", required=True, help="Output directory.")
    batch_parser.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        default=["scoreanalyzer_reference"],
        help="Difficulty profile id. Repeat to analyze with multiple profiles.",
    )
    batch_parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Write flat CSV exports alongside JSON payloads.",
    )

    return parser


def main() -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "extract":
        result = extract_score(args.path)
        print(json.dumps(result.to_json_payload(), indent=2, sort_keys=True))
        return 0
    if args.command == "analyze":
        profiles = tuple(dict.fromkeys(args.profiles))
        result = analyze_score(args.path, profile_ids=profiles)
        payload = result.to_json_payload()
        if args.format == "markdown":
            print(render_markdown_report(payload, profile_id=profiles[0]))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "analyze-batch":
        profiles = tuple(dict.fromkeys(args.profiles))
        batch = analyze_batch(
            args.source,
            out_dir=args.out_dir,
            profile_ids=profiles,
            write_csv=args.write_csv,
        )
        print(
            json.dumps(
                {
                    "file_count": len(batch.inputs),
                    "success_count": len(batch.payload_paths),
                    "failure_count": len(batch.failures),
                    "out_dir": args.out_dir,
                    "corpus_summary": str(batch.corpus_summary_path),
                    "errors_csv": str(batch.errors_csv_path) if batch.errors_csv_path else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if batch.failures else 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
