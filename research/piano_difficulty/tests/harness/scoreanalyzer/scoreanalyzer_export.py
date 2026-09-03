from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

DEFAULT_TIMEOUT_SECONDS = 15.0
SUPPORTED_SCORE_SUFFIXES = {".xml", ".musicxml", ".mxl"}

MATRIX_COLUMNS: tuple[str, ...] = (
    "source_row_index",
    "piece_id",
    "piece_uid",
    "title",
    "composer",
    "filename",
    "dataset_relative_path",
    "repo_relative_path",
    "source_path",
    "staged_piece_relpath",
    "status",
    "error_type",
    "message",
    "json_path",
    "stdout_path",
    "stderr_path",
    "fifths",
    "mode",
    "nbmeasures",
    "quantise",
    "baseDuration",
    "tempo",
    "beats",
    "beatType",
    "quickestValue",
    "maxIntervalRH",
    "maxIntervalLH",
    "octavesRatioRH",
    "octavesRatioLH",
    "noteCounterRH",
    "noteCounterLH",
    "nbPositionsRH",
    "nbPositionsLH",
    "length",
    "rhythm",
    "speed",
    "tonality",
    "harmony",
    "chords",
    "displacements",
    "displacementsRH",
    "displacementsLH",
    "chordsRH",
    "chordsLH",
    "harmonyRH",
    "harmonyLH",
    "speedDifficulty",
    "displacementsDifficulty",
    "chordsDifficulty",
    "harmonyDifficulty",
    "rhythmDifficulty",
    "lengthDifficulty",
    "tonalityDifficulty",
    "overallDifficulty",
)


@dataclass(frozen=True, slots=True)
class ExportInput:
    source_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PieceExportResult:
    source_path: Path
    piece_relpath: str
    staged_piece_path: Path | None
    status: str
    error_type: str
    message: str
    payload_path: Path | None
    stdout_path: Path | None
    stderr_path: Path | None
    payload: dict[str, Any] | None


@dataclass(slots=True)
class BatchExportResult:
    inputs: list[ExportInput]
    matrix_csv_path: Path
    summary_json_path: Path
    errors_csv_path: Path | None
    piece_json_dir: Path
    log_dir: Path
    failures: list[PieceExportResult]


def default_scoreanalyzer_root() -> Path:
    candidates = (
        Path("external/ScoreAnalyzer"),
        Path("reference_code/ScoreAnalyzer"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def discover_score_files(source_root: str | Path) -> list[Path]:
    root = Path(source_root).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(root)
    return sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SCORE_SUFFIXES
        ],
        key=lambda path: str(path),
    )


