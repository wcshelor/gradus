from __future__ import annotations

import sys
from pathlib import Path


def add_repo_root_to_sys_path() -> None:
    root = Path(__file__).resolve().parents[2]
    candidates = [root, root / "src"]
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
