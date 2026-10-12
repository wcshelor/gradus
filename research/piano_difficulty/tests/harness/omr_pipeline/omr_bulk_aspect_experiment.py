"""Incremental OMR bulk harness — piece-by-piece Oktav -> PDF -> Audiveris -> aspect traces.

Test-scoped. Streams outputs after each piece so the run can be stopped early
and still yield usable evidence. Also produces a statistical overview of
how well OMR preserves each difficulty_aspect.

Pipeline per piece:
  source .mxl/.musicxml -> MuseScore PDF -> Audiveris OMR -> difficulty_aspects (both)
                         -> single-graph overlay PNG per aspect (distinct colors)
                         -> per-aspect metrics (pearson/spearman/rmse/mae)

Artifacts under <out_dir>:
  pdfs/                — rendered PDFs
  omr_musicxml/        — Audiveris MusicXML outputs
  logs/pdf_export/     — per-file MuseScore logs
  logs/audiveris/      — per-file Audiveris stdout/stderr
  logs/audiveris_output/ — Audiveris .omr book dirs
  aspect_comparison_pngs/<piece>/<aspect>.png
  bulk_manifest.csv    — one row per source file, updated streaming
  bulk_summary.json    — updated after each piece, with per_aspect_stats
  aspect_overview.md   — markdown ranking table
  aspect_overview.png  — bar chart of mean pearson per aspect (if any success)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"
# Fallback demo corpus that always exists in this repo
FALLBACK_DATASET_ROOT = REPO_ROOT.parent.parent / "research" / "learning_support" / "david_demo" / "data" / "source_scores"
# Actually repo layout: research/ is sibling to piano_difficulty; handle both
ALTERNATE_FALLBACK = Path(__file__).resolve().parents[4] / "learning_support" / "david_demo" / "data" / "source_scores"

DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "omr_pipeline" / "experiment" / "bulk_aspect_run"
DEFAULT_MUSESCORE_TIMEOUT = 60.0
DEFAULT_AUDIVERIS_TIMEOUT = 600.0
SUPPORTED_SUFFIXES = {".mxl", ".musicxml", ".xml"}

MANIFEST_FIELDNAMES = [
    "piece_id",
    "filename",
    "source_path",
    "pdf_path",
    "pdf_status",
    "omr_musicxml_path",
    "omr_status",
    "failure_category",
    "original_window_count",
    "omr_window_count",
    "window_count_mismatch",
    "mean_pearson_r",
    "mean_spearman_r",
    "mean_rmse",
    "mean_mae",
    "per_aspect_metrics_json",
    "error",
]

__all__ = ["run_bulk_aspect_experiment", "build_parser", "main"]


def _sanitize_piece_id(text: str) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "piece"


def discover_score_files(root: Path, suffixes: set[str] | None = None) -> list[Path]:
    suffixes = suffixes or SUPPORTED_SUFFIXES
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {root}")
    lower_suffixes = {s.lower() for s in suffixes}
    return sorted(
        [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in lower_suffixes],
        key=lambda p: str(p),
    )


def resolve_musescore_binary(candidate: str | Path | None = None) -> Path:
    from tests.harness.oktav_dataset.pdf_export import resolve_musescore_binary as _resolve

    return _resolve(candidate)


def resolve_audiveris_binary(candidate: str | Path | None = None) -> Path:
    if candidate is not None:
        p = Path(candidate).expanduser()
        if p.is_file():
            return p.resolve()
        found = shutil.which(str(candidate))
        if found:
            return Path(found).resolve()
        raise FileNotFoundError(f"Audiveris binary not found: {candidate}")
    # common locations
    for cand in [
        Path("/Applications/Audiveris.app/Contents/MacOS/Audiveris"),
        Path("/Applications/Audiveris.app/Contents/Resources/Audiveris"),
    ]:
        if cand.is_file():
            return cand.resolve()
    found = shutil.which("Audiveris") or shutil.which("audiveris")
    if found:
        return Path(found).resolve()
    raise FileNotFoundError(
        "Audiveris binary not found. Install Audiveris or pass --audiveris-bin. Checked /Applications/Audiveris.app/Contents/MacOS/Audiveris"
    )


def _coerce_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v)


def _export_single_pdf(
    source_path: Path,
    pdf_path: Path,
    musescore_bin: Path,
    timeout_seconds: float,
    log_dir: Path,
) -> dict[str, Any]:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.unlink(missing_ok=True)
    stdout_path = log_dir / f"{source_path.stem}.stdout.txt"
    stderr_path = log_dir / f"{source_path.stem}.stderr.txt"
    # Try multiple variants to survive transient Rosetta mutex abort (seen exit -6)
    # Prior harness succeeded with plain "-o" but sometimes needed retry.
    # We try plain then "-f" (force) and treat PDF existence as success even if
    # stderr contains HIServices/mutex warnings.
    variants: list[list[str]] = [
        ["-o", str(pdf_path), str(source_path)],
        ["-f", "-o", str(pdf_path), str(source_path)],
    ]
    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    status = "success"
    error_type = ""
    message = ""
    # Use dataset parent as cwd (mirrors oktav harcness cwd=dataset_root); helps MuseScore 4
    cwd_for_mscore = source_path.parent
    for variant_idx, extra in enumerate(variants):
        pdf_path.unlink(missing_ok=True)
        command = [str(musescore_bin)] + extra
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd_for_mscore),
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
            # Success if PDF exists and non-empty, even if returncode !=0 but
            # contains known benign crash-reporter noise (HIServices/mutex).
            has_pdf = pdf_path.is_file() and pdf_path.stat().st_size > 0
            # Valid header check
            valid_header = False
            if has_pdf:
                try:
                    with pdf_path.open("rb") as fh:
                        valid_header = fh.read(5) == b"%PDF-"
                except Exception:
                    valid_header = False
            if has_pdf and valid_header:
                status = "success"
                error_type = ""
                message = ""
                break
            if returncode != 0:
                status = "failure"
                error_type = "NonZeroExit"
                message = f"MuseScore exited {returncode} for {source_path.name} (variant {variant_idx})"
                # If we have more variants, continue to retry
                if variant_idx + 1 < len(variants):
                    time.sleep(0.5)
                    continue
            elif not has_pdf or not valid_header:
                status = "failure"
                error_type = "MissingOutput"
                message = f"MuseScore no PDF at {pdf_path} (variant {variant_idx})"
                if variant_idx + 1 < len(variants):
                    time.sleep(0.5)
                    continue
            else:
                status = "success"
                break
        except subprocess.TimeoutExpired as exc:
            status = "timeout"
            error_type = "TimeoutExpired"
            message = f"MuseScore timeout {timeout_seconds}s for {source_path.name} (variant {variant_idx})"
            stdout_text = _coerce_text(getattr(exc, "output", None))
            stderr_text = _coerce_text(getattr(exc, "stderr", None))
            if variant_idx + 1 < len(variants):
                time.sleep(0.5)
                continue
        except OSError as exc:
            status = "failure"
            error_type = type(exc).__name__
            message = str(exc)
            break
    if status != "success":
        pdf_path.unlink(missing_ok=True)
    # Always write logs (even on success if non-empty)
    if stdout_text or status != "success":
        stdout_path.write_text(stdout_text, encoding="utf-8")
    else:
        stdout_path.unlink(missing_ok=True)
        stdout_path = None  # type: ignore[assignment]
    if stderr_text or status != "success":
        stderr_path.write_text(stderr_text, encoding="utf-8")
    else:
        stderr_path.unlink(missing_ok=True)
        stderr_path = None  # type: ignore[assignment]
    return {
        "status": status,
        "returncode": returncode if returncode is not None else "",
        "error_type": error_type,
        "message": message,
        "stdout_path": str(stdout_path) if isinstance(stdout_path, Path) else "",
        "stderr_path": str(stderr_path) if isinstance(stderr_path, Path) else "",
        "pdf_path": str(pdf_path),
    }


def _run_single_audiveris(
    pdf_path: Path,
    omr_out_path: Path,  # desired .musicxml/.mxl path
    audiveris_bin: Path,
    timeout_seconds: float,
    log_dir: Path,
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    audiveris_output_dir = log_dir.parent / "audiveris_output" / pdf_path.stem
    # Clean previous attempt
    if audiveris_output_dir.exists():
        shutil.rmtree(audiveris_output_dir)
    audiveris_output_dir.mkdir(parents=True, exist_ok=True)
    omr_out_path.parent.mkdir(parents=True, exist_ok=True)
    omr_out_path.unlink(missing_ok=True)

    stdout_path = log_dir / f"{pdf_path.stem}.stdout.txt"
    stderr_path = log_dir / f"{pdf_path.stem}.stderr.txt"

    command = [
        str(audiveris_bin),
        "-batch",
        "-transcribe",
        "-export",
        "-output",
        str(audiveris_output_dir),
        "--",
        str(pdf_path),
    ]
    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    status = "success"
    error_type = ""
    message = ""
    try:
        completed = subprocess.run(
            command,
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
            message = f"Audiveris exit {returncode} for {pdf_path.name}"
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        error_type = "TimeoutExpired"
        message = f"Audiveris timeout {timeout_seconds}s for {pdf_path.name}"
        stdout_text = _coerce_text(getattr(exc, "output", None))
        stderr_text = _coerce_text(getattr(exc, "stderr", None))
    except OSError as exc:
        status = "failure"
        error_type = type(exc).__name__
        message = str(exc)

    # Write logs
    stdout_path.write_text(stdout_text, encoding="utf-8")
    if stderr_text:
        stderr_path.write_text(stderr_text, encoding="utf-8")
    else:
        stderr_path.unlink(missing_ok=True)

    # Find exported MusicXML (Audiveris may emit .mxl or .musicxml)
    exported: Path | None = None
    if status == "success":
        candidates = list(audiveris_output_dir.rglob("*.mxl")) + list(audiveris_output_dir.rglob("*.musicxml")) + list(audiveris_output_dir.rglob("*.xml"))
        # Prefer file matching pdf stem
        for cand in sorted(candidates, key=lambda p: (0 if pdf_path.stem in p.stem else 1, str(p))):
            if cand.is_file() and cand.stat().st_size > 0:
                exported = cand
                break
        if exported is None:
            status = "failure"
            error_type = "MissingOutput"
            message = f"Audiveris reported success but no MusicXML in {audiveris_output_dir}"
        else:
            # Preserve exported suffix (.mxl vs .musicxml) to keep file readable
            actual_out = omr_out_path.parent / f"{omr_out_path.stem}{exported.suffix}"
            # Clean any stale alternative suffix
            for alt in [omr_out_path.with_suffix(".musicxml"), omr_out_path.with_suffix(".mxl"), omr_out_path.with_suffix(".xml")]:
                if alt != actual_out and alt.exists():
                    alt.unlink(missing_ok=True)
            omr_out_path = actual_out
            omr_out_path.parent.mkdir(parents=True, exist_ok=True)
            omr_out_path.unlink(missing_ok=True)
            shutil.copy2(exported, omr_out_path)
            if not omr_out_path.is_file() or omr_out_path.stat().st_size == 0:
                status = "failure"
                error_type = "CopyFailed"
                message = f"Failed to copy OMR output to {omr_out_path}"

    if status != "success":
        omr_out_path.unlink(missing_ok=True)

    return {
        "status": status,
        "returncode": returncode if returncode is not None else "",
        "error_type": error_type,
        "message": message,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path) if Path(stderr_path).exists() else "",
        "audiveris_output_dir": str(audiveris_output_dir),
        "exported_path": str(exported) if exported else "",
        "omr_musicxml_path": str(omr_out_path) if omr_out_path.exists() else "",
    }


def _build_per_aspect_metrics(
    original_path: Path, omr_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run difficulty_aspects on both scores and compute per-aspect metrics.

    Returns (per_aspect_metrics, diagnostics) where per_aspect_metrics is
    {aspect_id: {pearson_r, spearman_r, rmse, mae, n_aligned, ...}}
    and diagnostics contains window counts and error.
    """
    from tests.harness.omr_pipeline.aspect_trace_plots import (
        KNOWN_ASPECT_IDS,
        _extract_traces,
        _get_aspect_values,
        compute_aspect_metrics,
    )

    orig_payload, orig_diag, orig_err = _extract_traces(original_path)
    omr_payload, omr_diag, omr_err = _extract_traces(omr_path)
    if orig_payload is None:
        return {}, {"error": f"original extraction failed: {orig_err}", "original_window_count": "", "omr_window_count": ""}
    if omr_payload is None:
        return {}, {"error": f"omr extraction failed: {omr_err}", "original_window_count": len(orig_payload.get("regions") or []), "omr_window_count": ""}

    orig_win = len(orig_payload.get("regions") or [])
    omr_win = len(omr_payload.get("regions") or [])

    per_aspect: dict[str, dict[str, Any]] = {}
    for aspect_id in KNOWN_ASPECT_IDS:
        orig_vals = _get_aspect_values(orig_payload, aspect_id)
        omr_vals = _get_aspect_values(omr_payload, aspect_id)
        if orig_vals is None or omr_vals is None:
            per_aspect[aspect_id] = {"error": "aspect missing", "pearson_r": None, "spearman_r": None, "rmse": None, "mae": None}
            continue
        per_aspect[aspect_id] = compute_aspect_metrics(orig_vals, omr_vals)

    diagnostics = {
        "original_window_count": orig_win,
        "omr_window_count": omr_win,
        "window_count_mismatch": int(orig_win != omr_win),
        "original_title": (orig_diag or {}).get("title"),
        "omr_title": (omr_diag or {}).get("title"),
        "error": "",
    }
    return per_aspect, diagnostics


