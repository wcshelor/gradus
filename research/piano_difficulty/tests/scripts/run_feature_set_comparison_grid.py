#!/usr/bin/env python3
"""Run controlled comparison grid for predictive gap experiment.

Gathers metrics across feature sets and regularized models for Oktav and CIPI,
writing summary to tests/artifacts/difficulty_prediction/feature_set_comparison_summary.csv

This is harness-first work; no runtime extraction is changed.
"""
import csv
import pathlib
import sys
import time
from pathlib import Path

# Ensure repo root on path when executed directly
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tests.harness.difficulty_prediction.core import ExperimentConfig, TargetSchemeConfig, PreprocessingConfig
from tests.harness.difficulty_prediction.runner import run_experiment

# Matrices
RUNTIME_MATRICES = {
    "oktav": REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "python_analysis" / "full_run" / "oktav_labeled_feature_matrix.csv",
    "cipi": REPO_ROOT / "tests" / "artifacts" / "cipi_dataset" / "python_analysis" / "full_run" / "cipi_labeled_feature_matrix.csv",
}
YAN_MATRICES = {
    "oktav": REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "comparisons" / "20260722T183351Z__yan2023-cipi-vs-oktav" / "matrices" / "oktav_yan_labeled_features.csv",
    "cipi": REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "comparisons" / "20260722T183351Z__yan2023-cipi-vs-oktav" / "matrices" / "cipi_yan_labeled_features.csv",
}

OUTPUT_CSV = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "feature_set_comparison_summary.csv"
RUNS_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "comparisons" / "gap_grid"

FEATURE_SETS_RUNTIME = [
    "runtime_all",
    "runtime_core_no_expression",
    "runtime_core_no_sparse",
    "runtime_motor_texture",
    "runtime_yan_overlap",
]
FEATURE_SETS_YAN = ["yan2023_observed", "yan2023_observed_no_blocked"]

TARGETS = {
    "oktav": ("difficulty_numeric", TargetSchemeConfig(kind="continuous")),
    "cipi": ("henle", TargetSchemeConfig(kind="continuous")),
}
TARGETS_CLASS_3BIN = {
    "oktav": ("difficulty_numeric", TargetSchemeConfig(kind="quantile_bins", bins=3)),
    "cipi": ("henle", TargetSchemeConfig(kind="quantile_bins", bins=3)),
}
TARGETS_CLASS_9BIN_CIPI = ("henle", TargetSchemeConfig(kind="custom_bins", bin_edges=(0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5), labels=(1,2,3,4,5,6,7,8,9)))

REGRESSION_SWEEP = [
    ("dummy_regression", {"strategy": "mean"}),
    ("ridge_regression", {"alpha": 0.1}),
    ("ridge_regression", {"alpha": 1.0}),
    ("ridge_regression", {"alpha": 10.0}),
    ("ridge_regression", {"alpha": 100.0}),
    ("ridge_regression", {"alpha": 1000.0}),
    ("elasticnet", {"alpha": 0.01, "l1_ratio": 0.5}),
    ("elasticnet", {"alpha": 0.1, "l1_ratio": 0.5}),
    ("random_forest_regression", {"n_estimators": 200, "max_depth": 8}),
    ("gradient_boosting_regression", {"n_estimators": 100, "max_depth": 3}),
]

# Hygiene variants for runtime_all
HYGIENE_VARIANTS = [
    ("clean_sparse", PreprocessingConfig(imputer_strategy="median", scaler="standard", drop_sparse_duration_ratio=True)),
    ("clean_sparse_nzv", PreprocessingConfig(imputer_strategy="median", scaler="standard", drop_sparse_duration_ratio=True, drop_near_zero_variance=True, near_zero_variance_threshold=1e-9)),
    ("clean_sparse_winsor", PreprocessingConfig(imputer_strategy="median", scaler="standard", drop_sparse_duration_ratio=True, winsorize=True, winsorize_lower_quantile=0.01, winsorize_upper_quantile=0.99)),
]

CLASSIFICATION_MODELS = [
    ("dummy_classifier", {"strategy": "most_frequent"}),
    ("logistic_regression", {}),
    ("random_forest_classifier", {"n_estimators": 200, "max_depth": 8}),
]

