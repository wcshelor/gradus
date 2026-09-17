#!/usr/bin/env python3
import pathlib, sys
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from tests.harness.difficulty_prediction.core import ExperimentConfig, TargetSchemeConfig, PreprocessingConfig
from tests.harness.difficulty_prediction.runner import run_experiment
from pathlib import Path

RUNTIME_MAT = {
    "oktav": REPO_ROOT / "tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv",
    "cipi": REPO_ROOT / "tests/artifacts/cipi_dataset/python_analysis/full_run/cipi_labeled_feature_matrix.csv",
}
YAN_MAT = {
    "oktav": REPO_ROOT / "tests/artifacts/difficulty_prediction/comparisons/20260722T183351Z__yan2023-cipi-vs-oktav/matrices/oktav_yan_labeled_features.csv",
    "cipi": REPO_ROOT / "tests/artifacts/difficulty_prediction/comparisons/20260722T183351Z__yan2023-cipi-vs-oktav/matrices/cipi_yan_labeled_features.csv",
}
RUNS_ROOT = REPO_ROOT / "tests/artifacts/difficulty_prediction/comparisons/targeted_grid"
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

def run_one(dataset, feature_set, target_col, scheme, model_family, params, prep, run_name):
    mat = YAN_MAT[dataset] if feature_set.startswith("yan") else RUNTIME_MAT[dataset]
    cfg = ExperimentConfig(
        experiment_name=run_name,
        dataset_name=dataset,
        input_matrix_path=mat,
        id_columns=("source_row_index","filename","dataset_relative_path"),
        target_column=target_col,
        target_scheme=scheme,
        feature_set=feature_set,
        preprocessing=prep,
        model_family=model_family,
        model_parameters=params,
    )
    res = run_experiment(cfg, runs_root=RUNS_ROOT)
    m = res.metrics["overall_metrics"]
    print(f"{run_name}: r2={m.get('r2')} pearson={m.get('pearson')} bal_acc={m.get('balanced_accuracy')} r2? {m.get('r2')}")
    return res

# Clean preprocessing
clean = PreprocessingConfig(imputer_strategy="median", scaler="standard", drop_sparse_duration_ratio=True, drop_near_zero_variance=True)
clean_winsor = PreprocessingConfig(imputer_strategy="median", scaler="standard", drop_sparse_duration_ratio=True, winsorize=True)
std = PreprocessingConfig(imputer_strategy="median", scaler="standard")

# Regression targeted
for ds in ["oktav","cipi"]:
    target_col, scheme = ("difficulty_numeric", TargetSchemeConfig(kind="continuous")) if ds=="oktav" else ("henle", TargetSchemeConfig(kind="continuous"))
    # runtime_all standard
    for alpha in [1.0,10.0,100.0]:
        run_one(ds, "runtime_all", target_col, scheme, "ridge_regression", {"alpha": alpha}, std, f"{ds}-runtime_all-ridge-{alpha}")
    # runtime_all clean
    for alpha in [1.0,10.0,100.0]:
        run_one(ds, "runtime_all", target_col, scheme, "ridge_regression", {"alpha": alpha}, clean, f"{ds}-runtime_all-clean-ridge-{alpha}")
        run_one(ds, "runtime_all", target_col, scheme, "ridge_regression", {"alpha": alpha}, clean_winsor, f"{ds}-runtime_all-cleanwinsor-ridge-{alpha}")
    # core sets
    for fs in ["runtime_core_no_sparse","runtime_core_no_expression","runtime_motor_texture","runtime_yan_overlap"]:
        for alpha in [10.0,100.0]:
            run_one(ds, fs, target_col, scheme, "ridge_regression", {"alpha": alpha}, std, f"{ds}-{fs}-ridge-{alpha}")
    # yan
    for fs in ["yan2023_observed"]:
        for alpha in [1.0,10.0,100.0]:
            run_one(ds, fs, target_col, scheme, "ridge_regression", {"alpha": alpha}, std, f"{ds}-{fs}-ridge-{alpha}")
    # also elasticnet and RF for best
    run_one(ds, "runtime_all", target_col, scheme, "elasticnet", {"alpha":0.1,"l1_ratio":0.5}, clean, f"{ds}-runtime_all-clean-elasticnet")
    run_one(ds, "runtime_yan_overlap", target_col, scheme, "random_forest_regression", {"n_estimators":200,"max_depth":8}, std, f"{ds}-yan_overlap-rf")
    run_one(ds, "yan2023_observed", target_col, scheme, "random_forest_regression", {"n_estimators":200,"max_depth":8}, std, f"{ds}-yan-rf")
    # classification 3-bin
    scheme3 = TargetSchemeConfig(kind="quantile_bins", bins=3)
    target3 = target_col
    for fs in ["runtime_all","runtime_yan_overlap","yan2023_observed","runtime_core_no_sparse"]:
        for mf, mp in [("logistic_regression",{}), ("random_forest_classifier",{"n_estimators":200,"max_depth":8})]:
            run_one(ds, fs, target3, scheme3, mf, mp, std, f"{ds}-{fs}-{mf}-3bin")
# cipi 9-bin
for fs in ["runtime_all","runtime_yan_overlap","yan2023_observed","runtime_core_no_sparse"]:
    for mf, mp in [("logistic_regression",{}), ("random_forest_classifier",{"n_estimators":200,"max_depth":8})]:
        run_one("cipi", fs, "henle", TargetSchemeConfig(kind="custom_bins", bin_edges=(0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5), labels=(1,2,3,4,5,6,7,8,9)), mf, mp, std, f"cipi-{fs}-{mf}-9bin")

print("Done targeted")
