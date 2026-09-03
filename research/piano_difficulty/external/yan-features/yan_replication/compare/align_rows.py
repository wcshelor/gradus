from __future__ import annotations

import pandas as pd


def align_rows(ours: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Return aligned frames and a flag indicating trusted row-level alignment."""
    if len(ours) == len(reference):
        return ours.reset_index(drop=True), reference.reset_index(drop=True), False
    min_len = min(len(ours), len(reference))
    return ours.iloc[:min_len].reset_index(drop=True), reference.iloc[:min_len].reset_index(drop=True), False
