from __future__ import annotations

from pathlib import Path

from music21 import converter, stream


def load_score(path: str | Path) -> stream.Score:
    """Load a score file through music21.

    This experimental replication lab uses music21 as the score parser so the
    same entry point can handle MIDI, MusicXML, and compressed MXL files.
    """

    parsed = converter.parse(str(path))
    if not isinstance(parsed, stream.Score):
        parsed = parsed.makeMeasures().stream()
    return parsed


def load_midi_score(path: str | Path) -> stream.Score:
    """Backward-compatible alias for the score loader."""

    return load_score(path)
