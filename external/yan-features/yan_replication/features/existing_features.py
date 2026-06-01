from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from yan_replication.parsing.normalize_events import NoteEvent


def compute_core_features(events: Sequence[NoteEvent]) -> dict[str, float]:
    if not events:
        return {
            "note_count": 0.0,
            "mean_pitch": float("nan"),
            "pitch_std": float("nan"),
            "pitch_range": float("nan"),
            "note_density": float("nan"),
            "chord_count": 0.0,
            "chord_rate": float("nan"),
        }

    pitches = np.array([e.midi_pitch for e in events], dtype=float)
    onsets = np.array([e.onset_quarter for e in events], dtype=float)
    durations = np.array([e.duration_quarter for e in events], dtype=float)

    total_duration = float(np.max(onsets + durations) - np.min(onsets)) if len(events) else 0.0
    note_count = float(len(events))
    chord_ids = {e.chord_id for e in events if e.chord_id is not None}
    chord_count = float(len(chord_ids))

    note_density = note_count / total_duration if total_duration > 0 else math.nan
    chord_rate = chord_count / total_duration if total_duration > 0 else math.nan

    return {
        "note_count": note_count,
        "mean_pitch": float(np.mean(pitches)),
        "pitch_std": float(np.std(pitches)),
        "pitch_range": float(np.max(pitches) - np.min(pitches)),
        "note_density": note_density,
        "chord_count": chord_count,
        "chord_rate": chord_rate,
    }
