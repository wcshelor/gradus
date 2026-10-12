"""Batch visualization helper for OMR robustness — per-aspect trace comparisons.

Test-scoped. Generates PNGs that compare original vs OMR difficulty_aspects
traces one aspect at a time.

- Reads either an experiment output directory (experiment_manifest.csv /
  readback_manifest.csv) or a simple comparison manifest (piece_id,
  original_path, omr_path).
- For each (piece, aspect) writes one PNG: <out_dir>/aspect_comparison_pngs/<piece_id>/<aspect_id>.png
  with both original and OMR traces overlaid on a single axes (distinct colors),
  optional dashed composite.
- Supports .musicxml, .xml, .mxl, and compressed MusicXML via piano_difficulty.pipeline.
- Also computes per-aspect similarity metrics (pearson, spearman, rmse, mae)
  for the statistical overview.

This module stays out of runtime extraction; it only calls analyze_score with
difficulty_aspects.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

# Known aspect IDs from src/piano_difficulty/difficulty_analysis/aspects.py
KNOWN_ASPECT_IDS = (
    "rhythmic_demand",
    "pitch_movement_demand",
    "hand_shape_span_demand",
    "texture_polyphony_demand",
    "coordination_demand",
    "notation_reading_demand",
    "expression_control_demand",
    "structural_pattern_demand",
    "performance_interpretive_demand",
)

# Deterministic palette per aspect (distinct hues)
_ASPECT_PALETTE: dict[str, str] = {
    "rhythmic_demand": "#1f77b4",
    "pitch_movement_demand": "#d62728",
    "hand_shape_span_demand": "#2ca02c",
    "texture_polyphony_demand": "#9467bd",
    "coordination_demand": "#ff7f0e",
    "notation_reading_demand": "#8c564b",
    "expression_control_demand": "#e377c2",
    "structural_pattern_demand": "#7f7f7f",
    "performance_interpretive_demand": "#17becf",
}

DEFAULT_PLOT_SUBDIR = "aspect_comparison_pngs"


@dataclass(frozen=True, slots=True)
class ComparisonPair:
    piece_id: str
    original_path: Path
    omr_path: Path
    title: str | None = None


def _sanitize_piece_id(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "piece"


def _resolve_path(raw: str, base_dir: Path) -> Path:
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty path")
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def load_pairs_from_experiment_dir(experiment_dir: Path) -> list[ComparisonPair]:
    """Load pairs from an experiment output directory.

    Prefers experiment_manifest.csv, falls back to readback_manifest.csv.
    Supports direct manifest mode if neither exists but a generic
    comparison manifest is found (handled by caller).
    """
    experiment_dir = Path(experiment_dir).expanduser().resolve()
    candidates = [
        experiment_dir / "experiment_manifest.csv",
        experiment_dir / "readback_manifest.csv",
        experiment_dir / "pdf_manifest.csv",
    ]
    manifest_path = None
    for cand in candidates:
        if cand.exists():
            manifest_path = cand
            break
    if manifest_path is None:
        raise FileNotFoundError(
            f"No manifest found in {experiment_dir}. Expected one of: "
            + ", ".join(str(c) for c in candidates)
        )

    pairs: list[ComparisonPair] = []
    with manifest_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"Manifest {manifest_path} has no header")
        fn_lower = {k.lower(): k for k in reader.fieldnames}
        # Detect column names case-insensitively
        def col(*names: str) -> str | None:
            for n in names:
                if n.lower() in fn_lower:
                    return fn_lower[n.lower()]
            return None

        piece_col = col("piece_id", "score_id", "filename")
        orig_col = col("source_path", "original_path", "true_path", "score_path")
        omr_col = col("omr_musicxml_path", "omr_path", "readback_path", "omr_readback_path")

        if orig_col is None or omr_col is None:
            raise ValueError(
                f"Manifest {manifest_path} missing required columns. "
                f"Fields: {reader.fieldnames}. Need source_path/original_path and omr_musicxml_path/omr_path."
            )

        for idx, row in enumerate(reader):
            # Skip rows where omr status indicates failure if present
            # Prefer to include only rows where paths exist, but record anyway and handle skip later
            raw_orig = str(row.get(orig_col, "") or "").strip()
            raw_omr = str(row.get(omr_col, "") or "").strip()
            if not raw_orig or not raw_omr:
                continue
            # derive piece_id
            if piece_col is not None:
                raw_pid = str(row.get(piece_col, "") or "").strip()
                if raw_pid:
                    # strip extension if it's a filename
                    if raw_pid.lower().endswith((".musicxml", ".xml", ".mxl")):
                        raw_pid = Path(raw_pid).stem
                    piece_id = _sanitize_piece_id(raw_pid)
                else:
                    piece_id = _sanitize_piece_id(Path(raw_orig).stem or f"piece_{idx:03d}")
            else:
                piece_id = _sanitize_piece_id(Path(raw_orig).stem or f"piece_{idx:03d}")

            # Ensure piece_id uniqueness within this dir
            # If duplicate, append index
            existing = {p.piece_id for p in pairs}
            if piece_id in existing:
                piece_id = f"{piece_id}-{idx:03d}"

            orig_path = Path(raw_orig).expanduser()
            omr_path = Path(raw_omr).expanduser()
            # Resolve relative paths against experiment_dir
            if not orig_path.is_absolute():
                orig_path = (experiment_dir / orig_path).resolve()
            if not omr_path.is_absolute():
                omr_path = (experiment_dir / omr_path).resolve()

            pairs.append(ComparisonPair(piece_id=piece_id, original_path=orig_path, omr_path=omr_path))
    return pairs


def load_pairs_from_manifest(manifest_path: Path) -> list[ComparisonPair]:
    """Load pairs from a simple comparison manifest CSV.

    Supports columns (case-insensitive):
      piece_id / piece / score_id / filename
      original_path / source_path / true_path / original / source
      omr_path / omr_musicxml_path / readback_path / omr
    Paths may be absolute or relative to the manifest parent.
    """
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    pairs: list[ComparisonPair] = []
    with manifest_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"Manifest {manifest_path} has no header")
        fn_lower = {k.lower(): k for k in reader.fieldnames}

        def col(*names: str) -> str | None:
            for n in names:
                if n.lower() in fn_lower:
                    return fn_lower[n.lower()]
            return None

        piece_col = col("piece_id", "piece", "score_id", "id", "filename")
        orig_col = col("original_path", "source_path", "true_path", "original", "source", "score_path")
        omr_col = col("omr_path", "omr_musicxml_path", "readback_path", "omr", "readback")

        if orig_col is None or omr_col is None:
            raise ValueError(
                f"Manifest {manifest_path} missing required columns. "
                f"Fields: {reader.fieldnames}. Need one of original_path/source_path and one of omr_path/omr_musicxml_path."
            )

        base = manifest_path.parent
        for idx, row in enumerate(reader):
            raw_orig = str(row.get(orig_col, "") or "").strip()
            raw_omr = str(row.get(omr_col, "") or "").strip()
            if not raw_orig or not raw_omr:
                continue
            if piece_col is not None:
                raw_pid = str(row.get(piece_col, "") or "").strip()
                if raw_pid:
                    if raw_pid.lower().endswith((".musicxml", ".xml", ".mxl")):
                        raw_pid = Path(raw_pid).stem
                    piece_id = _sanitize_piece_id(raw_pid)
                else:
                    piece_id = _sanitize_piece_id(Path(raw_orig).stem or f"piece_{idx:03d}")
            else:
                piece_id = _sanitize_piece_id(Path(raw_orig).stem or f"piece_{idx:03d}")

            existing = {p.piece_id for p in pairs}
            if piece_id in existing:
                piece_id = f"{piece_id}-{idx:03d}"

            try:
                orig_path = _resolve_path(raw_orig, base)
                omr_path = _resolve_path(raw_omr, base)
            except ValueError:
                continue

            pairs.append(ComparisonPair(piece_id=piece_id, original_path=orig_path, omr_path=omr_path))
    return pairs


def _extract_traces(score_path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Run difficulty_aspects on one score and return (payload, diagnostics, error).

    Returns payload dict on success, None on failure with error string.
    """
    try:
        from piano_difficulty.pipeline import analyze_score

        result = analyze_score(score_path, profile_ids=("difficulty_aspects",))
        payload = None
        for profile in result.analysis_profiles:
            try:
                pl = profile.to_payload()  # type: ignore[union-attr]
                if isinstance(pl, dict) and pl.get("profile_id") == "difficulty_aspects":
                    payload = pl
                    break
            except Exception:
                continue
        if payload is None:
            return None, None, "difficulty_aspects payload missing"
        return payload, {"title": result.extraction.score.title, "composer": result.extraction.score.composer}, None
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _get_aspect_values(payload: dict[str, Any], aspect_id: str) -> list[float | None] | None:
    series = payload.get("series") or payload.get("aspect_series") or {}
    entry = series.get(aspect_id)
    if entry is None:
        return None
    vals = entry.get("normalized_values")
    if vals is None:
        vals = entry.get("smoothed_values") or entry.get("raw_values")
    if vals is None:
        return None
    # Ensure list of floats/None
    out: list[float | None] = []
    for v in vals:
        if v is None:
            out.append(None)
        else:
            try:
                fv = float(v)
                if math.isfinite(fv):
                    out.append(fv)
                else:
                    out.append(None)
            except Exception:
                out.append(None)
    return out


