from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from .feature_names import MANUAL_FEATURE_NAMES, try_load_feature_names


DATASETS = {"EN", "AMBPT"}
FEATURE_SETS = {"old", "new", "total"}


@dataclass
class ReferenceData:
    X: np.ndarray
    y: np.ndarray | None
    feature_names: list[str] | None
    metadata: dict[str, object]


def _find_primary_matrix(mat: dict) -> tuple[str, np.ndarray]:
    candidates = [(k, v) for k, v in mat.items() if not k.startswith("__")]
    if len(candidates) == 1:
        k, v = candidates[0]
        return k, np.asarray(v)
    for k, v in candidates:
        if isinstance(v, np.ndarray) and v.ndim == 2:
            return k, np.asarray(v)
    raise ValueError("Could not identify primary matrix key")


def _coerce_label(y: np.ndarray) -> np.ndarray:
    arr = np.asarray(y)
    if arr.ndim == 2 and 1 in arr.shape:
        arr = arr.reshape(-1)
    return arr


def load_yan_reference(dataset: str, feature_set: str, root: str | Path | None = None) -> ReferenceData:
    ds = dataset.upper()
    fs = feature_set.lower()
    if ds not in DATASETS:
        raise ValueError(f"Unsupported dataset: {dataset}")
    if fs not in FEATURE_SETS:
        raise ValueError(f"Unsupported feature_set: {feature_set}")

    base = Path(root) if root else Path(__file__).resolve().parents[2]
    x_path = base / f"{ds}_{fs}_features.mat"
    y_path = base / f"{ds}_label.mat"

    x_mat = loadmat(x_path)
    x_key, x = _find_primary_matrix(x_mat)

    y = None
    y_key = None
    if y_path.exists():
        y_mat = loadmat(y_path)
        y_key, y_raw = _find_primary_matrix(y_mat)
        y = _coerce_label(y_raw)

    feature_names = None
    feature_name_info = None
    if fs in {"old", "new", "total"}:
        fn_file = base / f"feature_name_{fs}.mat"
        if fn_file.exists():
            feature_name_info = try_load_feature_names(fn_file)
            if feature_name_info.get("decoded_names"):
                feature_names = list(feature_name_info["decoded_names"])
    if not feature_names and fs in MANUAL_FEATURE_NAMES:
        feature_names = MANUAL_FEATURE_NAMES[fs]

    return ReferenceData(
        X=np.asarray(x, dtype=float),
        y=y,
        feature_names=feature_names,
        metadata={
            "dataset": ds,
            "feature_set": fs,
            "matrix_file": str(x_path),
            "matrix_key": x_key,
            "label_file": str(y_path) if y_path.exists() else None,
            "label_key": y_key,
            "feature_name_info": feature_name_info,
        },
    )
