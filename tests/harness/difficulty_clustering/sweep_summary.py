from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_sweep_summary(path: str | Path) -> dict[str, Any]:
    summary_path = Path(path).expanduser()
    if summary_path.is_dir():
        raise FileNotFoundError(f"Expected a summary file, got directory: {summary_path}")
    if not summary_path.is_file():
        raise FileNotFoundError(f"Sweep summary file not found: {summary_path}")
    if summary_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(summary_path.read_text())
    else:
        payload = json.loads(summary_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Sweep summary must decode to an object: {summary_path}")
    return payload


def summarize_sweep(path: str | Path, top_n: int = 5) -> dict[str, Any]:
    payload = load_sweep_summary(path)
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Sweep summary payload must contain a list-valued 'results' field.")
    frame = pd.DataFrame(results)
    if frame.empty:
        return {"top_n": top_n, "row_count": 0, "top_rows": []}
    if "silhouette" in frame.columns:
        frame = frame.sort_values("silhouette", ascending=False)
    top_rows = frame.head(max(1, int(top_n))).to_dict(orient="records")
    return {"top_n": int(top_n), "row_count": int(len(frame)), "top_rows": top_rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a compact clustering sweep summary.")
    parser.add_argument("summary_file", type=Path)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args(argv)

    print(json.dumps(summarize_sweep(args.summary_file, top_n=args.top_n), indent=2, sort_keys=True))
    return 0
