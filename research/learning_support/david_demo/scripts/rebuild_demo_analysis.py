#!/usr/bin/env python3
"""Rebuild David demo analysis artifacts from the current runtime code.

This is a thin convenience wrapper around ``build_demo_piece.py``. It reads the
curated catalog from ``artifacts/pieces.json`` and rebuilds selected artifact
folders in place, so changes to feature extraction, taxonomy weights, hotspot
logic, or explanation code are reflected without hand-copying long commands.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS_DIR = REPO_ROOT / "research" / "learning_support" / "david_demo" / "artifacts"
PIECES_JSON = ARTIFACTS_DIR / "pieces.json"
SOURCE_DIR = REPO_ROOT / "research" / "learning_support" / "david_demo" / "data" / "source_scores"
BUILD_SCRIPT = REPO_ROOT / "research" / "learning_support" / "david_demo" / "scripts" / "build_demo_piece.py"
VALIDATE_SCRIPT = REPO_ROOT / "research" / "learning_support" / "david_demo" / "scripts" / "validate_demo_readiness.py"

CURATED_FILE_MAP = {
    "beethoven_fur_elise": "beethoven_fur-elise.musicxml",
    "beethoven_bagatelle_119_10": "beethoven_bagatelle-a-major-op-119-no-10.musicxml",
    "mozart_k545": "mozart_k545_mvt1.musicxml",
    "chopin_waltz_a_minor_kk_ivb_11": "chopin_waltz-a-minor-kk-ivb-11.musicxml",
    "chopin_prelude_e_minor_28_4": "chopin_prelude-e-minor-op-28-no-4.musicxml",
    "chopin_prelude_a_major_28_7": "chopin_prelude-a-major-op-28-no-7.musicxml",
    "debussy_arabesque_1": "debussy_arabesque-no-1.musicxml",
    "debussy_clair_de_lune": "debussy_clair-de-lune.musicxml",
    "satie_gymnopedie_1": "satie_gymnopedie-no-1.musicxml",
    "oktav_le_onde": "oktav_le-onde_OK00027.xml",
    "oktav_a_thousand_miles": "oktav_a-thousand-miles_OK00016.xml",
    "oktav_viva_la_vida": "oktav_viva-la-vida_OK00009.xml",
}


def _load_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pieces = data.get("pieces") if isinstance(data, dict) else data
    if not isinstance(pieces, list):
        raise ValueError(f"Catalog has no pieces list: {path}")
    return [piece for piece in pieces if isinstance(piece, dict)]


def _select_pieces(pieces: list[dict], requested: list[str]) -> list[dict]:
    if not requested or requested == ["all"]:
        return pieces
    by_id = {piece.get("id"): piece for piece in pieces}
    missing = [piece_id for piece_id in requested if piece_id not in by_id]
    if missing:
        known = ", ".join(str(piece.get("id")) for piece in pieces)
        raise ValueError(f"Unknown piece id(s): {', '.join(missing)}. Known: {known}")
    return [by_id[piece_id] for piece_id in requested]


def _command_for_piece(piece: dict, *, python_exe: str, window_sizes: str) -> list[str]:
    piece_id = str(piece["id"])
    try:
        filename = CURATED_FILE_MAP[piece_id]
    except KeyError as exc:
        raise ValueError(f"No curated source-score mapping for {piece_id}") from exc

    score = SOURCE_DIR / filename
    out_dir = ARTIFACTS_DIR / piece_id
    cmd = [
        python_exe,
        str(BUILD_SCRIPT),
        "--piece-id",
        piece_id,
        "--score",
        str(score),
        "--title",
        str(piece.get("title") or piece_id),
        "--composer",
        str(piece.get("composer") or "Unknown"),
        "--dataset",
        str(piece.get("dataset") or ""),
        "--out-dir",
        str(out_dir),
        "--window-sizes",
        window_sizes,
    ]
    if piece.get("dataset_id"):
        cmd += ["--dataset-id", str(piece["dataset_id"])]
    if piece.get("dataset_relative_path"):
        cmd += ["--dataset-relative-path", str(piece["dataset_relative_path"])]
    return cmd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild David demo analysis artifacts using the current analysis code and taxonomy weights."
    )
    parser.add_argument(
        "pieces",
        nargs="*",
        help="Piece ids to rebuild, or 'all'. Omit to rebuild all catalog pieces.",
    )
    parser.add_argument(
        "--pieces-json",
        type=Path,
        default=PIECES_JSON,
        help="Catalog JSON path. Defaults to David demo artifacts/pieces.json.",
    )
    parser.add_argument(
        "--window-sizes",
        default="2,4",
        help="Comma-separated window sizes passed to build_demo_piece.py, e.g. 2,4 or 1,2,4.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use for build_demo_piece.py. Defaults to current interpreter.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--keep-going", action="store_true", help="Continue rebuilding remaining pieces after failures.")
    parser.add_argument("--validate", action="store_true", help="Run validate_demo_readiness.py after successful rebuilds.")
    parser.add_argument("--list", action="store_true", help="List catalog piece ids and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pieces = _load_catalog(args.pieces_json)

    if args.list:
        for piece in pieces:
            print(f"{piece.get('id')}\t{piece.get('composer', '')}\t{piece.get('title', '')}")
        return 0

    selected = _select_pieces(pieces, args.pieces or ["all"])
    failures: list[tuple[str, int]] = []

    for index, piece in enumerate(selected, start=1):
        piece_id = str(piece["id"])
        cmd = _command_for_piece(piece, python_exe=args.python, window_sizes=args.window_sizes)
        print(f"[{index}/{len(selected)}] rebuild {piece_id}")
        print("  " + " ".join(cmd))
        if args.dry_run:
            continue
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failures.append((piece_id, result.returncode))
            if not args.keep_going:
                print(f"[error] {piece_id} failed with exit {result.returncode}", file=sys.stderr)
                return result.returncode

    if failures:
        print("[error] Rebuild failures:", file=sys.stderr)
        for piece_id, code in failures:
            print(f"  - {piece_id}: exit {code}", file=sys.stderr)
        return 1

    if args.validate and not args.dry_run:
        print("[validate] running demo readiness check")
        return subprocess.run([args.python, str(VALIDATE_SCRIPT), "--pieces", str(args.pieces_json)]).returncode

    print("[ok] rebuild complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
