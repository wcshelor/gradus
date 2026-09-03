from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class LoadedMatrix:
    dataset_name: str
    source_path: Path
    raw_frame: pd.DataFrame
    frame: pd.DataFrame
    status_filter_applied: bool


@dataclass(frozen=True, slots=True)
class MatrixLoadOptions:
    source_index_column: str | None = "source_row_index"
    status_column: str | None = "status"
    status_keep_values: tuple[str, ...] = ("success",)
    normalize_status_values: bool = True


def load_dataset_matrix(
    dataset_name: str,
    path: str | Path,
    *,
    options: MatrixLoadOptions | None = None,
) -> LoadedMatrix:
    return load_matrix(path, dataset_name=dataset_name, options=options)


def load_matrix(
    path: str | Path,
    *,
    dataset_name: str = "dataset",
    options: MatrixLoadOptions | None = None,
) -> LoadedMatrix:
    load_options = options or MatrixLoadOptions()
    source_path = Path(path).expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"Matrix CSV not found: {source_path}")

    raw_frame = pd.read_csv(source_path)
    if load_options.source_index_column and load_options.source_index_column not in raw_frame.columns:
        raw_frame.insert(0, load_options.source_index_column, np.arange(len(raw_frame), dtype=int))

    frame = raw_frame.copy()
    status_filter_applied = False
    if (
        load_options.status_column
        and load_options.status_column in raw_frame.columns
        and load_options.status_keep_values
    ):
        status_series = raw_frame[load_options.status_column].astype(str).str.strip()
        if load_options.normalize_status_values:
            status_series = status_series.str.lower()
            keep_values = tuple(str(value).strip().lower() for value in load_options.status_keep_values)
        else:
            keep_values = tuple(str(value).strip() for value in load_options.status_keep_values)
        frame = raw_frame.loc[status_series.isin(keep_values)].copy()
        status_filter_applied = True

    return LoadedMatrix(
        dataset_name=dataset_name.strip().lower(),
        source_path=source_path.resolve(),
        raw_frame=raw_frame,
        frame=frame,
        status_filter_applied=status_filter_applied,
    )


def load_oktav_matrix(
    path: str | Path,
    *,
    dataset_name: str = "oktav",
    options: MatrixLoadOptions | None = None,
) -> LoadedMatrix:
    return load_matrix(path, dataset_name=dataset_name, options=options)


__all__ = [
    "LoadedMatrix",
    "MatrixLoadOptions",
    "load_dataset_matrix",
    "load_matrix",
]