def _get_composite_values(payload: dict[str, Any]) -> list[float | None] | None:
    comp = payload.get("composite") or payload.get("overall_series") or payload.get("graph_composite")
    if comp is None:
        return None
    vals = comp.get("normalized_values") or comp.get("smoothed_values") or comp.get("raw_values")
    if vals is None:
        return None
    out: list[float | None] = []
    for v in vals:
        if v is None:
            out.append(None)
        else:
            try:
                fv = float(v)
                if math.isfinite(fv):
                    out.append(fv)
                else:
                    out.append(None)
            except Exception:
                out.append(None)
    return out


def _finite_range(*traces: list[float | None] | None) -> tuple[float, float] | None:
    vals: list[float] = []
    for tr in traces:
        if tr is None:
            continue
        for v in tr:
            if v is not None and math.isfinite(v):
                vals.append(float(v))
    if not vals:
        return None
    vmin = min(vals)
    vmax = max(vals)
    if math.isclose(vmin, vmax):
        pad = max(abs(vmin) * 0.1, 0.05)
        return (vmin - pad, vmax + pad)
    pad = (vmax - vmin) * 0.08
    if pad == 0:
        pad = 0.05
    return (vmin - pad, vmax + pad)


# Fixed OMR line color — chosen to contrast with all aspect hues.
_OMR_OVERLAY_COLOR = "#ff7f0e"
_OMR_COMPOSITE_COLOR = "#2ca02c"


