from __future__ import annotations

from pathlib import Path

import pandas as pd

from .manifest_schema import MANIFEST_COLUMNS


def ensure_manifest(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        pd.DataFrame(columns=MANIFEST_COLUMNS).to_csv(p, index=False)
    return p
