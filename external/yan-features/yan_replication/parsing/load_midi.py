from __future__ import annotations

from pathlib import Path

from music21 import converter, stream


def load_midi_score(path: str | Path) -> stream.Score:
    parsed = converter.parse(str(path))
    if not isinstance(parsed, stream.Score):
        parsed = parsed.makeMeasures().stream()
    return parsed
