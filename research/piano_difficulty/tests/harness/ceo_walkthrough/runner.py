"""Batch execution for the CEO CIPI walkthrough.

Single-piece analysis reuses the existing runtime path
(`analyze_score` + `write_analysis_outputs`); this module only plans,
isolates per-piece failures, and delegates report writing.
"""

from __future__ import annotations

import importlib.metadata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from piano_difficulty.output.overview import write_analysis_outputs
from piano_difficulty.pipeline import analyze_score

from . import artifacts as artifact_layout
from . import reports as report_writers
from .cipi_selection import (
    DEFAULT_CANONICAL_MANIFEST_CSV,
    DEFAULT_CURATION_MANIFEST_CSV,
    PlannedPiece,
    plan_batch,
)
from .manifest import CeoWalkthroughEntry, load_manifest


def _runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dist in ("piano-difficulty",):
        try:
            versions[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            versions[dist] = "unknown"
    return versions


def analyze_single_piece(source_path: str | Path, piece_dir: str | Path) -> dict[str, Any]:
    """Run existing analysis over one score and write the four artifacts."""
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Score file not found: {source}")
    result = analyze_score(source)
    payload = result.to_json_payload()
    write_analysis_outputs(payload, piece_dir, stem="analysis")
    return payload


def run_dry_run(
    *,
    manifest_csv: str | Path = DEFAULT_CURATION_MANIFEST_CSV,
    dataset_root: str | Path | None = None,
    canonical_manifest_csv: str | Path = DEFAULT_CANONICAL_MANIFEST_CSV,
    limit: int | None = None,
) -> dict[str, Any]:
    """Validate manifest, catalog matches, root, and files without analyzing."""
    entries = load_manifest(manifest_csv)
    if limit is not None:
        entries = entries[: max(0, int(limit))]
    planned = plan_batch(
        entries, dataset_root=dataset_root, canonical_manifest_csv=canonical_manifest_csv
    )
    ready = [item for item in planned if item.status == "ready"]
    blocked = [item for item in planned if item.status != "ready"]
    return {
        "manifest_csv": str(Path(manifest_csv).expanduser()),
        "piece_count": len(planned),
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "would_run": [item.entry.demo_id for item in ready],
        "blocked": [
            {"demo_id": item.entry.demo_id, "phase": item.status, "reason": item.reason}
            for item in blocked
        ],
    }


def run_batch(
    planned: list[PlannedPiece],
    out_root: str | Path,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Run all planned pieces; one bad row never stops the batch."""
    root = Path(out_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    versions = _runtime_versions()
    stamped = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    results: list[dict[str, Any]] = []
    scoped = planned[: max(0, int(limit))] if limit is not None else list(planned)
    for item in scoped:
        paths = artifact_layout.piece_artifact_paths(root, item.entry.demo_id)
        if item.status != "ready" or item.source_path is None:
            report_writers.write_piece_context(
                paths["dir"], item, status=item.status, reason=item.reason,
                artifact_paths={}, versions=versions, timestamp=stamped,
            )
            report_writers.write_demo_notes(
                paths["dir"], item, payload=None, status=item.status, reason=item.reason
            )
            results.append({
                "demo_id": item.entry.demo_id, "status": item.status,
                "reason": item.reason, "piece_dir": str(paths["dir"]),
                "source_path": None if item.source_path is None else str(item.source_path),
            })
            continue
        try:
            paths["dir"].mkdir(parents=True, exist_ok=True)
            payload = analyze_single_piece(item.source_path, paths["dir"])
            status, reason = "success", ""
        except Exception as exc:  # noqa: BLE001 - isolated per piece by design
            payload = None
            status = "analysis_failed"
            reason = f"{type(exc).__name__}: {' '.join(str(exc).split())}"
        report_writers.write_piece_context(
            paths["dir"], item, status=status, reason=reason,
            artifact_paths={name: str(path) for name, path in paths.items() if name != "dir"},
            versions=versions, timestamp=stamped, payload=payload,
        )
        report_writers.write_demo_notes(
            paths["dir"], item, payload=payload, status=status, reason=reason
        )
        results.append({
            "demo_id": item.entry.demo_id, "status": status, "reason": reason,
            "piece_dir": str(paths["dir"]), "source_path": str(item.source_path),
        })
    return results


def run_walkthrough(
    *,
    manifest_csv: str | Path = DEFAULT_CURATION_MANIFEST_CSV,
    out_dir: str | Path,
    dataset_root: str | Path | None = None,
    canonical_manifest_csv: str | Path = DEFAULT_CANONICAL_MANIFEST_CSV,
    limit: int | None = None,
    dry_run: bool = False,
    fresh_run_dir: bool = False,
) -> dict[str, Any]:
    """Plan, optionally analyze, and always write the top-level reports."""
    entries: list[CeoWalkthroughEntry] = load_manifest(manifest_csv)
    if limit is not None:
        entries = entries[: max(0, int(limit))]
    target = Path(out_dir).expanduser()
    if fresh_run_dir:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = target / f"run_{stamp}"
    if dry_run:
        summary = run_dry_run(
            manifest_csv=manifest_csv, dataset_root=dataset_root,
            canonical_manifest_csv=canonical_manifest_csv, limit=limit,
        )
        summary["out_dir"] = str(target)
        summary["mode"] = "dry_run"
        return summary

    artifact_layout.clean_planned_outputs(target, [entry.demo_id for entry in entries])
    planned = plan_batch(
        entries, dataset_root=dataset_root, canonical_manifest_csv=canonical_manifest_csv
    )
    results = run_batch(planned, target)
    index_payload = report_writers.write_index_json(
        target, entries, results, manifest_csv=manifest_csv
    )
    report_writers.write_index_markdown(target, entries, results)
    failures_path = report_writers.write_failures_csv(target, planned, results)
    return {
        "manifest_csv": str(Path(manifest_csv).expanduser()),
        "out_dir": str(target),
        "mode": "full",
        "piece_count": len(results),
        "success_count": sum(1 for item in results if item["status"] == "success"),
        "failure_count": sum(1 for item in results if item["status"] != "success"),
        "failures_csv": None if failures_path is None else str(failures_path),
        "index": index_payload,
        "results": results,
    }
