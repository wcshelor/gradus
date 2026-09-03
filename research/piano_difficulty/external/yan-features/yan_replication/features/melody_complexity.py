from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

import numpy as np

from yan_replication.parsing.normalize_events import NoteEvent

EXPERIMENTAL_MELODY_COMPLEXITY_BACKEND = "music21-proxy"

_KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88], dtype=float)
_KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17], dtype=float)
_SIMONTON_TRANSITIONS = np.zeros((12, 12), dtype=float)
_SIMONTON_TRANSITIONS[3, :] = 0.005
_SIMONTON_TRANSITIONS[:, 3] = 0.005
_SIMONTON_TRANSITIONS[8, :] = 0.005
_SIMONTON_TRANSITIONS[:, 8] = 0.005
_SIMONTON_TRANSITIONS[10, :] = 0.005
_SIMONTON_TRANSITIONS[:, 10] = 0.005
_SIMONTON_TRANSITIONS[6, 7] = 0.005
_SIMONTON_TRANSITIONS[7, 6] = 0.005
_SIMONTON_TRANSITIONS[7, 7] = 0.067
_SIMONTON_TRANSITIONS[0, 0] = 0.053
_SIMONTON_TRANSITIONS[7, 0] = 0.049
_SIMONTON_TRANSITIONS[0, 2] = 0.044
_SIMONTON_TRANSITIONS[0, 11] = 0.032
_SIMONTON_TRANSITIONS[0, 7] = 0.032
_SIMONTON_TRANSITIONS[7, 5] = 0.031
_SIMONTON_TRANSITIONS[4, 4] = 0.030
_SIMONTON_TRANSITIONS[4, 2] = 0.030
_SIMONTON_TRANSITIONS[2, 0] = 0.030
_SIMONTON_TRANSITIONS[7, 4] = 0.029
_SIMONTON_TRANSITIONS[7, 9] = 0.029
_SIMONTON_TRANSITIONS[4, 5] = 0.028
_SIMONTON_TRANSITIONS[4, 7] = 0.026
_SIMONTON_TRANSITIONS[2, 4] = 0.024
_SIMONTON_TRANSITIONS[11, 0] = 0.023
_SIMONTON_TRANSITIONS[0, 4] = 0.022
_SIMONTON_TRANSITIONS[5, 7] = 0.021
_SIMONTON_TRANSITIONS[5, 4] = 0.021
_SIMONTON_TRANSITIONS[9, 7] = 0.020
_SIMONTON_TRANSITIONS[3, 2] = 0.018
_SIMONTON_TRANSITIONS[4, 0] = 0.016
_SIMONTON_TRANSITIONS[2, 3] = 0.014
_SIMONTON_TRANSITIONS[9, 11] = 0.012
_SIMONTON_TRANSITIONS[11, 9] = 0.011
_SIMONTON_TRANSITIONS[2, 2] = 0.011
_SIMONTON_TRANSITIONS[8, 7] = 0.011


def _duraccent(durations: np.ndarray, tau: float = 0.5, accent_index: float = 2.0) -> np.ndarray:
    durations = np.asarray(durations, dtype=float)
    durations = np.maximum(durations, 0.0)
    return np.power(1.0 - np.exp(-durations / tau), accent_index)


def _entropy_from_weights(weights: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=float)
    total = float(np.sum(weights))
    if total <= 0.0:
        return 0.0
    probs = weights / total
    probs = probs[probs > 0]
    if probs.size == 0:
        return 0.0
    return float(-np.sum(probs * np.log2(probs)))


def _sorted_events(events: Sequence[NoteEvent]) -> list[NoteEvent]:
    return sorted(events, key=lambda e: (e.onset_quarter, e.duration_quarter, e.midi_pitch))


def _reduce_to_monophonic_melody(events: Sequence[NoteEvent]) -> list[NoteEvent]:
    """Experimental monophonic reduction used by the Yan replication lab.

    The MIDI Toolbox code assumes monophonic input. For MusicXML/MXL we keep the
    reduction explicit and simple: for each onset, retain the highest pitch.
    """

    by_onset: dict[float, list[NoteEvent]] = defaultdict(list)
    for event in _sorted_events(events):
        by_onset[event.onset_quarter].append(event)

    melody: list[NoteEvent] = []
    for onset in sorted(by_onset):
        onset_events = by_onset[onset]
        melody.append(max(onset_events, key=lambda e: (e.midi_pitch, e.duration_quarter)))
    return melody


