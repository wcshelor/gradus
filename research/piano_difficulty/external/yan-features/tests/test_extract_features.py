from pathlib import Path
import math

import pytest

music21 = pytest.importorskip("music21")
from music21 import meter, note, stream, key

from yan_replication.features.yan_table3_features import extract_first_pass_features
from yan_replication.parsing.load_midi import load_midi_score, load_score
from yan_replication.parsing.normalize_events import normalize_note_events


def test_extract_first_pass_features(tmp_path: Path):
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature("4/4"))
    p.append(key.KeySignature(0))
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
    assert "MC1" in feats and "MC2" in feats and "MC3" in feats
    assert math.isfinite(feats["MC1"])
    assert math.isfinite(feats["MC2"])
    assert math.isfinite(feats["MC3"])


def test_extract_first_pass_features_from_mxl(tmp_path: Path):
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature("4/4"))
    p.append(key.KeySignature(0))
    p.append(note.Note("C4", quarterLength=1.0))
    p.append(note.Note("D4", quarterLength=1.0))
    p.append(note.Note("E4", quarterLength=2.0))
    s.append(p)

    mxl_path = tmp_path / "simple.mxl"
    s.write("musicxml", fp=str(mxl_path))

    loaded = load_score(mxl_path)
    events = normalize_note_events(loaded)
    feats = extract_first_pass_features(events)

    assert len(events) == 3
    assert feats["note_count"] == 3.0
    assert math.isfinite(feats["MC1"])
