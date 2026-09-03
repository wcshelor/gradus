from __future__ import annotations

from pathlib import Path

from scipy.io import loadmat


MANUAL_FEATURE_NAMES = {
    "old": [
        "mean_pitch", "pitch_deviation", "pitch_range", "pitch_entropy", "hand_displacement_rate",
        "hand_stretch", "deviation_middle_c", "black_key_rate", "mean_note_duration",
        "note_duration_deviation", "playing_speed", "polyphony_rate", "distinct_stroke_rate",
        "irregular_rhythm", "length", "tempo", "key_signature",
    ],
    "new": [
        "CN", "ND", "PVE", "PV", "NDV", "PVV", "PSV", "SR", "DNR", "MC1", "MC2", "MC3",
    ],
}


def try_load_feature_names(path: str | Path) -> dict[str, object]:
    p = Path(path)
    mat = loadmat(p)
    user_keys = [k for k in mat if not k.startswith("__")]
    decoded: list[str] = []
    notes: list[str] = []
    for k in user_keys:
        obj = mat[k]
        if getattr(obj, "dtype", None) is not None and "O" in str(obj.dtype):
            notes.append("MATLAB opaque/object content could not be decoded with scipy.io.loadmat")
        if hasattr(obj, "tolist"):
            try:
                val = obj.tolist()
                if isinstance(val, list):
                    decoded.extend([str(x) for x in val if isinstance(x, str)])
            except Exception:
                pass
    return {
        "file": p.name,
        "keys": user_keys,
        "decoded_names": decoded,
        "notes": notes,
    }
