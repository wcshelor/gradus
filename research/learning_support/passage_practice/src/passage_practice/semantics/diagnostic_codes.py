"""S-X1 semantic diagnostic code registry.

Stable codes for missing view, unsupported notation, low confidence,
contradictory criteria, missing source refs, and learner-dependent claim.
No duplicate codes across categories.

Design refs:
- semantic_music_extraction_tasks.md S-X1
- models/diagnostics.py ( Diagnostic.code must be stable snake_case)
"""

from __future__ import annotations

# Each category maps code -> human description (stable, not parsed)
MISSING_VIEW_CODES: dict[str, str] = {
    "missing_required_view": "detector requires a view not present (e.g., salience_view, texture_grid)",
    "unsupported_view": "detector cannot run; missing required views",
    "detector_not_run_missing_view": "registry skipped detector due to missing required views",
    "missing_optional_view": "optional view absent; confidence may be reduced",
}

UNSUPPORTED_NOTATION_CODES: dict[str, str] = {
    "slur_evidence_unavailable": "slur phrase-marking not supported upstream; unavailable, not zero",
    "tuplet_subdivision_unsupported": "tuplet-derived subdivisions present; duration ratios not interpreted",
    "tuplet_subdivision": "tuplet present (generic)",
    "ornament_data_limited": "ornament/grace note evidence limited",
    "clef_data_unavailable": "clef change evidence unavailable",
    "layout_data_unavailable": "layout/page-break evidence unavailable",
    "pattern_exclusion_not_available": "accompaniment pattern-exclusion marker unavailable",
    "unknown_meter": "meter unknown for on_beat determination",
}

LOW_CONFIDENCE_CODES: dict[str, str] = {
    "low_confidence_melody": "melody detector confidence below presentation floor",
    "low_confidence_bass": "bass confidence low",
    "low_confidence_accompaniment": "accompaniment confidence low",
    "no_supported_melody": "no melody hypothesis met threshold",
    "no_supported_bass": "no bass hypothesis met threshold",
    "no_supported_accompaniment": "no accompaniment hypothesis met threshold",
    "no_supported_rhythm": "no rhythm layer hypothesis met threshold",
    "no_supported_texture": "no texture class met threshold",
    "no_supported_hypothesis": "no detector met its minimum evidence threshold",
    "low_key_confidence_abstention": "local key confidence too low; abstaining",
    "insufficient_harmony_evidence": "harmony view insufficient for key/cadence",
    "atonal_or_chromatic": "pitch-class distribution atonal/chromatic; key low confidence",
    "chromatic_ambiguity_low_key_confidence": "chromatic ambiguity reduces key confidence",
}

CONTRADICTORY_CRITERIA_CODES: dict[str, str] = {
    "contradictory_evidence": "evidence contradicts the hypothesis (e.g., static top vs moving lower)",
    "repeated_motif_ambiguity": "repeated interval pattern suggests phrase continuation ambiguity",
    "phrase_continuation_ambiguity": "phrase continuation ambiguous due to repeated motif",
    "similar_rhythm_different_contour": "rhythm repeats but contour differs; sequence candidate ambiguous",
    "ambiguous_texture": "multiple texture classes with similar confidence",
    "ambiguous_voice": "voice role ambiguous",
    "ambiguous_hand_for_crossing": "hand inference ambiguous for staff crossing",
}

MISSING_SOURCE_REFS_CODES: dict[str, str] = {
    "unresolvable_attack_ref": "passage attack ref does not resolve in score",
    "unresolvable_score_ref": "generic score ref unresolvable",
    "unresolvable_bass_ref": "bass ref not in score",
    "missing_bass_ref": "missing bass ref for cadence check",
    "unlocatable_pair": "pair measure context missing; region omitted",
    "simultaneous_pair": "simultaneous attacks have zero temporal extent; region omitted",
    "linked_attack_outside_passage": "linked attack outside passage interval",
    "missing_required_hypothesis": "required hypothesis missing for pedagogical rule",
    "semantic_missing_evidence": "semantic missing evidence recorded, never zeroed",
}

