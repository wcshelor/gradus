from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(slots=True)
class LoadedMatrix:
    dataset_name: str
    source_path: Path
    raw_frame: pd.DataFrame
    frame: pd.DataFrame
    status_filter_applied: bool


def load_dataset_matrix(dataset_name: str, path: str | Path) -> LoadedMatrix:
    dataset = dataset_name.strip().lower()
    if dataset == "oktav":
        return load_oktav_matrix(path)
    if dataset == "cipi":
        return load_oktav_matrix(path, dataset_name="cipi")
    raise ValueError(f"Unsupported dataset '{dataset_name}'.")


def load_oktav_matrix(path: str | Path, *, dataset_name: str = "oktav") -> LoadedMatrix:
    csv_path = Path(path).expanduser()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    raw_frame = pd.read_csv(csv_path)
    raw_frame.insert(0, "source_row_index", np.arange(len(raw_frame), dtype=int))

    frame = raw_frame.copy()
    status_filter_applied = False
    if "status" in frame.columns:
        status_values = frame["status"].astype(str).str.strip().str.lower()
        if (status_values == "success").any():
            frame = frame[status_values == "success"].copy()
            status_filter_applied = True

    return LoadedMatrix(
        dataset_name=dataset_name,
        source_path=csv_path,
        raw_frame=raw_frame,
        frame=frame,
        status_filter_applied=status_filter_applied,
    )
