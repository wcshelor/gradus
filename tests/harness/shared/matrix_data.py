from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class LoadedMatrix:
    raw_frame: pd.DataFrame
    frame: pd.DataFrame
    source_path: Path
    dataset_name: str
    status_filter_applied: bool


def load_dataset_matrix(dataset_name: str, path: str | Path) -> LoadedMatrix:
    normalized_dataset_name = dataset_name.strip().lower()
    if normalized_dataset_name in {"oktav", "cipi"}:
        return load_oktav_matrix(path, dataset_name=normalized_dataset_name)
    if not normalized_dataset_name:
        raise ValueError("dataset_name must be non-empty.")
    raise NotImplementedError(
        f"Unsupported dataset_name {dataset_name!r}. Expected one of: 'oktav', 'cipi'."
    )


def load_oktav_matrix(path: str | Path, dataset_name: str = "oktav") -> LoadedMatrix:
    source_path = Path(path).expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"Matrix CSV not found: {source_path}")

    raw_frame = pd.read_csv(source_path)
    if "source_row_index" not in raw_frame.columns:
        raw_frame.insert(0, "source_row_index", np.arange(len(raw_frame), dtype=int))

    status_filter_applied = False
    frame = raw_frame.copy()
    if "status" in raw_frame.columns:
        normalized_status = raw_frame["status"].astype(str).str.strip().str.lower()
        frame = raw_frame.loc[normalized_status == "success"].copy()
        status_filter_applied = True

    return LoadedMatrix(
        raw_frame=raw_frame,
        frame=frame,
        source_path=source_path.resolve(),
        dataset_name=dataset_name.strip().lower(),
        status_filter_applied=status_filter_applied,
    )