def _aggregate_per_aspect_stats(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    from tests.harness.omr_pipeline.aspect_trace_plots import KNOWN_ASPECT_IDS

    per_aspect_stats: dict[str, dict[str, Any]] = {}
    for aspect_id in KNOWN_ASPECT_IDS:
        # Collect metrics for this aspect across rows where rendered
        vals: list[dict[str, Any]] = []
        for row in all_rows:
            if row.get("pdf_status") != "success" or row.get("omr_status") != "success":
                continue
            try:
                per = json.loads(row.get("per_aspect_metrics_json") or "{}")
            except Exception:
                continue
            m = per.get(aspect_id)
            if not m or m.get("error"):
                continue
            # Filter non-finite
            if m.get("pearson_r") is not None:
                try:
                    v = float(m["pearson_r"])
                    if not math.isfinite(v):
                        continue
                except Exception:
                    continue
            vals.append(m)
        if not vals:
            continue
        def _mean(key: str) -> float | None:
            xs = [float(v[key]) for v in vals if v.get(key) is not None and isinstance(v[key], (int, float)) and math.isfinite(float(v[key]))]
            return sum(xs) / len(xs) if xs else None
        def _median(key: str) -> float | None:
            xs = sorted([float(v[key]) for v in vals if v.get(key) is not None and isinstance(v[key], (int, float)) and math.isfinite(float(v[key]))])
            return xs[len(xs)//2] if xs else None
        per_aspect_stats[aspect_id] = {
            "n": len(vals),
            "mean_pearson_r": _mean("pearson_r"),
            "median_pearson_r": _median("pearson_r"),
            "mean_spearman_r": _mean("spearman_r"),
            "mean_rmse": _mean("rmse"),
            "mean_mae": _mean("mae"),
            "min_pearson_r": min((float(v["pearson_r"]) for v in vals if v.get("pearson_r") is not None), default=None),
            "max_pearson_r": max((float(v["pearson_r"]) for v in vals if v.get("pearson_r") is not None), default=None),
        }
    sorted_aspects = sorted(
        per_aspect_stats.items(),
        key=lambda kv: (kv[1].get("mean_pearson_r") is None, -(kv[1].get("mean_pearson_r") or -2)),
    )
    most_robust = [k for k, _ in sorted_aspects[:3]]
    least_robust = [k for k, _ in list(reversed(sorted_aspects))[:3]] if sorted_aspects else []
    return {
        "per_aspect_stats": per_aspect_stats,
        "most_robust_aspects": most_robust,
        "least_robust_aspects": least_robust,
        "robustness_ranking": [k for k, _ in sorted_aspects],
    }


def _write_overview_md(out_dir: Path, summary: dict[str, Any]) -> None:
    md_path = out_dir / "aspect_overview.md"
    per_stats = summary.get("per_aspect_stats") or summary.get("per_aspect_stats", {})
    # summary may contain nested per_aspect_stats from aggregation
    # For bulk_summary, it is top-level "per_aspect_stats"
    if not per_stats:
        per_stats = summary.get("per_aspect_stats", {})
    lines: list[str] = []
    lines.append("# OMR Aspect Robustness — Streaming Overview")
    lines.append("")
    lines.append(f"- Generated: {summary.get('timestamp','')}")
    lines.append(f"- Out dir: {summary.get('out_dir','')}")
    lines.append(f"- Pieces processed: {summary.get('processed_count', summary.get('success_count', ''))} / {summary.get('total_discovered', summary.get('total_pairs',''))}")
    lines.append(f"- Success (both PDF+OMR): {summary.get('success_count',0)}  |  Failures: {summary.get('failure_count',0)}")
    lines.append("")
    if summary.get("failure_categories_counter"):
        lines.append("## Failure categories")
        for k, v in sorted(summary["failure_categories_counter"].items()):
            lines.append(f"- {k}: {v}")
        lines.append("")
    if not per_stats:
        lines.append("_No per-aspect stats yet (need at least one successful OMR comparison)._")
        lines.append("")
    else:
        lines.append("## Per-aspect means (ranked most robust first by mean Pearson r)")
        lines.append("")
        lines.append("| Rank | Aspect | n | mean r | median r | mean ρ | mean RMSE | mean MAE |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        ranking = summary.get("robustness_ranking") or sorted(per_stats, key=lambda k: -(per_stats[k].get("mean_pearson_r") or -2))
        for idx, aspect in enumerate(ranking, 1):
            s = per_stats[aspect]
            def _fmt(v: Any) -> str:
                if v is None:
                    return "n/a"
                if isinstance(v, float):
                    return f"{v:.3f}"
                return str(v)
            lines.append(
                f"| {idx} | {aspect} | {s.get('n','')} | {_fmt(s.get('mean_pearson_r'))} | {_fmt(s.get('median_pearson_r'))} | {_fmt(s.get('mean_spearman_r'))} | {_fmt(s.get('mean_rmse'))} | {_fmt(s.get('mean_mae'))} |"
            )
        lines.append("")
        if summary.get("most_robust_aspects"):
            lines.append(f"**Most robust:** {', '.join(summary['most_robust_aspects'])}")
        if summary.get("least_robust_aspects"):
            lines.append(f"**Least robust:** {', '.join(summary['least_robust_aspects'])}")
        lines.append("")
    lines.append("## Notes")
    lines.append("- Each PNG overlays original (aspect color) and OMR (orange) on one axes; window-count mismatch note if n differ.")
    lines.append("- Metrics truncated to min(n_orig, n_omr) and aligned skipping None gaps; r/ρ undefined if n_aligned<2 or constant.")
    lines.append("- Streaming: this file is rewritten after each piece; stopping early preserves partial ranking.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_overview_png(out_dir: Path, summary: dict[str, Any]) -> None:
    per_stats = summary.get("per_aspect_stats") or {}
    if not per_stats:
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ranking = summary.get("robustness_ranking") or sorted(per_stats, key=lambda k: -(per_stats[k].get("mean_pearson_r") or -2))
        vals = [per_stats[k].get("mean_pearson_r") for k in ranking]
        # Replace None with 0 for plotting but annotate n/a
        plot_vals = [v if isinstance(v, (int, float)) and math.isfinite(v) else 0 for v in vals]
        labels = ranking
        fig, ax = plt.subplots(figsize=(10, 4.5))
        colors = ["#2ca02c" if (v is not None and v > 0.5) else "#ff7f0e" if (v is not None and v > 0.2) else "#d62728" for v in vals]
        bars = ax.bar(range(len(labels)), plot_vals, color=colors, edgecolor="white")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
        ax.set_ylabel("mean Pearson r (original vs OMR)")
        ax.set_ylim(-0.1, 1.05)
        ax.set_title(f"OMR robustness per aspect — mean Pearson r (n pieces: {summary.get('success_count',0)})", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        for bar, v in zip(bars, vals):
            txt = f"{v:.2f}" if isinstance(v, float) else "n/a"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, txt, ha="center", va="bottom", fontsize=7)
        fig.tight_layout()
        out_path = out_dir / "aspect_overview.png"
        fig.savefig(out_path, dpi=180)
        plt.close(fig)
    except Exception:
        pass


def run_bulk_aspect_experiment(
    *,
    dataset_root: str | Path | None = None,
    out_dir: str | Path | None = None,
    musescore_bin: str | Path | None = None,
    audiveris_bin: str | Path | None = None,
    musescore_timeout_seconds: float = DEFAULT_MUSESCORE_TIMEOUT,
    audiveris_timeout_seconds: float = DEFAULT_AUDIVERIS_TIMEOUT,
    limit: int | None = None,
    suffixes: tuple[str, ...] = (".mxl", ".musicxml", ".xml"),
    include_composite: bool = False,
    resume: bool = False,
    dry_run_omr: bool = False,
) -> dict[str, Any]:
    # Resolve dataset_root with fallback
    candidates: list[Path] = []
    if dataset_root is not None:
        candidates.append(Path(dataset_root))
    candidates.extend([DEFAULT_DATASET_ROOT, FALLBACK_DATASET_ROOT, ALTERNATE_FALLBACK])
    # Also try david_demo source scores relative to repo
    candidates.append(REPO_ROOT.parent.parent / "research" / "learning_support" / "david_demo" / "data" / "source_scores")
    candidates.append(Path("/Users/campshelor/repos/gradus/research/learning_support/david_demo/data/source_scores"))
    dataset_path: Path | None = None
    for cand in candidates:
        try:
            if Path(cand).expanduser().is_dir():
                # ensure has some files
                if any(Path(cand).expanduser().rglob("*")):
                    dataset_path = Path(cand).expanduser().resolve()
                    break
        except Exception:
            continue
    if dataset_path is None:
        raise FileNotFoundError(f"No dataset root found. Tried: {candidates}")

    out_path = Path(out_dir).expanduser().resolve() if out_dir is not None else DEFAULT_OUT_DIR.resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    pdfs_dir = out_path / "pdfs"
    omr_dir = out_path / "omr_musicxml"
    logs_pdf_dir = out_path / "logs" / "pdf_export"
    logs_omr_dir = out_path / "logs" / "audiveris"
    png_root = out_path / "aspect_comparison_pngs"
    for d in [pdfs_dir, omr_dir, logs_pdf_dir, logs_omr_dir, png_root]:
        d.mkdir(parents=True, exist_ok=True)

    musescore_resolved: Path | None = None
    audiveris_resolved: Path | None = None
    musescore_error: str | None = None
    audiveris_error: str | None = None
    try:
        musescore_resolved = resolve_musescore_binary(musescore_bin)
    except Exception as exc:
        musescore_error = f"{type(exc).__name__}: {exc}"
    if not dry_run_omr:
        try:
            audiveris_resolved = resolve_audiveris_binary(audiveris_bin)
        except Exception as exc:
            audiveris_error = f"{type(exc).__name__}: {exc}"
    else:
        audiveris_error = "dry_run_omr: skipped"

    # Discover files
    suffix_set = {s.lower() if s.startswith(".") else f".{s.lower()}" for s in suffixes}
    source_files = discover_score_files(dataset_path, suffix_set)  # type: ignore[arg-type]
    if limit is not None:
        limit = int(limit)
        if limit >= 0:
            source_files = source_files[:limit]

    manifest_path = out_path / "bulk_manifest.csv"
    summary_path = out_path / "bulk_summary.json"
    # Load existing manifest for resume
    existing_rows: list[dict[str, Any]] = []
    existing_ids: set[str] = set()
    if resume and manifest_path.exists():
        try:
            with manifest_path.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    existing_rows.append(row)
                    existing_ids.add(row.get("piece_id", "") or row.get("source_path", ""))
        except Exception:
            existing_rows = []
            existing_ids = set()

    # If not resume, truncate manifest
    if not resume:
        existing_rows = []
        existing_ids = set()
        # Write header immediately for streaming visibility
        with manifest_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDNAMES)
            writer.writeheader()

    # For resume, we need to ensure file exists; if not, create
    if resume and not manifest_path.exists():
        with manifest_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDNAMES)
            writer.writeheader()

    failure_counter: dict[str, int] = {}
    # If resuming, count prior failures
    for r in existing_rows:
        cat = r.get("failure_category") or "success"
        if cat != "success":
            failure_counter[cat] = failure_counter.get(cat, 0) + 1
        else:
            # Check if previously failed due to missing OMR but now we might retry
            pass

    all_rows: list[dict[str, Any]] = list(existing_rows)  # for aggregation
    # Map existing piece_id -> row for quick skip
    existing_piece_map = {r.get("piece_id"): r for r in existing_rows if r.get("piece_id")}

    # Helper to flush summary after each piece
    def _write_summary(processed: int) -> dict[str, Any]:
        success = sum(1 for r in all_rows if r.get("pdf_status") == "success" and r.get("omr_status") == "success")
        failures = len(all_rows) - success
        agg = _aggregate_per_aspect_stats(all_rows)
        summary: dict[str, Any] = {
            "schema_version": "omr_bulk_aspect_experiment.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_root": str(dataset_path),
            "out_dir": str(out_path),
            "pdfs_dir": str(pdfs_dir),
            "omr_dir": str(omr_dir),
            "manifest_path": str(manifest_path),
            "summary_path": str(summary_path),
            "png_root": str(png_root),
            "musescore_bin": str(musescore_resolved) if musescore_resolved else None,
            "musescore_error": musescore_error,
            "audiveris_bin": str(audiveris_resolved) if audiveris_resolved else None,
            "audiveris_error": audiveris_error,
            "musescore_timeout_seconds": musescore_timeout_seconds,
            "audiveris_timeout_seconds": audiveris_timeout_seconds,
            "total_discovered": len(source_files),
            "processed_count": processed,
            "success_count": success,
            "failure_count": failures,
            "failure_categories_counter": dict(failure_counter),
            "limit": limit,
            "include_composite": include_composite,
            "dry_run_omr": dry_run_omr,
            "resume": resume,
            **agg,
        }
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        _write_overview_md(out_path, summary)
        _write_overview_png(out_path, summary)
        return summary

    # Initial summary write (so streaming file exists)
    _write_summary(len(all_rows))

    from tests.harness.omr_pipeline.aspect_trace_plots import (
        KNOWN_ASPECT_IDS,
        _get_aspect_values,
        _extract_traces,
        compute_aspect_metrics,
        _plot_single_comparison,
        _get_composite_values,
    )

    # Process piece by piece
    for idx, source_path in enumerate(source_files):
        piece_id = _sanitize_piece_id(source_path.stem)
        # Handle duplicate stems
        existing_pieces = {r.get("piece_id") for r in all_rows}
        base_piece_id = piece_id
        dup = 1
        while piece_id in existing_pieces:
            piece_id = f"{base_piece_id}-{dup:03d}"
            dup += 1

        # Resume skip: if we already have a row for this source_path (or piece_id)
        # and resume==True, check if we can skip
        if resume:
            # Look for prior row with same source_path
            prior = next((r for r in all_rows if r.get("source_path") == str(source_path.resolve())), None)
            if prior is not None:
                # If prior had success both, skip re-do
                if prior.get("pdf_status") == "success" and prior.get("omr_status") == "success":
                    continue
                # Otherwise we will re-process this piece: remove prior row from aggregation
                # but keep manifest history? For simplicity, replace row: remove prior and re-add
                all_rows = [r for r in all_rows if r.get("source_path") != str(source_path.resolve())]
                # Decrement failure counter for prior
                cat = prior.get("failure_category") or "success"
                if cat in failure_counter:
                    failure_counter[cat] = max(0, failure_counter[cat] - 1)
                    if failure_counter[cat] == 0:
                        del failure_counter[cat]

        pdf_path = pdfs_dir / f"{piece_id}.pdf"
        # OMR output may be .mxl or .musicxml — use stem to find actual
        omr_out_path = omr_dir / f"{piece_id}.musicxml"  # placeholder; actual suffix from Audiveris
        def _find_actual_omr(stem: str) -> Path | None:
            for suf in (".mxl", ".musicxml", ".xml"):
                cand = omr_dir / f"{stem}{suf}"
                if cand.is_file() and cand.stat().st_size > 0:
                    return cand
            # fallback glob
            for p in omr_dir.glob(f"{stem}.*"):
                if p.is_file() and p.stat().st_size > 0:
                    return p
            return None

        # MuseScore export
        pdf_result: dict[str, Any] | None = None
        omr_result: dict[str, Any] | None = None
        failure_category = "success"
        error_msg = ""
        per_aspect_json = "{}"
        orig_win = ""
        omr_win = ""
        window_mismatch = ""
        mean_pearson: float | str = ""
        mean_spearman: float | str = ""
        mean_rmse: float | str = ""
        mean_mae: float | str = ""

        if musescore_resolved is None:
            pdf_status = "failure"
            failure_category = "missing_musescore"
            error_msg = musescore_error or "MuseScore not found"
            pdf_result = {"status": pdf_status, "message": error_msg}
        else:
            # If resuming and pdf already exists and is valid, skip export
            if resume and pdf_path.is_file() and pdf_path.stat().st_size > 0:
                pdf_status = "success"
                pdf_result = {"status": "success", "pdf_path": str(pdf_path)}
            else:
                pdf_result = _export_single_pdf(source_path, pdf_path, musescore_resolved, musescore_timeout_seconds, logs_pdf_dir)
                pdf_status = pdf_result["status"]  # type: ignore[assignment]
                if pdf_status != "success":
                    failure_category = pdf_result.get("error_type") or "pdf_export_failed"
                    error_msg = pdf_result.get("message", "")
                    failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1

        omr_status = "failure"
        if pdf_status == "success":
            if dry_run_omr:
                omr_status = "failure"
                failure_category = "dry_run_omr"
                error_msg = "dry_run_omr: OMR skipped"
                failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1
                omr_result = {"status": omr_status, "message": error_msg}
            elif audiveris_resolved is None:
                omr_status = "failure"
                failure_category = "missing_audiveris"
                error_msg = audiveris_error or "Audiveris not found"
                failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1
                omr_result = {"status": omr_status, "message": error_msg}
            else:
                # Resume: if omr already exists (any suffix), skip
                existing_omr = _find_actual_omr(piece_id)
                if resume and existing_omr is not None:
                    omr_status = "success"
                    omr_result = {"status": "success", "omr_musicxml_path": str(existing_omr)}
                    omr_out_path = existing_omr  # use actual for downstream
                else:
                    omr_result = _run_single_audiveris(pdf_path, omr_out_path, audiveris_resolved, audiveris_timeout_seconds, logs_omr_dir)
                    omr_status = omr_result["status"]  # type: ignore[assignment]
                    if omr_status != "success":
                        failure_category = omr_result.get("error_type") or "omr_failed"
                        error_msg = omr_result.get("message", "")
                        failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1
                    else:
                        # _run_single_audiveris now returns actual suffix path
                        actual = omr_result.get("omr_musicxml_path")
                        if actual:
                            omr_out_path = Path(actual)

        # If both succeeded, compute per-aspect metrics and generate overlays
        per_aspect_metrics: dict[str, Any] = {}
        if pdf_status == "success" and omr_status == "success":
            # Ensure we have the actual OMR path (glob if needed)
            if not omr_out_path.is_file():
                found = _find_actual_omr(piece_id)
                if found is not None:
                    omr_out_path = found
            try:
                per_aspect_metrics, diag = _build_per_aspect_metrics(source_path, omr_out_path)
                per_aspect_json = json.dumps(per_aspect_metrics)
                orig_win = diag.get("original_window_count", "")
                omr_win = diag.get("omr_window_count", "")
                window_mismatch = diag.get("window_count_mismatch", "")
                if diag.get("error"):
                    failure_category = "analysis_failed"
                    error_msg = diag["error"]
                    failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1
                    # Keep omr_status success but mark failure_category for visibility
                else:
                    # Aggregate mean across aspects for manifest summary
                    pear_vals = [v.get("pearson_r") for v in per_aspect_metrics.values() if isinstance(v.get("pearson_r"), float) and math.isfinite(v["pearson_r"])]
                    spear_vals = [v.get("spearman_r") for v in per_aspect_metrics.values() if isinstance(v.get("spearman_r"), float) and math.isfinite(v["spearman_r"])]
                    rmse_vals = [v.get("rmse") for v in per_aspect_metrics.values() if isinstance(v.get("rmse"), float) and math.isfinite(v["rmse"])]
                    mae_vals = [v.get("mae") for v in per_aspect_metrics.values() if isinstance(v.get("mae"), float) and math.isfinite(v["mae"])]
                    if pear_vals:
                        mean_pearson = sum(pear_vals) / len(pear_vals)
                    if spear_vals:
                        mean_spearman = sum(spear_vals) / len(spear_vals)
                    if rmse_vals:
                        mean_rmse = sum(rmse_vals) / len(rmse_vals)
                    if mae_vals:
                        mean_mae = sum(mae_vals) / len(mae_vals)
                    failure_category = "success"

                    # Generate per-aspect overlay PNGs
                    # Need payloads for compositing
                    orig_payload, orig_diag, _ = _extract_traces(source_path)
                    omr_payload, omr_diag2, _ = _extract_traces(omr_out_path)
                    if orig_payload is not None and omr_payload is not None:
                        orig_title = (orig_diag or {}).get("title") or piece_id
                        omr_title = (omr_diag2 or {}).get("title")
                        for aspect_id in KNOWN_ASPECT_IDS:
                            orig_vals = _get_aspect_values(orig_payload, aspect_id)
                            omr_vals = _get_aspect_values(omr_payload, aspect_id)
                            if orig_vals is None or omr_vals is None:
                                continue
                            orig_comp = _get_composite_values(orig_payload) if include_composite else None
                            omr_comp = _get_composite_values(omr_payload) if include_composite else None
                            png_path = png_root / piece_id / f"{aspect_id}.png"
                            try:
                                _plot_single_comparison(
                                    piece_id=piece_id,
                                    aspect_id=aspect_id,
                                    original_vals=orig_vals,
                                    omr_vals=omr_vals,
                                    original_composite=orig_comp,
                                    omr_composite=omr_comp,
                                    out_path=png_path,
                                    include_composite=include_composite,
                                    original_title=orig_title,
                                    omr_title=omr_title,
                                )
                            except Exception:
                                pass
            except Exception as exc:
                per_aspect_json = json.dumps({"error": f"{type(exc).__name__}: {exc}"})
                failure_category = "analysis_exception"
                error_msg = f"{type(exc).__name__}: {exc}"
                failure_counter[failure_category] = failure_counter.get(failure_category, 0) + 1
        else:
            # For failures, still record window counts if possible (empty)
            per_aspect_json = "{}"

        # Build row (resolve actual OMR path for manifest)
        actual_omr_str = ""
        if omr_status == "success":
            # Prefer the actual file found
            actual = _find_actual_omr(piece_id)
            if actual is not None:
                actual_omr_str = str(actual)
            elif omr_result and omr_result.get("omr_musicxml_path"):
                actual_omr_str = str(omr_result.get("omr_musicxml_path"))
            elif omr_out_path.exists():
                actual_omr_str = str(omr_out_path)
        else:
            if omr_result and omr_result.get("omr_musicxml_path"):
                actual_omr_str = str(omr_result.get("omr_musicxml_path"))
        row: dict[str, Any] = {
            "piece_id": piece_id,
            "filename": source_path.name,
            "source_path": str(source_path.resolve()),
            "pdf_path": str(pdf_path) if pdf_path.exists() else (pdf_result.get("pdf_path", "") if pdf_result else ""),
            "pdf_status": pdf_status,
            "omr_musicxml_path": actual_omr_str,
            "omr_status": omr_status,
            "failure_category": failure_category,
            "original_window_count": orig_win,
            "omr_window_count": omr_win,
            "window_count_mismatch": window_mismatch,
            "mean_pearson_r": mean_pearson,
            "mean_spearman_r": mean_spearman,
            "mean_rmse": mean_rmse,
            "mean_mae": mean_mae,
            "per_aspect_metrics_json": per_aspect_json,
            "error": error_msg,
        }

        # Append to CSV streaming (append mode)
        file_exists = manifest_path.exists()
        with manifest_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDNAMES)
            if not file_exists or fh.tell() == 0:
                writer.writeheader()
            # Ensure all keys
            out_row = {k: ("" if row.get(k) is None else row.get(k)) for k in MANIFEST_FIELDNAMES}
            # Normalize floats None -> ""
            for k in ["mean_pearson_r", "mean_spearman_r", "mean_rmse", "mean_mae"]:
                if out_row[k] is None:
                    out_row[k] = ""
            writer.writerow(out_row)

        all_rows.append(row)
        # Update summary streaming
        _write_summary(len(all_rows))
        # Print progress line for meeting-friendly tailing
        print(f"[{len(all_rows)}/{len(source_files)}] {piece_id}: pdf={pdf_status} omr={omr_status} cat={failure_category} mean_r={mean_pearson if mean_pearson != '' else 'n/a'}")

    # Final summary
    final_summary = _write_summary(len(all_rows))
    return final_summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_omr_bulk_aspect_experiment",
        description="Piece-by-piece OMR bulk: Oktav source -> MuseScore PDF -> Audiveris -> single-graph aspect overlay + streaming stats. Safe to Ctrl-C early.",
    )
    p.add_argument("--dataset-root", type=Path, default=None, help="Dataset root containing .mxl/.musicxml. Defaults to Oktav dataset if present, else david_demo source_scores.")
    p.add_argument("--out-dir", type=Path, default=None, help="Output dir (default: tests/artifacts/omr_pipeline/experiment/bulk_aspect_run).")
    p.add_argument("--musescore-bin", type=Path, default=None, help="MuseScore binary.")
    p.add_argument("--audiveris-bin", type=Path, default=None, help="Audiveris binary.")
    p.add_argument("--musescore-timeout-seconds", type=float, default=DEFAULT_MUSESCORE_TIMEOUT, help="Per-file MuseScore timeout (default 60s).")
    p.add_argument("--audiveris-timeout-seconds", type=float, default=DEFAULT_AUDIVERIS_TIMEOUT, help="Per-file Audiveris timeout (default 600s).")
    p.add_argument("--limit", type=int, default=None, help="Limit number of pieces (for quick test).")
    p.add_argument("--suffix", action="append", dest="suffixes", default=None, help="Suffix to include (repeatable). Default: .mxl .musicxml .xml")
    p.add_argument("--include-composite", action="store_true", help="Overlay composite dashed lines on each PNG.")
    p.add_argument("--resume", action="store_true", help="Resume prior run in out-dir: skip already succeeded PDFs/OMRs and reuse manifest.")
    p.add_argument("--dry-run-omr", action="store_true", help="Skip Audiveris (use to test PDF+analysis plumbing fast).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = args.out_dir or DEFAULT_OUT_DIR
    suffixes = tuple(args.suffixes) if args.suffixes else (".mxl", ".musicxml", ".xml")
    summary = run_bulk_aspect_experiment(
        dataset_root=args.dataset_root,
        out_dir=out_dir,
        musescore_bin=args.musescore_bin,
        audiveris_bin=args.audiveris_bin,
        musescore_timeout_seconds=args.musescore_timeout_seconds,
        audiveris_timeout_seconds=args.audiveris_timeout_seconds,
        limit=args.limit,
        suffixes=suffixes,  # type: ignore[arg-type]
        include_composite=args.include_composite,
        resume=args.resume,
        dry_run_omr=args.dry_run_omr,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    # Exit 0 if at least one success, else 1
    return 0 if summary.get("success_count", 0) > 0 else 1
