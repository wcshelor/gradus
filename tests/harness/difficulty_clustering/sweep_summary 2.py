from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_sweep_summary(path: str | Path) -> dict[str, Any]:
    summary_path = Path(path).expanduser()
    if summary_path.is_dir():
        candidate = summary_path / "sweep_summary.json"
        if candidate.is_file():
            summary_path = candidate
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)

    if summary_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Sweep summary '{summary_path}' must contain a mapping.")
    return payload


def summarize_sweep(path: str | Path, *, top_n: int = 3) -> dict[str, Any]:
    summary = load_sweep_summary(path)
    candidate_rows = summary.get("candidate_rows", [])
    if not isinstance(candidate_rows, list):
        raise ValueError("Sweep summary candidate_rows must be a list.")

    frame = pd.DataFrame(candidate_rows)
    if frame.empty:
        return {
            "sweep_dir": summary.get("sweep_dir", ""),
            "selection_metric": summary.get("selection_metric", ""),
            "selection_goal": summary.get("selection_goal", ""),
            "best_k": summary.get("best_k", None),
            "best_run_dir": summary.get("best_run_dir", ""),
            "top_candidates": [],
            "candidate_count": 0,
        }

    if "selection_rank" in frame.columns:
        ordered = frame.sort_values(["selection_rank", "k"], na_position="last")
    elif "selection_score" in frame.columns:
        goal = str(summary.get("selection_goal", "maximize")).strip().lower()
        ordered = frame.sort_values(
            ["selection_score", "k"],
            ascending=[goal != "maximize", True],
            na_position="last",
        )
    else:
        ordered = frame.sort_values("k")

    top_candidates = ordered.head(max(int(top_n), 0)).to_dict(orient="records")
    return {
        "sweep_dir": summary.get("sweep_dir", ""),
        "selection_metric": summary.get("selection_metric", ""),
        "selection_goal": summary.get("selection_goal", ""),
        "best_k": summary.get("best_k", None),
        "best_run_dir": summary.get("best_run_dir", ""),
        "top_candidates": top_candidates,
        "candidate_count": int(len(frame)),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="print_difficulty_clustering_sweep_summary",
        description="Print the best k and top sweep candidates from a clustering sweep summary.",
    )
    parser.add_argument("summary", type=Path, help="Path to sweep_summary.json or the sweep directory.")
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of ranked candidates to include in the printed output.",
    )
    args = parser.parse_args(argv)

    payload = summarize_sweep(args.summary, top_n=args.top_n)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
