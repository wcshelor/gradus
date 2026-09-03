from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .align_rows import align_rows


def summarize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append(
            {
                "feature": col,
                "mean": float(np.nanmean(s)),
                "std": float(np.nanstd(s)),
                "min": float(np.nanmin(s)),
                "max": float(np.nanmax(s)),
            }
        )
    return pd.DataFrame(rows)


def compare_feature_frames(
    ours: pd.DataFrame,
    reference: pd.DataFrame,
    report_dir: str | Path,
    prefix: str,
) -> dict[str, object]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    common = [c for c in ours.columns if c in reference.columns]
    ours_num = ours[common].apply(pd.to_numeric, errors="coerce") if common else pd.DataFrame()
    ref_num = reference[common].apply(pd.to_numeric, errors="coerce") if common else pd.DataFrame()

    ours_summary = summarize_columns(ours_num) if not ours_num.empty else pd.DataFrame()
    ref_summary = summarize_columns(ref_num) if not ref_num.empty else pd.DataFrame()
    if not ours_summary.empty:
        ours_summary.to_csv(report_path / f"{prefix}_ours_summary.csv", index=False)
    if not ref_summary.empty:
        ref_summary.to_csv(report_path / f"{prefix}_reference_summary.csv", index=False)

    aligned_ours, aligned_ref, aligned = align_rows(ours_num, ref_num) if common else (pd.DataFrame(), pd.DataFrame(), False)
    pairwise = []
    if common and not aligned_ours.empty:
        for c in common:
            a = aligned_ours[c]
            b = aligned_ref[c]
            abs_err = np.nanmean(np.abs(a - b))
            corr = np.corrcoef(a.fillna(0), b.fillna(0))[0, 1] if len(a) > 1 else np.nan
            pairwise.append({"feature": c, "mae": float(abs_err), "corr": float(corr)})
        pd.DataFrame(pairwise).to_csv(report_path / f"{prefix}_pairwise.csv", index=False)

    return {
        "common_features": common,
        "row_alignment_known": aligned,
        "report_dir": str(report_path),
        "pairwise_count": len(pairwise),
    }