def _normalised_pitch_class_profile(melody: Sequence[NoteEvent]) -> np.ndarray:
    if not melody:
        return np.zeros(12, dtype=float)
    weights = _duraccent(np.array([e.duration_quarter for e in melody], dtype=float))
    profile = np.zeros(12, dtype=float)
    for event, weight in zip(melody, weights, strict=False):
        profile[event.midi_pitch % 12] += float(weight)
    total = float(profile.sum())
    return profile / total if total > 0 else profile


def _weighted_interval_profile(melody: Sequence[NoteEvent]) -> np.ndarray:
    profile = np.zeros(25, dtype=float)
    if len(melody) < 2:
        return profile
    weights = _duraccent(np.array([e.duration_quarter for e in melody], dtype=float))
    for idx in range(1, len(melody)):
        interval = melody[idx].midi_pitch - melody[idx - 1].midi_pitch
        if abs(interval) <= 12:
            profile[interval + 12] += float(weights[idx - 1] + weights[idx])
    total = float(profile.sum())
    return profile / total if total > 0 else profile


def _duration_profile(melody: Sequence[NoteEvent]) -> np.ndarray:
    durations = np.array([e.duration_quarter for e in melody if e.duration_quarter > 0], dtype=float)
    if durations.size == 0:
        return np.zeros(9, dtype=float)
    bins = np.round(2.0 * np.log2(durations))
    bins = bins[np.abs(bins) <= 4]
    bins = bins + 5
    profile = np.zeros(9, dtype=float)
    for idx in bins.astype(int):
        profile[idx - 1] += 1.0
    total = float(profile.sum())
    return profile / total if total > 0 else profile


def _note_density(melody: Sequence[NoteEvent]) -> float:
    if not melody:
        return math.nan
    onsets = np.array([e.onset_quarter for e in melody], dtype=float)
    ends = np.array([e.onset_quarter + e.duration_quarter for e in melody], dtype=float)
    span = float(np.max(ends) - np.min(onsets))
    if span <= 0:
        return math.nan
    return float(len(melody) / span)


def _tonality_profile(melody: Sequence[NoteEvent]) -> tuple[int, np.ndarray]:
    profile = _normalised_pitch_class_profile(melody)
    if not np.any(profile):
        return 0, _KK_MAJOR

    best_score = -np.inf
    best_root = 0
    best_profile = _KK_MAJOR

    for root in range(12):
        major = np.roll(_KK_MAJOR, root)
        minor = np.roll(_KK_MINOR, root)
        for candidate in (major, minor):
            if np.std(candidate) == 0 or np.std(profile) == 0:
                score = 0.0
            else:
                score = float(np.corrcoef(profile, candidate)[0, 1])
            if np.isnan(score):
                score = -np.inf
            if score > best_score:
                best_score = score
                best_root = root
                best_profile = candidate
    return best_root, best_profile


def _tonality_values(melody: Sequence[NoteEvent]) -> np.ndarray:
    if not melody:
        return np.array([], dtype=float)
    _, key_profile = _tonality_profile(melody)
    return np.array([float(key_profile[event.midi_pitch % 12]) for event in melody], dtype=float)


def _meteraccent_proxy(melody: Sequence[NoteEvent]) -> float:
    if not melody:
        return math.nan
    beat_strength = np.array([0.5 if event.beat_strength is None else float(event.beat_strength) for event in melody], dtype=float)
    beat_strength = np.clip(beat_strength, 0.0, None)
    dur_acc = _duraccent(np.array([e.duration_quarter for e in melody], dtype=float))
    return float(-np.mean(beat_strength * dur_acc))


