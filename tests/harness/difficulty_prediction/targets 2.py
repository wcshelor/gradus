from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .core import TargetBundle, TargetSchemeConfig


def transform_target(values: pd.Series, scheme: TargetSchemeConfig) -> TargetBundle:
    series = pd.to_numeric(values, errors="coerce")
    if series.isna().any():
        raise ValueError("Target transformation received missing values after numeric coercion.")

    raw_values = series.to_numpy(dtype=float)
    kind = scheme.kind.strip().lower()

    if kind == "continuous":
        return TargetBundle(
            kind="regression",
            raw_values=raw_values,
            model_values=raw_values.copy(),
        )

    if kind == "rounded_class":
        labels = np.rint(raw_values).astype(int)
        class_labels = tuple(sorted({int(value) for value in labels.tolist()}))
        ordinal_map = {label: index for index, label in enumerate(class_labels)}
        model_values = np.asarray([int(value) for value in labels.tolist()], dtype=object)
        return TargetBundle(
            kind="classification",
            raw_values=raw_values,
            model_values=model_values,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
        )

    if kind == "quantile_bins":
        requested_bins = scheme.bins or 3
        if requested_bins < 2:
            raise ValueError("quantile_bins target scheme requires at least two bins.")
        qcut = pd.qcut(series, q=min(requested_bins, series.nunique()), labels=False, retbins=True, duplicates="drop")
        labels = qcut[0]
        if labels.isna().any():
            raise ValueError("quantile_bins target scheme produced missing class labels.")
        model_values = labels.astype(int).to_numpy()
        class_labels = tuple(range(int(model_values.max()) + 1))
        ordinal_map = {label: label for label in class_labels}
        bin_edges = tuple(float(value) for value in qcut[1].tolist())
        return TargetBundle(
            kind="classification",
            raw_values=raw_values,
            model_values=model_values,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
            bin_edges=bin_edges,
        )

    if kind == "custom_bins":
        if scheme.bin_edges is None:
            raise ValueError("custom_bins target scheme requires 'bin_edges'.")
        if len(scheme.bin_edges) < 3:
            raise ValueError("custom_bins target scheme requires at least two bins.")
        labels = pd.cut(series, bins=list(scheme.bin_edges), labels=False, include_lowest=True)
        if labels.isna().any():
            raise ValueError("custom_bins target scheme produced missing class labels.")
        model_values = labels.astype(int).to_numpy()
        if scheme.labels is not None:
            if len(scheme.labels) != len(scheme.bin_edges) - 1:
                raise ValueError("custom_bins labels must match the number of bins.")
            class_labels: tuple[Any, ...] = tuple(scheme.labels)
        else:
            class_labels = tuple(range(len(scheme.bin_edges) - 1))
        ordinal_map = {label: index for index, label in enumerate(class_labels)}
        if all(isinstance(label, (int, np.integer)) for label in class_labels):
            model_value_array = np.asarray(
                [class_labels[index] for index in model_values.tolist()],
                dtype=int,
            )
        else:
            model_value_array = np.asarray(
                [class_labels[index] for index in model_values.tolist()],
                dtype=object,
            )
        return TargetBundle(
            kind="classification",
            raw_values=raw_values,
            model_values=model_value_array,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
            bin_edges=scheme.bin_edges,
        )

    raise ValueError(
        f"Unsupported target scheme '{scheme.kind}'. Supported schemes: continuous, rounded_class, quantile_bins, custom_bins."
    )
