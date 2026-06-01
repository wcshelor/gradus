from pathlib import Path

from yan_replication.reference.load_reference import load_yan_reference


def test_load_reference_shapes():
    root = Path(__file__).resolve().parents[1]
    ref = load_yan_reference("EN", "old", root=root)
    assert ref.X.shape == (677, 39)
    assert ref.y is not None
    assert ref.y.shape == (677,)
