"""Deferred MIDI loading support.

MIDI is intentionally included in the scaffold to reserve the boundary, but it
is not part of the first implementation milestone. MIDI lacks much of the
notation detail required by this repository's main goals, so its eventual
support should carry explicit coverage limitations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_midi(path: str | Path) -> Any:
    """Load a MIDI file for future reduced-coverage extraction paths."""

    raise NotImplementedError("MIDI loading is deferred.")

