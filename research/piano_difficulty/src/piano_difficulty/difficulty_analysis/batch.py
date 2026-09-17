"""Batch analysis helpers."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from piano_difficulty.pipeline import DEFAULT_PROFILE_IDS, analyze_score
from piano_difficulty.difficulty_analysis.overview import OverviewOptions
from piano_difficulty.output.overview import write_analysis_outputs

_SUPPORTED_SUFFIXES = {".musicxml", ".xml", ".mxl"}


@dataclass(slots=True)
class BatchFailure:
    source_path: Path
    error_type: str
    message: str


@dataclass(slots=True)
class BatchAnalysisResult:
    inputs: list[Path]
    payload_paths: list[Path]
    failures: list[BatchFailure]
    corpus_summary_path: Path
    errors_csv_path: Path | None


def analyze_batch(
    source: str | Path,
    *,
    out_dir: str | Path,
    profile_ids: tuple[str, ...] = DEFAULT_PROFILE_IDS,
    write_csv: bool = False,
    overview_options: OverviewOptions | None = None,
) -> BatchAnalysisResult:
    """Analyze a file or directory into deterministic JSON outputs."""

    inputs = _resolve_inputs(source)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload_paths: list[Path] = []
    failures: list[BatchFailure] = []
    feature_rows: list[dict[str, object]] = []
    analysis_rows: list[dict[str, object]] = []
    score_rows: list[dict[str, object]] = []

    for path, output_path in _iter_output_paths(inputs, output_dir):
        try:
            result = analyze_score(path, profile_ids=profile_ids, overview_options=overview_options)
        except Exception as exc:
            failure = BatchFailure(
                source_path=path,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            failures.append(failure)
            score_rows.append(
                {
                    "source_path": str(path),
                    "status": "failure",
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
            )
            continue

        payload = result.to_json_payload()
        output_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        if "difficulty_overview" in profile_ids:
            write_analysis_outputs(payload, output_dir, stem=output_path.stem, write_csv=write_csv)
        payload_paths.append(output_path)
        feature_rows.extend(_feature_rows(payload))
        analysis_rows.extend(_analysis_rows(payload))
        score_rows.append(
            {
                "source_path": str(path),
                "status": "success",
                "json_path": str(output_path),
            }
        )

    corpus_summary = {
        "schema": "piano_difficulty.batch_summary",
        "schema_version": "batch_summary.v2",
        "file_count": len(inputs),
        "success_count": len(payload_paths),
        "failure_count": len(failures),
        "profile_ids": list(profile_ids),
        "scores": score_rows,
    }
    corpus_summary_path = output_dir / "corpus_summary.json"
    corpus_summary_path.write_text(json.dumps(corpus_summary, sort_keys=True, indent=2) + "\n")

    errors_csv_path: Path | None = None
    if failures:
        errors_csv_path = output_dir / "errors.csv"
        with errors_csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["source_path", "error_type", "message"],
            )
            writer.writeheader()
            writer.writerows(
                [
                    {
                        "source_path": str(failure.source_path),
                        "error_type": failure.error_type,
                        "message": failure.message,
                    }
                    for failure in failures
                ]
            )

    if write_csv:
        _write_csv(output_dir / "features.csv", feature_rows)
        _write_csv(output_dir / "analysis_dimensions.csv", analysis_rows)

    return BatchAnalysisResult(
        inputs=inputs,
        payload_paths=payload_paths,
        failures=failures,
        corpus_summary_path=corpus_summary_path,
        errors_csv_path=errors_csv_path,
    )


def _resolve_inputs(source: str | Path) -> list[Path]:
    source_path = Path(source)
    if source_path.is_file():
        return [source_path]
    if not source_path.is_dir():
        raise FileNotFoundError(source_path)
    return sorted(
        [
            path
            for path in source_path.rglob("*")
            if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES
        ],
        key=lambda path: str(path),
    )


def _iter_output_paths(inputs: list[Path], output_dir: Path):
    used_names: dict[str, int] = {}
    allocated = {"corpus_summary.json"}
    for path in inputs:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-") or "score"
        count = used_names.get(slug, 0) + 1
        used_names[slug] = count
        filename = f"{slug}.json" if count == 1 else f"{slug}-{count}.json"
        while filename in allocated:
            count += 1
            filename = f"{slug}-{count}.json"
        used_names[slug] = count
        allocated.add(filename)
        yield path, output_dir / filename


def _feature_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in payload.get("features", []):
        rows.append(
            {
                "source_path": payload["source"]["path"],
                "feature_id": feature["feature_id"],
                "scope": feature["scope"],
                "scope_ref": feature["scope_ref"],
                "value": feature["value"],
                "units": feature["units"],
                "measure_start": feature["source_span"]["measure_start"],
                "measure_end": feature["source_span"]["measure_end"],
            }
        )
    return rows


def _analysis_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in payload.get("analysis_profiles", []):
        for dimension in profile.get("dimensions", []):
            rows.append(
                {
                    "source_path": payload["source"]["path"],
                    "profile_id": profile["profile_id"],
                    "dimension_id": dimension["dimension_id"],
                    "mark": dimension["mark"],
                    "legacy_label": dimension.get("legacy_label"),
                    "raw_value": dimension["raw_value"],
                    "raw_units": dimension["raw_units"],
                    "measure_start": dimension["source_span"]["measure_start"],
                    "measure_end": dimension["source_span"]["measure_end"],
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    headers = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
