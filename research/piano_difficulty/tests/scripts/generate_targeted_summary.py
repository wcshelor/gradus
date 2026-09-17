#!/usr/bin/env python3
import csv, json, pathlib, yaml
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GRID_ROOT = REPO_ROOT / "tests/artifacts/difficulty_prediction/comparisons/targeted_grid"
OUT = REPO_ROOT / "tests/artifacts/difficulty_prediction/feature_set_comparison_summary.csv"
rows=[]
for p in GRID_ROOT.iterdir():
    if not p.is_dir(): continue
    mpath = p/"metrics.json"
    rpath = p/"resolved_config.yaml"
    if not mpath.exists(): continue
    m=json.loads(mpath.read_text())
    r=yaml.safe_load(rpath.read_text())
    overall=m.get("overall_metrics",{})
    params=r.get("model_parameters",{})
    prep=r.get("preprocessing",{})
    rows.append({
        "dataset": m.get("dataset_name"),
        "feature_set": m.get("feature_set"),
        "feature_set_label": p.name.split("__")[-1].replace("-","_"),
        "target_column": m.get("target_column"),
        "target_scheme": r.get("target_scheme",{}).get("kind"),
        "bins": r.get("target_scheme",{}).get("bins"),
        "labels": str(r.get("target_scheme",{}).get("labels")),
        "model_family": m.get("model_family"),
        "model_params": str(params),
        "alpha": params.get("alpha",""),
        "preprocessing_drop_sparse": prep.get("drop_sparse_duration_ratio"),
        "preprocessing_winsor": prep.get("winsorize"),
        "preprocessing_nzv": prep.get("drop_near_zero_variance"),
        "analyzed_row_count": m.get("analyzed_row_count"),
        "selected_columns": len(m.get("feature_selection",{}).get("selected_columns",[])),
        "r2": overall.get("r2"),
        "pearson": overall.get("pearson"),
        "spearman": overall.get("spearman"),
        "mae": overall.get("mae"),
        "rmse": overall.get("rmse"),
        "accuracy": overall.get("accuracy"),
        "balanced_accuracy": overall.get("balanced_accuracy"),
        "macro_f1": overall.get("macro_f1"),
        "mean_absolute_class_error": overall.get("mean_absolute_class_error"),
        "off_by_one_accuracy": overall.get("off_by_one_accuracy"),
        "run_dir": str(p),
    })
rows.sort(key=lambda x: (x["dataset"], x["feature_set"], str(x["model_family"]), str(x["alpha"])))
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to {OUT}")
# Print summary
for ds in ["oktav","cipi"]:
    print(f"\n=== {ds} regression top ===")
    reg=[r for r in rows if r["dataset"]==ds and r["target_scheme"]=="continuous"]
    reg_sorted=sorted([r for r in reg if r["r2"] is not None], key=lambda x: float(x["r2"]) if x["r2"] not in [None,""] else -999, reverse=True)
    for r in reg_sorted[:6]:
        print(f"{r['feature_set']:25} {r['model_family']:25} alpha={str(r['alpha']):5} r2={r['r2']:.4f} pearson={r['pearson']:.3f} rmse={r['rmse']:.2f} prep_drop_sparse={r['preprocessing_drop_sparse']} winsor={r['preprocessing_winsor']}")
    print(f"\n=== {ds} 3-bin classification ===")
    cls=[r for r in rows if r["dataset"]==ds and r["target_scheme"]=="quantile_bins"]
    for r in sorted(cls, key=lambda x: float(x["balanced_accuracy"] or 0), reverse=True)[:6]:
        print(f"{r['feature_set']:25} {r['model_family']:25} bal_acc={r['balanced_accuracy']:.3f} macro_f1={r['macro_f1']:.3f}")
if any(r["target_scheme"]=="custom_bins" for r in rows):
    print("\n=== CIPI 9-bin ===")
    cls9=[r for r in rows if r["target_scheme"]=="custom_bins"]
    for r in sorted(cls9, key=lambda x: float(x["balanced_accuracy"] or 0), reverse=True):
        print(f"{r['feature_set']:25} {r['model_family']:25} bal_acc={r['balanced_accuracy']:.3f}")
