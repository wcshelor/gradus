from pathlib import Path

import pytest

music21 = pytest.importorskip("music21")
from music21 import note, stream

from yan_replication.features.yan_table3_features import extract_first_pass_features
from yan_replication.parsing.load_midi import load_midi_score
from yan_replication.parsing.normalize_events import normalize_note_events


def test_extract_first_pass_features(tmp_path: Path):
    s = stream.Score()
    p = stream.Part()
    p.append(note.Note("C4", quarterLength=1.0))
    p.append(note.Note("E4", quarterLength=1.0))
    p.append(note.Note("G4", quarterLength=2.0))
    s.append(p)

    midi_path = tmp_path / "simple.mid"
    s.write("midi", fp=str(midi_path))

    loaded = load_midi_score(midi_path)
    events = normalize_note_events(loaded)
    feats = extract_first_pass_features(events)

    assert feats["note_count"] == 3.0
    assert feats["pitch_range"] == 7.0
