"""Manifest-driven personal piece lab for Difficulty Dynamics."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .config import load_difficulty_dynamics_config
from .models import DifficultyDynamicsConfig, DifficultyDynamicsRunResult
from .runner import run_experiment

PieceLabStatus = Literal["success", "error"]


@dataclass(frozen=True, slots=True)
class PieceLabEntry:
    piece_id: str
    score_path: Path
    title: str | None = None
    composer: str | None = None
    learned_by_user: bool | None = None
    known_hard_measures: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PieceLabItemResult:
    entry: PieceLabEntry
    status: PieceLabStatus
    run_result: DifficultyDynamicsRunResult | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PieceLabRunResult:
    batch_dir: Path
    manifest_path: Path
    summary_csv_path: Path
    report_path: Path
    item_results: tuple[PieceLabItemResult, ...]


def load_piece_lab_manifest(
    csv_path: str | Path,
    *,
    piece_id_column: str = "score_id",
    score_path_column: str = "score_path",
) -> tuple[PieceLabEntry, ...]:
    manifest_path = Path(csv_path).expanduser().resolve()
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing_columns = [
            column
            for column in (piece_id_column, score_path_column)
            if column not in fieldnames
        ]
        if missing_columns:
            raise ValueError(
                f"Manifest {manifest_path} is missing required column(s): {', '.join(missing_columns)}"
            )

        entries: list[PieceLabEntry] = []
        for index, row in enumerate(reader):
            piece_id = str(row[piece_id_column]).strip() or f"piece_{index:05d}"
            score_path_text = str(row[score_path_column]).strip()
            if not score_path_text:
                raise ValueError(f"Manifest {manifest_path} has an empty score_path at row {index + 2}.")
            raw_score_path = Path(score_path_text).expanduser()
            score_path = raw_score_path if raw_score_path.is_absolute() else (manifest_path.parent / raw_score_path).resolve()
            entries.append(
                PieceLabEntry(
                    piece_id=piece_id,
                    score_path=score_path,
                    title=_optional_cell(row.get("title")),
                    composer=_optional_cell(row.get("composer")),
                    learned_by_user=_optional_bool(row.get("learned_by_user")),
                    known_hard_measures=_optional_cell(row.get("known_hard_measures")),
                    notes=_optional_cell(row.get("notes")),
                    metadata={
                        key: value
                        for key, value in row.items()
                        if key not in {piece_id_column, score_path_column, "title", "composer", "learned_by_user", "known_hard_measures", "notes"}
                    },
                )
            )

    if not entries:
        raise ValueError(f"Manifest {manifest_path} contains no score rows.")
    return tuple(entries)


def run_piece_lab(
    config: DifficultyDynamicsConfig | str | Path,
    manifest: str | Path,
    *,
    runs_root: str | Path | None = None,
) -> PieceLabRunResult:
    experiment_config = config if isinstance(config, DifficultyDynamicsConfig) else load_difficulty_dynamics_config(config)
    manifest_path = Path(manifest).expanduser().resolve()
    entries = load_piece_lab_manifest(manifest_path)

    output_root = Path(runs_root).expanduser().resolve() if runs_root is not None else experiment_config.export.output_root
    batch_dir = _allocate_batch_dir(output_root, manifest_path.stem)
    pieces_root = batch_dir / "pieces"
    pieces_root.mkdir(parents=True, exist_ok=False)

    item_results: list[PieceLabItemResult] = []
    for entry in entries:
        piece_config = replace(
            experiment_config,
            score_path=entry.score_path,
            score_id=entry.piece_id,
            export=replace(
                experiment_config.export,
                output_root=pieces_root,
                run_name=entry.piece_id,
            ),
        )
        try:
            run_result = run_experiment(piece_config)
        except Exception as exc:
            item_results.append(PieceLabItemResult(entry=entry, status="error", error=str(exc)))
            continue
        item_results.append(PieceLabItemResult(entry=entry, status="success", run_result=run_result))

    summary_csv_path = batch_dir / "piece_lab_summary.csv"
    report_path = batch_dir / "piece_lab_report.md"
    _write_summary_csv(summary_csv_path, item_results)
    report_path.write_text(_render_piece_lab_report(manifest_path, item_results), encoding="utf-8")
    (batch_dir / "manifest_context.json").write_text(
        json.dumps(
            {
                "manifest_path": str(manifest_path),
                "entry_count": len(entries),
                "success_count": sum(1 for result in item_results if result.status == "success"),
                "error_count": sum(1 for result in item_results if result.status == "error"),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return PieceLabRunResult(
        batch_dir=batch_dir,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        report_path=report_path,
        item_results=tuple(item_results),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Difficulty Dynamics over a CSV manifest of pieces and summarize the results."
    )
    parser.add_argument("config", type=Path, help="Path to a Difficulty Dynamics YAML config.")
    parser.add_argument("manifest", type=Path, help="CSV manifest with score_id and score_path columns.")
    parser.add_argument("--runs-root", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run_piece_lab(args.config, args.manifest, runs_root=args.runs_root)
    print(
        json.dumps(
            {
                "batch_dir": str(result.batch_dir),
                "manifest_path": str(result.manifest_path),
                "summary_csv_path": str(result.summary_csv_path),
                "report_path": str(result.report_path),
                "piece_count": len(result.item_results),
                "success_count": sum(1 for item in result.item_results if item.status == "success"),
                "error_count": sum(1 for item in result.item_results if item.status == "error"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _write_summary_csv(path: Path, item_results: list[PieceLabItemResult]) -> None:
    fieldnames = [
        "piece_id",
        "title",
        "composer",
        "score_path",
        "learned_by_user",
        "known_hard_measures",
        "status",
        "run_dir",
        "error",
        "hotspot_count",
        "top_hotspot_measure_span",
        "top_support_count",
        "top_feature_contributors",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in item_results:
            writer.writerow(_summary_row(result))


def _summary_row(result: PieceLabItemResult) -> dict[str, object]:
    base = {
        "piece_id": result.entry.piece_id,
        "title": result.entry.title,
        "composer": result.entry.composer,
        "score_path": str(result.entry.score_path),
        "learned_by_user": result.entry.learned_by_user,
        "known_hard_measures": result.entry.known_hard_measures,
        "status": result.status,
        "run_dir": None if result.run_result is None else str(result.run_result.run_dir),
        "error": result.error,
    }
    if result.run_result is None:
        return {
            **base,
            "hotspot_count": 0,
            "top_hotspot_measure_span": None,
            "top_support_count": None,
            "top_feature_contributors": None,
        }

    hard_spots = result.run_result.profile.hard_spots
    top_hotspot = hard_spots[0] if hard_spots else None
    contributors = (
        ", ".join(contribution.feature_id for contribution in top_hotspot.feature_contributions[:3])
        if top_hotspot is not None
        else None
    )
    return {
        **base,
        "hotspot_count": len(hard_spots),
        "top_hotspot_measure_span": None if top_hotspot is None else f"{top_hotspot.region.measure_start}-{top_hotspot.region.measure_end}",
        "top_support_count": None if top_hotspot is None else top_hotspot.support_count,
        "top_feature_contributors": contributors,
    }


def _render_piece_lab_report(manifest_path: Path, item_results: list[PieceLabItemResult]) -> str:
    success_count = sum(1 for result in item_results if result.status == "success")
    error_count = sum(1 for result in item_results if result.status == "error")
    lines = [
        "# Difficulty Dynamics Piece Lab",
        "",
        f"- Manifest: {manifest_path}",
        f"- Pieces: {len(item_results)}",
        f"- Successful runs: {success_count}",
        f"- Failed runs: {error_count}",
        "",
        "## Pieces",
        "",
    ]
    for result in item_results:
        lines.append(f"### {result.entry.piece_id}")
        lines.append("")
        lines.append(f"- Score path: {result.entry.score_path}")
        if result.entry.title:
            lines.append(f"- Title: {result.entry.title}")
        if result.entry.composer:
            lines.append(f"- Composer: {result.entry.composer}")
        if result.entry.known_hard_measures:
            lines.append(f"- Known hard measures: {result.entry.known_hard_measures}")
        if result.status == "error":
            lines.append(f"- Status: error")
            lines.append(f"- Error: {result.error}")
            lines.append("")
            continue
        assert result.run_result is not None
        hard_spots = result.run_result.profile.hard_spots
        lines.append(f"- Status: success")
        lines.append(f"- Run dir: {result.run_result.run_dir}")
        lines.append(f"- Hard spots: {len(hard_spots)}")
        if hard_spots:
            top_hotspot = hard_spots[0]
            top_features = ", ".join(contribution.feature_id for contribution in top_hotspot.feature_contributions[:3]) or "none"
            lines.append(
                f"- Top hotspot: measures {top_hotspot.region.measure_start}-{top_hotspot.region.measure_end} "
                f"(support {top_hotspot.support_count})"
            )
            lines.append(f"- Top contributors: {top_features}")
        lines.append("")
    return "\n".join(lines)


def _optional_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    text = _optional_cell(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    return None


def _allocate_batch_dir(output_root: Path, manifest_stem: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    label = _slugify(manifest_stem)
    candidate = output_root / f"{timestamp}__piece-lab__{label}"
    if candidate.exists():
        suffix = 2
        while True:
            numbered = output_root / f"{timestamp}__piece-lab__{label}-{suffix}"
            if not numbered.exists():
                return numbered
            suffix += 1
    return candidate


def _slugify(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in text).strip("-") or "piece-lab"


__all__ = [
    "PieceLabEntry",
    "PieceLabItemResult",
    "PieceLabRunResult",
    "load_piece_lab_manifest",
    "run_piece_lab",
    "main",
]
