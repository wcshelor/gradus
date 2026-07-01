from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_MPLCONFIGDIR = Path(os.environ.get("MPLCONFIGDIR", Path(tempfile.gettempdir()) / "piano-difficulty-mplconfig"))
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import yaml
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

from tests.harness.cipi_dataset.catalog import DEFAULT_CATALOG_CSV, load_catalog_dataframe
from tests.harness.shared import DEFAULT_METADATA_COLUMNS, load_dataset_matrix, select_feature_columns

from .config import load_experiment_config
from .core import DEFAULT_ARTIFACTS_ROOT, DEFAULT_RUNS_ROOT, ExperimentConfig, ExperimentRunResult


def run_experiment_from_config(
    config: ExperimentConfig | str | Path,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    experiment_config = config if isinstance(config, ExperimentConfig) else load_experiment_config(config)
    return run_experiment(experiment_config, runs_root=runs_root)


def run_experiment(
    config: ExperimentConfig,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    loaded_matrix = load_dataset_matrix(config.dataset_name, config.input_matrix_path)
    frame = loaded_matrix.frame.copy()

    if config.label_column and config.dataset_name == "cipi" and config.label_column not in frame.columns:
        frame, label_join_diagnostics = _attach_posthoc_label_column(
            frame=frame,
            label_column=config.label_column,
        )
    else:
        label_join_diagnostics = None

    _validate_required_columns(frame, config.id_columns, config.label_column)
    feature_columns, selection_report = _resolve_feature_columns(frame, config)
    prepared_frame = _prepare_feature_frame(
        frame=frame,
        feature_columns=feature_columns,
        strategy=config.preprocessing.missing_feature_strategy,
    )
    if prepared_frame.empty:
        raise ValueError("Prepared feature frame is empty after missing-value handling.")

    feature_matrix = prepared_frame.to_numpy(dtype=float)
    if config.preprocessing.scaler and config.preprocessing.scaler.strip().lower() == "standard":
        feature_matrix = StandardScaler().fit_transform(feature_matrix)

    n_components = min(config.pca.n_components, feature_matrix.shape[0], feature_matrix.shape[1])
    if n_components < 1:
        raise ValueError("PCA requires at least one non-constant feature column.")

    pca = PCA(n_components=n_components, random_state=config.clustering.random_state)
    coordinates = pca.fit_transform(feature_matrix)
    cluster_labels, clustering_diagnostics = _cluster(coordinates, config)

    runs_root_path = _resolve_runs_root(config, Path(runs_root).expanduser())
    runs_root_path.mkdir(parents=True, exist_ok=True)
    run_dir = _allocate_run_dir(runs_root_path, config)
    run_dir.mkdir(parents=True, exist_ok=False)

    resolved_config_path = run_dir / "resolved_config.yaml"
    metrics_path = run_dir / "metrics.json"
    report_path = run_dir / "report.md"
    piece_coordinates_path = run_dir / "piece_coordinates.csv"
    cluster_assignments_path = run_dir / "cluster_assignments.csv"
    cluster_profiles_path = run_dir / "cluster_profiles.csv"
    pca_explained_variance_path = run_dir / "pca_explained_variance.csv"
    pca_loadings_path = run_dir / "pca_loadings.csv"
    label_crosstab_path = run_dir / "cluster_label_crosstab.csv"

    assignments = _build_assignments(
        frame=frame.loc[prepared_frame.index].reset_index(drop=False),
        id_columns=config.id_columns,
        label_column=config.label_column,
        coordinates=coordinates,
        cluster_labels=cluster_labels,
    )
    explained_variance_frame = _build_explained_variance_frame(pca)
    loadings_frame = _build_loadings_frame(pca, feature_columns)
    cluster_profiles = _build_cluster_profiles(
        assignments=assignments,
        feature_frame=prepared_frame.reset_index(drop=True),
        label_column=config.label_column,
    )
    label_crosstab = _build_label_crosstab(assignments, config.label_column)

    metrics = _build_metrics(
        config=config,
        loaded_matrix=loaded_matrix,
        feature_columns=feature_columns,
        assignments=assignments,
        explained_variance_frame=explained_variance_frame,
        cluster_profiles=cluster_profiles,
        label_join_diagnostics=label_join_diagnostics,
        clustering_diagnostics=clustering_diagnostics,
    )

    resolved_config_path.write_text(
        yaml.safe_dump(
            {
                "experiment_name": config.experiment_name,
                "dataset_name": config.dataset_name,
                "input_matrix_path": str(config.input_matrix_path.resolve()),
                "source_path": str(loaded_matrix.source_path),
                "id_columns": list(config.id_columns),
                "label_column": config.label_column,
                "feature_columns": list(feature_columns),
                "feature_set": config.feature_set,
                "excluded_columns": list(config.excluded_columns),
                "preprocessing": {
                    "missing_feature_strategy": config.preprocessing.missing_feature_strategy,
                    "scaler": config.preprocessing.scaler,
                },
                "pca": {"n_components": n_components},
                "clustering": {
                    "method": config.clustering.method,
                    "n_clusters": config.clustering.n_clusters,
                    "random_state": config.clustering.random_state,
                    "n_init": config.clustering.n_init,
                },
                "feature_selection": selection_report,
            },
            sort_keys=False,
        )
    )
    piece_coordinates_path.write_text(assignments.to_csv(index=False))
    cluster_assignments_path.write_text(assignments.to_csv(index=False))
    cluster_profiles.to_csv(cluster_profiles_path, index=False)
    explained_variance_frame.to_csv(pca_explained_variance_path, index=False)
    loadings_frame.to_csv(pca_loadings_path, index=False)
    if label_crosstab is not None:
        label_crosstab.to_csv(label_crosstab_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))

    _save_cluster_scatter(assignments, run_dir / "pca_scatter_by_cluster.png")
    if config.label_column and assignments[config.label_column].notna().any():
        _save_label_scatter(assignments, config.label_column, run_dir / "pca_scatter_by_label.png")
        if pd.api.types.is_numeric_dtype(assignments[config.label_column]):
            _save_difficulty_boxplot(assignments, config.label_column, run_dir / "difficulty_by_cluster_boxplot.png")
    if config.clustering.method.startswith("ward"):
        _save_dendrogram(coordinates, run_dir / "ward_dendrogram.png")

    report_path.write_text(
        _build_report(
            config=config,
            metrics=metrics,
            explained_variance_frame=explained_variance_frame,
            cluster_profiles=cluster_profiles,
            label_crosstab=label_crosstab,
        )
    )

    return ExperimentRunResult(
        run_dir=run_dir,
        resolved_config_path=resolved_config_path,
        metrics_path=metrics_path,
        report_path=report_path,
        piece_coordinates_path=piece_coordinates_path,
        cluster_assignments_path=cluster_assignments_path,
        cluster_profiles_path=cluster_profiles_path,
        metrics=metrics,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a config-driven difficulty clustering experiment.")
    parser.add_argument("config", type=Path)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    args = parser.parse_args(argv)

    result = run_experiment_from_config(args.config, runs_root=args.runs_root)
    print(
        json.dumps(
            {
                "run_dir": str(result.run_dir),
                "metrics_path": str(result.metrics_path),
                "report_path": str(result.report_path),
                "metrics": result.metrics,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _validate_required_columns(frame: pd.DataFrame, id_columns: tuple[str, ...], label_column: str | None) -> None:
    missing_columns = [column for column in id_columns if column not in frame.columns]
    if label_column and label_column not in frame.columns:
        missing_columns.append(label_column)
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {missing_text}")


def _resolve_feature_columns(frame: pd.DataFrame, config: ExperimentConfig) -> tuple[list[str], dict[str, Any]]:
    if config.feature_columns:
        missing_columns = [column for column in config.feature_columns if column not in frame.columns]
        if missing_columns:
            missing_text = ", ".join(missing_columns)
            raise ValueError(f"Explicit feature_columns missing from matrix: {missing_text}")
        return list(config.feature_columns), {
            "mode": "explicit_columns",
            "selected_columns": list(config.feature_columns),
        }

    if not config.feature_set:
        raise ValueError("Clustering config must define feature_columns or feature_set.")

    excluded_columns = tuple(
        dict.fromkeys(
            [
                *DEFAULT_METADATA_COLUMNS,
                *config.id_columns,
                *( [config.label_column] if config.label_column else [] ),
                *config.excluded_columns,
            ]
        )
    )
    selection_report = select_feature_columns(
        available_columns=list(frame.columns),
        feature_set=config.feature_set,
        excluded_columns=excluded_columns,
    )
    if not selection_report.selected_columns:
        raise ValueError(f"Feature set {config.feature_set!r} selected no columns.")
    return list(selection_report.selected_columns), selection_report.to_dict()


def _prepare_feature_frame(
    frame: pd.DataFrame,
    feature_columns: list[str],
    strategy: str,
) -> pd.DataFrame:
    numeric_frame = frame.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    numeric_frame = numeric_frame.loc[:, numeric_frame.notna().sum() > 0]
    if numeric_frame.empty:
        raise ValueError("All requested feature columns are fully missing or non-numeric.")

    normalized_strategy = strategy.strip().lower()
    if normalized_strategy in {"drop", "drop_rows"}:
        numeric_frame = numeric_frame.dropna(axis=0)
    elif normalized_strategy in {"median", "mean", "most_frequent"}:
        imputer = SimpleImputer(strategy=normalized_strategy)
        numeric_frame = pd.DataFrame(
            imputer.fit_transform(numeric_frame),
            columns=list(numeric_frame.columns),
            index=numeric_frame.index,
        )
    elif normalized_strategy in {"zero", "constant"}:
        imputer = SimpleImputer(strategy="constant", fill_value=0.0)
        numeric_frame = pd.DataFrame(
            imputer.fit_transform(numeric_frame),
            columns=list(numeric_frame.columns),
            index=numeric_frame.index,
        )
    else:
        raise ValueError(f"Unsupported missing_feature_strategy {strategy!r}.")

    numeric_frame = numeric_frame.loc[:, numeric_frame.nunique(dropna=False) > 1]
    return numeric_frame


def _cluster(coordinates: np.ndarray, config: ExperimentConfig) -> tuple[np.ndarray, dict[str, Any]]:
    method = config.clustering.method.strip().lower()
    if method == "ward":
        estimator = AgglomerativeClustering(n_clusters=config.clustering.n_clusters, linkage="ward")
        labels = estimator.fit_predict(coordinates)
        return labels, {"method": method}
    if method == "kmeans":
        estimator = KMeans(
            n_clusters=config.clustering.n_clusters,
            random_state=config.clustering.random_state,
            n_init=config.clustering.n_init,
        )
        labels = estimator.fit_predict(coordinates)
        return labels, {"method": method, "inertia": float(estimator.inertia_)}
    if method == "ward_then_kmeans":
        ward_labels = AgglomerativeClustering(
            n_clusters=config.clustering.n_clusters,
            linkage="ward",
        ).fit_predict(coordinates)
        centroids = np.vstack(
            [coordinates[ward_labels == cluster_index].mean(axis=0) for cluster_index in range(config.clustering.n_clusters)]
        )
        estimator = KMeans(
            n_clusters=config.clustering.n_clusters,
            random_state=config.clustering.random_state,
            n_init=1,
            init=centroids,
        )
        labels = estimator.fit_predict(coordinates)
        return labels, {"method": method, "inertia": float(estimator.inertia_)}
    raise ValueError(f"Unsupported clustering method {config.clustering.method!r}.")


def _build_assignments(
    frame: pd.DataFrame,
    id_columns: tuple[str, ...],
    label_column: str | None,
    coordinates: np.ndarray,
    cluster_labels: np.ndarray,
) -> pd.DataFrame:
    assignment_frame = frame.loc[:, [column for column in id_columns if column in frame.columns]].copy()
    if label_column and label_column in frame.columns:
        assignment_frame[label_column] = frame[label_column].to_numpy()
        catalog_value_column = f"{label_column}_catalog_values"
        catalog_count_column = f"{label_column}_catalog_value_count"
        if catalog_value_column in frame.columns:
            assignment_frame[catalog_value_column] = frame[catalog_value_column].to_numpy()
        if catalog_count_column in frame.columns:
            assignment_frame[catalog_count_column] = frame[catalog_count_column].to_numpy()
        if "label_join_source" in frame.columns:
            assignment_frame["label_join_source"] = frame["label_join_source"].to_numpy()
    assignment_frame["cluster"] = cluster_labels.astype(int)
    for component_index in range(coordinates.shape[1]):
        assignment_frame[f"pc_{component_index + 1}"] = coordinates[:, component_index]
    return assignment_frame


def _build_explained_variance_frame(pca: PCA) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "component": [f"PC{i + 1}" for i in range(len(pca.explained_variance_ratio_))],
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance_ratio": np.cumsum(pca.explained_variance_ratio_),
        }
    )


def _build_loadings_frame(pca: PCA, feature_columns: list[str]) -> pd.DataFrame:
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    frame = pd.DataFrame(loadings, columns=[f"pc_{i + 1}" for i in range(loadings.shape[1])])
    frame.insert(0, "feature", list(feature_columns))
    return frame


def _build_cluster_profiles(
    assignments: pd.DataFrame,
    feature_frame: pd.DataFrame,
    label_column: str | None,
) -> pd.DataFrame:
    working_frame = pd.concat(
        [
            assignments.loc[:, ["cluster"]].reset_index(drop=True),
            feature_frame.reset_index(drop=True),
            assignments.loc[:, [label_column]].reset_index(drop=True)
            if label_column and label_column in assignments.columns
            else pd.DataFrame(),
        ],
        axis=1,
    )
    numeric_columns = [
        column for column in working_frame.columns if column != "cluster" and pd.api.types.is_numeric_dtype(working_frame[column])
    ]
    grouped_means = working_frame.groupby("cluster")[numeric_columns].mean().reset_index()
    cluster_sizes = working_frame.groupby("cluster").size().reset_index(name="piece_count")
    profiles = cluster_sizes.merge(grouped_means, on="cluster", how="left")
    profiles.insert(2, "share_of_dataset", profiles["piece_count"] / float(len(assignments)))
    return profiles


def _build_label_crosstab(assignments: pd.DataFrame, label_column: str | None) -> pd.DataFrame | None:
    if not label_column or label_column not in assignments.columns:
        return None
    labeled = assignments.loc[assignments[label_column].notna(), ["cluster", label_column]].copy()
    if labeled.empty:
        return None
    return pd.crosstab(labeled["cluster"], labeled[label_column])


def _build_metrics(
    config: ExperimentConfig,
    loaded_matrix: Any,
    feature_columns: list[str],
    assignments: pd.DataFrame,
    explained_variance_frame: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
    label_join_diagnostics: dict[str, Any] | None,
    clustering_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    coordinates = assignments.loc[:, [column for column in assignments.columns if column.startswith("pc_")]].to_numpy()
    metrics: dict[str, Any] = {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "source_path": str(loaded_matrix.source_path),
        "status_filter_applied": bool(loaded_matrix.status_filter_applied),
        "raw_row_count": int(len(loaded_matrix.raw_frame)),
        "analyzed_row_count": int(len(assignments)),
        "feature_columns": list(feature_columns),
        "n_features": int(len(feature_columns)),
        "pca": {
            "n_components": int(coordinates.shape[1]),
            "explained_variance_ratio": explained_variance_frame["explained_variance_ratio"].tolist(),
        },
        "clustering": {
            "method": config.clustering.method,
            "n_clusters": int(config.clustering.n_clusters),
            **clustering_diagnostics,
        },
        "cluster_counts": {
            str(cluster): int(count)
            for cluster, count in assignments["cluster"].value_counts().sort_index().items()
        },
        "silhouette": float(silhouette_score(coordinates, assignments["cluster"]))
        if len(assignments["cluster"].unique()) > 1 and len(assignments) > len(assignments["cluster"].unique())
        else float("nan"),
        "calinski_harabasz": float(calinski_harabasz_score(coordinates, assignments["cluster"]))
        if len(assignments["cluster"].unique()) > 1
        else float("nan"),
        "davies_bouldin": float(davies_bouldin_score(coordinates, assignments["cluster"]))
        if len(assignments["cluster"].unique()) > 1
        else float("nan"),
        "cluster_profiles": cluster_profiles.to_dict(orient="records"),
    }

    if config.label_column and config.label_column in assignments.columns:
        labeled = assignments.loc[assignments[config.label_column].notna(), ["cluster", config.label_column]].copy()
        if not labeled.empty:
            labels = labeled[config.label_column].astype(str)
            metrics["label_metrics"] = {
                "label_column": config.label_column,
                "labeled_rows": int(len(labeled)),
                "ari": float(adjusted_rand_score(labels, labeled["cluster"])),
                "nmi": float(normalized_mutual_info_score(labels, labeled["cluster"])),
                "purity": _cluster_purity(labeled["cluster"], labels),
            }
            if pd.api.types.is_numeric_dtype(assignments[config.label_column]):
                metrics["label_metrics"]["cluster_label_summary"] = (
                    assignments.groupby("cluster")[config.label_column]
                    .agg(["mean", "median", "min", "max"])
                    .reset_index()
                    .to_dict(orient="records")
                )

    if label_join_diagnostics is not None:
        metrics["label_join"] = label_join_diagnostics

    return metrics


def _cluster_purity(clusters: pd.Series, labels: pd.Series) -> float:
    contingency = pd.crosstab(clusters, labels)
    return float(contingency.max(axis=1).sum() / contingency.to_numpy().sum())


def _save_cluster_scatter(assignments: pd.DataFrame, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 5))
    scatter = axis.scatter(assignments["pc_1"], assignments["pc_2"], c=assignments["cluster"], cmap="tab10")
    axis.set_title("PCA scatter by cluster")
    axis.set_xlabel("PC1")
    axis.set_ylabel("PC2")
    axis.legend(*scatter.legend_elements(), title="Cluster", loc="best")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _save_label_scatter(assignments: pd.DataFrame, label_column: str, output_path: Path) -> None:
    labeled = assignments.loc[assignments[label_column].notna()].copy()
    figure, axis = plt.subplots(figsize=(7, 5))
    if pd.api.types.is_numeric_dtype(labeled[label_column]):
        scatter = axis.scatter(labeled["pc_1"], labeled["pc_2"], c=labeled[label_column], cmap="viridis")
        figure.colorbar(scatter, ax=axis, label=label_column)
    else:
        categories = pd.Categorical(labeled[label_column].astype(str))
        scatter = axis.scatter(labeled["pc_1"], labeled["pc_2"], c=categories.codes, cmap="tab20")
        axis.legend(*scatter.legend_elements(), title=label_column, loc="best")
    axis.set_title(f"PCA scatter by {label_column}")
    axis.set_xlabel("PC1")
    axis.set_ylabel("PC2")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _save_difficulty_boxplot(assignments: pd.DataFrame, label_column: str, output_path: Path) -> None:
    labeled = assignments.loc[assignments[label_column].notna(), ["cluster", label_column]].copy()
    values = [group[label_column].to_numpy() for _, group in labeled.groupby("cluster")]
    labels = [str(cluster) for cluster, _ in labeled.groupby("cluster")]
    figure, axis = plt.subplots(figsize=(7, 5))
    axis.boxplot(values, tick_labels=labels)
    axis.set_title(f"{label_column} by cluster")
    axis.set_xlabel("Cluster")
    axis.set_ylabel(label_column)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _save_dendrogram(coordinates: np.ndarray, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    dendrogram(linkage(coordinates, method="ward"), ax=axis)
    axis.set_title("Ward dendrogram")
    axis.set_xlabel("Piece index")
    axis.set_ylabel("Distance")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _build_report(
    config: ExperimentConfig,
    metrics: dict[str, Any],
    explained_variance_frame: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
    label_crosstab: pd.DataFrame | None,
) -> str:
    lines = [
        f"# {config.experiment_name}",
        "",
        f"- dataset: `{config.dataset_name}`",
        f"- clustering: `{config.clustering.method}` with `k={config.clustering.n_clusters}`",
        f"- analyzed rows: `{metrics['analyzed_row_count']}`",
        f"- feature count: `{metrics['n_features']}`",
        "",
        "## PCA explained variance",
    ]
    for row in explained_variance_frame.itertuples(index=False):
        lines.append(
            f"- {row.component}: {row.explained_variance_ratio:.3f} "
            f"(cumulative {row.cumulative_explained_variance_ratio:.3f})"
        )

    lines.extend(["", "## Cluster metrics"])
    lines.extend(
        [
            f"- silhouette: `{metrics['silhouette']:.4f}`",
            f"- calinski_harabasz: `{metrics['calinski_harabasz']:.4f}`",
            f"- davies_bouldin: `{metrics['davies_bouldin']:.4f}`",
        ]
    )

    if "label_metrics" in metrics:
        label_metrics = metrics["label_metrics"]
        lines.extend(
            [
                "",
                "## Label comparison",
                f"- label column: `{label_metrics['label_column']}`",
                f"- labeled rows: `{label_metrics['labeled_rows']}`",
                f"- ARI: `{label_metrics['ari']:.4f}`",
                f"- NMI: `{label_metrics['nmi']:.4f}`",
                f"- purity: `{label_metrics['purity']:.4f}`",
            ]
        )
    if "label_join" in metrics:
        label_join = metrics["label_join"]
        lines.extend(
            [
                "",
                "## CIPI label join provenance",
                f"- catalog path: `{label_join['catalog_path']}`",
                f"- join key: `{label_join['join_key']}`",
                f"- joined rows: `{label_join['joined_rows']}`",
                f"- filename fallback rows: `{label_join['rows_joined_via_filename_fallback']}`",
                f"- rows with multiple catalog labels: `{label_join['rows_with_multiple_catalog_labels']}`",
                "- `piece_coordinates.csv` includes `henle_catalog_values` and `label_join_source`.",
            ]
        )

    lines.extend(["", "## Cluster profiles", cluster_profiles.to_string(index=False)])
    if label_crosstab is not None:
        lines.extend(["", "## Cluster label crosstab", label_crosstab.to_string()])
    return "\n".join(lines)


def _allocate_run_dir(runs_root: Path, config: ExperimentConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_label = _slugify(config.output_options.run_name or config.experiment_name)
    candidate = runs_root / f"{timestamp}__{run_label}"
    if candidate.exists():
        suffix = 2
        while True:
            alternate = runs_root / f"{timestamp}__{run_label}-{suffix}"
            if not alternate.exists():
                return alternate
            suffix += 1
    return candidate


def _resolve_runs_root(config: ExperimentConfig, runs_root: Path) -> Path:
    if runs_root == DEFAULT_RUNS_ROOT:
        return DEFAULT_ARTIFACTS_ROOT / config.dataset_name
    return runs_root


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _attach_posthoc_label_column(
    frame: pd.DataFrame,
    label_column: str,
    catalog_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    catalog_frame = load_catalog_dataframe(catalog_path or DEFAULT_CATALOG_CSV)
    if "dataset_relative_path" not in frame.columns:
        raise ValueError("Post-hoc CIPI label join requires dataset_relative_path in the matrix.")
    if "dataset_relative_path" not in catalog_frame.columns or label_column not in catalog_frame.columns:
        raise ValueError(
            f"CIPI catalog must contain dataset_relative_path and {label_column!r} columns."
        )

    working_frame = frame.copy()
    working_frame["_normalized_dataset_relative_path"] = working_frame["dataset_relative_path"].map(_normalize_path_like)
    working_frame["_normalized_filename"] = working_frame.get("filename", "").map(_normalize_filename_like)

    catalog = catalog_frame.copy()
    catalog["_normalized_dataset_relative_path"] = catalog["dataset_relative_path"].map(_normalize_path_like)
    catalog["_normalized_filename"] = catalog.get("filename", "").map(_normalize_filename_like)

    label_catalog = _aggregate_catalog_labels(catalog, label_column)
    working_frame = working_frame.merge(
        label_catalog,
        how="left",
        on="_normalized_dataset_relative_path",
        suffixes=("", "_catalog"),
    )

    working_frame["label_join_source"] = np.where(
        working_frame[f"{label_column}_catalog_primary"].notna(),
        "dataset_relative_path",
        pd.NA,
    )

    unmatched_mask = working_frame[f"{label_column}_catalog_primary"].isna()
    if unmatched_mask.any():
        filename_catalog = _aggregate_catalog_labels(catalog, label_column, key_column="_normalized_filename")
        fallback_frame = working_frame.loc[unmatched_mask, ["_normalized_filename"]].merge(
            filename_catalog,
            how="left",
            on="_normalized_filename",
            suffixes=("", "_fallback"),
        )
        for column in [
            f"{label_column}_catalog_primary",
            f"{label_column}_catalog_values",
            f"{label_column}_catalog_value_count",
        ]:
            working_frame.loc[unmatched_mask, column] = fallback_frame[column].to_numpy()
        fallback_joined = working_frame.loc[unmatched_mask, f"{label_column}_catalog_primary"].notna()
        working_frame.loc[unmatched_mask & fallback_joined, "label_join_source"] = "filename_fallback"

    if label_column not in working_frame.columns:
        working_frame[label_column] = working_frame[f"{label_column}_catalog_primary"]
    else:
        working_frame[label_column] = working_frame[label_column].fillna(
            working_frame[f"{label_column}_catalog_primary"]
        )

    diagnostics = {
        "join_key": "dataset_relative_path + filename fallback",
        "catalog_path": str(Path(catalog_path or DEFAULT_CATALOG_CSV)),
        "joined_rows": int(working_frame[label_column].notna().sum()),
        "rows_joined_via_filename_fallback": int((working_frame["label_join_source"] == "filename_fallback").sum()),
        "rows_with_multiple_catalog_labels": int(
            (working_frame.get(f"{label_column}_catalog_value_count", pd.Series(dtype=float)).fillna(0) > 1).sum()
        ),
    }

    drop_columns = ["_normalized_dataset_relative_path", "_normalized_filename"]
    working_frame = working_frame.drop(columns=[column for column in drop_columns if column in working_frame.columns])
    return working_frame, diagnostics


def _aggregate_catalog_labels(
    catalog: pd.DataFrame,
    label_column: str,
    key_column: str = "_normalized_dataset_relative_path",
) -> pd.DataFrame:
    rows = []
    for key, group in catalog.groupby(key_column):
        labels = [
            int(value) if float(value).is_integer() else float(value)
            for value in pd.to_numeric(group[label_column], errors="coerce").dropna().tolist()
        ]
        if not labels:
            continue
        unique_labels = sorted(dict.fromkeys(labels))
        rows.append(
            {
                key_column: key,
                f"{label_column}_catalog_primary": unique_labels[0],
                f"{label_column}_catalog_values": "|".join(str(label) for label in unique_labels),
                f"{label_column}_catalog_value_count": len(unique_labels),
            }
        )
    return pd.DataFrame(rows)


def _normalize_path_like(value: Any) -> str:
    return _normalize_text(str(value or "").replace("\\", "/"))


def _normalize_filename_like(value: Any) -> str:
    return _normalize_text(Path(str(value or "")).name)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()
