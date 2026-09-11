"""S4.7/S6.7 semantic-to-strategy compatibility table.

Maps pedagogical hypothesis IDs (qualified learner challenges) to objective IDs
and candidate strategy IDs without invoking transformations. The table is
declarative, deterministic, and test-scoped for verification that compatible
strategies are present and incompatible strategies are absent. S6.7 extends
the table with harmonic skeleton, cadence focus, phrase-shape, and
sequence-chunking strategies.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1)
- pedagogy/contracts.py (PedagogicalHypothesis)
- pedagogy/melody_projection.py, bass_leap.py, rhythmic_coordination.py, reading_load.py
- S6.2-S6.6 harmony, cadence, phrase, sequence heuristics
"""

from __future__ import annotations

from passage_practice.pedagogy.bass_leap import BASS_LEAP_HYPOTHESIS_TYPE
from passage_practice.pedagogy.melody_projection import MELODY_PROJECTION_HYPOTHESIS_TYPE
from passage_practice.pedagogy.reading_load import READING_LOAD_HYPOTHESIS_TYPE
from passage_practice.pedagogy.rhythmic_coordination import RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE

# S6.7 hypothesis types for harmony/phrase/sequence pedagogical hypotheses
HARMONIC_SKELETON_HYPOTHESIS_TYPE = "pedagogy.harmonic_skeleton"
CADENCE_FOCUS_HYPOTHESIS_TYPE = "pedagogy.cadence_focus"
PHRASE_SHAPE_HYPOTHESIS_TYPE = "pedagogy.phrase_shape"
SEQUENCE_CHUNKING_HYPOTHESIS_TYPE = "pedagogy.sequence_chunking"

# Declarative compatibility: hypothesis_type -> {objectives, strategies}
COMPATIBILITY_TABLE: dict[str, dict[str, tuple[str, ...]]] = {
    MELODY_PROJECTION_HYPOTHESIS_TYPE: {
        "objectives": ("objective.project_melody", "objective.balance_melody_accompaniment"),
        "strategies": ("strategy.melody_accent", "strategy.simplify_accompaniment"),
    },
    BASS_LEAP_HYPOTHESIS_TYPE: {
        "objectives": ("objective.landing_target", "objective.relocation_preparation"),
        "strategies": ("strategy.blocked_bass", "strategy.isolated_leaps"),
    },
    RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE: {
        "objectives": ("objective.hand_coordination", "objective.rhythmic_alignment"),
        "strategies": ("strategy.hands_separate_then_together", "strategy.common_attack_skeleton"),
    },
    READING_LOAD_HYPOTHESIS_TYPE: {
        "objectives": ("objective.reading_chunking", "objective.visual_grouping"),
        "strategies": ("strategy.blocked_harmony", "strategy.rhythmic_simplification"),
    },
    HARMONIC_SKELETON_HYPOTHESIS_TYPE: {
        "objectives": ("objective.harmonic_skeleton", "objective.harmonic_understanding"),
        "strategies": ("strategy.blocked_harmony", "strategy.harmonic_skeleton"),
    },
    CADENCE_FOCUS_HYPOTHESIS_TYPE: {
        "objectives": ("objective.cadence_preparation", "objective.phrase_ending"),
        "strategies": ("strategy.cadence_preparation", "strategy.phrase_ending_focus"),
    },
    PHRASE_SHAPE_HYPOTHESIS_TYPE: {
        "objectives": ("objective.phrase_shaping", "objective.breathing"),
        "strategies": ("strategy.phrase_shaping", "strategy.breath_mark"),
    },
    SEQUENCE_CHUNKING_HYPOTHESIS_TYPE: {
        "objectives": ("objective.sequence_chunking", "objective.pattern_chunking"),
        "strategies": ("strategy.sequence_practice", "strategy.chunked_repetition"),
    },
}


def get_compatible_objectives(hypothesis_type: str) -> tuple[str, ...]:
    """Return objective IDs compatible with ``hypothesis_type``."""
    if not isinstance(hypothesis_type, str) or not hypothesis_type:
        raise ValueError(f"hypothesis_type must be non-empty str, got {hypothesis_type!r}")
    entry = COMPATIBILITY_TABLE.get(hypothesis_type)
    if entry is None:
        return ()
    return entry["objectives"]


def get_compatible_strategies(hypothesis_type: str) -> tuple[str, ...]:
    """Return strategy IDs compatible with ``hypothesis_type``."""
    if not isinstance(hypothesis_type, str) or not hypothesis_type:
        raise ValueError(f"hypothesis_type must be non-empty str, got {hypothesis_type!r}")
    entry = COMPATIBILITY_TABLE.get(hypothesis_type)
    if entry is None:
        return ()
    return entry["strategies"]


def is_strategy_compatible(hypothesis_type: str, strategy_id: str) -> bool:
    """Return True if ``strategy_id`` is compatible with ``hypothesis_type``."""
    return strategy_id in get_compatible_strategies(hypothesis_type)


def get_all_compatible(hypothesis_type: str) -> dict[str, tuple[str, ...]]:
    """Return full compatibility entry for ``hypothesis_type`` or empty dict."""
    entry = COMPATIBILITY_TABLE.get(hypothesis_type)
    if entry is None:
        return {"objectives": (), "strategies": ()}
    return {"objectives": entry["objectives"], "strategies": entry["strategies"]}


def get_strategies_for_harmony_view(harmony_view) -> tuple[str, ...]:
    """Return strategies for a harmony view, or empty if unsupported.

    - If view has diagnostic ``insufficient_harmony_evidence`` or
      ``low_key_confidence_abstention`` or ``atonal_or_chromatic``, no action
      is suggested (S6.7 test). Otherwise returns strategies for harmonic_skeleton.
    """
    # Check diagnostics for unsupported harmony
    for d in getattr(harmony_view, "diagnostics", ()):
        code = getattr(d, "code", "")
        if code in ("insufficient_harmony_evidence", "atonal_or_chromatic", "chromatic_ambiguity_low_key_confidence", "low_key_confidence_abstention"):
            return ()
    # If no local key candidates, also unsupported
    if not getattr(harmony_view, "local_key_candidates", ()):
        return ()
    return get_compatible_strategies(HARMONIC_SKELETON_HYPOTHESIS_TYPE)


__all__ = [
    "CADENCE_FOCUS_HYPOTHESIS_TYPE",
    "COMPATIBILITY_TABLE",
    "HARMONIC_SKELETON_HYPOTHESIS_TYPE",
    "PHRASE_SHAPE_HYPOTHESIS_TYPE",
    "SEQUENCE_CHUNKING_HYPOTHESIS_TYPE",
    "get_compatible_objectives",
    "get_compatible_strategies",
    "get_all_compatible",
    "get_strategies_for_harmony_view",
    "is_strategy_compatible",
]
