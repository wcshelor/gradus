from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_SCORE_SUFFIXES: tuple[str, ...] = (".xml", ".musicxml", ".mxl")
IGNORED_FILENAMES = {".ds_store"}


def normalize_filename(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def dataset_relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def repo_relative_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def is_supported_score_file(path: Path, suffixes: Sequence[str] = DEFAULT_SCORE_SUFFIXES) -> bool:
    allowed = {suffix.lower() for suffix in suffixes}
    return path.suffix.lower() in allowed


def discover_score_files(
    root: str | Path,
    *,
    suffixes: Sequence[str] = DEFAULT_SCORE_SUFFIXES,
    recursive: bool = False,
) -> list[Path]:
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        return []
    allowed = {suffix.lower() for suffix in suffixes}
    pattern = "**/*" if recursive else "*"
    paths: list[Path] = []
    for candidate in sorted(root_path.glob(pattern), key=lambda item: item.as_posix().lower()):
        if not candidate.is_file():
            continue
        if candidate.name.lower() in IGNORED_FILENAMES:
            continue
        if candidate.suffix.lower() not in allowed:
            continue
        paths.append(candidate)
    return paths


def partition_directory_entries(root: str | Path, suffixes: Sequence[str] = DEFAULT_SCORE_SUFFIXES) -> tuple[list[Path], list[str]]:
    root_path = Path(root).expanduser()
    supported = discover_score_files(root_path, suffixes=suffixes, recursive=False)
    supported_names = {item.name for item in supported}
    unsupported: list[str] = []
    if root_path.is_dir():
        for candidate in sorted(root_path.iterdir(), key=lambda item: item.name.lower()):
            if not candidate.is_file():
                continue
            if candidate.name.lower() in IGNORED_FILENAMES:
                continue
            if candidate.name in supported_names:
                continue
            unsupported.append(candidate.name)
    return supported, sorted(unsupported, key=str.lower)


def find_unsupported_files(paths: Iterable[Path], suffixes: Sequence[str] = DEFAULT_SCORE_SUFFIXES) -> list[str]:
    allowed = {suffix.lower() for suffix in suffixes}
    return sorted(
        {candidate.name for candidate in paths if candidate.suffix.lower() not in allowed},
        key=str.lower,
    )