def _run_one(dataset, feature_set, target_col, target_scheme, model_family, model_params, preprocessing, id_columns=("source_row_index","filename","dataset_relative_path")):
    # choose matrix
    if feature_set in FEATURE_SETS_YAN:
        matrix_path = YAN_MATRICES[dataset]
    else:
        matrix_path = RUNTIME_MATRICES[dataset]
    cfg = ExperimentConfig(
        experiment_name=f"{dataset}-{feature_set}-{model_family}-{target_scheme.kind}",
        dataset_name=dataset,
        input_matrix_path=matrix_path,
        id_columns=tuple(id_columns),
        target_column=target_col,
        target_scheme=target_scheme,
        feature_set=feature_set,
        preprocessing=preprocessing,
        model_family=model_family,
        model_parameters=dict(model_params),
    )
    try:
        result = run_experiment(cfg, runs_root=RUNS_ROOT)
        metrics = result.metrics.get("overall_metrics", {})
        return {
            "dataset": dataset,
            "target_column": target_col,
            "target_scheme": target_scheme.kind + (f":{target_scheme.bins}bins" if target_scheme.bins else ("_9bin" if target_scheme.labels and len(target_scheme.labels)==9 else "")),
            "feature_set": feature_set,
            "model_family": model_family,
            "model_params": str(dict(model_params)),
            "preprocessing": f"imputer={preprocessing.imputer_strategy},scaler={preprocessing.scaler},drop_sparse={preprocessing.drop_sparse_duration_ratio},nzv={preprocessing.drop_near_zero_variance},winsor={preprocessing.winsorize}",
            "run_dir": str(result.run_dir),
            "analyzed_row_count": result.metrics.get("analyzed_row_count"),
            "selected_columns_count": len(result.feature_selection_report.selected_columns),
            "r2": metrics.get("r2"),
            "pearson": metrics.get("pearson"),
            "spearman": metrics.get("spearman"),
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "accuracy": metrics.get("accuracy"),
            "balanced_accuracy": metrics.get("balanced_accuracy"),
            "macro_f1": metrics.get("macro_f1"),
            "mean_absolute_class_error": metrics.get("mean_absolute_class_error"),
            "off_by_one_accuracy": metrics.get("off_by_one_accuracy"),
            "status": "ok",
            "error": "",
        }
    except Exception as e:
        return {
            "dataset": dataset,
            "target_column": target_col,
            "target_scheme": target_scheme.kind,
            "feature_set": feature_set,
            "model_family": model_family,
            "model_params": str(dict(model_params)),
            "preprocessing": str(preprocessing),
            "run_dir": "",
            "analyzed_row_count": "",
            "selected_columns_count": "",
            "r2": "",
            "pearson": "",
            "spearman": "",
            "mae": "",
            "rmse": "",
            "accuracy": "",
            "balanced_accuracy": "",
            "macro_f1": "",
            "mean_absolute_class_error": "",
            "off_by_one_accuracy": "",
            "status": "error",
            "error": str(e)[:500],
        }

def main():
    rows = []
    # Regression grid
    for dataset in ["oktav", "cipi"]:
        target_col, target_scheme = TARGETS[dataset]
        for feature_set in FEATURE_SETS_RUNTIME + FEATURE_SETS_YAN:
            # Skip yan no_blocked duplicate for runtime matrix? It uses same yan matrix, so it will succeed but duplicate. Keep one for now.
            if feature_set == "yan2023_observed_no_blocked" and dataset == "oktav":
                # limit to one to reduce duplicate
                pass
            for model_family, model_params in REGRESSION_SWEEP:
                # Hygiene variants only for runtime_all with ridge alpha 10/100 to answer question 1
                # For standard sweep, use standard preprocessing
                preprocessing = PreprocessingConfig(imputer_strategy="median", scaler="standard")
                row = _run_one(dataset, feature_set, target_col, target_scheme, model_family, model_params, preprocessing)
                rows.append(row)
                print(f"REG {dataset} {feature_set} {model_family} {model_params} -> r2={row.get('r2')} status={row['status']}")
        # Hygiene specific
        for variant_name, prep in HYGIENE_VARIANTS:
            for alpha in [1.0, 10.0, 100.0]:
                row = _run_one(dataset, "runtime_all", target_col, target_scheme, "ridge_regression", {"alpha": alpha}, prep)
                row["feature_set"] = f"runtime_all__{variant_name}"
                rows.append(row)
                print(f"HYGIENE {dataset} {variant_name} alpha={alpha} -> r2={row.get('r2')}")

    # Classification 3-bin
    for dataset in ["oktav", "cipi"]:
        target_col, target_scheme = TARGETS_CLASS_3BIN[dataset]
        for feature_set in FEATURE_SETS_RUNTIME + ["yan2023_observed"]:
            for model_family, model_params in CLASSIFICATION_MODELS:
                preprocessing = PreprocessingConfig(imputer_strategy="median", scaler="standard")
                # RF doesn't need scaler, but keep standard; models.py handles scaler only for linear families
                row = _run_one(dataset, feature_set, target_col, target_scheme, model_family, model_params, preprocessing)
                rows.append(row)
                print(f"CLS3 {dataset} {feature_set} {model_family} -> bal_acc={row.get('balanced_accuracy')}")

    # CIPI 9-bin logistic
    dataset = "cipi"
    target_col, target_scheme = TARGETS_CLASS_9BIN_CIPI
    for feature_set in FEATURE_SETS_RUNTIME + ["yan2023_observed"]:
        for model_family, model_params in [("dummy_classifier", {"strategy": "most_frequent"}), ("logistic_regression", {}), ("random_forest_classifier", {"n_estimators": 200, "max_depth": 8})]:
            preprocessing = PreprocessingConfig(imputer_strategy="median", scaler="standard")
            row = _run_one(dataset, feature_set, target_col, target_scheme, model_family, model_params, preprocessing)
            rows.append(row)
            print(f"CLS9 {dataset} {feature_set} {model_family} -> bal_acc={row.get('balanced_accuracy')}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")

    # Also write a concise summary sorted by r2 for regression
    # Find best per dataset/feature_set
    import pandas as pd
    df = pd.read_csv(OUTPUT_CSV)
    print(df.head())

if __name__ == "__main__":
    main()
