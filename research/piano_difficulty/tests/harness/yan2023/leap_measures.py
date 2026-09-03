"""Shared hand-leap proxy helpers for Yan 2023 score experiments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from piano_difficulty.normalize.schema import LogicalNoteIR

LeapHandName = Literal["left", "right"]

DEFAULT_HAND_LEAP_NOTICEABLE_INTERVAL_SEMITONES = 8
DEFAULT_HAND_LEAP_DIFFICULT_INTERVAL_SEMITONES = 12
DEFAULT_HAND_LEAP_MAX_REST_BEATS = 2.0


@dataclass(frozen=True, slots=True)
class _LeapAttack:
    onset: Fraction
    duration: Fraction
    pitch_midi: int


def compute_hand_leap_proxy(
    logical_notes: Sequence[LogicalNoteIR],
    hand: LeapHandName,
    noticeable_interval_semitones: int = DEFAULT_HAND_LEAP_NOTICEABLE_INTERVAL_SEMITONES,
    difficult_interval_semitones: int = DEFAULT_HAND_LEAP_DIFFICULT_INTERVAL_SEMITONES,
    max_rest_beats: float = DEFAULT_HAND_LEAP_MAX_REST_BEATS,
) -> tuple[float, tuple[str, ...]]:
    """Return a gap-weighted hand-leap proxy for one hand-local attack stream."""

    attack_stream = _build_attack_stream(logical_notes, hand)
    if len(attack_stream) < 2:
        diagnostics = (
            f"hand_leap_hand={hand}",
            f"hand_leap_noticeable_threshold={noticeable_interval_semitones}",
            f"hand_leap_difficult_threshold={difficult_interval_semitones}",
            f"hand_leap_long_rest_limit_beats={max_rest_beats}",
            "hand_leap_transitions=0",
            "hand_leap_noticeable_count=0",
            "hand_leap_difficult_count=0",
            "hand_leap_long_rest_filtered=0",
            "hand_leap_average_attack_gap_beats=0.000",
            f"hand_leap_representative_pitch={_representative_pitch_strategy(hand)}",
        )
        return 0.0, diagnostics

    weighted_score = 0.0
    considered_transitions = 0
    noticeable_count = 0
    difficult_count = 0
    filtered_long_rests = 0
    attack_gap_sum = 0.0

    for left, right in zip(attack_stream, attack_stream[1:]):
        rest_gap_beats = max(float(right.onset - (left.onset + left.duration)), 0.0)
        if rest_gap_beats > max_rest_beats:
            filtered_long_rests += 1
            continue

        attack_gap_beats = max(float(right.onset - left.onset), 0.0)
        interval_semitones = abs(right.pitch_midi - left.pitch_midi)
        jump_weight = 0.0
        if interval_semitones >= noticeable_interval_semitones:
            jump_weight += 1.0
            noticeable_count += 1
        if interval_semitones >= difficult_interval_semitones:
            jump_weight += 1.0
            difficult_count += 1
        if jump_weight == 0.0:
            considered_transitions += 1
            attack_gap_sum += attack_gap_beats
            continue

        speed_weight = 1.0 / (1.0 + attack_gap_beats)
        weighted_score += jump_weight * speed_weight
        considered_transitions += 1
        attack_gap_sum += attack_gap_beats

    if considered_transitions == 0:
        diagnostics = (
            f"hand_leap_hand={hand}",
            f"hand_leap_noticeable_threshold={noticeable_interval_semitones}",
            f"hand_leap_difficult_threshold={difficult_interval_semitones}",
            f"hand_leap_long_rest_limit_beats={max_rest_beats}",
            "hand_leap_transitions=0",
            "hand_leap_noticeable_count=0",
            "hand_leap_difficult_count=0",
            f"hand_leap_representative_pitch={_representative_pitch_strategy(hand)}",
            f"hand_leap_long_rest_filtered={filtered_long_rests}",
        )
        return 0.0, diagnostics

    rate = weighted_score / (2.0 * considered_transitions)
    diagnostics = (
        f"hand_leap_hand={hand}",
        f"hand_leap_noticeable_threshold={noticeable_interval_semitones}",
        f"hand_leap_difficult_threshold={difficult_interval_semitones}",
        f"hand_leap_long_rest_limit_beats={max_rest_beats}",
        f"hand_leap_representative_pitch={_representative_pitch_strategy(hand)}",
        f"hand_leap_transitions={considered_transitions}",
        f"hand_leap_noticeable_count={noticeable_count}",
        f"hand_leap_difficult_count={difficult_count}",
        f"hand_leap_long_rest_filtered={filtered_long_rests}",
        f"hand_leap_average_attack_gap_beats={attack_gap_sum / considered_transitions:.3f}",
    )
    return rate, diagnostics


def _build_attack_stream(
    logical_notes: Sequence[LogicalNoteIR],
    hand: LeapHandName,
) -> list[_LeapAttack]:
    grouped: dict[Fraction, list[LogicalNoteIR]] = {}
    for note in _ordered_logical_notes(logical_notes):
        if not _note_matches_hand(note, hand):
            continue
        grouped.setdefault(note.onset, []).append(note)

    attack_stream: list[_LeapAttack] = []
    for onset in sorted(grouped):
        notes_at_onset = grouped[onset]
        if not notes_at_onset:
            continue
        representative_pitch = (
            max(note.pitch_midi for note in notes_at_onset)
            if hand == "right"
            else min(note.pitch_midi for note in notes_at_onset)
        )
        duration = max(note.duration for note in notes_at_onset)
        attack_stream.append(
            _LeapAttack(
                onset=onset,
                duration=duration,
                pitch_midi=representative_pitch,
            )
        )
    return attack_stream


def _ordered_logical_notes(
    logical_notes: Sequence[LogicalNoteIR],
) -> list[LogicalNoteIR]:
    return sorted(
        logical_notes,
        key=lambda note: (
            note.onset,
            note.measure_index or 0,
            note.measure_staff_order or 0,
            note.xml_order or 0,
            note.note_id,
        ),
    )


def _note_matches_hand(note: LogicalNoteIR, hand: LeapHandName) -> bool:
    if note.hand is not None:
        return note.hand == hand
    if note.staff is None:
        return False
    return (note.staff == 1 and hand == "right") or (note.staff == 2 and hand == "left")


def _representative_pitch_strategy(hand: LeapHandName) -> str:
    return "max_pitch" if hand == "right" else "min_pitch"
