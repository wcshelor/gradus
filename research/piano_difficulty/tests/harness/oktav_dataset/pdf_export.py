from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_SUFFIXES: tuple[str, ...] = (".mxl",)
SUPPORTED_SCORE_SUFFIXES = {".xml", ".musicxml", ".mxl"}

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "pdf_export" / "full_run"
DEFAULT_PDF_DIR = DEFAULT_OUT_DIR / "pdfs"
DEFAULT_LOG_DIR = DEFAULT_OUT_DIR / "logs"
DEFAULT_MANIFEST_CSV = DEFAULT_OUT_DIR / "pdf_manifest.csv"
DEFAULT_SUMMARY_JSON = DEFAULT_OUT_DIR / "corpus_summary.json"
DEFAULT_ERRORS_CSV = DEFAULT_OUT_DIR / "errors.csv"

MATRIX_COLUMNS: tuple[str, ...] = (
    "source_row_index",
    "filename",
    "dataset_relative_path",
    "repo_relative_path",
    "source_path",
    "pdf_path",
    "status",
    "returncode",
    "error_type",
    "message",
    "stdout_path",
    "stderr_path",
)

_APP_BUNDLE_BINARY_CANDIDATES = (
    Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore"),
    Path("/Applications/MuseScore Studio 4.app/Contents/MacOS/mscore"),
    Path("/Applications/MuseScore 4.app/Contents/MacOS/MuseScore"),
    Path("/Applications/MuseScore Studio 4.app/Contents/MacOS/MuseScore"),
)


@dataclass(frozen=True, slots=True)
class PdfExportInput:
    source_path: Path
    pdf_path: Path
    dataset_relative_path: str
    repo_relative_path: str


def discover_score_files(source_root: str | Path, suffixes: Sequence[str] = DEFAULT_SUFFIXES) -> list[Path]:
    root = Path(source_root).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {root}")
    suffix_set = _normalize_suffixes(suffixes)
    return sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in suffix_set
        ],
        key=lambda path: str(path),
    )


def build_pdf_export_inputs(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    suffixes: Sequence[str] = DEFAULT_SUFFIXES,
    repo_root: str | Path | None = None,
) -> list[PdfExportInput]:
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser().resolve()
    out_dir_path = Path(out_dir).expanduser().resolve()
    pdf_dir = out_dir_path / "pdfs"

    source_paths = discover_score_files(dataset_root_path, suffixes=suffixes)
    planned: list[PdfExportInput] = []
    seen_outputs: dict[Path, Path] = {}
    collisions: list[str] = []

    for source_path in source_paths:
        relative_path = source_path.resolve().relative_to(dataset_root_path)
        pdf_path = (pdf_dir / relative_path).with_suffix(".pdf")
        previous_source = seen_outputs.get(pdf_path)
        if previous_source is not None and previous_source != source_path:
            collisions.append(f"{previous_source} -> {pdf_path} <- {source_path}")
            continue
        seen_outputs[pdf_path] = source_path
        planned.append(
            PdfExportInput(
                source_path=source_path.resolve(),
                pdf_path=pdf_path,
                dataset_relative_path=relative_path.as_posix(),
                repo_relative_path=_relative_path(source_path, repo_root_path),
            )
        )

    if collisions:
        joined = "\n".join(collisions)
        raise ValueError(
            "PDF export path collisions detected. Use a narrower suffix set or a different output root.\n"
            f"{joined}"
        )

    return planned


def resolve_musescore_binary(candidate: str | Path | None = None) -> Path:
    if candidate is not None:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.is_file():
            return candidate_path.resolve()
        resolved = shutil.which(str(candidate))
        if resolved:
            return Path(resolved).resolve()
        raise FileNotFoundError(f"MuseScore binary not found: {candidate_path}")

    resolved = shutil.which("mscore")
    if resolved:
        return Path(resolved).resolve()

    for app_binary in _APP_BUNDLE_BINARY_CANDIDATES:
        if app_binary.is_file():
            return app_binary.resolve()

    candidate_list = "\n".join(f"- {path}" for path in _APP_BUNDLE_BINARY_CANDIDATES)
    raise FileNotFoundError(
        "MuseScore binary not found. Install MuseScore or pass --musescore-bin.\n"
        f"Checked PATH and these macOS app bundle locations:\n{candidate_list}"
    )