def compute_melodic_complexity_experimental(events: Sequence[NoteEvent]) -> float:
    """Experimental proxy for Yan MC1.

    This mirrors the MIDI Toolbox `complebm(..., "o")` composite score as a
    score-parsed approximation rather than a bit-for-bit reproduction.
    """

    melody = _reduce_to_monophonic_melody(events)
    if not melody:
        return math.nan

    pitches = np.array([e.midi_pitch for e in melody], dtype=float)
    durations = np.array([e.duration_quarter for e in melody], dtype=float)
    intervals = np.diff(pitches)
    dur_acc = _duraccent(durations)
    pcd = _normalised_pitch_class_profile(melody)
    ivd = _weighted_interval_profile(melody)
    durd = _duration_profile(melody)
    tonality = _tonality_values(melody)
    note_density = _note_density(melody)

    # Experimental proxies for the MATLAB `complebm` components.
    aveint_ = float(np.mean(intervals) * 0.2) if intervals.size else 0.0
    pcd1_ = _entropy_from_weights(pcd) * 1.5
    ivd1_ = _entropy_from_weights(ivd) * 1.3
    ton_ = float(np.mean(dur_acc * tonality) * -1.0) if tonality.size else 0.0
    dud_ = _entropy_from_weights(durd) * 0.5
    noteden_ = note_density * 0.4 if not math.isnan(note_density) else 0.0

    positive_durations = durations[durations > 0]
    rhyvar_ = float(np.std(np.log(positive_durations)) * 0.9) if positive_durations.size else 0.0
    metach_ = _meteraccent_proxy(melody) * 0.8

    constant = -1.9025
    y = (constant + aveint_ + pcd1_ + ivd1_ + ton_ + dud_ + noteden_ + rhyvar_ + metach_) / 1.5034
    return float(y + 5.0)


def compute_melodic_originality_experimental(events: Sequence[NoteEvent]) -> float:
    """Experimental proxy for Yan MC2.

    This mirrors the MIDI Toolbox `compltrans` score on the reduced melodic
    line. The transition table is copied from the toolbox reference matrix.
    """

    melody = _reduce_to_monophonic_melody(events)
    if len(melody) < 2:
        return math.nan

    pcs = np.array([event.midi_pitch % 12 for event in melody], dtype=int)
    pcd = np.zeros((12, 12), dtype=float)
    for idx in range(1, len(pcs)):
        pcd[pcs[idx - 1], pcs[idx]] += 1.0

    total = pcd * _SIMONTON_TRANSITIONS
    s = -float(np.sum(total) / (len(pcs) - 1))
    return float((s + 0.0530) * 188.68)


def compute_degree_of_melodiousness_experimental(events: Sequence[NoteEvent]) -> float:
    """Experimental proxy for Yan MC3.

    This mirrors the MIDI Toolbox `gradus` score on the reduced melodic line.
    Lower values still indicate a more melodious line.
    """

    melody = _reduce_to_monophonic_melody(events)
    if len(melody) < 2:
        return math.nan

    intervals = np.abs(np.diff([event.midi_pitch for event in melody])) % 12
    frq1 = np.array([1, 16, 9, 6, 5, 4, 45, 3, 8, 5, 16, 15], dtype=int)
    frq2 = np.array([1, 15, 8, 5, 4, 3, 32, 2, 5, 3, 9, 8], dtype=int)

    gs: list[float] = []
    for interval in intervals:
        g = int(frq1[int(interval)] * frq2[int(interval)])
        # Recompute the MATLAB `factor`-based score in plain Python.
        rem = g
        prime_factors: list[int] = []
        divisor = 2
        while rem > 1 and divisor * divisor <= rem:
            while rem % divisor == 0:
                prime_factors.append(divisor)
                rem //= divisor
            divisor += 1
        if rem > 1:
            prime_factors.append(rem)
        if prime_factors:
            gs.append(float(sum(p - 1 for p in prime_factors) + 1))
        else:
            gs.append(1.0)
    return float(np.mean(gs))


def compute_melody_complexity_features_experimental(events: Sequence[NoteEvent]) -> dict[str, float]:
    return {
        "MC1": compute_melodic_complexity_experimental(events),
        "MC2": compute_melodic_originality_experimental(events),
        "MC3": compute_degree_of_melodiousness_experimental(events),
    }


def compute_melody_complexity_features(events: Sequence[NoteEvent]) -> dict[str, float]:
    """Backward-compatible public entry point for the experimental proxies."""

    return compute_melody_complexity_features_experimental(events)
