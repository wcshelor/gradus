from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def snapshot_json(payload: dict[str, object]) -> str:
    normalized = copy.deepcopy(payload)
    source = normalized.get("source")
    if isinstance(source, dict):
        path_value = source.get("path")
        if isinstance(path_value, str):
            source["path"] = _normalize_path(path_value)
    return json.dumps(normalized, sort_keys=True, indent=2) + "\n"


def _normalize_path(path_value: str) -> str:
    path = Path(path_value)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
