#!/usr/bin/env python3
"""Debussy-only compatibility wrapper for the CEO demo.

Preserves the documented Debussy command:

    python research/learning_support/ceo_demo/scripts/build_debussy_demo.py
    python research/learning_support/ceo_demo/scripts/build_debussy_demo.py --score <path> --out-dir <dir>

Delegates to ``build_demo_piece.py`` with Debussy defaults so older docs and
invocations keep working. New catalog builds should call build_demo_piece.py
directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT_DIR = Path(__file__).resolve().parent

# Ensure sibling script is importable without relying on PYTHONPATH.
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from build_demo_piece import main as build_piece_main  # type: ignore[import]

CANONICAL_SCORE_REL = Path("research/learning_support/ceo_demo/data/source_scores/debussy_arabesque-no-1.musicxml")
CANONICAL_SCORE_ABS = _REPO_ROOT / CANONICAL_SCORE_REL
ARTIFACT_DIR_REL = Path("research/learning_support/ceo_demo/artifacts/debussy_arabesque_1")
ARTIFACT_DIR_ABS = _REPO_ROOT / ARTIFACT_DIR_REL

DEMO_ID = "debussy_arabesque_1"
CIPI_ID = "x-336"
CIPI_RELATIVE_PATH = "pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Debussy Arabesque CEO demo artifacts (compatibility wrapper)"
    )
    parser.add_argument(
        "--score",
        type=Path,
        default=CANONICAL_SCORE_ABS,
        help=f"Path to the canonical MusicXML score (default: {CANONICAL_SCORE_REL.as_posix()})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ARTIFACT_DIR_ABS,
        help=f"Output directory for generated artifacts (default: {ARTIFACT_DIR_REL.as_posix()})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Forward to the generalized builder with Debussy identity filled in.
    forward_argv = [
        "--piece-id", DEMO_ID,
        "--score", str(Path(args.score)),
        "--title", "Arabesque No. 1",
        "--composer", "Claude Debussy",
        "--dataset", "cipi",
        "--dataset-id", CIPI_ID,
        "--dataset-relative-path", CIPI_RELATIVE_PATH,
        "--out-dir", str(Path(args.out_dir)),
    ]
    # Canonical warning preserved via presence check; delegate handles file-not-found.
    if Path(args.score).resolve() != CANONICAL_SCORE_ABS.resolve():
        print(
            f"[warn] Using non-canonical score path: {args.score} "
            f"(canonical is {CANONICAL_SCORE_REL.as_posix()})",
            file=sys.stderr,
        )
    return build_piece_main(forward_argv)


if __name__ == "__main__":
    raise SystemExit(main())
