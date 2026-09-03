"""Shared helpers for matrix-backed experiment harnesses."""

from .matrix_data import LoadedMatrix, MatrixLoadOptions, load_dataset_matrix, load_matrix
from .matrix_features import (
    DEFAULT_METADATA_COLUMNS,
    FEATURE_SET_SPECS,
    OG_PHP_FEATURES,
    RUNTIME_FAMILY_PREFIXES,
    SEBASTIEN_CLUSTERING_FEATURES,
    FeatureSelectionReport,
    FeatureSetSpec,
    select_feature_columns,
)
from .runtime_matrix_export import (
    MATRIX_METADATA_COLUMNS,
    RuntimeExportInput,
    RuntimeMatrixExportResult,
    RuntimePieceExportResult,
    run_runtime_matrix_export,
)

__all__ = [
    "DEFAULT_METADATA_COLUMNS",
    "FEATURE_SET_SPECS",
    "MATRIX_METADATA_COLUMNS",
    "OG_PHP_FEATURES",
    "RUNTIME_FAMILY_PREFIXES",
    "SEBASTIEN_CLUSTERING_FEATURES",
    "FeatureSelectionReport",
    "FeatureSetSpec",
    "LoadedMatrix",
    "MatrixLoadOptions",
    "RuntimeExportInput",
    "RuntimeMatrixExportResult",
    "RuntimePieceExportResult",
    "load_dataset_matrix",
    "load_matrix",
    "run_runtime_matrix_export",
    "select_feature_columns",
]