LEARNER_DEPENDENT_CODES: dict[str, str] = {
    "learner_caveat": "learner perspective is separate evidence; not verified",
    "reading_missing_evidence": "reading claim requires learner confirmation",
    "rhythm_evidence_incomplete": "rhythm evidence incomplete; learner confirmation may be needed",
    "feedback_boosted": "learner feedback boosted hypothesis (report preserved)",
    "feedback_demoted": "learner feedback demoted hypothesis",
    "request_more_evidence": "learner selected 'not sure' or 'something else'; need more evidence",
    "reported_concern": "learner-reported concern preserved verbatim",
}

# Synthetic / plumbing
PLUMBING_CODES: dict[str, str] = {
    "synthetic_data": "synthetic fixture/test; no real participant data",
    "small_data_warning": "small sample; metrics illustrative only",
    "model_version": "model version provenance",
    "training_data_id": "training data identity",
    "insufficient_attacks": "need at least N attacks; fewer found (FACT vs zero)",
    "non_logical_refs_skipped": "non-logical refs excluded from observations",
    "hand_scoped_inference": "hand filtering relies on staff-inferred labels (INFERENCE)",
    "empty_selection": "no attacks in interval",
}

# Combined registry for validation
ALL_CODES: dict[str, str] = {
    **MISSING_VIEW_CODES,
    **UNSUPPORTED_NOTATION_CODES,
    **LOW_CONFIDENCE_CODES,
    **CONTRADICTORY_CRITERIA_CODES,
    **MISSING_SOURCE_REFS_CODES,
    **LEARNER_DEPENDENT_CODES,
    **PLUMBING_CODES,
}

# Also include other observed codes that are plumbing but not categorized above,
# ensure they are still registered to avoid untracked codes.
OTHER_CODES: dict[str, str] = {
    "no_salience_events": "no events for salience",
    "no_rhythm_cells": "no rhythm cells",
    "no_texture_slices": "no texture slices",
    "too_short_for_sequence": "too short for sequence (need motif*2-1)",
    "too_short_motif": "motif too short",
    "too_short_pattern": "pattern too short",
    "insufficient_notes_for_phrase": "no notes for phrase boundary detection",
    "insufficient_bass_motion": "need at least 2 onsets with bass for cadence",
    "cadence_not_on_downbeat": "cadence-like but not on downbeat",
    "cadence_duration_too_short": "final duration too short for cadence",
    "cadence_bass_motion_not_dominant_tonic": "bass motion not dominant->tonic for key",
    "cadence_detected": "cadence candidate detected",
    "phrase_boundary_supports_cadence": "phrase boundary near cadence",
    "no_compatible_strategy": "no pedagogical strategy compatible",
    "no_supported_pedagogical_hypothesis": "no pedagogical hypothesis met threshold",
}

# Merge others into ALL for completeness (no duplicate keys)
for _k, _v in OTHER_CODES.items():
    if _k not in ALL_CODES:
        ALL_CODES[_k] = _v

CATEGORY_MAP: dict[str, dict[str, str]] = {
    "missing_view": MISSING_VIEW_CODES,
    "unsupported_notation": UNSUPPORTED_NOTATION_CODES,
    "low_confidence": LOW_CONFIDENCE_CODES,
    "contradictory_criteria": CONTRADICTORY_CRITERIA_CODES,
    "missing_source_refs": MISSING_SOURCE_REFS_CODES,
    "learner_dependent": LEARNER_DEPENDENT_CODES,
    "plumbing": PLUMBING_CODES,
    "other": OTHER_CODES,
}

__all__ = [
    "MISSING_VIEW_CODES",
    "UNSUPPORTED_NOTATION_CODES",
    "LOW_CONFIDENCE_CODES",
    "CONTRADICTORY_CRITERIA_CODES",
    "MISSING_SOURCE_REFS_CODES",
    "LEARNER_DEPENDENT_CODES",
    "ALL_CODES",
    "CATEGORY_MAP",
]