def run_scoreanalyzer_export(
    inputs: Sequence[ExportInput],
    *,
    out_dir: str | Path,
    matrix_csv_name: str = "og_full_dataset.csv",
    summary_json_name: str = "corpus_summary.json",
    errors_csv_name: str = "errors.csv",
    php_bin: str | Path = "php",
    scoreanalyzer_root: str | Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> BatchExportResult:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    out_dir_path = Path(out_dir).expanduser()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    scoreanalyzer_root_path = Path(scoreanalyzer_root or default_scoreanalyzer_root()).expanduser()
    pieces_root = (scoreanalyzer_root_path / "pieces").resolve()
    if not pieces_root.is_dir():
        raise FileNotFoundError(f"ScoreAnalyzer pieces directory not found: {pieces_root}")

    matrix_csv_path = out_dir_path / matrix_csv_name
    summary_json_path = out_dir_path / summary_json_name
    errors_csv_path = out_dir_path / errors_csv_name
    piece_json_dir = out_dir_path / "piece_json"
    log_dir = out_dir_path / "logs"
    piece_json_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    failures: list[PieceExportResult] = []
    scoreanalyzer_root_resolved = scoreanalyzer_root_path.resolve()

    with tempfile.TemporaryDirectory(prefix=".codex-scoreanalyzer-", dir=pieces_root) as staging_dir:
        staging_root = Path(staging_dir)
        for index, export_input in enumerate(inputs):
            row, failure = _run_single_input(
                export_input,
                index=index,
                staging_root=staging_root,
                pieces_root=pieces_root,
                scoreanalyzer_root=scoreanalyzer_root_resolved,
                php_bin=Path(php_bin),
                timeout_seconds=timeout_seconds,
                piece_json_dir=piece_json_dir,
                log_dir=log_dir,
            )
            rows.append(row)
            if failure is not None:
                failures.append(failure)

    _write_matrix_csv(matrix_csv_path, rows)
    _write_summary_json(
        summary_json_path,
        inputs=inputs,
        rows=rows,
        failures=failures,
        matrix_csv_path=matrix_csv_path,
        timeout_seconds=timeout_seconds,
        scoreanalyzer_root=scoreanalyzer_root_path,
    )
    if failures:
        _write_errors_csv(errors_csv_path, failures)
    else:
        errors_csv_path = None

    return BatchExportResult(
        inputs=list(inputs),
        matrix_csv_path=matrix_csv_path,
        summary_json_path=summary_json_path,
        errors_csv_path=errors_csv_path,
        piece_json_dir=piece_json_dir,
        log_dir=log_dir,
        failures=failures,
    )


def _run_single_input(
    export_input: ExportInput,
    *,
    index: int,
    staging_root: Path,
    pieces_root: Path,
    scoreanalyzer_root: Path,
    php_bin: Path,
    timeout_seconds: float,
    piece_json_dir: Path,
    log_dir: Path,
) -> tuple[dict[str, Any], PieceExportResult | None]:
    source_path = Path(export_input.source_path).expanduser()
    piece_uid = _piece_uid(export_input, index)
    piece_dir = staging_root / f"{index:05d}__{piece_uid}"
    piece_dir.mkdir(parents=True, exist_ok=True)
    staged_xml_path = _materialize_source_xml(source_path, piece_dir, scoreanalyzer_root=scoreanalyzer_root)
    piece_relpath = staged_xml_path.parent.relative_to(pieces_root).as_posix()

    file_slug = f"{index:05d}__{piece_uid}"
    stdout_path = log_dir / f"{file_slug}.stdout.txt"
    stderr_path = log_dir / f"{file_slug}.stderr.txt"
    payload_path = piece_json_dir / f"{file_slug}.json"

    base_row = _build_base_row(
        export_input=export_input,
        index=index,
        source_path=source_path,
        piece_uid=piece_uid,
        piece_relpath=piece_relpath,
    )

    try:
        completed = subprocess.run(
            [str(php_bin), "scoreanalyzer_json.php", "--piece", piece_relpath],
            cwd=scoreanalyzer_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        stdout_path.write_text(completed.stdout)
        stderr_path.write_text(completed.stderr)

        if completed.returncode != 0:
            message = _clean_message(completed.stderr or completed.stdout or "ScoreAnalyzer failed.")
            failure = PieceExportResult(
                source_path=source_path,
                piece_relpath=piece_relpath,
                staged_piece_path=staged_xml_path,
                status="failure",
                error_type="ScoreAnalyzerExitError",
                message=message,
                payload_path=None,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                payload=None,
            )
            return _finalize_failure_row(base_row, failure)

        payload = _parse_payload(completed.stdout)
        if isinstance(payload.get("error"), str) and payload["error"].strip():
            message = payload["error"].strip()
            failure = PieceExportResult(
                source_path=source_path,
                piece_relpath=piece_relpath,
                staged_piece_path=staged_xml_path,
                status="failure",
                error_type="ScoreAnalyzerPayloadError",
                message=message,
                payload_path=None,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                payload=payload,
            )
            return _finalize_failure_row(base_row, failure)

        payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        row = dict(base_row)
        row.update(_payload_row(payload))
        row.update(
            {
                "status": "success",
                "error_type": "",
                "message": "",
                "json_path": str(payload_path),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
            }
        )
        return row, None
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "")
        stderr_path.write_text(exc.stderr or "")
        failure = PieceExportResult(
            source_path=source_path,
            piece_relpath=piece_relpath,
            staged_piece_path=staged_xml_path,
            status="timeout",
            error_type="TimeoutExpired",
            message=f"ScoreAnalyzer exceeded {timeout_seconds:.1f}s timeout.",
            payload_path=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            payload=None,
        )
        return _finalize_failure_row(base_row, failure)
    except Exception as exc:  # noqa: BLE001
        failure = PieceExportResult(
            source_path=source_path,
            piece_relpath=piece_relpath,
            staged_piece_path=staged_xml_path,
            status="failure",
            error_type=type(exc).__name__,
            message=_clean_message(str(exc)),
            payload_path=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            payload=None,
        )
        return _finalize_failure_row(base_row, failure)


def _finalize_failure_row(
    base_row: dict[str, Any],
    failure: PieceExportResult,
) -> tuple[dict[str, Any], PieceExportResult]:
    row = dict(base_row)
    row.update(
        {
            "status": failure.status,
            "error_type": failure.error_type,
            "message": failure.message,
            "json_path": "",
            "stdout_path": str(failure.stdout_path) if failure.stdout_path else "",
            "stderr_path": str(failure.stderr_path) if failure.stderr_path else "",
        }
    )
    row.update({column: "" for column in MATRIX_COLUMNS if column not in row})
    return row, failure


def _build_base_row(
    *,
    export_input: ExportInput,
    index: int,
    source_path: Path,
    piece_uid: str,
    piece_relpath: str,
) -> dict[str, Any]:
    metadata = dict(export_input.metadata)
    row = {
        "source_row_index": index,
        "piece_id": metadata.get("piece_id", piece_uid),
        "piece_uid": metadata.get("piece_uid", piece_uid),
        "title": metadata.get("title", source_path.stem),
        "composer": metadata.get("composer", ""),
        "filename": metadata.get("filename", source_path.name),
        "dataset_relative_path": metadata.get("dataset_relative_path", ""),
        "repo_relative_path": metadata.get("repo_relative_path", ""),
        "source_path": str(source_path.resolve()),
        "staged_piece_relpath": piece_relpath,
        "status": "failure",
        "error_type": "",
        "message": "",
        "json_path": "",
        "stdout_path": "",
        "stderr_path": "",
    }
    row.update({column: "" for column in MATRIX_COLUMNS if column not in row})
    return row


def _payload_row(payload: dict[str, Any]) -> dict[str, Any]:
    stats = dict(payload.get("stats") or {})
    criteria = dict(payload.get("criteria") or {})
    fifths = _coerce_number(stats.get("fifths"))
    displacements_rh = _coerce_number(criteria.get("displacementsRH"))
    displacements_lh = _coerce_number(criteria.get("displacementsLH"))
    chords_rh = _coerce_number(criteria.get("chordsRH"))
    chords_lh = _coerce_number(criteria.get("chordsLH"))
    harmony_rh = _coerce_number(criteria.get("harmonyRH"))
    harmony_lh = _coerce_number(criteria.get("harmonyLH"))
    speed = _coerce_number(criteria.get("speed"))
    length = _coerce_number(criteria.get("length"))
    rhythm = _coerce_number(criteria.get("rhythm"))

    row = {
        "fifths": fifths,
        "mode": stats.get("mode", ""),
        "nbmeasures": _coerce_number(stats.get("nbmeasures")),
        "quantise": _coerce_number(stats.get("quantise")),
        "baseDuration": _coerce_number(stats.get("baseDuration")),
        "tempo": _coerce_number(stats.get("tempo")),
        "beats": _coerce_number(stats.get("beats")),
        "beatType": _coerce_number(stats.get("beatType")),
        "quickestValue": _coerce_number(stats.get("quickestValue")),
        "maxIntervalRH": _coerce_number(stats.get("maxIntervalRH")),
        "maxIntervalLH": _coerce_number(stats.get("maxIntervalLH")),
        "octavesRatioRH": _coerce_number(stats.get("octavesRatioRH")),
        "octavesRatioLH": _coerce_number(stats.get("octavesRatioLH")),
        "noteCounterRH": _coerce_number(stats.get("noteCounterRH")),
        "noteCounterLH": _coerce_number(stats.get("noteCounterLH")),
        "nbPositionsRH": _coerce_number(stats.get("nbPositionsRH")),
        "nbPositionsLH": _coerce_number(stats.get("nbPositionsLH")),
        "length": length,
        "rhythm": rhythm,
        "speed": speed,
        "tonality": abs(fifths) if fifths is not None else "",
        "harmony": _best_numeric(harmony_rh, harmony_lh),
        "chords": _best_numeric(chords_rh, chords_lh),
        "displacements": _best_numeric(displacements_rh, displacements_lh),
        "displacementsRH": displacements_rh,
        "displacementsLH": displacements_lh,
        "chordsRH": chords_rh,
        "chordsLH": chords_lh,
        "harmonyRH": harmony_rh,
        "harmonyLH": harmony_lh,
        "speedDifficulty": _coerce_number(criteria.get("speedDifficulty")),
        "displacementsDifficulty": _coerce_number(criteria.get("displacementsDifficulty")),
        "chordsDifficulty": _coerce_number(criteria.get("chordsDifficulty")),
        "harmonyDifficulty": _coerce_number(criteria.get("harmonyDifficulty")),
        "rhythmDifficulty": _coerce_number(criteria.get("rhythmDifficulty")),
        "lengthDifficulty": _coerce_number(criteria.get("lengthDifficulty")),
        "tonalityDifficulty": _coerce_number(criteria.get("tonalityDifficulty")),
        "overallDifficulty": _coerce_number(criteria.get("overallDifficulty")),
    }
    return row


def _write_matrix_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MATRIX_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MATRIX_COLUMNS})


