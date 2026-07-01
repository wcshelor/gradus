from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .core import TargetBundle, TargetSchemeConfig


def transform_target(raw_values: pd.Series, target_scheme: TargetSchemeConfig) -> TargetBundle:
    numeric_values = pd.to_numeric(raw_values, errors="coerce")
    if numeric_values.isna().any():
        raise ValueError("Target values must be numeric after filtering missing rows.")

    kind = target_scheme.kind.strip().lower()
    if kind == "continuous":
        return TargetBundle(
            kind=kind,
            raw_values=numeric_values.copy(),
            model_values=numeric_values.copy(),
        )

    if kind == "rounded_class":
        model_values = pd.Series(np.rint(numeric_values.to_numpy(dtype=float)).astype(int), index=numeric_values.index)
        class_labels = tuple(sorted(model_values.unique().tolist()))
        ordinal_map = {label: index for index, label in enumerate(class_labels)}
        return TargetBundle(
            kind=kind,
            raw_values=numeric_values.copy(),
            model_values=model_values,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
        )

    if kind == "quantile_bins":
        if not target_scheme.bins or target_scheme.bins < 2:
            raise ValueError("quantile_bins requires target_scheme.bins >= 2.")
        effective_bins = min(target_scheme.bins, int(numeric_values.nunique()))
        labels = list(range(1, effective_bins + 1))
        model_values = pd.qcut(
            numeric_values,
            q=effective_bins,
            labels=labels,
            duplicates="drop",
        )
        model_values = pd.Series(model_values.astype(int), index=numeric_values.index)
        class_labels = tuple(sorted(model_values.unique().tolist()))
        ordinal_map = {label: index for index, label in enumerate(class_labels)}
        return TargetBundle(
            kind=kind,
            raw_values=numeric_values.copy(),
            model_values=model_values,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
        )

    if kind == "custom_bins":
        if not target_scheme.bin_edges or len(target_scheme.bin_edges) < 2:
            raise ValueError("custom_bins requires at least two target_scheme.bin_edges.")
        labels = list(target_scheme.labels or range(1, len(target_scheme.bin_edges)))
        if len(labels) != len(target_scheme.bin_edges) - 1:
            raise ValueError("custom_bins labels must align with bin_edges - 1.")
        cut_values = pd.cut(
            numeric_values,
            bins=list(target_scheme.bin_edges),
            labels=labels,
            include_lowest=True,
        )
        if cut_values.isna().any():
            raise ValueError("custom_bins produced NaN labels; check that bin_edges cover the target range.")

        numeric_int_labels = all(
            isinstance(label, (int, np.integer)) and not isinstance(label, bool)
            for label in labels
        )
        if numeric_int_labels:
            model_values = pd.Series(cut_values.astype(int), index=numeric_values.index, dtype=int)
        else:
            model_values = pd.Series(cut_values.astype(object), index=numeric_values.index)

        class_labels = tuple(labels)
        ordinal_map = {label: index for index, label in enumerate(class_labels)}
        return TargetBundle(
            kind=kind,
            raw_values=numeric_values.copy(),
            model_values=model_values,
            class_labels=class_labels,
            ordinal_map=ordinal_map,
            bin_edges=tuple(float(edge) for edge in target_scheme.bin_edges),
        )

    raise ValueError(f"Unsupported target scheme kind {target_scheme.kind!r}.")

