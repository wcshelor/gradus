"""Hand-shape and hand-position descriptors — vertical span, chord-shape variability,
chord-tone motion (sorted pitch only), and likely hand-position (center) shifts.

Provenance: Gradus experimental; not Yan-derived. Yan-adjacent: related to
``hand_stretch``/``chord_number`` families but formulas are Gradus-defined.
Does not infer fingering, independent voices, or voice-leading.
Chord-tone comparisons are sorted-pitch comparisons only.

Thresholds:
- large_span_threshold = 12 semitones
- comfortable_span_threshold = 9 semitones
- large_center_shift_threshold = 7 semitones
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from fractions import Fraction

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import (
    feature_record,
    score_duration_quarters,
)
from piano_difficulty.normalize.schema import LogicalNoteIR, ScoreIR

LARGE_SPAN_THRESHOLD = 12
COMFORTABLE_SPAN_THRESHOLD = 9
LARGE_CENTER_SHIFT_THRESHOLD = 7
UNMATCHED_PENALTY_PER_TONE = 6

_Diagnostics = list[str]

_COMMON_PROVENANCE: list[str] = [
    "Gradus experimental: vertical hand-shape feature; not Yan-derived.",
    "Yan-adjacent: related to hand_stretch/chord_number families, formula is Gradus-defined.",
    "Does not infer fingering, independent voices, or voice-leading.",
]

_SPAN_THRESHOLDS_NOTE = "large_span_threshold=12 semitones."
_COMFORTABLE_NOTE = "comfortable_span_threshold=9 semitones."
_CENTER_THRESH_NOTE = "large_center_shift_threshold=7 semitones."
_EDIT_NOTE = "unmatched_penalty=6 semitones per extra chord tone."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _HandOnset:
    """One hand-specific onset snapshot."""

    __slots__ = (
        "onset",
        "pitches",
        "note_count",
        "span",
        "center",
        "fingerprint",
        "is_chordal",
        "is_octave",
    )

    def __init__(self, onset: Fraction, pitches: list[int]) -> None:
        self.onset = onset
        self.pitches = sorted(pitches)
        self.note_count = len(self.pitches)
        if self.note_count >= 2:
            self.span = max(self.pitches) - min(self.pitches)
            self.center = (min(self.pitches) + max(self.pitches)) / 2.0
            self.fingerprint: tuple[int, ...] = tuple(p - min(self.pitches) for p in self.pitches)
            self.is_chordal = True
        else:
            self.span = 0
            # single note: center is the pitch itself
            self.center = float(self.pitches[0]) if self.pitches else 0.0
            self.fingerprint = (0,) if self.pitches else ()
            self.is_chordal = False
        # octave if any pair is exactly 12 semitones apart
        self.is_octave = False
        if self.note_count >= 2:
            pitch_set = set(self.pitches)
            for p in self.pitches:
                if (p + 12) in pitch_set or (p - 12) in pitch_set:
                    self.is_octave = True
                    break


def _build_hand_onsets(score: ScoreIR, hand: str) -> list[_HandOnset]:
    """Group logical notes by exact onset for one hand."""

    grouped: dict[Fraction, list[int]] = defaultdict(list)
    for note in score.logical_notes:
        if note.hand == hand:
            grouped[note.onset].append(note.pitch_midi)
    if not grouped:
        return []
    result: list[_HandOnset] = []
    for onset in sorted(grouped.keys()):
        pitches = sorted(grouped[onset])
        result.append(_HandOnset(onset, pitches))
    return result


def _hand_notes(score: ScoreIR, hand: str) -> list[LogicalNoteIR]:
    return [n for n in score.logical_notes if n.hand == hand]


def _population_stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _is_parallel(motion: list[int]) -> bool:
    """Parallel check per spec."""
    if not motion:
        return True
    if all(v == motion[0] for v in motion):
        return True
    nonzero = [v for v in motion if v != 0]
    if not nonzero:
        return True  # all zero handled above but keep safe
    if not all(v > 0 for v in nonzero) and not all(v < 0 for v in nonzero):
        return False
    # all nonzero same sign — check range <=1
    if max(motion) - min(motion) <= 1:
        return True
    return False


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def extract(score: ScoreIR) -> list[FeatureRecord]:
    records: list[FeatureRecord] = []
    duration = score_duration_quarters(score)

    for hand in ("right", "left"):
        hand_notes = _hand_notes(score, hand)
        onsets = _build_hand_onsets(score, hand)
        hand_onset_count = len(onsets)
        chordal_onsets = [o for o in onsets if o.is_chordal]
        chordal_count = len(chordal_onsets)

        # Precompute transition helpers
        chordal_transition_count = max(0, chordal_count - 1)

        # For same-size transitions
        # Build list of consecutive chordal pairs (for chord-shape derived) vs
        # eligible same-size pairs.
        chordal_pairs = list(zip(chordal_onsets, chordal_onsets[1:])) if chordal_count >= 2 else []

        # --- Span / chord size features ---

        # 1. octave_onset_rate
        octave_count = sum(1 for o in onsets if o.is_octave)
        if hand_onset_count == 0:
            records.append(
                feature_record(
                    "hand_shape.octave_onset_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["No hand onsets; feature not applicable."],
                )
            )
        else:
            records.append(
                feature_record(
                    "hand_shape.octave_onset_rate",
                    value=octave_count / hand_onset_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_SPAN_THRESHOLDS_NOTE, "Octave defined as any pitch pair exactly 12 semitones apart."],
                )
            )

        # 2. large_span_onset_rate
        large_span_count = sum(1 for o in onsets if o.span >= LARGE_SPAN_THRESHOLD)
        if hand_onset_count == 0:
            records.append(
                feature_record(
                    "hand_shape.large_span_onset_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_SPAN_THRESHOLDS_NOTE, "No hand onsets; feature not applicable."],
                )
            )
        else:
            records.append(
                feature_record(
                    "hand_shape.large_span_onset_rate",
                    value=large_span_count / hand_onset_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_SPAN_THRESHOLDS_NOTE],
                )
            )

        # 3. mean_large_span_burden
        if hand_onset_count == 0:
            records.append(
                feature_record(
                    "hand_shape.mean_large_span_burden",
                    value=0.0,
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_COMFORTABLE_NOTE, "No hand onsets; feature not applicable."],
                )
            )
        else:
            burdens = [max(0, o.span - COMFORTABLE_SPAN_THRESHOLD) for o in onsets]
            val = sum(burdens) / len(burdens) if burdens else 0.0
            records.append(
                feature_record(
                    "hand_shape.mean_large_span_burden",
                    value=float(val),
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_COMFORTABLE_NOTE],
                )
            )

        # 4. wide_chord_density
        wide_chord_count = sum(1 for o in onsets if o.is_chordal and o.span >= LARGE_SPAN_THRESHOLD)
        if duration <= 0:
            records.append(
                feature_record(
                    "hand_shape.wide_chord_density",
                    value=0.0,
                    units="onsets_per_quarter",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_SPAN_THRESHOLDS_NOTE, "Region duration is zero; density not applicable."],
                )
            )
        else:
            val = float(wide_chord_count) / float(duration)
            records.append(
                feature_record(
                    "hand_shape.wide_chord_density",
                    value=val,
                    units="onsets_per_quarter",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_SPAN_THRESHOLDS_NOTE],
                )
            )

        # 5. repeated_octave_texture_rate
        if chordal_transition_count == 0:
            records.append(
                feature_record(
                    "hand_shape.repeated_octave_texture_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            repeated_octave = sum(
                1 for a, b in chordal_pairs if a.is_octave and b.is_octave
            )
            records.append(
                feature_record(
                    "hand_shape.repeated_octave_texture_rate",
                    value=repeated_octave / chordal_transition_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [],
                )
            )

        # 6. chord_shape_change_rate
        if chordal_transition_count == 0:
            records.append(
                feature_record(
                    "hand_shape.chord_shape_change_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            changes = sum(1 for a, b in chordal_pairs if a.fingerprint != b.fingerprint)
            records.append(
                feature_record(
                    "hand_shape.chord_shape_change_rate",
                    value=changes / chordal_transition_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Chord shape compared via interval fingerprint tuple."],
                )
            )

        # 7. chord_shape_entropy
        if chordal_count == 0:
            records.append(
                feature_record(
                    "hand_shape.chord_shape_entropy",
                    value=0.0,
                    units="bits",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            counter = Counter(o.fingerprint for o in chordal_onsets)
            total = chordal_count
            entropy = -sum((c / total) * math.log2(c / total) for c in counter.values() if c > 0)
            records.append(
                feature_record(
                    "hand_shape.chord_shape_entropy",
                    value=float(entropy),
                    units="bits",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Shannon entropy over chord-shape fingerprints among chordal onsets."],
                )
            )

        # 8. chord_shape_edit_distance_mean
        if chordal_transition_count == 0:
            records.append(
                feature_record(
                    "hand_shape.chord_shape_edit_distance_mean",
                    value=0.0,
                    units="semitones_per_chord_tone",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_EDIT_NOTE, "Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            distances: list[float] = []
            for a, b in chordal_pairs:
                f1 = a.fingerprint
                f2 = b.fingerprint
                matched_len = min(len(f1), len(f2))
                matched_cost = sum(abs(f1[i] - f2[i]) for i in range(matched_len))
                unmatched_count = abs(len(f1) - len(f2))
                raw = matched_cost + UNMATCHED_PENALTY_PER_TONE * unmatched_count
                max_len = max(len(f1), len(f2))
                distances.append(raw / max_len if max_len else 0.0)
            mean_dist = sum(distances) / len(distances) if distances else 0.0
            records.append(
                feature_record(
                    "hand_shape.chord_shape_edit_distance_mean",
                    value=float(mean_dist),
                    units="semitones_per_chord_tone",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_EDIT_NOTE],
                )
            )

        # 9. chord_size_change_rate
        if chordal_transition_count == 0:
            records.append(
                feature_record(
                    "hand_shape.chord_size_change_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            size_changes = sum(1 for a, b in chordal_pairs if a.note_count != b.note_count)
            records.append(
                feature_record(
                    "hand_shape.chord_size_change_rate",
                    value=size_changes / chordal_transition_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [],
                )
            )

        # 10. repeated_shape_ratio
        if chordal_transition_count == 0:
            records.append(
                feature_record(
                    "hand_shape.repeated_shape_ratio",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Fewer than 2 chordal onsets; no eligible chordal transitions."],
                )
            )
        else:
            repeated = sum(1 for a, b in chordal_pairs if a.fingerprint == b.fingerprint)
            records.append(
                feature_record(
                    "hand_shape.repeated_shape_ratio",
                    value=repeated / chordal_transition_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [],
                )
            )

        # 11. chord_tone_motion_variability (only same-size chordal transitions, note_count >=2)
        eligible_same = [(a, b) for a, b in chordal_pairs if a.note_count == b.note_count and a.note_count >= 2]
        eligible_same_count = len(eligible_same)
        if eligible_same_count == 0:
            records.append(
                feature_record(
                    "hand_shape.chord_tone_motion_variability",
                    value=0.0,
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE
                    + ["Fewer than 2 same-size chordal onsets; no eligible same-size chordal transitions. Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )
        else:
            per_transition_stds: list[float] = []
            for a, b in eligible_same:
                motion = [b.pitches[i] - a.pitches[i] for i in range(a.note_count)]
                per_transition_stds.append(_population_stddev([float(v) for v in motion]))
            val = sum(per_transition_stds) / len(per_transition_stds) if per_transition_stds else 0.0
            records.append(
                feature_record(
                    "hand_shape.chord_tone_motion_variability",
                    value=float(val),
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )

        # 12. nonparallel_chord_tone_motion_rate (same eligible)
        if eligible_same_count == 0:
            records.append(
                feature_record(
                    "hand_shape.nonparallel_chord_tone_motion_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE
                    + ["Fewer than 2 same-size chordal onsets; no eligible same-size chordal transitions. Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )
        else:
            nonparallel = 0
            for a, b in eligible_same:
                motion = [b.pitches[i] - a.pitches[i] for i in range(a.note_count)]
                if not _is_parallel(motion):
                    nonparallel += 1
            records.append(
                feature_record(
                    "hand_shape.nonparallel_chord_tone_motion_rate",
                    value=nonparallel / eligible_same_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )

        # 13. inner_chord_tone_change_rate (same-size, note_count >=3)
        eligible_inner = [(a, b) for a, b in chordal_pairs if a.note_count == b.note_count and a.note_count >= 3]
        eligible_inner_count = len(eligible_inner)
        if eligible_inner_count == 0:
            records.append(
                feature_record(
                    "hand_shape.inner_chord_tone_change_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE
                    + ["Fewer than 2 same-size chordal onsets with note_count >= 3; no eligible inner chord-tone transitions. Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )
        else:
            inner_changes = 0
            for a, b in eligible_inner:
                # normalize by lowest pitch already done via fingerprint, but inner = fingerprint[1:-1]
                inner_a = a.fingerprint[1:-1] if len(a.fingerprint) >= 3 else ()
                inner_b = b.fingerprint[1:-1] if len(b.fingerprint) >= 3 else ()
                if inner_a != inner_b:
                    inner_changes += 1
            records.append(
                feature_record(
                    "hand_shape.inner_chord_tone_change_rate",
                    value=inner_changes / eligible_inner_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Sorted-pitch comparison only; does not infer independent voices or voice-leading."],
                )
            )

        # 14-17 Hand position features (all consecutive hand onsets)
        hand_transition_count = max(0, hand_onset_count - 1)
        consecutive_pairs = list(zip(onsets, onsets[1:])) if hand_onset_count >= 2 else []
        center_shifts = [abs(b.center - a.center) for a, b in consecutive_pairs]

        # 14. hand_position.max_center_shift
        if hand_transition_count == 0:
            records.append(
                feature_record(
                    "hand_position.max_center_shift",
                    value=0.0,
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_CENTER_THRESH_NOTE, "Insufficient hand onsets; no eligible transitions. Likely hand-position shift (center shift), not literal repositioning."],
                )
            )
        else:
            records.append(
                feature_record(
                    "hand_position.max_center_shift",
                    value=float(max(center_shifts)) if center_shifts else 0.0,
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_CENTER_THRESH_NOTE, "Likely hand-position shift (center shift), not literal repositioning. Does not infer fingering."],
                )
            )

        # 15. hand_position.mean_center_shift
        if hand_transition_count == 0:
            records.append(
                feature_record(
                    "hand_position.mean_center_shift",
                    value=0.0,
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Insufficient hand onsets; no eligible transitions. Likely hand-position shift (center shift), not literal repositioning."],
                )
            )
        else:
            mean_shift = sum(center_shifts) / len(center_shifts) if center_shifts else 0.0
            records.append(
                feature_record(
                    "hand_position.mean_center_shift",
                    value=float(mean_shift),
                    units="semitones",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Likely hand-position shift (center shift), not literal repositioning. Does not infer fingering."],
                )
            )

        # 16. hand_position.large_center_shift_rate
        if hand_transition_count == 0:
            records.append(
                feature_record(
                    "hand_position.large_center_shift_rate",
                    value=0.0,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_CENTER_THRESH_NOTE, "Insufficient hand onsets; no eligible transitions. Likely hand-position shift, not literal repositioning."],
                )
            )
        else:
            large_count = sum(1 for s in center_shifts if s >= LARGE_CENTER_SHIFT_THRESHOLD)
            records.append(
                feature_record(
                    "hand_position.large_center_shift_rate",
                    value=large_count / hand_transition_count,
                    units="ratio",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [_CENTER_THRESH_NOTE, "Likely hand-position shift (center shift), not literal repositioning."],
                )
            )

        # 17. hand_position.timed_center_shift
        # mean(center_shift / onset_gap) over transitions with onset_gap > 0
        timed_values: list[float] = []
        for a, b in consecutive_pairs:
            gap = b.onset - a.onset
            if gap <= 0:
                continue
            shift = abs(b.center - a.center)
            timed_values.append(shift / float(gap))
        if not timed_values:
            # denominator zero case: no positive gaps
            if hand_transition_count == 0:
                diag_extra = "Insufficient hand onsets; no eligible transitions."
            else:
                diag_extra = "No transitions with positive onset gap; timed center shift not applicable."
            records.append(
                feature_record(
                    "hand_position.timed_center_shift",
                    value=0.0,
                    units="semitones_per_quarter",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + [diag_extra, "Timed center shift ignores transitions with onset_gap <= 0. Likely hand-position shift, not literal repositioning."],
                )
            )
        else:
            val = sum(timed_values) / len(timed_values)
            records.append(
                feature_record(
                    "hand_position.timed_center_shift",
                    value=float(val),
                    units="semitones_per_quarter",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                    diagnostics=_COMMON_PROVENANCE + ["Timed center shift ignores transitions with onset_gap <= 0. Likely hand-position shift, not literal repositioning."],
                )
            )

    return records
