from __future__ import annotations

from pathlib import Path


def write_diagnostic_note(path: str | Path, lines: list[str]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n")
    return p
