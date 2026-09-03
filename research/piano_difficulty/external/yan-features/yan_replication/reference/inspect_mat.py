from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


@dataclass
class MatArrayInfo:
    key: str
    shape: tuple[int, ...]
    dtype: str
    python_type: str
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    object_sample: str | None = None


@dataclass
class MatFileInfo:
    path: Path
    arrays: list[MatArrayInfo]


def inspect_mat_file(path: str | Path) -> MatFileInfo:
    p = Path(path)
    content = loadmat(p)
    arrays: list[MatArrayInfo] = []
    for key, value in content.items():
        if key.startswith("__"):
            continue
        shape = tuple(getattr(value, "shape", ()))
        dtype = str(getattr(value, "dtype", type(value)))
        info = MatArrayInfo(
            key=key,
            shape=shape,
            dtype=dtype,
            python_type=type(value).__name__,
        )
        if isinstance(value, np.ndarray):
            if value.dtype == object and value.size:
                info.object_sample = repr(value.flat[0])
            elif np.issubdtype(value.dtype, np.number) and value.size:
                arr = np.asarray(value, dtype=float)
                info.min_value = float(np.nanmin(arr))
                info.max_value = float(np.nanmax(arr))
                info.mean_value = float(np.nanmean(arr))
        arrays.append(info)
    return MatFileInfo(path=p, arrays=arrays)


def inspect_all_mat_files(root: str | Path) -> list[MatFileInfo]:
    root_path = Path(root)
    return [inspect_mat_file(p) for p in sorted(root_path.glob("*.mat"))]


def format_inspection_report(files: list[MatFileInfo]) -> str:
    lines: list[str] = []
    for file_info in files:
        lines.append(f"{file_info.path.name}")
        for arr in file_info.arrays:
            lines.append(
                f"  - key={arr.key} shape={arr.shape} dtype={arr.dtype} type={arr.python_type}"
            )
            if arr.min_value is not None:
                lines.append(
                    f"    stats: min={arr.min_value:.6g} max={arr.max_value:.6g} mean={arr.mean_value:.6g}"
                )
            if arr.object_sample:
                lines.append(f"    sample: {arr.object_sample}")
    return "\n".join(lines)
