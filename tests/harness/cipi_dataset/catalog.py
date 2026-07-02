from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi"
DEFAULT_INDEX_JSON = REPO_ROOT / "evaluation_scores" / "known_levels" / "henle" / "cipi_index.json"
DEFAULT_CATALOG_CSV = REPO_ROOT / "evaluation_scores" / "manifests" / "cipi_dataset_catalog.csv"


@dataclass(frozen=True, slots=True)
class CipiCatalogResult:
    rows: list[dict[str, Any]]
    missing_files: tuple[str, ...]
    extra_files: tuple[str, ...]


def load_catalog_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    csv_path = Path(path or DEFAULT_CATALOG_CSV).expanduser()
    if not csv_path.is_file():
        raise FileNotFoundError(f"CIPI catalog CSV not found: {csv_path}")
    return pd.read_csv(csv_path)


def load_index_json(path: str | Path | None = None) -> dict[str, Any]:
    index_path = Path(path or DEFAULT_INDEX_JSON).expanduser()
    payload = json.loads(index_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"CIPI index JSON must decode to an object: {index_path}")
    return {str(key): value for key, value in payload.items()}


def build_catalog(
    dataset_root: str | Path,
    index_json: dict[str, Any],
    repo_root: str | Path | None = None,
) -> CipiCatalogResult:
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser().resolve()
    dataset_index = _build_dataset_index(dataset_root_path)

    rows: list[dict[str, Any]] = []
    matched_paths: set[str] = set()
    for score_id, record in sorted(index_json.items()):
        if not isinstance(record, dict):
            continue
        resolved_path = _resolve_score_path(dataset_index, record)
        title = _clean_text(record.get("title"))
        composer = _clean_text(record.get("composer"))
        henle = record.get("henle")
        relative_path = ""
        repo_relative_path = ""
        filename = ""
        if resolved_path is not None:
            matched_paths.add(resolved_path.as_posix())
            relative_path = _relative_path(resolved_path, dataset_root_path)
            repo_relative_path = _relative_path(resolved_path, repo_root_path)
            filename = resolved_path.name
        rows.append(
            {
                "score_id": str(score_id),
                "title": title,
                "composer": composer,
                "henle": henle,
                "dataset_relative_path": relative_path,
                "repo_relative_path": repo_relative_path,
                "filename": filename,
            }
        )

    extra_files = sorted(set(dataset_index) - matched_paths)
    missing_files = sorted(row["score_id"] for row in rows if not row["dataset_relative_path"])
    return CipiCatalogResult(
        rows=rows,
        missing_files=tuple(missing_files),
        extra_files=tuple(extra_files),
    )


def write_catalog_csv(rows: list[dict[str, Any]], path: str | Path) -> None:
    csv_path = Path(path).expanduser()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "score_id",
                "title",
                "composer",
                "henle",
                "dataset_relative_path",
                "repo_relative_path",
                "filename",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def catalog_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a repository-side CIPI catalog CSV.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--index-json", type=Path, default=DEFAULT_INDEX_JSON)
    parser.add_argument("--catalog-csv", type=Path, default=DEFAULT_CATALOG_CSV)
    args = parser.parse_args(argv)

    index_json = load_index_json(args.index_json)
    result = build_catalog(args.dataset_root, index_json, repo_root=REPO_ROOT)
    write_catalog_csv(result.rows, args.catalog_csv)
    print(
        json.dumps(
            {
                "catalog_csv": str(args.catalog_csv.expanduser()),
                "row_count": len(result.rows),
                "missing_files": list(result.missing_files),
                "extra_files": list(result.extra_files),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _build_dataset_index(dataset_root: Path) -> dict[str, Path]:
    score_paths = {}
    for path in dataset_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".xml", ".musicxml", ".mxl"}:
            continue
        score_paths[path.as_posix()] = path
    return score_paths


def _resolve_score_path(dataset_index: dict[str, Path], record: dict[str, Any]) -> Path | None:
    candidates = [record.get("path"), record.get("dataset_relative_path"), record.get("filename")]
    normalized_index = {
        _normalize_text(path.as_posix()): path for path in dataset_index.values()
    }
    for candidate in candidates:
        if not candidate:
            continue
        normalized_candidate = _normalize_text(str(candidate))
        if normalized_candidate in normalized_index:
            return normalized_index[normalized_candidate]

    best_path: Path | None = None
    best_score = 0
    target_text = " ".join(
        filter(
            None,
            [
                _normalize_text(str(record.get("title", ""))),
                _normalize_text(str(record.get("composer", ""))),
                _normalize_text(str(record.get("filename", ""))),
            ],
        )
    )
    for path in dataset_index.values():
        score = _token_overlap_score(target_text, _normalize_text(path.as_posix()))
        if score > best_score:
            best_score = score
            best_path = path
    return best_path


def resolve_score_path(
    record: dict[str, Any],
    *,
    dataset_root: str | Path,
    repo_root: str | Path | None = None,
) -> Path | None:
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser().resolve()
    dataset_index = _build_dataset_index(dataset_root_path)
    resolved_path = _resolve_score_path(dataset_index, record)
    if resolved_path is None:
        return None
    if resolved_path.is_relative_to(dataset_root_path):
        return resolved_path.resolve()
    if resolved_path.is_relative_to(repo_root_path):
        return resolved_path.resolve()
    return resolved_path.resolve()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()


def _token_overlap_score(left: str, right: str) -> int:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    return len(left_tokens & right_tokens)