def _write_errors_csv(path: Path, failures: Sequence[PieceExportResult]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_path", "piece_relpath", "status", "error_type", "message"],
        )
        writer.writeheader()
        for failure in failures:
            writer.writerow(
                {
                    "source_path": str(failure.source_path),
                    "piece_relpath": failure.piece_relpath,
                    "status": failure.status,
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
            )


def _write_summary_json(
    path: Path,
    *,
    inputs: Sequence[ExportInput],
    rows: Sequence[dict[str, Any]],
    failures: Sequence[PieceExportResult],
    matrix_csv_path: Path,
    timeout_seconds: float,
    scoreanalyzer_root: Path,
) -> None:
    payload = {
        "schema": "piano_difficulty.scoreanalyzer_export",
        "schema_version": "scoreanalyzer_export.v1",
        "input_count": len(inputs),
        "success_count": sum(1 for row in rows if str(row.get("status", "")).strip().lower() == "success"),
        "failure_count": len(failures),
        "timeout_count": sum(1 for failure in failures if failure.status == "timeout"),
        "timeout_seconds": timeout_seconds,
        "scoreanalyzer_root": str(scoreanalyzer_root),
        "matrix_csv_path": str(matrix_csv_path),
        "failure_rows": [
            {
                "source_path": str(failure.source_path),
                "piece_relpath": failure.piece_relpath,
                "status": failure.status,
                "error_type": failure.error_type,
                "message": failure.message,
            }
            for failure in failures
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _materialize_source_xml(source_path: Path, piece_dir: Path, *, scoreanalyzer_root: Path) -> Path:
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    piece_dir.mkdir(parents=True, exist_ok=True)
    target_path = piece_dir / f"{piece_dir.name}.xml"

    if source_path.suffix.lower() == ".mxl" and zipfile.is_zipfile(source_path):
        with zipfile.ZipFile(source_path) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/")]
            if not members:
                raise ValueError(f"MusicXML archive is empty: {source_path}")
            xml_members = [name for name in members if name.lower().endswith(".xml")]
            member_name = sorted(xml_members or members)[0]
            target_path.write_bytes(archive.read(member_name))
            _ensure_placeholder_image(piece_dir, scoreanalyzer_root)
            return target_path

    shutil.copy2(source_path, target_path)
    _ensure_placeholder_image(piece_dir, scoreanalyzer_root)
    return target_path


def _ensure_placeholder_image(piece_dir: Path, scoreanalyzer_root: Path) -> None:
    images_dir = piece_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    if any(images_dir.iterdir()):
        return

    placeholder_source = _find_placeholder_image(scoreanalyzer_root)
    placeholder_target = images_dir / "placeholder.pdf"
    if placeholder_source is not None:
        shutil.copy2(placeholder_source, placeholder_target)
        return

    placeholder_target.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
    )


def _find_placeholder_image(scoreanalyzer_root: Path) -> Path | None:
    candidates = [
        scoreanalyzer_root / "pieces" / "fur_elise_test" / "images" / "placeholder.pdf",
        scoreanalyzer_root / "pieces" / "demo" / "images" / "placeholder.pdf",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _parse_payload(stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for candidate in reversed(lines):
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
    raise ValueError("ScoreAnalyzer did not emit a JSON payload.")


def _clean_message(message: str) -> str:
    return " ".join(message.strip().split())


def _piece_uid(export_input: ExportInput, index: int) -> str:
    metadata = export_input.metadata
    candidate = metadata.get("piece_uid") or metadata.get("piece_id") or export_input.source_path.stem
    slug = _slugify(str(candidate))
    return slug or f"piece-{index:05d}"


def _slugify(value: str) -> str:
    text = value.strip().replace("\\", "__").replace("/", "__")
    text = "".join(character if character.isalnum() or character in {".", "-", "_"} else "-" for character in text)
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-._")


def _coerce_number(value: Any) -> Any:
    if value in {None, ""}:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return value
    if number.is_integer():
        return int(number)
    return number


def _best_numeric(left: Any, right: Any) -> Any:
    left_number = _coerce_number(left)
    right_number = _coerce_number(right)
    if left_number in {"", None} and right_number in {"", None}:
        return ""
    if left_number in {"", None}:
        return right_number
    if right_number in {"", None}:
        return left_number
    try:
        return left_number if float(left_number) >= float(right_number) else right_number
    except (TypeError, ValueError):
        return left_number
