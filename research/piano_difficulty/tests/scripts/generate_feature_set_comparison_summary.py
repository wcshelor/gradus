#!/usr/bin/env python3
"""Generate feature_set_comparison_summary.csv from gap_grid runs."""
import csv
import json
import pathlib
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GAP_GRID_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "comparisons" / "gap_grid"
OUTPUT_CSV = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "feature_set_comparison_summary.csv"

def collect():
    rows = []
    for run_dir in GAP_GRID_ROOT.iterdir():
        if not run_dir.is_dir():
            continue
        metrics_path = run_dir / "metrics.json"
        resolved_path = run_dir / "resolved_config.yaml"
        if not metrics_path.exists() or not resolved_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text())
        resolved = yaml.safe_load(resolved_path.read_text())
        overall = metrics.get("overall_metrics", {})
        model_params = resolved.get("model_parameters", {})
        preprocessing = resolved.get("preprocessing", {})
        # Determine hygiene variant from preprocessing
        prep_str = f"drop_sparse={preprocessing.get('drop_sparse_duration_ratio')},nzv={preprocessing.get('drop_near_zero_variance')},winsor={preprocessing.get('winsorize')}"
        rows.append({
            "dataset": metrics.get("dataset_name"),
            "target_column": metrics.get("target_column"),
            "target_scheme": str(metrics.get("target_scheme", {}).get("kind")),
            "feature_set": metrics.get("feature_set"),
            "model_family": metrics.get("model_family"),
            "model_params": str(model_params),
            "alpha": model_params.get("alpha", ""),
            "preprocessing": prep_str,
            "run_dir": str(run_dir),
            "analyzed_row_count": metrics.get("analyzed_row_count"),
            "selected_columns": len(metrics.get("feature_selection", {}).get("selected_columns", [])),
            "r2": overall.get("r2", ""),
            "pearson": overall.get("pearson", ""),
            "spearman": overall.get("spearman", ""),
            "mae": overall.get("mae", ""),
            "rmse": overall.get("rmse", ""),
            "accuracy": overall.get("accuracy", ""),
            "balanced_accuracy": overall.get("balanced_accuracy", ""),
            "macro_f1": overall.get("macro_f1", ""),
            "mean_absolute_class_error": overall.get("mean_absolute_class_error", ""),
            "off_by_one_accuracy": overall.get("off_by_one_accuracy", ""),
        })
    # sort
    rows.sort(key=lambda r: (r["dataset"], r["feature_set"], r["model_family"], str(r["alpha"])))
    return rows

if __name__ == "__main__":
    rows = collect()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        print(f"No rows found in {GAP_GRID_ROOT}")
    else:
        fieldnames = list(rows[0].keys())
        with OUTPUT_CSV.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
        # print top per dataset
        for ds in ["oktav", "cipi"]:
            ds_rows = [r for r in rows if r["dataset"]==ds and r["target_scheme"]=="continuous"]
            # sort by r2 descending
            def _r2(r):
                try:
                    return float(r["r2"])
                except:
                    return -999
            ds_rows_sorted = sorted(ds_rows, key=_r2, reverse=True)
            print(f"\nTop 5 regression r2 for {ds}:")
            for r in ds_rows_sorted[:5]:
                print(f"  {r['feature_set']} {r['model_family']} alpha={r['alpha']} r2={r['r2']:.4f} pearson={r['pearson']} rmse={r['rmse']}")
