"""Working paper-first slot inventory for the Yan 2023 lane.

This module records a machine-readable subset of the paper-derived feature map.
It is intentionally explicit about what is directly named in the paper, what is
visible in Figure 6, and what is only a systematic scope expansion used for
repo-native reconstruction work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FeatureStatus = Literal["implemented", "proxyable", "blocked"]
ScopeCode = Literal["es", "bs", "ts", "global"]
SourceKind = Literal[
    "paper_text",
    "table3",
    "figure6_visible",
    "paper_scope_expansion",
]


@dataclass(frozen=True, slots=True)
class Yan2023FeatureSlot:
    """One working slot in the Yan paper-first inventory."""

    slot_id: str
    base_feature: str
    family: str
    scope_code: ScopeCode
    status: FeatureStatus
    source_kinds: tuple[SourceKind, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class _ScopedFeatureSpec:
    base_feature: str
    family: str
    status: FeatureStatus
    notes: str
    source_kinds: tuple[SourceKind, ...]
    scopes: tuple[ScopeCode, ...] = ("es", "bs", "ts")


@dataclass(frozen=True, slots=True)
class _GlobalFeatureSpec:
    base_feature: str
    family: str
    status: FeatureStatus
    notes: str
    source_kinds: tuple[SourceKind, ...]


_SCOPED_FEATURE_SPECS: tuple[_ScopedFeatureSpec, ...] = (
    _ScopedFeatureSpec(
        base_feature="pitch_mean",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; reconstructed as mean MIDI pitch.",
        source_kinds=("paper_text", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="deviation_of_pitch",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; reconstructed as population std-dev of MIDI pitch.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="pitch_range",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; direct max-minus-min pitch span.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="pitch_entropy",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; reconstructed as Shannon entropy over exact MIDI pitches.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="hand_displacement_rate",
        family="legacy_pitch",
        status="proxyable",
        notes="Paper names the feature, but the exact thresholding and aggregation remain ambiguous.",
        source_kinds=("paper_text", "figure6_visible"),
    ),
    _ScopedFeatureSpec(
        base_feature="hand_stretch",
        family="legacy_pitch",
        status="proxyable",
        notes="Paper names the feature, but the precise stretch model remains ambiguous.",
        source_kinds=("paper_text", "figure6_visible"),
        scopes=("bs", "ts"),
    ),
    _ScopedFeatureSpec(
        base_feature="deviation_of_pitch_from_C4",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; reconstructed as mean absolute semitone distance from MIDI 60.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="black_key_rate",
        family="legacy_pitch",
        status="implemented",
        notes="Paper pitch-content feature; direct pitch-class rate.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="mean_of_note_duration",
        family="legacy_rhythm",
        status="implemented",
        notes="Paper rhythmic-content feature; reconstructed from quarter-note durations.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="deviation_of_note_duration",
        family="legacy_rhythm",
        status="implemented",
        notes="Paper rhythmic-content feature; reconstructed as population std-dev of quarter-note durations.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="playing_speed",
        family="legacy_rhythm",
        status="proxyable",
        notes="Paper names the feature, but the exact formula is not fully published; repo uses attacks per quarter as a proxy.",
        source_kinds=("paper_text", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="polyphony_rate",
        family="legacy_rhythm",
        status="implemented",
        notes="Paper rhythmic-content feature; direct same-onset multi-note ratio.",
        source_kinds=("paper_text", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="distinct_stroke_rate",
        family="legacy_rhythm",
        status="proxyable",
        notes="Paper names the feature, but the exact stroke identity rule is not fully published.",
        source_kinds=("paper_text", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="irregular_rhythm",
        family="legacy_rhythm",
        status="proxyable",
        notes="Paper names the feature, but the exact irregularity formula remains ambiguous.",
        source_kinds=("paper_text", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="pressing_velocity_entropy",
        family="new_timbre",
        status="blocked",
        notes="Paper feature depends on symbolic-to-velocity mapping not yet defined in the lane.",
        source_kinds=("table3", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="pressing_velocity_variability",
        family="new_timbre",
        status="blocked",
        notes="Paper feature depends on symbolic-to-velocity mapping not yet defined in the lane.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="pitch_variability",
        family="new_contour",
        status="implemented",
        notes="Table 3 publishes an adjacent-note normalized variability formula.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="note_duration_variability",
        family="new_contour",
        status="implemented",
        notes="Table 3 publishes an adjacent-note normalized variability formula.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="note_density",
        family="new_contour",
        status="implemented",
        notes="Table 3 publishes notes-per-length density; repo reconstructs it as notes per quarter-note.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="triad",
        family="new_chord_number",
        status="implemented",
        notes="Figure 6 exposes this chord-count slot explicitly.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="seventh_chord",
        family="new_chord_number",
        status="implemented",
        notes="Figure 6 exposes this chord-count slot explicitly.",
        source_kinds=("table3", "figure6_visible", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="ninth_chord",
        family="new_chord_number",
        status="implemented",
        notes="Table 3 describes ninth chords as part of chord-number extraction.",
        source_kinds=("table3", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="staccato_rate",
        family="new_particular_notes",
        status="implemented",
        notes="Table 3 publishes a direct note-rate definition.",
        source_kinds=("table3", "paper_scope_expansion"),
    ),
    _ScopedFeatureSpec(
        base_feature="dotted_note_rate",
        family="new_particular_notes",
        status="proxyable",
        notes="Table 3 publishes a direct note-rate definition, but ScoreIR currently needs heuristic dot recovery from duration values.",
        source_kinds=("table3", "paper_scope_expansion"),
    ),
)

_GLOBAL_FEATURE_SPECS: tuple[_GlobalFeatureSpec, ...] = (
    _GlobalFeatureSpec(
        base_feature="length",
        family="legacy_other",
        status="implemented",
        notes="Paper 'other' feature; repo reconstructs it as total quarter-note score length.",
        source_kinds=("paper_text",),
    ),
    _GlobalFeatureSpec(
        base_feature="tempo",
        family="legacy_other",
        status="implemented",
        notes="Paper 'other' feature; repo uses the initial tempo BPM when available.",
        source_kinds=("paper_text",),
    ),
    _GlobalFeatureSpec(
        base_feature="key_signature",
        family="legacy_other",
        status="implemented",
        notes="Paper 'other' feature; repo uses the initial key-fifths value when available.",
        source_kinds=("paper_text", "figure6_visible"),
    ),
    _GlobalFeatureSpec(
        base_feature="playing_speed_variation",
        family="new_speed",
        status="implemented",
        notes="Table 3 publishes a tempo-variation ratio formula.",
        source_kinds=("table3",),
    ),
    _GlobalFeatureSpec(
        base_feature="melodic_complexity",
        family="new_mc",
        status="blocked",
        notes="Table 3 references the MIDI Toolbox expectancy model, but the exact lane contract is not yet reconstructed.",
        source_kinds=("table3", "figure6_visible"),
    ),
    _GlobalFeatureSpec(
        base_feature="melodic_originality",
        family="new_mc",
        status="blocked",
        notes="Table 3 references the MIDI Toolbox expectancy model, but the exact lane contract is not yet reconstructed.",
        source_kinds=("table3",),
    ),
    _GlobalFeatureSpec(
        base_feature="degree_of_melodiousness",
        family="new_mc",
        status="blocked",
        notes="Table 3 references the MIDI Toolbox expectancy model, but the exact lane contract is not yet reconstructed.",
        source_kinds=("table3",),
    ),
)


def build_working_slot_inventory() -> tuple[Yan2023FeatureSlot, ...]:
    """Return the current working subset of paper-derived slot definitions."""

    slots: list[Yan2023FeatureSlot] = []
    for spec in _SCOPED_FEATURE_SPECS:
        for scope in spec.scopes:
            slots.append(
                Yan2023FeatureSlot(
                    slot_id=f"{spec.base_feature}_{scope}",
                    base_feature=spec.base_feature,
                    family=spec.family,
                    scope_code=scope,
                    status=spec.status,
                    source_kinds=spec.source_kinds,
                    notes=spec.notes,
                )
            )
    for spec in _GLOBAL_FEATURE_SPECS:
        slots.append(
            Yan2023FeatureSlot(
                slot_id=spec.base_feature,
                base_feature=spec.base_feature,
                family=spec.family,
                scope_code="global",
                status=spec.status,
                source_kinds=spec.source_kinds,
                notes=spec.notes,
            )
        )
    return tuple(slots)


WORKING_FEATURE_SLOTS = build_working_slot_inventory()


def slot_status_counts() -> dict[FeatureStatus, int]:
    counts: dict[FeatureStatus, int] = {
        "implemented": 0,
        "proxyable": 0,
        "blocked": 0,
    }
    for slot in WORKING_FEATURE_SLOTS:
        counts[slot.status] += 1
    return counts


def slot_scope_counts() -> dict[ScopeCode, int]:
    counts: dict[ScopeCode, int] = {
        "es": 0,
        "bs": 0,
        "ts": 0,
        "global": 0,
    }
    for slot in WORKING_FEATURE_SLOTS:
        counts[slot.scope_code] += 1
    return counts


def slot_source_counts() -> dict[SourceKind, int]:
    counts: dict[SourceKind, int] = {
        "paper_text": 0,
        "table3": 0,
        "figure6_visible": 0,
        "paper_scope_expansion": 0,
    }
    for slot in WORKING_FEATURE_SLOTS:
        for source_kind in slot.source_kinds:
            counts[source_kind] += 1
    return counts


__all__ = [
    "FeatureStatus",
    "ScopeCode",
    "SourceKind",
    "WORKING_FEATURE_SLOTS",
    "Yan2023FeatureSlot",
    "build_working_slot_inventory",
    "slot_scope_counts",
    "slot_source_counts",
    "slot_status_counts",
]