def run_oktav_pdf_export(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    musescore_bin: str | Path | None = None,
    suffixes: Sequence[str] = DEFAULT_SUFFIXES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    force: bool = False,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    out_dir_path = Path(out_dir).expanduser().resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir_path / "pdfs"
    log_dir = out_dir_path / "logs"
    if pdf_dir.exists():
        shutil.rmtree(pdf_dir)
    if log_dir.exists():
        shutil.rmtree(log_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    inputs = build_pdf_export_inputs(
        dataset_root=dataset_root,
        out_dir=out_dir_path,
        suffixes=suffixes,
    )

    manifest_csv_path = out_dir_path / "pdf_manifest.csv"
    summary_json_path = out_dir_path / "corpus_summary.json"
    errors_csv_path = out_dir_path / "errors.csv"

    if not inputs:
        _write_matrix_csv(manifest_csv_path, [])
        errors_csv_path.unlink(missing_ok=True)
        summary = {
            "schema_version": "oktav_pdf_export_summary.v1",
            "dataset_root": str(Path(dataset_root).expanduser().resolve()),
            "out_dir": str(out_dir_path),
            "pdf_dir": str(pdf_dir),
            "manifest_csv_path": str(manifest_csv_path),
            "errors_csv_path": None,
            "input_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "suffixes": list(_normalize_suffixes(suffixes)),
            "timeout_seconds": timeout_seconds,
            "musescore_bin": None,
            "failed_source_paths": [],
        }
        summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "dataset_root": summary["dataset_root"],
            "out_dir": summary["out_dir"],
            "pdf_dir": summary["pdf_dir"],
            "manifest_csv_path": summary["manifest_csv_path"],
            "summary_json_path": str(summary_json_path),
            "errors_csv_path": None,
            "input_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "suffixes": summary["suffixes"],
            "timeout_seconds": timeout_seconds,
            "musescore_bin": None,
        }

    resolved_binary = resolve_musescore_binary(musescore_bin or os.environ.get("MUSESCORE_BIN") or os.environ.get("MSCORE_BIN"))

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(inputs):
        row = _export_single_pdf(
            item,
            index=index,
            musescore_bin=resolved_binary,
            timeout_seconds=timeout_seconds,
            log_dir=log_dir,
            force=force,
            dataset_root=Path(dataset_root).expanduser().resolve(),
        )
        rows.append(row)

    _write_matrix_csv(manifest_csv_path, rows)
    failure_rows = [row for row in rows if row["status"] != "success"]
    if failure_rows:
        _write_matrix_csv(errors_csv_path, failure_rows)
    else:
        errors_csv_path.unlink(missing_ok=True)
        errors_csv_path = None

    summary = {
        "schema_version": "oktav_pdf_export_summary.v1",
        "dataset_root": str(Path(dataset_root).expanduser().resolve()),
        "out_dir": str(out_dir_path),
        "pdf_dir": str(pdf_dir),
        "manifest_csv_path": str(manifest_csv_path),
        "errors_csv_path": str(errors_csv_path) if errors_csv_path is not None else None,
        "input_count": len(rows),
        "success_count": len(rows) - len(failure_rows),
        "failure_count": len(failure_rows),
        "suffixes": list(_normalize_suffixes(suffixes)),
        "timeout_seconds": timeout_seconds,
        "musescore_bin": str(resolved_binary),
        "failed_source_paths": [row["source_path"] for row in failure_rows],
    }
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dataset_root": summary["dataset_root"],
        "out_dir": summary["out_dir"],
        "pdf_dir": summary["pdf_dir"],
        "manifest_csv_path": summary["manifest_csv_path"],
        "summary_json_path": str(summary_json_path),
        "errors_csv_path": summary["errors_csv_path"],
        "input_count": summary["input_count"],
        "success_count": summary["success_count"],
        "failure_count": summary["failure_count"],
        "suffixes": summary["suffixes"],
        "timeout_seconds": timeout_seconds,
        "musescore_bin": summary["musescore_bin"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_oktav_pdf_export",
        description="Convert Oktav .mxl scores to PDF with MuseScore and write a manifest under tests/artifacts/oktav_dataset.",
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--musescore-bin", type=Path, default=None)
    parser.add_argument(
        "--suffix",
        action="append",
        dest="suffixes",
        default=None,
        help="Score file suffix to include. Repeat to include multiple suffixes. Defaults to .mxl.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-file MuseScore timeout in seconds.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass MuseScore's -f flag to ignore corruption and version mismatch warnings.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_oktav_pdf_export(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        musescore_bin=args.musescore_bin,
        suffixes=tuple(args.suffixes or DEFAULT_SUFFIXES),
        timeout_seconds=args.timeout_seconds,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failure_count"] else 0


def _export_single_pdf(
    item: PdfExportInput,
    *,
    index: int,
    musescore_bin: Path,
    timeout_seconds: float,
    log_dir: Path,
    force: bool,
    dataset_root: Path,
) -> dict[str, Any]:
    item.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    item.pdf_path.unlink(missing_ok=True)

    command = [str(musescore_bin), "-R", "-s", "-w"]
    if force:
        command.append("-f")
    command.extend(["-o", str(item.pdf_path), str(item.source_path)])

    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    status = "success"
    error_type = ""
    message = ""
    try:
        completed = subprocess.run(
            command,
            cwd=dataset_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        returncode = int(completed.returncode)
        stdout_text = _coerce_text(completed.stdout)
        stderr_text = _coerce_text(completed.stderr)
        if returncode != 0:
            status = "failure"
            error_type = "NonZeroExit"
            message = f"MuseScore exited with {returncode} while exporting {item.source_path.name}."
        elif not item.pdf_path.is_file() or item.pdf_path.stat().st_size == 0:
            status = "failure"
            error_type = "MissingOutput"
            message = f"MuseScore reported success but did not create a usable PDF at {item.pdf_path}."
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        error_type = "TimeoutExpired"
        message = f"MuseScore timed out after {timeout_seconds} seconds while exporting {item.source_path.name}."
        stdout_text = _coerce_text(getattr(exc, "output", None))
        stderr_text = _coerce_text(getattr(exc, "stderr", None))
    except OSError as exc:
        status = "failure"
        error_type = exc.__class__.__name__
        message = str(exc)

    if status != "success":
        item.pdf_path.unlink(missing_ok=True)

    stdout_path = _maybe_write_log(log_dir, item.source_path, dataset_root, ".stdout.txt", stdout_text, status)
    stderr_path = _maybe_write_log(log_dir, item.source_path, dataset_root, ".stderr.txt", stderr_text, status)

    return {
        "source_row_index": index,
        "filename": item.source_path.name,
        "dataset_relative_path": item.dataset_relative_path,
        "repo_relative_path": item.repo_relative_path,
        "source_path": str(item.source_path),
        "pdf_path": str(item.pdf_path),
        "status": status,
        "returncode": returncode if returncode is not None else "",
        "error_type": error_type,
        "message": message,
        "stdout_path": str(stdout_path) if stdout_path is not None else "",
        "stderr_path": str(stderr_path) if stderr_path is not None else "",
    }


def _maybe_write_log(
    log_dir: Path,
    source_path: Path,
    dataset_root: Path,
    suffix: str,
    contents: str,
    status: str,
) -> Path | None:
    if not contents and status == "success":
        return None
    relative_path = source_path.resolve().relative_to(dataset_root)
    log_path = (log_dir / relative_path).with_suffix(suffix)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(contents, encoding="utf-8")
    return log_path


def _write_matrix_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    csv_path = Path(path).expanduser()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _normalize_suffixes(suffixes: Sequence[str]) -> tuple[str, ...]:
    normalized = []
    for suffix in suffixes:
        value = str(suffix).strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        if value not in SUPPORTED_SCORE_SUFFIXES:
            raise ValueError(f"Unsupported score suffix: {suffix}")
        normalized.append(value)
    if not normalized:
        raise ValueError("At least one score suffix must be provided.")
    return tuple(dict.fromkeys(normalized))


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
