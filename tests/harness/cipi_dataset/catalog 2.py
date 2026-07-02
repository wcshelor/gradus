from __future__ import annotations

import argparse
import csv
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_DATASET_ROOT = Path(
    os.environ.get("CIPI_DATASET_ROOT", "/Users/campshelor/Desktop/oktav-thesis/datasets/cipi")
)
DEFAULT_INDEX_JSON = Path(
    os.environ.get("CIPI_INDEX_JSON", "/Users/campshelor/Downloads/index.json")
)
DEFAULT_CATALOG_CSV = Path("evaluation_scores/manifests/cipi_dataset_catalog.csv")


@dataclass(slots=True)
class CipiCatalogResult:
    rows: list[dict[str, Any]]
    missing_files: list[str]
    extra_files: list[str]


def load_catalog_dataframe(path: str | Path = DEFAULT_CATALOG_CSV) -> pd.DataFrame:
    csv_path = Path(path).expanduser()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)
    return pd.read_csv(csv_path)


def load_index_json(path: str | Path) -> dict[str, dict[str, Any]]:
    index_path = Path(path).expanduser()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"CIPI index '{index_path}' must be a JSON object.")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def build_catalog(
    index_rows: dict[str, dict[str, Any]],
    *,
    dataset_root: str | Path,
    repo_root: str | Path,
) -> CipiCatalogResult:
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root).expanduser().resolve()
    dataset_index = _build_dataset_index(dataset_root_path)

    rows: list[dict[str, Any]] = []
    missing_files: list[str] = []
    matched_paths: set[str] = set()

    for piece_id, row in sorted(index_rows.items()):
        paths = row.get("path") or {}
        if not isinstance(paths, dict) or not paths:
            continue

        for movement, relative_path in sorted(paths.items(), key=lambda item: str(item[0])):
            score_path = _resolve_score_path(
                dataset_index,
                composer=_clean_text(row.get("composer")),
                work_name=_clean_text(row.get("work_name")),
                movement=str(movement),
            )
            if score_path is None:
                missing_files.append(str(relative_path))
                continue

            resolved = score_path.resolve()
            matched_paths.add(resolved.relative_to(dataset_root_path).as_posix())
            parent = score_path.parent
            composer_folder = ""
            try:
                composer_folder = parent.relative_to(dataset_root_path).parts[0]
            except ValueError:
                composer_folder = ""

            rows.append(
                {
                    "piece_id": piece_id,
                    "movement": str(movement),
                    "book": _clean_text(row.get("book")),
                    "composer": _clean_text(row.get("composer")),
                    "work_name": _clean_text(row.get("work_name")),
                    "henle": row.get("henle", ""),
                    "uri": _clean_text(row.get("URI")),
                    "dataset_relative_path": resolved.relative_to(dataset_root_path).as_posix(),
                    "repo_relative_path": _relative_path(resolved, repo_root_path).as_posix(),
                    "filename": score_path.name,
                    "composer_folder": composer_folder,
                    "file_suffix": score_path.suffix.lower(),
                }
            )

    extra_files = sorted(
        rel_path for rel_path in dataset_index if rel_path not in matched_paths
    )
    rows.sort(key=lambda row: (str(row["composer"]), str(row["work_name"]), str(row["movement"])))
    return CipiCatalogResult(rows=rows, missing_files=sorted(missing_files), extra_files=extra_files)


def write_catalog_csv(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "piece_id",
                "movement",
                "book",
                "composer",
                "work_name",
                "henle",
                "uri",
                "dataset_relative_path",
                "repo_relative_path",
                "filename",
                "composer_folder",
                "file_suffix",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def catalog_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_cipi_dataset_catalog",
        description="Normalize the CIPI index JSON into a repo-local manifest.",
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--index-json", type=Path, default=DEFAULT_INDEX_JSON)
    parser.add_argument("--catalog-csv", type=Path, default=DEFAULT_CATALOG_CSV)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    index_rows = load_index_json(args.index_json)
    result = build_catalog(index_rows, dataset_root=args.dataset_root, repo_root=args.repo_root)
    write_catalog_csv(result.rows, args.catalog_csv)

    print(
        json.dumps(
            {
                "catalog_csv": str(args.catalog_csv),
                "dataset_root": str(Path(args.dataset_root).expanduser()),
                "index_json": str(Path(args.index_json).expanduser()),
                "row_count": len(result.rows),
                "missing_files": len(result.missing_files),
                "extra_files": len(result.extra_files),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _build_dataset_index(dataset_root: Path) -> dict[str, Path]:
    suffixes = {".xml", ".musicxml", ".mxl"}
    index: dict[str, Path] = {}
    for path in dataset_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            index[path.relative_to(dataset_root).as_posix()] = path
    return index


def _resolve_score_path(
    dataset_index: dict[str, Path],
    *,
    composer: str,
    work_name: str,
    movement: str,
) -> Path | None:
    candidates = list(dataset_index.values())
    target = _normalize_text(f"{composer} {work_name} mvt{movement}")
    best_path: Path | None = None
    best_score = 0

    for path in candidates:
        normalized_path = _normalize_text(path.as_posix())
        normalized_name = _normalize_text(path.name)
        score = _token_overlap_score(target, normalized_name) + _token_overlap_score(target, normalized_path)
        if score > best_score:
            best_score = score
            best_path = path

    if best_score <= 0:
        return None
    return best_path


def _relative_path(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path.resolve()


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _token_overlap_score(left: str, right: str) -> int:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0
    return len(left_tokens & right_tokens)
