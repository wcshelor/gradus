"""Deterministic artifact layout for the David CIPI walkthrough.

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

SNIPPET_DIR_NAME = "snippets"
SNIPPET_FILENAME_PATTERN = "window_{idx:03d}__measures_{rng}.png"

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
        "snippets_dir": directory / SNIPPET_DIR_NAME,
    }


def snippet_path_for_hotspot(snippets_dir: str | Path, window_index: int | None, measure_numbers) -> Path:
    """Stable snippet filename: window_<idx>__measures_<range>.png."""
    raw = list(measure_numbers or [])
    nums = [str(x).strip() for x in raw if str(x).strip()]
    # numeric sort when possible
    try:
        ints = sorted(set(int(x) for x in nums))
        nums = [str(i) for i in ints]
    except ValueError:
        nums = sorted(set(nums))
    if len(nums) == 1:
        rng = nums[0]
    elif nums:
        try:
            ints2 = [int(x) for x in nums]
            rng = f"{min(ints2)}-{max(ints2)}"
        except ValueError:
            rng = f"{nums[0]}-{nums[-1]}"
    else:
        rng = "unknown"
    import re as _re

    safe = _re.sub(r"[^A-Za-z0-9._-]", "_", rng)
    idx = int(window_index) if isinstance(window_index, int) and window_index >= 0 else 0
    return Path(snippets_dir).expanduser() / f"window_{idx:03d}__measures_{safe}.png"


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

    Only planned per-piece analysis files and top-level index files are
    removed; snippets/ directories are preserved so pre-rendered PNGs survive
    reruns (David pre-render flow).
    """
    root = Path(out_root).expanduser()
    for demo_id in demo_ids:
        directory = piece_dir(root, demo_id)
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir() and child.name == SNIPPET_DIR_NAME:
                    # preserve pre-rendered snippets
                    continue
                elif child.is_dir():
                    # remove other stray dirs? keep conservative: leave untouched
                    continue
            # remove dir only if empty or only snippets/ remains
            try:
                remaining = list(directory.iterdir())
                if not remaining:
                    directory.rmdir()
                elif len(remaining) == 1 and remaining[0].name == SNIPPET_DIR_NAME:
                    # keep piece dir with snippets
                    pass
            except FileNotFoundError:
                pass
    top = top_level_paths(root)
    for name in (TOP_INDEX_JSON, TOP_INDEX_MARKDOWN, TOP_FAILURES_CSV):
        candidate = top[name]
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()
