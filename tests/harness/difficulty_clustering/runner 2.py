from __future__ import annotations

import json
import os
import unicodedata
import warnings
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_MPLCONFIGDIR = Path(__file__).resolve().parents[3] / "tests" / "artifacts" / "difficulty_clustering" / ".mplconfig"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
warnings.filterwarnings(
    "ignore",
    message="Could not find the number of physical cores for the following reason:",
    category=UserWarning,
)

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import yaml
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from tests.harness.shared.matrix_data import load_dataset_matrix
from tests.harness.shared.matrix_features import DEFAULT_METADATA_COLUMNS, select_feature_columns
from tests.harness.cipi_dataset.catalog import DEFAULT_CATALOG_CSV, load_catalog_dataframe

from .config import load_experiment_config
from .core import DEFAULT_RUNS_ROOT, ClusterSweepResult, ExperimentConfig, ExperimentRunResult


def run_experiment_from_config(
    config: str | Path | ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult | ClusterSweepResult:
    experiment = config if isinstance(config, ExperimentConfig) else load_experiment_config(config)
    if experiment.sweep.enabled:
        return run_cluster_sweep(experiment, runs_root=runs_root)
    return run_experiment(experiment, runs_root=runs_root)


def run_experiment(
    config: ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    return _run_single_experiment(config, runs_root=runs_root)


def run_cluster_sweep(
    config: ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ClusterSweepResult:
    k_values = _resolve_sweep_k_values(config)
    runs_root_path = Path(runs_root).expanduser()
    sweep_root = _allocate_sweep_root(runs_root_path, config)
    sweep_root.mkdir(parents=True, exist_ok=False)

    candidate_rows: list[dict[str, Any]] = []
    candidate_runs: list[ExperimentRunResult] = []
    best_candidate: tuple[float, ExperimentRunResult, dict[str, Any]] | None = None
    metric_name = _resolve_sweep_selection_metric(config.sweep.selection_metric)
    selection_goal = _resolve_selection_goal(config.sweep.selection_goal, metric_name)

    for k in k_values:
        candidate_dir = sweep_root / f"k{k}"
        candidate_config = replace(
            config,
            clustering=replace(config.clustering, n_clusters=k),
            output_options=replace(
                config.output_options,
                run_name=_sweep_run_name(config.output_options.run_name or config.experiment_name, k),
            ),
        )
        result = _run_single_experiment(candidate_config, runs_root=sweep_root, run_dir=candidate_dir)
        candidate_runs.append(result)

        row = _build_sweep_candidate_row(
            result=result,
            k=k,
            metric_name=metric_name,
            selection_goal=selection_goal,
            include_label_metrics=config.sweep.include_label_metrics,
        )
        candidate_rows.append(row)

        score = row.get("selection_score")
        if score is None:
            continue
        if best_candidate is None:
            best_candidate = (float(score), result, row)
            continue
        current_score = float(score)
        best_score = best_candidate[0]
        if selection_goal == "maximize" and current_score > best_score:
            best_candidate = (current_score, result, row)
        elif selection_goal == "minimize" and current_score < best_score:
            best_candidate = (current_score, result, row)

    if not candidate_rows:
        raise ValueError("k sweep produced no candidate rows.")
    if best_candidate is None:
        raise ValueError(
            f"k sweep could not rank any candidates with selection_metric='{metric_name}'."
        )

    summary = _build_sweep_summary(
        config=config,
        sweep_root=sweep_root,
        candidate_rows=candidate_rows,
        best_candidate=best_candidate[2],
        metric_name=metric_name,
        selection_goal=selection_goal,
    )
    summary_path = sweep_root / "sweep_summary.json"
    report_path = sweep_root / "sweep_report.md"
    summary_frame = pd.DataFrame(candidate_rows)
    summary_frame.to_csv(sweep_root / "sweep_summary.csv", index=False)
    _write_json(summary_path, summary)
    report_path.write_text(
        _build_sweep_report(config=config, summary=summary, summary_frame=summary_frame),
        encoding="utf-8",
    )
    _save_sweep_metric_curve(summary_frame, metric_name, selection_goal, sweep_root / "sweep_metric_curve.png")

    return ClusterSweepResult(
        sweep_dir=sweep_root,
        summary_path=summary_path,
        report_path=report_path,
        best_run=best_candidate[1],
        candidate_runs=tuple(candidate_runs),
        summary=summary,
    )


def _run_single_experiment(
    config: ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    run_dir: Path | None = None,
) -> ExperimentRunResult:
    loaded = load_dataset_matrix(config.dataset_name, config.input_matrix_path)
    frame = loaded.frame.copy()
    frame, label_join_diagnostics = _attach_posthoc_label_column(frame, loaded.source_path, config)

    _validate_required_columns(frame, loaded.source_path, config)
    selected_columns, feature_selection_details = _resolve_feature_columns(frame, config)

    modeling_frame, label_series, feature_frame, diagnostics = _prepare_modeling_frame(
        frame=frame,
        selected_columns=selected_columns,
        label_column=config.label_column,
        missing_feature_strategy=config.preprocessing.missing_feature_strategy,
    )
    if modeling_frame.empty:
        raise ValueError("No usable rows remain after feature preprocessing.")

    if config.preprocessing.scaler.strip().lower() != "standard":
        raise ValueError(
            f"Unsupported scaler '{config.preprocessing.scaler}'. Only 'standard' is supported."
        )
    if config.pca.n_components < 2:
        raise ValueError("PCA scatter outputs require pca.n_components >= 2.")
    max_components = min(len(modeling_frame), feature_frame.shape[1])
    if config.pca.n_components > max_components:
        raise ValueError(
            f"Configured pca.n_components={config.pca.n_components} exceeds the usable limit "
            f"of {max_components} for {len(modeling_frame)} rows and {feature_frame.shape[1]} features."
        )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feature_frame)
    pca = PCA(n_components=config.pca.n_components, random_state=config.clustering.random_state)
    coordinates = pca.fit_transform(X_scaled)

    cluster_labels_zero_based, cluster_metadata = _cluster_in_pca_space(
        coordinates=coordinates,
        method=config.clustering.method,
        n_clusters=config.clustering.n_clusters,
        random_state=config.clustering.random_state,
        n_init=config.clustering.n_init,
    )
    cluster_labels = cluster_labels_zero_based + 1

    runs_root_path = Path(runs_root).expanduser()
    runs_root_path.mkdir(parents=True, exist_ok=True)
    if run_dir is None:
        run_dir = _allocate_run_dir(runs_root_path, config)
        run_dir.mkdir(parents=True, exist_ok=False)
    else:
        run_dir.mkdir(parents=True, exist_ok=False)

    component_names = [f"pc_{index}" for index in range(1, config.pca.n_components + 1)]
    coordinate_frame = pd.DataFrame(coordinates, columns=component_names, index=modeling_frame.index)
    assignments = _build_assignments_frame(
        modeling_frame=modeling_frame,
        coordinate_frame=coordinate_frame,
        id_columns=config.id_columns,
        label_column=config.label_column,
        cluster_labels=cluster_labels,
    )

    explained_variance = _build_explained_variance_frame(pca)
    loadings = _build_loadings_frame(pca, feature_frame.columns, component_names)
    cluster_profiles = _build_cluster_profiles(
        assignments=assignments,
        feature_frame=feature_frame,
        standardized_frame=pd.DataFrame(X_scaled, columns=feature_frame.columns, index=feature_frame.index),
        label_column=config.label_column,
        component_names=component_names,
    )
    crosstab = _build_label_crosstab(assignments, label_column=config.label_column)

    resolved_config = _build_resolved_config(
        config=config,
        loaded_path=loaded.source_path,
        run_dir=run_dir,
        selected_columns=selected_columns,
        feature_selection_details=feature_selection_details,
        diagnostics=diagnostics,
        row_count=len(modeling_frame),
    )
    metrics = _build_metrics(
        config=config,
        loaded=loaded,
        assignments=assignments,
        coordinates=coordinates,
        explained_variance=explained_variance,
        diagnostics=diagnostics,
        cluster_metadata=cluster_metadata,
        label_column=config.label_column,
        label_join=label_join_diagnostics,
    )

    resolved_config_path = run_dir / "resolved_config.yaml"
    explained_variance_path = run_dir / "pca_explained_variance.csv"
    loadings_path = run_dir / "pca_loadings.csv"
    coordinates_path = run_dir / "piece_coordinates.csv"
    assignments_path = run_dir / "cluster_assignments.csv"
    profiles_path = run_dir / "cluster_profiles.csv"
    metrics_path = run_dir / "metrics.json"
    report_path = run_dir / "report.md"

    resolved_config_path.write_text(yaml.safe_dump(resolved_config, sort_keys=False), encoding="utf-8")
    explained_variance.to_csv(explained_variance_path, index=False)
    loadings.to_csv(loadings_path, index=False)
    assignments.to_csv(coordinates_path, index=False)
    assignments.loc[:, _assignment_columns(config.id_columns, config.label_column)].to_csv(
        assignments_path,
        index=False,
    )
    cluster_profiles.to_csv(profiles_path, index=False)
    _write_json(metrics_path, metrics)

    if crosstab is not None:
        crosstab.to_csv(run_dir / "cluster_label_crosstab.csv")

    _save_cluster_scatter(assignments, run_dir / "pca_scatter_by_cluster.png")
    if config.label_column and config.label_column in assignments.columns and assignments[config.label_column].notna().any():
        _save_label_scatter(assignments, label_column=config.label_column, path=run_dir / "pca_scatter_by_label.png")
        if pd.api.types.is_numeric_dtype(assignments[config.label_column]):
            _save_difficulty_boxplot(
                assignments,
                label_column=config.label_column,
                path=run_dir / "difficulty_by_cluster_boxplot.png",
            )

    linkage_matrix = None
    if config.clustering.method.strip().lower() in {"ward", "ward_then_kmeans"}:
        linkage_matrix = linkage(coordinates, method="ward")
        _save_dendrogram(linkage_matrix, run_dir / "ward_dendrogram.png")

    report_path.write_text(
        _build_report(
            config=config,
            metrics=metrics,
            explained_variance=explained_variance,
            cluster_profiles=cluster_profiles,
            crosstab=crosstab,
        ),
        encoding="utf-8",
    )

    return ExperimentRunResult(
        run_dir=run_dir,
        resolved_config_path=resolved_config_path,
        metrics_path=metrics_path,
        report_path=report_path,
        metrics=metrics,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="run_difficulty_clustering",
        description="Run a config-driven unsupervised difficulty-clustering experiment.",
    )
    parser.add_argument("config", type=Path, help="Path to a YAML experiment config.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="Directory that will hold timestamped run subdirectories.",
    )
    args = parser.parse_args(argv)

    result = run_experiment_from_config(args.config, runs_root=args.runs_root)
    if isinstance(result, ClusterSweepResult):
        payload = {
            "sweep_dir": str(result.sweep_dir),
            "summary_path": str(result.summary_path),
            "report_path": str(result.report_path),
            "best_run_dir": str(result.best_run.run_dir),
            "best_k": int(result.summary["best_k"]),
            "selection_metric": result.summary["selection_metric"],
            "selection_goal": result.summary["selection_goal"],
            "candidate_count": int(result.summary["candidate_count"]),
        }
    else:
        payload = {
            "run_dir": str(result.run_dir),
            "metrics_path": str(result.metrics_path),
            "report_path": str(result.report_path),
            "row_count": int(result.metrics.get("row_count", 0)),
            "feature_count": int(result.metrics.get("feature_count", 0)),
            "cluster_count": int(result.metrics.get("cluster_count", 0)),
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _validate_required_columns(frame: pd.DataFrame, source_path: Path, config: ExperimentConfig) -> None:
    missing_id_columns = [column for column in config.id_columns if column not in frame.columns]
    if missing_id_columns:
        raise ValueError(f"Matrix '{source_path}' is missing configured id columns: {missing_id_columns}")
    if config.label_column and config.label_column not in frame.columns:
        raise ValueError(f"Matrix '{source_path}' is missing label column '{config.label_column}'.")


def _attach_posthoc_label_column(
    frame: pd.DataFrame,
    source_path: Path,
    config: ExperimentConfig,
) -> tuple[pd.DataFrame, dict[str, Any] | None]:
    if not config.label_column:
        return frame, None
    if config.label_column in frame.columns:
        return frame, None
    if config.dataset_name.strip().lower() != "cipi":
        return frame, None

    if "dataset_relative_path" not in frame.columns:
        raise ValueError(
            f"Matrix '{source_path}' does not expose 'dataset_relative_path', which is required to join CIPI Henle labels."
        )
    if "filename" not in frame.columns:
        raise ValueError(
            f"Matrix '{source_path}' does not expose 'filename', which is required for the CIPI filename fallback join."
        )

    catalog = load_catalog_dataframe(DEFAULT_CATALOG_CSV)
    if config.label_column not in catalog.columns:
        raise ValueError(
            f"CIPI catalog '{DEFAULT_CATALOG_CSV}' does not contain label column '{config.label_column}'."
        )
    if "dataset_relative_path" not in catalog.columns:
        raise ValueError(
            f"CIPI catalog '{DEFAULT_CATALOG_CSV}' does not contain 'dataset_relative_path' for the label join."
        )
    if "filename" not in catalog.columns:
        raise ValueError(
            f"CIPI catalog '{DEFAULT_CATALOG_CSV}' does not contain 'filename' for the label join."
        )

    working_frame = frame.copy()
    working_frame["_normalized_dataset_relative_path"] = working_frame["dataset_relative_path"].map(
        _normalize_cipi_path_key
    )
    filename_variants = [
        ("exact", lambda value: _normalize_cipi_filename_key(value)),
        ("drop_version", lambda value: _normalize_cipi_filename_key(value, remove_version=True)),
        ("drop_prelude_and", lambda value: _normalize_cipi_filename_key(value, remove_prelude_and=True)),
        ("drop_and_fugue", lambda value: _normalize_cipi_filename_key(value, remove_and_fugue=True)),
    ]
    for variant_name, normalizer in filename_variants:
        working_frame[f"_normalized_filename_{variant_name}"] = working_frame["filename"].map(normalizer)

    exact_join = _build_cipi_label_join_frame(
        catalog,
        config.label_column,
        source_column="dataset_relative_path",
        normalized_column="_normalized_dataset_relative_path",
        normalize_key=_normalize_cipi_path_key,
    )

    merged = working_frame.merge(
        exact_join,
        on="_normalized_dataset_relative_path",
        how="left",
        validate="m:1",
    )
    missing = merged[config.label_column].isna()
    fallback_rows = 0
    label_source = pd.Series(pd.NA, index=merged.index, dtype="object")
    label_source.loc[merged[config.label_column].notna()] = "dataset_relative_path"
    for variant_name, normalizer in filename_variants:
        if not missing.any():
            break
        fallback_join = _build_cipi_label_join_frame(
            catalog,
            config.label_column,
            source_column="filename",
            normalized_column=f"_normalized_filename_{variant_name}",
            normalize_key=normalizer,
        )
        fallback = merged.loc[missing, [f"_normalized_filename_{variant_name}"]].merge(
            fallback_join,
            on=f"_normalized_filename_{variant_name}",
            how="left",
            validate="m:1",
        )
        resolved = fallback[config.label_column].notna()
        if resolved.any():
            target_index = merged.index[missing][resolved.to_numpy()]
            for column in (
                config.label_column,
                f"{config.label_column}_catalog_values",
                f"{config.label_column}_catalog_value_count",
            ):
                merged.loc[target_index, column] = fallback.loc[resolved, column].to_numpy()
            label_source.loc[target_index] = f"filename:{variant_name}"
            fallback_rows += int(resolved.sum())
        missing = merged[config.label_column].isna()
    merged["label_join_source"] = label_source
    missing = merged[config.label_column].isna()
    if missing.any():
        missing_rows = merged.loc[missing, "dataset_relative_path"].astype(str).head(10).tolist()
        raise ValueError(
            f"Joining CIPI label column '{config.label_column}' from '{DEFAULT_CATALOG_CSV}' left "
            f"{int(missing.sum())} rows without labels. Examples: {missing_rows}"
        )
    label_value_column = f"{config.label_column}_catalog_values"
    diagnostics = {
        "join_key": "dataset_relative_path + filename fallback",
        "catalog_path": str(DEFAULT_CATALOG_CSV),
        "joined_rows": int(len(merged)),
        "rows_with_multiple_catalog_labels": int(
            (merged[f"{config.label_column}_catalog_value_count"] > 1).sum()
        ),
        "rows_joined_via_filename_fallback": fallback_rows,
    }
    drop_columns = ["_normalized_dataset_relative_path"] + [
        f"_normalized_filename_{variant_name}" for variant_name, _ in filename_variants
    ]
    return merged.drop(columns=drop_columns), diagnostics


def _build_cipi_label_join_frame(
    catalog: pd.DataFrame,
    label_column: str,
    *,
    source_column: str,
    normalized_column: str,
    normalize_key,
) -> pd.DataFrame:
    keyed = catalog.loc[:, [source_column, label_column]].copy()
    keyed[normalized_column] = keyed[source_column].map(normalize_key)
    collapsed = (
        keyed.loc[:, [normalized_column, label_column]]
        .groupby(normalized_column, sort=False)[label_column]
        .agg(_collapse_catalog_labels)
    )
    join_frame = collapsed.apply(pd.Series)
    join_frame.columns = [
        label_column,
        f"{label_column}_catalog_values",
        f"{label_column}_catalog_value_count",
    ]
    join_frame = join_frame.reset_index()
    return join_frame


def _collapse_catalog_labels(values: pd.Series) -> tuple[Any, str, int]:
    normalized = [_normalize_catalog_label_value(value) for value in values.tolist()]
    unique_values: list[Any] = []
    for value in normalized:
        if value not in unique_values:
            unique_values.append(value)

    if all(isinstance(value, (int, float, np.integer, np.floating)) for value in unique_values):
        unique_values.sort(key=lambda value: float(value))
    else:
        unique_values.sort(key=lambda value: str(value))
    chosen = unique_values[0]
    joined_values = "|".join(str(value) for value in unique_values)
    return chosen, joined_values, len(unique_values)


def _normalize_cipi_path_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return text.replace("\\", "/").strip().lower()


def _normalize_cipi_filename_key(
    value: Any,
    *,
    remove_version: bool = False,
    remove_prelude_and: bool = False,
    remove_and_fugue: bool = False,
) -> str:
    text = _normalize_cipi_path_key(value)
    if text.endswith(".musicxml"):
        text = text[: -len(".musicxml")]
    if remove_version:
        text = text.replace("version-according-to-fontana-", "")
    if remove_prelude_and:
        text = text.replace("prelude-and-", "")
    if remove_and_fugue:
        text = text.replace("and-fugue-", "")
    return f"{text}.musicxml"


def _normalize_catalog_label_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    return value


def _resolve_feature_columns(
    frame: pd.DataFrame,
    config: ExperimentConfig,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    if config.feature_columns:
        missing = [column for column in config.feature_columns if column not in frame.columns]
        if missing:
            raise ValueError(
                f"Matrix '{config.input_matrix_path}' is missing configured feature columns: {missing}"
            )
        return config.feature_columns, {
            "mode": "explicit_columns",
            "feature_columns": list(config.feature_columns),
            "missing_feature_columns": [],
        }

    blocked_columns = tuple(
        dict.fromkeys(
            [
                *DEFAULT_METADATA_COLUMNS,
                *config.id_columns,
                *( [config.label_column] if config.label_column else [] ),
                *config.excluded_columns,
            ]
        )
    )
    selection = select_feature_columns(
        list(frame.columns),
        feature_set=config.feature_set or "",
        blocked_columns=blocked_columns,
    )
    if not selection.selected_columns:
        raise ValueError(
            "Feature selection produced no usable columns for "
            f"feature_set='{config.feature_set}'. Missing exact columns: {list(selection.missing_exact_columns)}; "
            f"missing prefixes: {list(selection.missing_prefixes)}."
        )
    return selection.selected_columns, {
        "mode": "feature_set",
        "feature_set": config.feature_set,
        "selection_report": selection.to_dict(),
    }


def _prepare_modeling_frame(
    *,
    frame: pd.DataFrame,
    selected_columns: tuple[str, ...],
    label_column: str | None,
    missing_feature_strategy: str,
) -> tuple[pd.DataFrame, pd.Series | None, pd.DataFrame, dict[str, Any]]:
    feature_frame = frame.loc[:, list(selected_columns)].apply(pd.to_numeric, errors="coerce")
    label_series = frame[label_column].copy() if label_column else None

    all_missing_columns = [
        column for column in feature_frame.columns if feature_frame[column].notna().sum() == 0
    ]
    usable_feature_frame = feature_frame.drop(columns=all_missing_columns)
    if usable_feature_frame.empty:
        raise ValueError("All configured feature columns are entirely missing in the selected matrix slice.")

    strategy = missing_feature_strategy.strip().lower()
    if strategy == "median":
        imputer = SimpleImputer(strategy="median")
        imputed = pd.DataFrame(
            imputer.fit_transform(usable_feature_frame),
            columns=usable_feature_frame.columns,
            index=usable_feature_frame.index,
        )
        modeling_frame = frame.copy()
        processed_feature_frame = imputed
        dropped_row_count = 0
    elif strategy == "drop_rows":
        usable_mask = usable_feature_frame.notna().all(axis=1)
        modeling_frame = frame.loc[usable_mask].copy()
        processed_feature_frame = usable_feature_frame.loc[usable_mask].copy()
        label_series = label_series.loc[usable_mask] if label_series is not None else None
        dropped_row_count = int((~usable_mask).sum())
    else:
        raise ValueError(
            f"Unsupported missing_feature_strategy '{missing_feature_strategy}'. "
            "Supported values: 'median', 'drop_rows'."
        )

    constant_columns = [
        column for column in processed_feature_frame.columns if processed_feature_frame[column].nunique(dropna=False) <= 1
    ]
    processed_feature_frame = processed_feature_frame.drop(columns=constant_columns)
    if processed_feature_frame.empty:
        raise ValueError(
            "No usable feature columns remain after dropping all-missing and constant columns."
        )

    diagnostics = {
        "requested_feature_columns": list(selected_columns),
        "all_missing_feature_columns": all_missing_columns,
        "constant_feature_columns": constant_columns,
        "usable_feature_columns": list(processed_feature_frame.columns),
        "dropped_row_count_for_missing_features": dropped_row_count,
        "rows_after_preprocessing": int(len(modeling_frame)),
    }
    return modeling_frame, label_series, processed_feature_frame, diagnostics


def _cluster_in_pca_space(
    *,
    coordinates: np.ndarray,
    method: str,
    n_clusters: int,
    random_state: int,
    n_init: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    key = method.strip().lower()
    if n_clusters < 2:
        raise ValueError("clustering.n_clusters must be at least 2.")

    if key == "ward":
        model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
        labels = model.fit_predict(coordinates)
        return labels, {"method": "ward"}
    if key == "kmeans":
        model = KMeans(n_clusters=n_clusters, n_init=n_init, random_state=random_state)
        labels = model.fit_predict(coordinates)
        return labels, {"method": "kmeans", "inertia": float(model.inertia_)}
    if key == "ward_then_kmeans":
        ward = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
        ward_labels = ward.fit_predict(coordinates)
        initial_centers = np.vstack(
            [coordinates[ward_labels == cluster_index].mean(axis=0) for cluster_index in range(n_clusters)]
        )
        model = KMeans(
            n_clusters=n_clusters,
            init=initial_centers,
            n_init=1,
            random_state=random_state,
        )
        labels = model.fit_predict(coordinates)
        return labels, {
            "method": "ward_then_kmeans",
            "inertia": float(model.inertia_),
            "ward_seeded": True,
        }
    raise ValueError(
        f"Unsupported clustering method '{method}'. Supported methods: ward, kmeans, ward_then_kmeans."
    )


def _build_assignments_frame(
    *,
    modeling_frame: pd.DataFrame,
    coordinate_frame: pd.DataFrame,
    id_columns: tuple[str, ...],
    label_column: str | None,
    cluster_labels: np.ndarray,
) -> pd.DataFrame:
    columns = list(id_columns)
    if label_column:
        columns.append(label_column)
        provenance_columns = [
            column
            for column in modeling_frame.columns
            if column.startswith(f"{label_column}_catalog_") or column == "label_join_source"
        ]
        columns.extend(column for column in provenance_columns if column not in columns)
    assignments = modeling_frame.loc[:, columns].copy()
    assignments.insert(len(columns), "cluster", cluster_labels.astype(int))
    for name in coordinate_frame.columns:
        assignments[name] = coordinate_frame[name].to_numpy()
    return assignments.reset_index(drop=True)


def _build_explained_variance_frame(pca: PCA) -> pd.DataFrame:
    explained = pd.DataFrame(
        {
            "component": [f"pc_{index}" for index in range(1, len(pca.explained_variance_ratio_) + 1)],
            "explained_variance_ratio": pca.explained_variance_ratio_,
        }
    )
    explained["cumulative_explained_variance_ratio"] = explained["explained_variance_ratio"].cumsum()
    return explained


def _build_loadings_frame(pca: PCA, feature_names: pd.Index, component_names: list[str]) -> pd.DataFrame:
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    frame = pd.DataFrame(loadings, columns=component_names)
    frame.insert(0, "feature", list(feature_names))
    return frame


def _build_cluster_profiles(
    *,
    assignments: pd.DataFrame,
    feature_frame: pd.DataFrame,
    standardized_frame: pd.DataFrame,
    label_column: str | None,
    component_names: list[str],
) -> pd.DataFrame:
    base = assignments[["cluster", *component_names]].copy()
    for column in feature_frame.columns:
        base[f"feature_mean__{column}"] = feature_frame[column].to_numpy()
        base[f"feature_z_mean__{column}"] = standardized_frame[column].to_numpy()
    if label_column and label_column in assignments.columns:
        base[label_column] = assignments[label_column].to_numpy()

    grouped = base.groupby("cluster", dropna=False)
    profiles = grouped.mean(numeric_only=True)
    profiles.insert(0, "piece_count", grouped.size())
    profiles.insert(1, "share_of_dataset", profiles["piece_count"] / float(len(assignments)))
    if label_column and label_column in base.columns and pd.api.types.is_numeric_dtype(base[label_column]):
        profiles["label_median"] = grouped[label_column].median()
    return profiles.reset_index()


def _build_label_crosstab(assignments: pd.DataFrame, *, label_column: str | None) -> pd.DataFrame | None:
    if not label_column or label_column not in assignments.columns:
        return None
    usable = assignments[assignments[label_column].notna()].copy()
    if usable.empty:
        return None
    return pd.crosstab(usable["cluster"], usable[label_column], dropna=False)


def _build_resolved_config(
    *,
    config: ExperimentConfig,
    loaded_path: Path,
    run_dir: Path,
    selected_columns: tuple[str, ...],
    feature_selection_details: dict[str, Any],
    diagnostics: dict[str, Any],
    row_count: int,
) -> dict[str, Any]:
    return {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "input_matrix_path": str(config.input_matrix_path.resolve()),
        "resolved_input_matrix_path": str(loaded_path.resolve()),
        "id_columns": list(config.id_columns),
        "label_column": config.label_column,
        "feature_columns": list(config.feature_columns),
        "feature_set": config.feature_set,
        "excluded_columns": list(config.excluded_columns),
        "preprocessing": {
            "missing_feature_strategy": config.preprocessing.missing_feature_strategy,
            "scaler": config.preprocessing.scaler,
        },
        "pca": {"n_components": config.pca.n_components},
        "clustering": {
            "method": config.clustering.method,
            "n_clusters": config.clustering.n_clusters,
            "random_state": config.clustering.random_state,
            "n_init": config.clustering.n_init,
        },
        "sweep": {
            "enabled": config.sweep.enabled,
            "k_values": list(config.sweep.k_values),
            "k_min": config.sweep.k_min,
            "k_max": config.sweep.k_max,
            "k_step": config.sweep.k_step,
            "selection_metric": config.sweep.selection_metric,
            "selection_goal": config.sweep.selection_goal,
            "include_label_metrics": config.sweep.include_label_metrics,
        },
        "output_options": {"run_name": config.output_options.run_name},
        "resolved_run_dir": str(run_dir.resolve()),
        "effective_row_count": int(row_count),
        "selected_feature_columns": list(selected_columns),
        "feature_selection": feature_selection_details,
        "preprocessing_diagnostics": diagnostics,
    }


def _build_metrics(
    *,
    config: ExperimentConfig,
    loaded: Any,
    assignments: pd.DataFrame,
    coordinates: np.ndarray,
    explained_variance: pd.DataFrame,
    diagnostics: dict[str, Any],
    cluster_metadata: dict[str, Any],
    label_column: str | None,
    label_join: dict[str, Any] | None,
) -> dict[str, Any]:
    cluster_ids = assignments["cluster"].to_numpy(dtype=int)
    internal_metrics = _compute_internal_metrics(coordinates, cluster_ids)
    metrics: dict[str, Any] = {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "input_matrix_path": str(loaded.source_path.resolve()),
        "row_count": int(len(assignments)),
        "feature_count": int(len(diagnostics["usable_feature_columns"])),
        "cluster_count": int(assignments["cluster"].nunique()),
        "cluster_sizes": {
            str(cluster_id): int(size)
            for cluster_id, size in assignments["cluster"].value_counts().sort_index().items()
        },
        "pca_n_components": int(config.pca.n_components),
        "pca_explained_variance_ratio": explained_variance["explained_variance_ratio"].tolist(),
        "pca_cumulative_explained_variance_ratio": explained_variance[
            "cumulative_explained_variance_ratio"
        ].tolist(),
        "status_filter_applied": bool(loaded.status_filter_applied),
        "preprocessing": diagnostics,
        "clustering": {
            "method": config.clustering.method,
            "n_clusters": config.clustering.n_clusters,
            **cluster_metadata,
        },
        "label_join": label_join,
    }
    metrics["internal_metrics"] = internal_metrics or None

    metrics["label_evaluation"] = _build_label_metrics(assignments, label_column=label_column)
    return metrics


def _build_label_metrics(assignments: pd.DataFrame, *, label_column: str | None) -> dict[str, Any] | None:
    if not label_column or label_column not in assignments.columns:
        return None

    usable = assignments[assignments[label_column].notna()].copy()
    if usable.empty:
        return {
            "label_column": label_column,
            "label_row_count": 0,
            "note": "Configured label column is present but all values are missing.",
        }

    labels = usable[label_column]
    clusters = usable["cluster"]
    result: dict[str, Any] = {
        "label_column": label_column,
        "label_row_count": int(len(usable)),
        "label_unique_values": _json_safe_label_values(labels.unique().tolist()),
    }
    if pd.api.types.is_numeric_dtype(labels):
        result["label_summary"] = {
            "mean": float(labels.mean()),
            "median": float(labels.median()),
            "min": float(labels.min()),
            "max": float(labels.max()),
        }
        cluster_means = usable.groupby("cluster")[label_column].mean()
        result["cluster_mean_label"] = {str(index): float(value) for index, value in cluster_means.items()}

    discrete_labels = labels.astype(str)
    result["adjusted_rand_score"] = float(adjusted_rand_score(discrete_labels, clusters.astype(str)))
    result["normalized_mutual_info_score"] = float(
        normalized_mutual_info_score(discrete_labels, clusters.astype(str))
    )
    result["cluster_purity"] = float(
        usable.groupby("cluster")[label_column].agg(lambda series: series.value_counts().max()).sum() / len(usable)
    )
    return result


def _compute_internal_metrics(coordinates: np.ndarray, cluster_ids: np.ndarray) -> dict[str, float]:
    if len(cluster_ids) < 3 or len(np.unique(cluster_ids)) < 2:
        return {}

    metrics: dict[str, float] = {}
    for name, scorer in (
        ("silhouette_score", silhouette_score),
        ("calinski_harabasz_score", calinski_harabasz_score),
        ("davies_bouldin_score", davies_bouldin_score),
    ):
        try:
            metrics[name] = float(scorer(coordinates, cluster_ids))
        except Exception:
            continue
    return metrics


def _build_sweep_candidate_row(
    *,
    result: ExperimentRunResult,
    k: int,
    metric_name: str,
    selection_goal: str,
    include_label_metrics: bool,
) -> dict[str, Any]:
    metrics = result.metrics
    row: dict[str, Any] = {
        "k": int(k),
        "run_dir": str(result.run_dir),
        "cluster_count": int(metrics.get("cluster_count", 0)),
        "row_count": int(metrics.get("row_count", 0)),
        "feature_count": int(metrics.get("feature_count", 0)),
        "selection_metric": metric_name,
        "selection_goal": selection_goal,
        "selection_score": _extract_selection_score(metrics, metric_name),
    }
    internal_metrics = metrics.get("internal_metrics")
    if isinstance(internal_metrics, dict):
        for key, value in internal_metrics.items():
            row[key] = value
    if include_label_metrics and isinstance(metrics.get("label_evaluation"), dict):
        for key, value in metrics["label_evaluation"].items():
            if key in {
                "adjusted_rand_score",
                "normalized_mutual_info_score",
                "cluster_purity",
                "label_row_count",
            }:
                row[key] = value
    return row


def _extract_selection_score(metrics: dict[str, Any], metric_name: str) -> float | None:
    internal_metrics = metrics.get("internal_metrics")
    if isinstance(internal_metrics, dict) and metric_name in internal_metrics:
        value = internal_metrics[metric_name]
        return float(value) if value is not None else None

    label_metrics = metrics.get("label_evaluation")
    if isinstance(label_metrics, dict) and metric_name in label_metrics:
        value = label_metrics[metric_name]
        return float(value) if value is not None else None
    return None


def _resolve_sweep_k_values(config: ExperimentConfig) -> tuple[int, ...]:
    sweep = config.sweep
    values: list[int]
    if sweep.k_values:
        values = list(sweep.k_values)
    elif sweep.k_min is not None and sweep.k_max is not None:
        values = list(range(sweep.k_min, sweep.k_max + 1, sweep.k_step))
    else:
        raise ValueError(
            "k sweep requires either clustering.sweep.k_values or clustering.sweep.k_min/k_max."
        )

    unique_values = sorted({int(value) for value in values})
    if len(unique_values) < 2:
        raise ValueError("k sweep requires at least two candidate cluster counts.")
    if any(value < 2 for value in unique_values):
        raise ValueError("k sweep candidate values must be at least 2.")
    return tuple(unique_values)


def _resolve_sweep_selection_metric(metric_name: str) -> str:
    key = metric_name.strip()
    supported = {
        "silhouette_score",
        "calinski_harabasz_score",
        "davies_bouldin_score",
        "adjusted_rand_score",
        "normalized_mutual_info_score",
        "cluster_purity",
    }
    if key not in supported:
        raise ValueError(
            f"Unsupported clustering sweep selection_metric '{metric_name}'. "
            f"Supported metrics: {sorted(supported)}."
        )
    return key


def _resolve_selection_goal(selection_goal: str | None, metric_name: str) -> str:
    if selection_goal:
        key = selection_goal.strip().lower()
        if key not in {"maximize", "minimize"}:
            raise ValueError("clustering.sweep.selection_goal must be 'maximize' or 'minimize'.")
        return key
    if metric_name == "davies_bouldin_score":
        return "minimize"
    return "maximize"


def _allocate_sweep_root(runs_root: Path, config: ExperimentConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(config.output_options.run_name or config.experiment_name)
    candidate = runs_root / "sweeps" / f"{timestamp}__{slug}"
    suffix = 2
    while candidate.exists():
        candidate = runs_root / "sweeps" / f"{timestamp}__{slug}__{suffix}"
        suffix += 1
    return candidate


def _sweep_run_name(base_name: str, k: int) -> str:
    return f"{base_name}__k{k}"


def _build_sweep_summary(
    *,
    config: ExperimentConfig,
    sweep_root: Path,
    candidate_rows: list[dict[str, Any]],
    best_candidate: dict[str, Any],
    metric_name: str,
    selection_goal: str,
) -> dict[str, Any]:
    completed_rows = [row for row in candidate_rows if row.get("selection_score") is not None]
    ranked_rows = sorted(
        completed_rows,
        key=lambda row: float(row["selection_score"]),
        reverse=selection_goal == "maximize",
    )
    for index, row in enumerate(ranked_rows, start=1):
        row["selection_rank"] = index

    best_k = int(best_candidate["k"])
    return {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "sweep_dir": str(sweep_root.resolve()),
        "selection_metric": metric_name,
        "selection_goal": selection_goal,
        "best_k": best_k,
        "best_run_dir": best_candidate["run_dir"],
        "candidate_count": int(len(candidate_rows)),
        "completed_candidate_count": int(len(completed_rows)),
        "candidate_rows": candidate_rows,
        "best_candidate": best_candidate,
        "k_values": [int(row["k"]) for row in candidate_rows],
        "completed_k_values": [int(row["k"]) for row in completed_rows],
    }


def _build_sweep_report(
    *,
    config: ExperimentConfig,
    summary: dict[str, Any],
    summary_frame: pd.DataFrame,
) -> str:
    lines = [
        f"# {config.experiment_name} k Sweep",
        "",
        f"- dataset: `{config.dataset_name}`",
        f"- selection metric: `{summary['selection_metric']}`",
        f"- selection goal: `{summary['selection_goal']}`",
        f"- best k: `{summary['best_k']}`",
        f"- best run: `{summary['best_run_dir']}`",
        f"- candidate count: {summary['candidate_count']}",
        f"- completed candidate count: {summary['completed_candidate_count']}",
        "",
        "## Candidate Ranking",
        "",
        "```text",
        summary_frame.sort_values(
            by=["selection_rank", "k"], na_position="last"
        ).to_string(index=False),
        "```",
        "",
        "## Interpretation",
        "",
        (
            "The sweep selects the best candidate using a post-fit score on the clustered PCA space. "
            "Label-based metrics, when enabled, remain post hoc and do not influence fitting."
        ),
    ]
    return "\n".join(lines) + "\n"


def _save_sweep_metric_curve(
    summary_frame: pd.DataFrame,
    metric_name: str,
    selection_goal: str,
    path: Path,
) -> None:
    usable = summary_frame[summary_frame["selection_score"].notna()].copy()
    if usable.empty:
        return
    usable = usable.sort_values("k")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(usable["k"], usable["selection_score"], marker="o")
    ax.set_title(f"k Sweep: {metric_name}")
    ax.set_xlabel("k")
    ax.set_ylabel(metric_name)
    ax.grid(True, alpha=0.3)
    if selection_goal == "minimize":
        ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_cluster_scatter(assignments: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(
        assignments["pc_1"],
        assignments["pc_2"],
        c=assignments["cluster"],
        cmap="tab10",
        s=36,
        alpha=0.85,
    )
    ax.set_title("PCA Scatter Colored by Cluster")
    ax.set_xlabel("PC 1")
    ax.set_ylabel("PC 2")
    legend = ax.legend(*scatter.legend_elements(), title="Cluster", loc="best")
    ax.add_artist(legend)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_label_scatter(assignments: pd.DataFrame, *, label_column: str, path: Path) -> None:
    usable = assignments[assignments[label_column].notna()].copy()
    fig, ax = plt.subplots(figsize=(8, 6))
    if pd.api.types.is_numeric_dtype(usable[label_column]):
        scatter = ax.scatter(
            usable["pc_1"],
            usable["pc_2"],
            c=usable[label_column],
            cmap="viridis",
            s=36,
            alpha=0.85,
        )
        fig.colorbar(scatter, ax=ax, label=label_column)
    else:
        categories = pd.Categorical(usable[label_column].astype(str))
        scatter = ax.scatter(
            usable["pc_1"],
            usable["pc_2"],
            c=categories.codes,
            cmap="tab10",
            s=36,
            alpha=0.85,
        )
        legend = ax.legend(*scatter.legend_elements(), title=label_column, loc="best")
        ax.add_artist(legend)
    ax.set_title("PCA Scatter Colored by OKTAV Label")
    ax.set_xlabel("PC 1")
    ax.set_ylabel("PC 2")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_dendrogram(linkage_matrix: np.ndarray, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    dendrogram(linkage_matrix, ax=ax, no_labels=True, color_threshold=None)
    ax.set_title("Ward Dendrogram")
    ax.set_xlabel("Pieces")
    ax.set_ylabel("Distance")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_difficulty_boxplot(assignments: pd.DataFrame, *, label_column: str, path: Path) -> None:
    usable = assignments[assignments[label_column].notna()].copy()
    groups = [group[label_column].to_numpy() for _, group in usable.groupby("cluster")]
    labels = [str(cluster_id) for cluster_id, _ in usable.groupby("cluster")]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.boxplot(groups, tick_labels=labels)
    ax.set_title("Difficulty by Cluster")
    ax.set_xlabel("Cluster")
    ax.set_ylabel(label_column)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _build_report(
    *,
    config: ExperimentConfig,
    metrics: dict[str, Any],
    explained_variance: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
    crosstab: pd.DataFrame | None,
) -> str:
    label_eval = metrics.get("label_evaluation")
    variance_lines = [
        f"- {row.component}: {row.explained_variance_ratio:.3f} (cumulative {row.cumulative_explained_variance_ratio:.3f})"
        for row in explained_variance.itertuples(index=False)
    ]
    cluster_lines = [
        f"- cluster {int(row.cluster)}: n={int(row.piece_count)}, share={float(row.share_of_dataset):.3f}"
        for row in cluster_profiles.itertuples(index=False)
    ]
    lines = [
        f"# {config.experiment_name}",
        "",
        (
            "This run keeps the difficulty labels out of PCA and clustering. "
            "Labels are used only for post-hoc interpretation."
            if label_eval
            else "This run is unsupervised; no label column was provided."
        ),
        "",
        "## Dataset",
        f"- dataset: `{config.dataset_name}`",
        f"- input matrix: `{metrics['input_matrix_path']}`",
        f"- usable rows: {metrics['row_count']}",
        f"- usable features: {metrics['feature_count']}",
        f"- clustering method: `{config.clustering.method}`",
        f"- clusters requested: {config.clustering.n_clusters}",
        "",
        "## Features Used",
    ]
    lines.extend([f"- `{column}`" for column in metrics["preprocessing"]["usable_feature_columns"]])
    if metrics["preprocessing"]["constant_feature_columns"] or metrics["preprocessing"]["all_missing_feature_columns"]:
        lines.extend(
            [
                "",
                "## Dropped Features",
                f"- all-missing: {metrics['preprocessing']['all_missing_feature_columns'] or 'none'}",
                f"- constant: {metrics['preprocessing']['constant_feature_columns'] or 'none'}",
            ]
        )
    lines.extend(["", "## PCA Variance"])
    lines.extend(variance_lines)
    lines.extend(["", "## Cluster Sizes"])
    lines.extend(cluster_lines)
    if label_eval:
        lines.extend(["", "## Label Comparison"])
        if metrics.get("label_join"):
            label_join = metrics["label_join"]
            lines.extend(
                [
                    f"- joined CIPI labels from `{label_join['catalog_path']}` using `{label_join['join_key']}`",
                    f"- rows with multiple catalog Henle labels: {label_join['rows_with_multiple_catalog_labels']}",
                    "- `piece_coordinates.csv` includes the joined `henle_catalog_values` provenance column.",
                ]
            )
        if "label_summary" in label_eval:
            summary = label_eval["label_summary"]
            lines.append(
                f"- label summary: mean={summary['mean']:.3f}, median={summary['median']:.3f}, min={summary['min']:.3f}, max={summary['max']:.3f}"
            )
        if "adjusted_rand_score" in label_eval:
            lines.append(f"- adjusted rand index: {label_eval['adjusted_rand_score']:.3f}")
            lines.append(f"- normalized mutual information: {label_eval['normalized_mutual_info_score']:.3f}")
            lines.append(f"- cluster purity: {label_eval['cluster_purity']:.3f}")
        if crosstab is not None:
            lines.extend(["", "Cluster x label counts:", "", "```text", crosstab.to_string(), "```"])
    return "\n".join(lines) + "\n"


def _assignment_columns(id_columns: tuple[str, ...], label_column: str | None) -> list[str]:
    columns = [*id_columns]
    if label_column:
        columns.append(label_column)
    columns.append("cluster")
    return columns


def _allocate_run_dir(runs_root: Path, config: ExperimentConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(config.output_options.run_name or config.experiment_name)
    candidate = runs_root / f"{timestamp}__{slug}"
    suffix = 2
    while candidate.exists():
        candidate = runs_root / f"{timestamp}__{slug}__{suffix}"
        suffix += 1
    return candidate


def _slugify(value: str) -> str:
    text = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
    return "-".join(part for part in text.split("-") if part) or "run"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_safe_label_values(values: list[Any]) -> list[Any]:
    decorated: list[tuple[str, Any]] = []
    for value in values:
        if pd.isna(value):
            safe = "NaN"
        elif isinstance(value, (np.integer, int)):
            safe = int(value)
        elif isinstance(value, (np.floating, float)):
            safe = float(value)
        else:
            safe = str(value)
        decorated.append((str(safe), safe))
    decorated.sort(key=lambda item: item[0])
    return [safe for _, safe in decorated]
