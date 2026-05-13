"""Command-line entrypoint for the extraction pipeline.

The first command should remain narrow and predictable:

`piano-difficulty extract <path>`

As the repository grows, this module can add options for output format, measure
detail, debug diagnostics, and eventually windowed summaries.
"""

from __future__ import annotations

import argparse


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

    return parser


def main() -> int:
    """CLI entrypoint.

    The final implementation should dispatch to the extraction pipeline and
    print or write structured output.
    """

    parser = build_parser()
    parser.parse_args()
    raise NotImplementedError("CLI execution is not implemented yet.")

