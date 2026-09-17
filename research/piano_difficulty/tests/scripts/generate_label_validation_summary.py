from __future__ import annotations
import json
import csv
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction"
OUTPUT_CSV = ARTIFACT_ROOT / "label_validation_summary.csv"

def target_scheme_label(scheme: dict) -> str:
    kind = str(scheme.get("kind", "unknown"))
    if kind == "quantile_bins":
        return f"{kind}:{scheme.get('bins')}"
    if kind == "custom_bins":
        labels = scheme.get("labels")
        if isinstance(labels, list):
            return f"{kind}:{len(labels)}"
        return kind
    return kind

def collect_runs():
    roots = [ARTIFACT_ROOT / "oktav", ARTIFACT_ROOT / "cipi"]
    # Also include comparisons? Not needed.
    run_dirs = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.glob("20260916T*"):
            if (p / "metrics.json").is_file() and (p / "resolved_config.yaml").is_file():
                run_dirs.append(p)
    # also check any other recent runs: include all with metrics if not filtered? For now filter to 20260916*
    # Sort by dataset and experiment
    run_dirs = sorted(run_dirs)
    return run_dirs

def main():
    run_dirs = collect_runs()
    rows = []
    # Build lookup for baseline
    # Baseline mapping: (dataset, target_scheme_label, kind) -> baseline run
    baselines = {}
    for rd in run_dirs:
        rc = yaml.safe_load((rd / "resolved_config.yaml").read_text()) or {}
        metrics = json.loads((rd / "metrics.json").read_text())
        model_family = rc.get("model_family", "")
        if "dummy" in model_family:
            key = (rc.get("dataset_name"), target_scheme_label(rc.get("target_scheme", {})), rc.get("target_column"))
            baselines[key] = (rd, metrics, rc)
    for rd in run_dirs:
        rc = yaml.safe_load((rd / "resolved_config.yaml").read_text()) or {}
        metrics = json.loads((rd / "metrics.json").read_text())
        overall = metrics.get("overall_metrics", {})
        target_scheme = rc.get("target_scheme", {})
        dataset = rc.get("dataset_name")
        target = rc.get("target_column")
        feature_set = rc.get("feature_set")
        model_family = rc.get("model_family")
        primary_metric = metrics.get("primary_metric")
        # Determine baseline for this group
        key = (dataset, target_scheme_label(target_scheme), target)
        baseline = baselines.get(key)
        baseline_run_dir = ""
        lift = ""
        if baseline is not None:
            b_rd, b_metrics, b_rc = baseline
            if str(b_rd) != str(rd):
                baseline_run_dir = str(b_rd)
                # compute lift based on primary_metric
                b_overall = b_metrics.get("overall_metrics", {})
                if primary_metric and primary_metric in overall and primary_metric in b_overall:
                    try:
                        lift_val = float(overall[primary_metric]) - float(b_overall[primary_metric])
                        lift = f"{lift_val:.4f}"
                    except Exception:
                        lift = ""
        row = {
            "dataset": dataset,
            "target": target,
            "target_scheme": target_scheme_label(target_scheme),
            "feature_set": feature_set,
            "model_family": model_family,
            "run_dir": str(rd),
            "primary_metric": primary_metric,
            "r2": overall.get("r2", ""),
            "pearson": overall.get("pearson", ""),
            "spearman": overall.get("spearman", ""),
            "mae": overall.get("mae", ""),
            "rmse": overall.get("rmse", ""),
            "balanced_accuracy": overall.get("balanced_accuracy", ""),
            "macro_f1": overall.get("macro_f1", ""),
            "accuracy": overall.get("accuracy", ""),
            "mean_absolute_class_error": overall.get("mean_absolute_class_error", ""),
            "off_by_one_accuracy": overall.get("off_by_one_accuracy", ""),
            "baseline_run_dir": baseline_run_dir,
            "lift_vs_baseline": lift,
            "analyzed_row_count": metrics.get("analyzed_row_count", ""),
            "effective_folds": metrics.get("effective_folds", ""),
        }
        rows.append(row)
    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        print("No runs found")
        return
    fieldnames = ["dataset","target","target_scheme","feature_set","model_family","run_dir","primary_metric","r2","pearson","spearman","mae","rmse","balanced_accuracy","macro_f1","accuracy","mean_absolute_class_error","off_by_one_accuracy","baseline_run_dir","lift_vs_baseline","analyzed_row_count","effective_folds"]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
    for r in rows:
        print(r["dataset"], r["target_scheme"], r["feature_set"], r["model_family"], "r2", r["r2"], "bal_acc", r["balanced_accuracy"], "lift", r["lift_vs_baseline"])

if __name__ == "__main__":
    main()
