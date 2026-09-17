from __future__ import annotations
import pandas as pd
import json, yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction"

# Identify main ridge runs - most recent
def find_main_ridge(dataset: str) -> Path | None:
    root = ARTIFACT_ROOT / dataset
    candidates = list(root.glob("*__*runtime-ridge-regression"))
    # Filter to those with metrics.json
    candidates = [p for p in candidates if (p / "metrics.json").is_file()]
    if not candidates:
        return None
    # Pick latest by name (timestamp prefix)
    candidates = sorted(candidates)
    # Prefer runtime_all over no_expression
    for c in reversed(candidates):
        rc = yaml.safe_load((c / "resolved_config.yaml").read_text()) or {}
        if rc.get("feature_set") == "runtime_all":
            return c
    return candidates[-1]

def error_table_for_run(run_dir: Path, dataset: str, top_n: int = 10):
    pred_path = run_dir / "predictions.csv"
    if not pred_path.is_file():
        return None
    df = pd.read_csv(pred_path)
    # Expected columns from evaluation: actual_raw_value, predicted_model_value, absolute_error, plus id columns
    # Compute error = predicted - actual
    df["error"] = df["predicted_model_value"] - df["actual_raw_value"]
    # Sort
    over = df.sort_values("error", ascending=False).head(top_n)
    under = df.sort_values("error", ascending=True).head(top_n)
    largest = df.sort_values("absolute_error", ascending=False).head(top_n)
    # Tag
    over = over.assign(error_type="overpredicted")
    under = under.assign(error_type="underpredicted")
    largest = largest.assign(error_type="largest_abs")
    combined = pd.concat([over, under, largest], ignore_index=True)
    # Keep relevant columns if present
    cols = []
    for c in ["error_type", "source_index", "filename", "dataset_relative_path", "title", "composer", "actual_raw_value", "actual_model_value", "predicted_model_value", "absolute_error", "error", "fold"]:
        if c in combined.columns:
            cols.append(c)
    # Add any id columns not yet included
    for c in combined.columns:
        if c not in cols and c not in ["error_type"]:
            # include piece_uid etc if present
            if c in ["piece_uid", "piece_id", "dataset_relative_path", "composer", "title"]:
                cols.append(c)
    # Ensure uniqueness
    cols = [c for c in cols if c in combined.columns]
    # Also add piece lookup from matrix if title/composer missing
    # Try to enrich via matrix if needed
    if "title" not in combined.columns or combined["title"].isna().all():
        # Load matrix to get title/composer for filename
        try:
            rc = yaml.safe_load((run_dir / "resolved_config.yaml").read_text()) or {}
            matrix_path = Path(rc.get("input_matrix_path", ""))
            if matrix_path.is_file():
                mdf = pd.read_csv(matrix_path, usecols=lambda x: x in ["filename", "title", "composer", "dataset_relative_path", "source_row_index", "henle", "difficulty_numeric"])
                # Merge on filename or source_index
                combined = combined.merge(mdf, on="filename", how="left", suffixes=("", "_matrix"))
        except Exception as e:
            print(f"enrich failed {e}")
    combined = combined[cols] if cols else combined
    combined["run_dir"] = str(run_dir)
    combined["dataset"] = dataset
    return combined

def main():
    outputs = []
    for ds in ["oktav", "cipi"]:
        run_dir = find_main_ridge(ds)
        if run_dir is None:
            print(f"No ridge run for {ds}")
            continue
        print(f"Error analysis for {ds} -> {run_dir}")
        tbl = error_table_for_run(run_dir, ds, top_n=10)
        if tbl is not None:
            outputs.append(tbl)
    if not outputs:
        print("No tables")
        return
    full = pd.concat(outputs, ignore_index=True)
    # Reorder columns: dataset first
    cols = ["dataset", "error_type", "filename", "dataset_relative_path", "title", "composer", "actual_raw_value", "predicted_model_value", "absolute_error", "error", "fold", "source_index", "run_dir"]
    cols = [c for c in cols if c in full.columns]
    full = full[cols]
    out_path = ARTIFACT_ROOT / "label_validation_errors.csv"
    full.to_csv(out_path, index=False)
    print(f"Wrote {len(full)} rows to {out_path}")
    print(full.head(20).to_string())

if __name__ == "__main__":
    main()
