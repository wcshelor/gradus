from __future__ import annotations

from yan_replication.features.existing_features import compute_core_features
from yan_replication.parsing.normalize_events import NoteEvent


def extract_first_pass_features(events: list[NoteEvent]) -> dict[str, float]:
    features = compute_core_features(events)
    # TODO: Add full Yan existing feature set implementation.
    # TODO: Add Table 3 features: CN, ND, PVE, PV, NDV, PVV, PSV, SR, DNR.
    # TODO: Integrate MC1/MC2/MC3 via MATLAB MIDI Toolbox-compatible backend.
    return features