def _pearson(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 2 or len(b) != n:
        return None
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a)
    db = sum((y - mb) ** 2 for y in b)
    den = math.sqrt(da * db)
    if den == 0:
        return None
    return num / den


def _spearman(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 2 or len(b) != n:
        return None
    # rank with average for ties
    def _rank(vals: list[float]) -> list[float]:
        sorted_idx = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[sorted_idx[j + 1]] == vals[sorted_idx[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[sorted_idx[k]] = avg
            i = j + 1
        return ranks
    ra = _rank(a)
    rb = _rank(b)
    return _pearson(ra, rb)


def _aligned_numeric_pairs(
    orig: list[float | None], omr: list[float | None]
) -> tuple[list[float], list[float]]:
    n = min(len(orig), len(omr))
    a: list[float] = []
    b: list[float] = []
    for i in range(n):
        va = orig[i]
        vb = omr[i]
        if va is None or vb is None:
            continue
        if not math.isfinite(va) or not math.isfinite(vb):
            continue
        a.append(float(va))
        b.append(float(vb))
    return a, b


def compute_aspect_metrics(
    original_vals: list[float | None], omr_vals: list[float | None]
) -> dict[str, float | int | None]:
    a, b = _aligned_numeric_pairs(original_vals, omr_vals)
    n_aligned = len(a)
    n_truncated = min(len(original_vals), len(omr_vals))
    if n_aligned == 0:
        return {
            "n_aligned": 0,
            "n_truncated": n_truncated,
            "window_count_mismatch": int(len(original_vals) != len(omr_vals)),
            "pearson_r": None,
            "spearman_r": None,
            "rmse": None,
            "mae": None,
            "mean_abs_diff": None,
        }
    rmse = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / n_aligned) if n_aligned else None
    mae = sum(abs(x - y) for x, y in zip(a, b)) / n_aligned if n_aligned else None
    return {
        "n_aligned": n_aligned,
        "n_truncated": n_truncated,
        "window_count_mismatch": int(len(original_vals) != len(omr_vals)),
        "pearson_r": _pearson(a, b),
        "spearman_r": _spearman(a, b),
        "rmse": rmse,
        "mae": mae,
        "mean_abs_diff": mae,
    }


def _plot_single_comparison(
    *,
    piece_id: str,
    aspect_id: str,
    original_vals: list[float | None],
    omr_vals: list[float | None],
    original_composite: list[float | None] | None,
    omr_composite: list[float | None] | None,
    out_path: Path,
    include_composite: bool,
    original_title: str | None,
    omr_title: str | None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_path.parent.mkdir(parents=True, exist_ok=True)

    aspect_color = _ASPECT_PALETTE.get(aspect_id, "#1f77b4")
    # Ensure OMR color contrasts with aspect color
    omr_color = _OMR_OVERLAY_COLOR
    if aspect_color.lower() == omr_color.lower():
        omr_color = "#d62728" if aspect_color.lower() != "#d62728" else "#1f77b4"

    orig_len = len(original_vals)
    omr_len = len(omr_vals)
    mismatch = orig_len != omr_len

    # Determine y-limits shared
    y_range = _finite_range(
        original_vals,
        omr_vals,
        original_composite if include_composite else None,
        omr_composite if include_composite else None,
    )
    if y_range is None:
        y_range = (0.0, 1.0)
    y0, y1 = y_range

    # Single overlaid axes — both traces on same graph, distinct colors.
    fig, ax = plt.subplots(1, 1, figsize=(10, 4.2))

    # Original line
    x_orig = list(range(len(original_vals)))
    y_orig = [v if v is not None else float("nan") for v in original_vals]
    ax.plot(x_orig, y_orig, color=aspect_color, linewidth=1.9, marker="o", markersize=2.8, label="original", zorder=3)

    # OMR line — different color
    x_omr = list(range(len(omr_vals)))
    y_omr = [v if v is not None else float("nan") for v in omr_vals]
    ax.plot(x_omr, y_omr, color=omr_color, linewidth=1.6, marker="s", markersize=2.4, linestyle="-", alpha=0.92, label="OMR", zorder=3)

    if include_composite:
        if original_composite is not None:
            y_c = [v if v is not None else float("nan") for v in original_composite]
            # Truncate/pad to matching x length (original length)
            ax.plot(list(range(len(y_c))), y_c, color="black", linewidth=1.0, linestyle="--", alpha=0.55, label="composite (orig)", zorder=2)
        if omr_composite is not None:
            y_c2 = [v if v is not None else float("nan") for v in omr_composite]
            ax.plot(list(range(len(y_c2))), y_c2, color=_OMR_COMPOSITE_COLOR, linewidth=1.0, linestyle=":", alpha=0.65, label="composite (OMR)", zorder=2)

    ax.set_ylim(y0, y1)
    max_len = max(len(original_vals), len(omr_vals), 1)
    ax.set_xlim(-0.5, max_len - 0.5)
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.set_ylabel("normalized score")
    ax.set_xlabel("window index")
    leg = ax.legend(loc="best", fontsize=7, framealpha=0.9)
    if leg is not None:
        leg.get_frame().set_edgecolor("0.7")

    # Titles / subtitles — compact single title
    disp_title = original_title or piece_id
    title_main = f"{piece_id} — {aspect_id}"
    fig.suptitle(title_main, fontsize=11, fontweight="bold", y=0.98)

    # Subtitle as axes title (single line with both counts)
    orig_label = Path(disp_title).name if disp_title and disp_title != piece_id else piece_id
    if original_title and original_title != piece_id:
        orig_label = original_title
    sub = f"original: {orig_label} (n={orig_len})  |  OMR: {omr_title or 'OMR'} (n={omr_len})"
    # Keep within 110 chars
    if len(sub) > 130:
        sub = f"original n={orig_len}  |  OMR n={omr_len}"
    ax.set_title(sub, fontsize=7, loc="left", pad=8, color="#333333")

    # Window-count mismatch note
    if mismatch:
        note = f"window-count mismatch: original {orig_len} vs OMR {omr_len} (truncated to {min(orig_len, omr_len)} for metrics)"
        fig.text(0.5, 0.015, note, ha="center", fontsize=6.5, color="#b00020", style="italic")
        # Annotate counts on plot
        ax.text(0.01, 0.93, f"n orig={orig_len}  n omr={omr_len}", transform=ax.transAxes, fontsize=6.5, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="0.7", alpha=0.85))

    # Handle blocked aspect (all None)
    orig_finite = any(v is not None for v in original_vals)
    omr_finite = any(v is not None for v in omr_vals)
    if not orig_finite and not omr_finite:
        ax.text(0.5, 0.5, f"No temporal signal for '{aspect_id}' (blocked/caveated)", ha="center", va="center",
                transform=ax.transAxes, fontsize=9, color="#7f7f7f", bbox=dict(boxstyle="round,pad=0.4", fc="#f2f2f2", ec="#cccccc"))

    # Metrics inset — quick numeric summary
    try:
        m = compute_aspect_metrics(original_vals, omr_vals)
        pear = m.get("pearson_r")
        spear = m.get("spearman_r")
        rmse = m.get("rmse")
        mae = m.get("mae")
        pear_s = f"{pear:.2f}" if isinstance(pear, float) else "n/a"
        spear_s = f"{spear:.2f}" if isinstance(spear, float) else "n/a"
        rmse_s = f"{rmse:.3f}" if isinstance(rmse, float) else "n/a"
        ax.text(0.99, 0.02, f"r={pear_s}  ρ={spear_s}  RMSE={rmse_s}", transform=ax.transAxes, fontsize=6.5, va="bottom", ha="right",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.8", alpha=0.9))
    except Exception:
        pass

    fig.tight_layout(rect=[0, 0.04 if mismatch else 0.02, 1, 0.93])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def run_aspect_trace_plots(
    *,
    experiment_dir: str | Path | None = None,
    manifest: str | Path | None = None,
    out_dir: str | Path | None = None,
    aspects: list[str] | None = None,
    all_aspects: bool = False,
    include_composite: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Core harness logic.

    Returns a summary dict suitable for JSON serialization.
    Writes PNGs plus plot_manifest.csv and plot_summary.json to out_dir.
    """
    if experiment_dir is None and manifest is None:
        raise ValueError("Must provide --experiment-dir or --manifest")

    pairs: list[ComparisonPair] = []
    source_label = ""
    if manifest is not None:
        pairs = load_pairs_from_manifest(Path(manifest))
        source_label = str(Path(manifest).resolve())
    elif experiment_dir is not None:
        pairs = load_pairs_from_experiment_dir(Path(experiment_dir))
        source_label = str(Path(experiment_dir).resolve())

    if limit is not None:
        limit = int(limit)
        if limit >= 0:
            pairs = pairs[:limit]

    # Resolve aspects
    if all_aspects:
        requested_aspects = list(KNOWN_ASPECT_IDS)
    elif aspects:
        # Deduplicate preserving order
        seen: set[str] = set()
        requested_aspects = []
        for a in aspects:
            a = a.strip()
            if not a:
                continue
            if a not in seen:
                seen.add(a)
                requested_aspects.append(a)
        if not requested_aspects:
            requested_aspects = list(KNOWN_ASPECT_IDS)
    else:
        # Default: if neither --all-aspects nor --aspect, treat as all? But CLI will validate.
        requested_aspects = list(KNOWN_ASPECT_IDS)

    # Validate aspects against known
    unknown_aspects = [a for a in requested_aspects if a not in KNOWN_ASPECT_IDS]
    # Keep unknown but warn; they'll produce skipped rows

    # Resolve out_dir
    if out_dir is not None:
        out_path = Path(out_dir).expanduser().resolve()
    else:
        if experiment_dir is not None:
            out_path = Path(experiment_dir).expanduser().resolve()
        elif manifest is not None:
            out_path = Path(manifest).expanduser().resolve().parent
        else:
            out_path = Path.cwd()

    png_root = out_path / DEFAULT_PLOT_SUBDIR
    png_root.mkdir(parents=True, exist_ok=True)

    plot_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    rendered = 0

    # Cache extracted payloads per path (to avoid re-analyzing same file multiple times if shared)
    payload_cache: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]] = {}

    def get_payload(p: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in payload_cache:
            if not p.exists():
                payload_cache[key] = (None, None, f"file not found: {p}")
            else:
                payload_cache[key] = _extract_traces(p)
        return payload_cache[key]

    for pair in pairs:
        orig_payload, orig_diag, orig_err = get_payload(pair.original_path)
        omr_payload, omr_diag, omr_err = get_payload(pair.omr_path)

        if orig_payload is None:
            for aspect_id in requested_aspects:
                skipped.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "reason": f"original extraction failed: {orig_err}",
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                })
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": "",
                    "omr_window_count": "",
                    "png_path": "",
                    "status": "skipped",
                    "error": f"original extraction failed: {orig_err}",
                })
            continue
        if omr_payload is None:
            for aspect_id in requested_aspects:
                skipped.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "reason": f"OMR extraction failed: {omr_err}",
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                })
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": len(orig_payload.get("regions") or []),
                    "omr_window_count": "",
                    "png_path": "",
                    "status": "skipped",
                    "error": f"OMR extraction failed: {omr_err}",
                })
            continue

        orig_title = (orig_diag or {}).get("title") or pair.title or pair.piece_id
        omr_title = (omr_diag or {}).get("title")
        orig_regions = orig_payload.get("regions") or []
        omr_regions = omr_payload.get("regions") or []
        orig_win_count = len(orig_regions)
        omr_win_count = len(omr_regions)

        for aspect_id in requested_aspects:
            if aspect_id not in KNOWN_ASPECT_IDS:
                skipped.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "reason": f"unknown aspect_id: {aspect_id}",
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                })
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": orig_win_count,
                    "omr_window_count": omr_win_count,
                    "png_path": "",
                    "status": "skipped",
                    "error": f"unknown aspect_id: {aspect_id}",
                })
                continue

            orig_vals = _get_aspect_values(orig_payload, aspect_id)
            omr_vals = _get_aspect_values(omr_payload, aspect_id)

            if orig_vals is None or omr_vals is None:
                skipped.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "reason": f"aspect not found in payload: {aspect_id}",
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                })
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": orig_win_count,
                    "omr_window_count": omr_win_count,
                    "png_path": "",
                    "status": "skipped",
                    "error": f"aspect not found: {aspect_id}",
                })
                continue

            orig_comp = _get_composite_values(orig_payload) if include_composite else None
            omr_comp = _get_composite_values(omr_payload) if include_composite else None
            # Metrics for statistical overview (truncated alignment)
            metrics = compute_aspect_metrics(orig_vals, omr_vals)

            png_path = png_root / _sanitize_piece_id(pair.piece_id) / f"{_sanitize_piece_id(aspect_id)}.png"
            try:
                _plot_single_comparison(
                    piece_id=pair.piece_id,
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
                rendered += 1
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": orig_win_count,
                    "omr_window_count": omr_win_count,
                    "png_path": str(png_path.resolve()),
                    "status": "rendered",
                    "error": "",
                    "n_aligned": metrics.get("n_aligned"),
                    "pearson_r": metrics.get("pearson_r"),
                    "spearman_r": metrics.get("spearman_r"),
                    "rmse": metrics.get("rmse"),
                    "mae": metrics.get("mae"),
                })
            except Exception as exc:
                skipped.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "reason": f"plot failed: {type(exc).__name__}: {exc}",
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                })
                plot_rows.append({
                    "piece_id": pair.piece_id,
                    "aspect_id": aspect_id,
                    "original_path": str(pair.original_path),
                    "omr_path": str(pair.omr_path),
                    "original_window_count": orig_win_count,
                    "omr_window_count": omr_win_count,
                    "png_path": "",
                    "status": "skipped",
                    "error": f"plot failed: {type(exc).__name__}: {exc}",
                })

    # Write plot_manifest.csv (now with per-aspect metrics)
    manifest_csv_path = out_path / "plot_manifest.csv"
    fieldnames = ["piece_id", "aspect_id", "original_path", "omr_path", "original_window_count", "omr_window_count", "png_path", "status", "error", "n_aligned", "pearson_r", "spearman_r", "rmse", "mae"]
    with manifest_csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in plot_rows:
            # Ensure all fieldnames present (skipped rows may not have metrics)
            for k in fieldnames:
                row.setdefault(k, "")
            # Normalize None -> ""
            out_row = {k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames}
            writer.writerow(out_row)

    # Per-aspect aggregated stats
    per_aspect_stats: dict[str, dict[str, Any]] = {}
    for aspect_id in requested_aspects:
        vals = [r for r in plot_rows if r.get("aspect_id") == aspect_id and r.get("status") == "rendered"]
        if not vals:
            continue
        def _col(name: str) -> list[float]:
            out: list[float] = []
            for r in vals:
                v = r.get(name)
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    out.append(float(v))
                elif isinstance(v, str) and v not in ("", "None"):
                    try:
                        fv = float(v)
                        if math.isfinite(fv):
                            out.append(fv)
                    except Exception:
                        pass
            return out
        pear = _col("pearson_r")
        spear = _col("spearman_r")
        rmse_vals = _col("rmse")
        mae_vals = _col("mae")
        def _mean(xs: list[float]) -> float | None:
            return sum(xs) / len(xs) if xs else None
        per_aspect_stats[aspect_id] = {
            "n": len(vals),
            "mean_pearson_r": _mean(pear),
            "median_pearson_r": sorted(pear)[len(pear)//2] if pear else None,
            "mean_spearman_r": _mean(spear),
            "mean_rmse": _mean(rmse_vals),
            "mean_mae": _mean(mae_vals),
            "min_pearson_r": min(pear) if pear else None,
            "max_pearson_r": max(pear) if pear else None,
        }

    # Ranking most/least robust by mean pearson
    sorted_aspects = sorted(
        per_aspect_stats.items(),
        key=lambda kv: (kv[1].get("mean_pearson_r") is None, -(kv[1].get("mean_pearson_r") or -2)),
    )
    most_robust = [k for k, _ in sorted_aspects[:3]]
    least_robust = [k for k, _ in list(reversed(sorted_aspects))[:3]] if sorted_aspects else []

    summary = {
        "schema_version": "omr_aspect_trace_plots.v2",
        "source": source_label,
        "experiment_dir": str(Path(experiment_dir).resolve()) if experiment_dir is not None else None,
        "manifest": str(Path(manifest).resolve()) if manifest is not None else None,
        "out_dir": str(out_path.resolve()),
        "png_root": str(png_root.resolve()),
        "aspects_requested": requested_aspects,
        "include_composite": include_composite,
        "limit": limit,
        "piece_count": len(pairs),
        "aspect_count": len(requested_aspects),
        "rendered": rendered,
        "skipped": len(skipped),
        "total_expected": len(pairs) * len(requested_aspects) if pairs else 0,
        "skipped_comparisons": skipped,
        "plot_manifest_csv": str(manifest_csv_path.resolve()),
        "plot_summary_json": str((out_path / "plot_summary.json").resolve()),
        "per_aspect_stats": per_aspect_stats,
        "most_robust_aspects": most_robust,
        "least_robust_aspects": least_robust,
    }

    summary_path = out_path / "plot_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_omr_aspect_trace_plots",
        description=(
            "Batch OMR robustness visualization: per-aspect original vs OMR trace comparisons. "
            "Generates one PNG per (piece, aspect) with both traces overlaid on a single axes (distinct colors)."
        ),
    )
    parser.add_argument("--experiment-dir", type=Path, default=None, help="Experiment output dir containing experiment_manifest.csv / readback_manifest.csv")
    parser.add_argument("--manifest", type=Path, default=None, help="Simple comparison manifest CSV with piece_id,original_path,omr_path")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for PNGs and manifests (default: experiment-dir or manifest parent)")
    parser.add_argument("--aspect", action="append", dest="aspects", default=None, help="Aspect id to plot. Repeatable. e.g., rhythmic_demand")
    parser.add_argument("--all-aspects", action="store_true", help="Plot all known aspects (9).")
    parser.add_argument("--include-composite", action="store_true", help="Overlay dashed composite aspect_demand line on both panels.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of pieces (for quick debugging).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.experiment_dir is None and args.manifest is None:
        parser.error("Must provide --experiment-dir or --manifest")
    if args.experiment_dir is not None and args.manifest is not None:
        parser.error("Provide only one of --experiment-dir or --manifest, not both")
    if not args.all_aspects and not args.aspects:
        parser.error("Must provide --all-aspects or at least one --aspect <id>")

    summary = run_aspect_trace_plots(
        experiment_dir=args.experiment_dir,
        manifest=args.manifest,
        out_dir=args.out_dir,
        aspects=args.aspects,
        all_aspects=args.all_aspects,
        include_composite=args.include_composite,
        limit=args.limit,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["rendered"] > 0 else 1


__all__ = [
    "KNOWN_ASPECT_IDS",
    "ComparisonPair",
    "compute_aspect_metrics",
    "load_pairs_from_experiment_dir",
    "load_pairs_from_manifest",
    "run_aspect_trace_plots",
    "build_parser",
    "main",
]
