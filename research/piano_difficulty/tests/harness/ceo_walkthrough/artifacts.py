"""Deterministic artifact layout for the CEO CIPI walkthrough.

No timestamps in default paths; reruns overwrite the explicit output root
in place (see README for the freshness policy).
"""

from __future__ import annotations

from pathlib import Path

from .manifest import validate_demo_id

PIECE_ANALYSIS_FILES: tuple[str, ...] = (
    "analysis.json",
    "analysis.md",
    "analysis.html",
    "analysis.csv",
)
PIECE_CONTEXT_FILE = "piece_context.json"
PIECE_NOTES_FILE = "demo_notes.md"

TOP_INDEX_JSON = "index.json"
TOP_INDEX_MARKDOWN = "index.md"
TOP_FAILURES_CSV = "failures.csv"


def piece_dir(out_root: str | Path, demo_id: str) -> Path:
    """Return the per-piece directory, rejecting IDs that could escape."""
    cleaned = validate_demo_id(demo_id, source="artifact layout")
    root = Path(out_root).expanduser()
    resolved = (root / cleaned).resolve()
    if resolved != root.resolve() and root.resolve() not in resolved.parents:
        raise ValueError(f"demo_id {cleaned!r} escapes the artifact root {root}.")
    return root / cleaned


def piece_artifact_paths(out_root: str | Path, demo_id: str) -> dict[str, Path]:
    """Map artifact names to paths for one piece directory."""
    directory = piece_dir(out_root, demo_id)
    return {
        "dir": directory,
        "analysis.json": directory / "analysis.json",
        "analysis.md": directory / "analysis.md",
        "analysis.html": directory / "analysis.html",
        "analysis.csv": directory / "analysis.csv",
        "piece_context.json": directory / PIECE_CONTEXT_FILE,
        "demo_notes.md": directory / PIECE_NOTES_FILE,
    }


def top_level_paths(out_root: str | Path) -> dict[str, Path]:
    """Map top-level run files to paths."""
    root = Path(out_root).expanduser()
    return {
        "dir": root,
        TOP_INDEX_JSON: root / TOP_INDEX_JSON,
        TOP_INDEX_MARKDOWN: root / TOP_INDEX_MARKDOWN,
        TOP_FAILURES_CSV: root / TOP_FAILURES_CSV,
    }


def clean_planned_outputs(out_root: str | Path, demo_ids: list[str]) -> None:
    """Remove stale planned outputs so reruns cannot silently mix evidence.

    Only the planned per-piece directories and the top-level index files
    are removed; anything else under the output root is left untouched.
    """
    root = Path(out_root).expanduser()
    for demo_id in demo_ids:
        directory = piece_dir(root, demo_id)
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if child.is_file() or child.is_symlink():
                    child.unlink()
            directory.rmdir()
    top = top_level_paths(root)
    for name in (TOP_INDEX_JSON, TOP_INDEX_MARKDOWN, TOP_FAILURES_CSV):
        candidate = top[name]
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()
