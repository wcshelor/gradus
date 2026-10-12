"""Manifest resolution against the canonical CIPI movement manifest.

Reuses the shared dataset-root resolver; never duplicates root-resolution
logic and never creates dataset roots.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.harness.shared.dataset_config import (
    DatasetRootResolution,
    resolve_dataset_root,
)

from .manifest import DavidWalkthroughEntry

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CURATION_MANIFEST_CSV = (
    REPO_ROOT / "evaluation_scores" / "manifests" / "david_walkthrough" / "cipi_familiar_v1.csv"
)
DEFAULT_CANONICAL_MANIFEST_CSV = (
    REPO_ROOT / "evaluation_scores" / "manifests" / "cipi" / "cipi_movement_manifest.csv"
)
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi"


@dataclass(frozen=True, slots=True)
class CipiMatch:
    demo_id: str
    status: str  # "matched" | "missing_catalog_match" | "duplicate_catalog_match"
    cipi_row: dict[str, Any] | None
    reason: str


@dataclass(frozen=True, slots=True)
class PlannedPiece:
    entry: DavidWalkthroughEntry
    match: CipiMatch
    dataset_root: Path | None
    root_source: str
    root_detail: str
    pieces_dir_hint: bool
    source_path: Path | None
    status: str  # "ready" | "missing_catalog_match" | "duplicate_catalog_match"
    # | "dataset_root_unresolved" | "missing_source_file"
    reason: str


def load_canonical_index(
    manifest_csv: str | Path = DEFAULT_CANONICAL_MANIFEST_CSV,
) -> dict[str, list[dict[str, Any]]]:
    """Index canonical CIPI rows by exact `dataset_relative_path`."""
    manifest_path = Path(manifest_csv).expanduser()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"CIPI movement manifest not found: {manifest_path}")
    index: dict[str, list[dict[str, Any]]] = {}
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            key = str(row.get("dataset_relative_path", "") or "").strip().replace("\\", "/")
            if not key:
                continue
            index.setdefault(key, []).append({key: value for key, value in row.items()})
    return index


def match_entry(
    entry: DavidWalkthroughEntry,
    index: dict[str, list[dict[str, Any]]],
) -> CipiMatch:
    """Resolve one curated row against the canonical manifest index."""
    key = entry.dataset_relative_path.replace("\\", "/")
    candidates = index.get(key, [])
    if not candidates:
        return CipiMatch(
            demo_id=entry.demo_id,
            status="missing_catalog_match",
            cipi_row=None,
            reason=(
                f"No canonical CIPI row matches dataset_relative_path {key!r}; "
                "check the path against evaluation_scores/manifests/cipi/cipi_movement_manifest.csv."
            ),
        )
    if len(candidates) > 1:
        return CipiMatch(
            demo_id=entry.demo_id,
            status="duplicate_catalog_match",
            cipi_row=None,
            reason=(
                f"dataset_relative_path {key!r} matches {len(candidates)} canonical "
                "CIPI rows; refusing to guess which movement is meant."
            ),
        )
    return CipiMatch(
        demo_id=entry.demo_id, status="matched", cipi_row=dict(candidates[0]), reason=""
    )


def resolve_dataset_root_for_david(
    explicit_root: str | Path | None = None,
) -> DatasetRootResolution:
    """Reuse shared CIPI root resolution: CLI flag, env, config, repo fallback."""
    explicit = Path(explicit_root).expanduser() if explicit_root not in (None, "") else None
    return resolve_dataset_root("cipi", explicit_root=explicit, repo_fallback=DEFAULT_DATASET_ROOT)


def plan_batch(
    entries: list[DavidWalkthroughEntry],
    *,
    dataset_root: str | Path | None = None,
    canonical_manifest_csv: str | Path = DEFAULT_CANONICAL_MANIFEST_CSV,
) -> list[PlannedPiece]:
    """Plan every manifest row without stopping at individual failures."""
    index = load_canonical_index(canonical_manifest_csv)
    resolution = resolve_dataset_root_for_david(dataset_root)
    root = resolution.root
    pieces_dir_hint = root is not None and root.name.lower() == "pieces"
    effective_root = root.parent if (pieces_dir_hint and root is not None) else root

    planned: list[PlannedPiece] = []
    for entry in entries:
        match = match_entry(entry, index)
        if match.status != "matched":
            planned.append(
                PlannedPiece(
                    entry=entry, match=match, dataset_root=root,
                    root_source=resolution.source, root_detail=resolution.detail,
                    pieces_dir_hint=pieces_dir_hint, source_path=None,
                    status=match.status, reason=match.reason,
                )
            )
            continue
        if effective_root is None or not resolution.exists:
            planned.append(
                PlannedPiece(
                    entry=entry, match=match, dataset_root=root,
                    root_source=resolution.source, root_detail=resolution.detail,
                    pieces_dir_hint=pieces_dir_hint, source_path=None,
                    status="dataset_root_unresolved",
                    reason=f"CIPI dataset root is not available: {resolution.detail}",
                )
            )
            continue
        rel = entry.dataset_relative_path.replace("\\", "/")
        candidate = (effective_root / rel).expanduser()
        if pieces_dir_hint:
            note = (
                f"CIPI root points directly at a pieces/ directory ({root}); "
                "expected the dataset root containing metadata/ and pieces/. "
                "Resolve manifest paths against the parent directory instead, or reconfigure."
            )
        else:
            note = ""
        if candidate.is_file():
            planned.append(
                PlannedPiece(
                    entry=entry, match=match, dataset_root=root,
                    root_source=resolution.source, root_detail=resolution.detail,
                    pieces_dir_hint=pieces_dir_hint,
                    source_path=candidate.resolve(),
                    status="ready", reason=note,
                )
            )
        else:
            reason = f"Score file not found under the CIPI root: {rel}."
            if note:
                reason = f"{note} {reason}"
            planned.append(
                PlannedPiece(
                    entry=entry, match=match, dataset_root=root,
                    root_source=resolution.source, root_detail=resolution.detail,
                    pieces_dir_hint=pieces_dir_hint, source_path=candidate,
                    status="missing_source_file", reason=reason,
                )
            )
    return planned
