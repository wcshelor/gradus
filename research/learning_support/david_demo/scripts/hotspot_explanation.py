#!/usr/bin/env python3
"""Deterministic hotspot explanation helper for David demo — three-layer system.

Layers:
  1. Deterministic evidence brief (compact, hashable)
  2. Deterministic heuristic explanation (prose from brief, no LLM)
  3. Optional LLM polish (narrates brief, stored with hash/model metadata)

The LLM narrates and clarifies; it is not the analyst of record.
All math is unchanged — this file is a presentation layer only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Glossaries — plain language for the 6 graph dimensions (primary UI) and
# 9-aspect backend taxonomy (provenance only), plus micro-component features.
# ---------------------------------------------------------------------------

GRAPH_GLOSSARY: dict[str, dict[str, str]] = {
    "finger_dexterity": {
        "plain": "finger dexterity",
        "label": "Finger Dexterity",
        "phrase": "finger dexterity (finger-level execution, articulation precision)",
    },
    "hand_movement_position": {
        "plain": "hand position / movement",
        "label": "Hand Position / Movement",
        "phrase": "hand position / movement (reaches, stretches, leaps, register shifts)",
    },
    "layers_coordination": {
        "plain": "coordination / layers",
        "label": "Coordination / Layers",
        "phrase": "coordination / layers (layered texture, polyphony, inter-hand independence)",
    },
    "rhythm_timing": {
        "plain": "rhythm & timing",
        "label": "Rhythm & Timing",
        "phrase": "rhythm & timing (density in time, subdivision variety, timing pressure)",
    },
    "expression_sound_control": {
        "plain": "control / expression",
        "label": "Control / Expression",
        "phrase": "control / expression (dynamics, hairpins, sound-shaping demands)",
    },
    "notation_reading": {
        "plain": "notation / reading",
        "label": "Notation / Reading",
        "phrase": "notation / reading (accidentals, clef, ledger lines, cross-staff)",
    },
}

ASPECT_GLOSSARY: dict[str, dict[str, str]] = {
    "rhythmic_demand": {
        "plain": "rhythm",
        "label": "Rhythmic demand",
        "phrase": "rhythmic demand (timing, density and subdivision variety)",
    },
    "pitch_movement_demand": {
        "plain": "pitch movement",
        "label": "Pitch / movement demand",
        "phrase": "pitch movement (distance and frequency of relocations)",
    },
    "hand_shape_span_demand": {
        "plain": "hand shape and span",
        "label": "Hand-shape / span demand",
        "phrase": "hand shape and span (how wide the hand needs to stretch at once)",
    },
    "texture_polyphony_demand": {
        "plain": "texture and polyphony",
        "label": "Texture / polyphony demand",
        "phrase": "texture and polyphony (how many notes sound together)",
    },
    "coordination_demand": {
        "plain": "hand coordination",
        "label": "Coordination demand",
        "phrase": "hand coordination (how the two hands align or diverge in time)",
    },
    "notation_reading_demand": {
        "plain": "notation reading",
        "label": "Notation / reading demand",
        "phrase": "notation reading (accidentals, clef changes and related symbols)",
    },
    "expression_control_demand": {
        "plain": "expression and control",
        "label": "Expression / control demand",
        "phrase": "expression and control (written dynamics and articulations)",
    },
    "structural_pattern_demand": {
        "plain": "structure and patterns",
        "label": "Structural / pattern demand",
        "phrase": "structure and patterns (repetition and formal organization — blocked, no temporal trace)",
    },
    "performance_interpretive_demand": {
        "plain": "interpretive nuance",
        "label": "Performance / interpretive demand",
        "phrase": "interpretive nuance (written proxies only — caveated, learner-dependent)",
    },
}

FEATURE_GLOSSARY: dict[str, str] = {
    "rhythm.note_density": "note density (notes per quarter)",
    "rhythm.attack_density": "attack density (onsets per quarter)",
    "rhythm.shortest_written_duration": "shortest written duration",
    "rhythm.tuplet_count": "tuplet presence",
    "rhythm.significant_shortest_value": "shortest notable note value",
    "rhythm.asymmetric_tuplet_measure_ratio": "asymmetric tuplet share",
    "rhythm.polyrhythm_measure_ratio": "polyrhythm share",
    "rhythm.polyrhythm_flag": "polyrhythm flag",
    "rhythm.duration_value_ratio": "duration variety",
    "leaps.mean_melodic_leap": "average melodic leap",
    "leaps.max_melodic_leap": "largest melodic leap",
    "leaps.count_ge_5": "leaps ≥5 semitones",
    "leaps.count_ge_8": "leaps ≥8 semitones",
    "leaps.count_ge_12": "leaps ≥12 semitones",
    "leaps.timed_difficult_displacement_ratio": "share of harder timed displacements",
    "leaps.max_timed_difficult_displacement": "largest harder timed displacement",
    "leaps.timed_difficult_displacement_count": "count of harder timed displacements",
    "metadata.pitch_range": "pitch range across the window",
    "pitch_geometry.max_simultaneity_span": "widest simultaneous span",
    "pitch_geometry.mean_simultaneity_span": "average simultaneous span",
    "pitch_geometry.register_range": "register range (lowest to highest pitch)",
    "texture.notes_per_onset": "notes per onset",
    "texture.simultaneity_density": "share of onsets with multiple notes",
    "texture.vertical_density_proxy": "average sounding notes (vertical density)",
    "texture.chord_count": "chord onsets",
    "texture.chord_ratio": "share of chord onsets",
    "texture.octave_chord_ratio": "octave-chord share",
    "coordination.aligned_hand_onset_count": "aligned hand onsets",
    "coordination.asynchronous_hand_onset_count": "offset hand onsets",
    "coordination.aligned_hand_onset_ratio": "share of aligned hand onsets",
    "coordination.subdivision_mismatch_proxy": "subdivision mismatch between hands (proxy)",
    "notation.accidental_density": "accidental density",
    "notation.accidental_count": "accidental count",
    "notation.accidental_ratio": "accidental share",
    "notation.clef_change_count": "clef changes",
    "notation.cross_staff_note_count": "cross-staff notes",
    "notation.ledger_line_burden": "ledger-line burden",
    "expression.articulated_note_ratio": "articulated note share",
    "expression.articulation_density": "articulation density",
    "expression.staccato_note_ratio": "staccato share",
    "expression.accent_note_ratio": "accent share",
    "expression.strong_accent_note_ratio": "strong-accent share",
    "expression.tenuto_note_ratio": "tenuto share",
    "expression.dynamic_marking_count": "dynamic marking count",
    "expression.dynamic_marking_rate": "dynamic marking rate",
    "expression.dynamic_change_count": "dynamic change count",
    "expression.dynamic_range_span": "dynamic range span",
    "expression.wedge_start_count": "hairpin (wedge) count",
    "expression.crescendo_start_count": "crescendo hairpins",
    "expression.diminuendo_start_count": "diminuendo hairpins",
    "expression.staff_specific_dynamic_ratio": "staff-specific dynamic share",
    "statistics.duration_mean": "average duration",
    "statistics.duration_std": "duration variability (std)",
    "statistics.duration_variability": "duration variability",
    "statistics.pitch_mean": "average pitch height",
    "statistics.pitch_std": "pitch height spread",
    "statistics.pitch_entropy": "pitch variety (entropy)",
    "statistics.black_key_rate": "black-key share",
}

# ---------------------------------------------------------------------------
# Phase 1 — learner-facing observation builder (conservative mapping from
# existing signals; no new musical claims, no contour/hand inference).
# ---------------------------------------------------------------------------

# Feature → safe observation phrase (one of the 6 blessed phrases, or close)
_FEATURE_OBSERVATION_MAP: dict[str, str] = {
    # coordination — hands don't land together
    "coordination.asynchronous_hand_onset_count": "the hands do not always land together",
    "coordination.asynchronous_hand_onset_ratio": "the hands do not always land together",
    "coordination.aligned_hand_onset_count": "the hands do not always land together",
    "coordination.aligned_hand_onset_ratio": "the hands do not always land together",
    "coordination.subdivision_mismatch_proxy": "the hands do not always land together",
    # texture/polyphony — several notes line up
    "texture.notes_per_onset": "several notes need to line up cleanly",
    "texture.simultaneity_density": "several notes need to line up cleanly",
    "texture.vertical_density_proxy": "several notes need to line up cleanly",
    "texture.chord_count": "several notes need to line up cleanly",
    "texture.chord_ratio": "several notes need to line up cleanly",
    "texture.octave_chord_ratio": "several notes need to line up cleanly",
    # hand movement / span — wider shape
    "leaps.mean_melodic_leap": "the hand has to move across a wider shape",
    "leaps.max_melodic_leap": "the hand has to move across a wider shape",
    "leaps.count_ge_5": "the hand has to move across a wider shape",
    "leaps.count_ge_8": "the hand has to move across a wider shape",
    "leaps.count_ge_12": "the hand has to move across a wider shape",
    "leaps.timed_difficult_displacement_ratio": "the hand has to move across a wider shape",
    "leaps.max_timed_difficult_displacement": "the hand has to move across a wider shape",
    "leaps.timed_difficult_displacement_count": "the hand has to move across a wider shape",
    "metadata.pitch_range": "the hand has to move across a wider shape",
    "pitch_geometry.max_simultaneity_span": "the hand has to move across a wider shape",
    "pitch_geometry.mean_simultaneity_span": "the hand has to move across a wider shape",
    "pitch_geometry.register_range": "the hand has to move across a wider shape",
    # rhythm / timing — less room for adjustment
    "rhythm.note_density": "timing has less room for adjustment",
    "rhythm.attack_density": "timing has less room for adjustment",
    "rhythm.shortest_written_duration": "timing has less room for adjustment",
    "rhythm.tuplet_count": "timing has less room for adjustment",
    "rhythm.significant_shortest_value": "timing has less room for adjustment",
    "rhythm.asymmetric_tuplet_measure_ratio": "timing has less room for adjustment",
    "rhythm.polyrhythm_measure_ratio": "timing has less room for adjustment",
    "rhythm.polyrhythm_flag": "timing has less room for adjustment",
    "rhythm.duration_value_ratio": "timing has less room for adjustment",
    "statistics.duration_mean": "timing has less room for adjustment",
    "statistics.duration_std": "timing has less room for adjustment",
    "statistics.duration_variability": "timing has less room for adjustment",
    # expression / control
    "expression.articulated_note_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.articulation_density": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.staccato_note_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.accent_note_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.strong_accent_note_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.tenuto_note_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.dynamic_marking_count": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.dynamic_marking_rate": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.dynamic_change_count": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.dynamic_range_span": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.wedge_start_count": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.crescendo_start_count": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.diminuendo_start_count": "dynamic or articulation control has to stay consistent while the notes change",
    "expression.staff_specific_dynamic_ratio": "dynamic or articulation control has to stay consistent while the notes change",
    # notation / reading
    "notation.accidental_density": "reading load may be higher because of accidentals or dense notation",
    "notation.accidental_count": "reading load may be higher because of accidentals or dense notation",
    "notation.accidental_ratio": "reading load may be higher because of accidentals or dense notation",
    "notation.clef_change_count": "reading load may be higher because of accidentals or dense notation",
    "notation.cross_staff_note_count": "reading load may be higher because of accidentals or dense notation",
    "notation.ledger_line_burden": "reading load may be higher because of accidentals or dense notation",
    "statistics.black_key_rate": "reading load may be higher because of accidentals or dense notation",
}

_DIMENSION_OBSERVATION_MAP: dict[str, str] = {
    "layers_coordination": "the hands do not always land together",
    "hand_movement_position": "the hand has to move across a wider shape",
    "rhythm_timing": "timing has less room for adjustment",
    "expression_sound_control": "dynamic or articulation control has to stay consistent while the notes change",
    "notation_reading": "reading load may be higher because of accidentals or dense notation",
    "finger_dexterity": "timing has less room for adjustment",
}

# Observation → why it feels hard (second sentence, still plain)
_OBSERVATION_REASON: dict[str, str] = {
    "the hands do not always land together": "Keeping the parts together while each hand follows its own timing adds coordination pressure.",
    "several notes need to line up cleanly": "Voicing and balancing several notes at once makes it harder to keep the sound even.",
    "the hand has to move across a wider shape": "Covering larger intervals or wider shapes makes it harder to land accurately.",
    "timing has less room for adjustment": "Shorter values and varied rhythms leave less time to adjust between notes.",
    "dynamic or articulation control has to stay consistent while the notes change": "Shaping loudness and touch consistently while the notes move adds control work.",
    "reading load may be higher because of accidentals or dense notation": "More symbols to read means extra attention before the hands can play fluently.",
    # Phase 2 semantic observations — keep reasons conservative and aligned
    "the hands do not always land together, so coordination has to stay steady between layers": "Keeping independent layers aligned while each hand follows its own timing adds coordination pressure.",
    "dynamic shaping happens while the notes are changing, so control has to stay consistent through the motion": "Shaping loudness and touch while the notes move adds control work that has to stay even through the motion.",
    "the passage combines wider hand movement with timing precision": "Large shifts combined with timing precision leave less room to recover between moves.",
    "one hand moves across a wider shape while the other keeps another layer active": "One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.",
    "the left hand moves across a wider shape while the right hand keeps another layer active": "One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.",
    "the right hand moves across a wider shape while the left hand keeps another layer active": "One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.",
    "one part sustains while another part moves, so balance and coordination matter": "Holding one part steady while another moves asks for balance and independent control.",
}


# ---------------------------------------------------------------------------
# Phase 2 — window-level semantic observations (conservative, evidence-backed)
# ---------------------------------------------------------------------------

def _dim_value(brief: dict[str, Any], dim_id: str) -> float | None:
    for d in brief.get("dimensions") or []:
        if (d.get("dimension_id") or "") == dim_id:
            nv = d.get("normalized_value")
            if isinstance(nv, (int, float)):
                return float(nv)
    return None


def _has_micro(brief: dict[str, Any], feature_ids: set[str] | str, threshold: float = 0.5) -> tuple[bool, dict | None]:
    """Check if any micro_feature among feature_ids meets threshold. Returns (found, best_entry)."""
    if isinstance(feature_ids, str):
        feature_ids = {feature_ids}
    best: dict | None = None
    best_nv = -1.0
    for m in brief.get("micro_features") or []:
        fid = m.get("feature_id") or ""
        if fid not in feature_ids:
            continue
        nv = m.get("normalized_value")
        nv_f = float(nv) if isinstance(nv, (int, float)) else -1.0
        if nv_f > best_nv:
            best_nv = nv_f
            best = m
        if nv_f >= threshold:
            return True, m
    if best is not None and isinstance(best.get("normalized_value"), (int, float)) and float(best["normalized_value"]) >= threshold:
        return True, best
    return False, best


def _micro_prefix_match(brief: dict[str, Any], prefix: str, threshold: float = 0.5) -> tuple[bool, dict | None]:
    best: dict | None = None
    best_nv = -1.0
    for m in brief.get("micro_features") or []:
        fid = m.get("feature_id") or ""
        if not fid.startswith(prefix):
            continue
        nv = m.get("normalized_value")
        nv_f = float(nv) if isinstance(nv, (int, float)) else -1.0
        if nv_f > best_nv:
            best_nv = nv_f
            best = m
        if nv_f >= threshold:
            return True, m
    if best is not None and best_nv >= threshold:
        return True, best
    return False, best


def _build_semantic_observations(brief: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured semantic observations if evidence supports them.

    Each entry: {kind, text, confidence, support_level, evidence:list[str]}.
    Conservative: only emits when thresholds on existing dimensions/micro_features
    are met. Hand/staff attribution only if source micro carries scope_ref.
    Contour is NOT emitted (no pitch-sequence data in brief).
    """
    dims = brief.get("dimensions") or []
    micros = brief.get("micro_features") or []
    if not dims and not micros:
        return []

    # Build lookup for evidence convenience
    dim_vals: dict[str, float] = {}
    for d in dims:
        did = d.get("dimension_id") or ""
        nv = d.get("normalized_value")
        if isinstance(nv, (int, float)):
            dim_vals[did] = float(nv)

    # Feature sets
    _coord_async_ids = {
        "coordination.asynchronous_hand_onset_count",
        "coordination.asynchronous_hand_onset_ratio",
        "coordination.aligned_hand_onset_ratio",
        "coordination.subdivision_mismatch_proxy",
    }
    _texture_ids = {
        "texture.notes_per_onset",
        "texture.simultaneity_density",
        "texture.vertical_density_proxy",
        "texture.chord_count",
        "texture.chord_ratio",
        "texture.octave_chord_ratio",
    }
    _leap_ids = {
        "leaps.mean_melodic_leap",
        "leaps.max_melodic_leap",
        "leaps.count_ge_5",
        "leaps.count_ge_8",
        "leaps.count_ge_12",
        "leaps.timed_difficult_displacement_ratio",
        "leaps.max_timed_difficult_displacement",
        "leaps.timed_difficult_displacement_count",
        "metadata.pitch_range",
        "pitch_geometry.max_simultaneity_span",
        "pitch_geometry.mean_simultaneity_span",
        "pitch_geometry.register_range",
    }
    _rhythm_ids = {
        "rhythm.note_density",
        "rhythm.attack_density",
        "rhythm.shortest_written_duration",
        "rhythm.tuplet_count",
        "rhythm.significant_shortest_value",
        "rhythm.asymmetric_tuplet_measure_ratio",
        "rhythm.polyrhythm_measure_ratio",
        "rhythm.polyrhythm_flag",
        "rhythm.duration_value_ratio",
        "statistics.duration_mean",
        "statistics.duration_std",
        "statistics.duration_variability",
    }
    _expression_ids = {
        "expression.articulated_note_ratio",
        "expression.articulation_density",
        "expression.staccato_note_ratio",
        "expression.accent_note_ratio",
        "expression.strong_accent_note_ratio",
        "expression.tenuto_note_ratio",
        "expression.dynamic_marking_count",
        "expression.dynamic_marking_rate",
        "expression.dynamic_change_count",
        "expression.dynamic_range_span",
        "expression.wedge_start_count",
        "expression.crescendo_start_count",
        "expression.diminuendo_start_count",
        "expression.staff_specific_dynamic_ratio",
    }

    hand_move_v = dim_vals.get("hand_movement_position")
    rhythm_v = dim_vals.get("rhythm_timing")
    coord_v = dim_vals.get("layers_coordination")
    expr_v = dim_vals.get("expression_sound_control")
    finger_v = dim_vals.get("finger_dexterity")
    notation_v = dim_vals.get("notation_reading")

    observations: list[dict[str, Any]] = []

    # 1. Coordination offset — hands not always together
    has_coord_async, coord_micro = _has_micro(brief, _coord_async_ids, 0.45)
    # Also consider aligned ratio low (<0.5) as async evidence if coord dimension elevated
    if coord_v is not None and coord_v >= 0.40:
        # need micro evidence or strong dimension
        if has_coord_async or coord_v >= 0.55:
            # Only emit if layers_coordination is primary or secondary and evidence exists
            if coord_v >= 0.45 and (has_coord_async or coord_v >= 0.50):
                # For conservative, require either micro or very high dimension
                ev = ["layers_coordination"]
                if coord_micro:
                    ev.append(coord_micro.get("feature_id") or "")
                observations.append(
                    {
                        "kind": "coordination_offset",
                        "text": "the hands do not always land together, so coordination has to stay steady between layers",
                        "confidence": "high" if (coord_v or 0) >= 0.55 and has_coord_async else "medium",
                        "support_level": "strong" if has_coord_async else "moderate",
                        "evidence": [e for e in ev if e],
                    }
                )

    # 2. Movement + timing coincidence
    has_leap, leap_micro = _has_micro(brief, _leap_ids, 0.55)
    has_rhythm, rhythm_micro = _has_micro(brief, _rhythm_ids, 0.45)
    # Also consider dimension-level coincidence
    if hand_move_v is not None and rhythm_v is not None:
        if hand_move_v >= 0.45 and rhythm_v >= 0.35 and (has_leap or hand_move_v >= 0.50) and (has_rhythm or rhythm_v >= 0.50):
            # Require both families present to avoid over-claiming
            if has_leap and has_rhythm:
                ev = ["hand_movement_position", "rhythm_timing", leap_micro.get("feature_id") if leap_micro else "", rhythm_micro.get("feature_id") if rhythm_micro else ""]
                observations.append(
                    {
                        "kind": "movement_plus_timing",
                        "text": "the passage combines wider hand movement with timing precision",
                        "confidence": "high" if hand_move_v >= 0.55 and rhythm_v >= 0.45 else "medium",
                        "support_level": "strong",
                        "evidence": [e for e in ev if e],
                    }
                )

    # 3. Expression over motion
    has_expr, expr_micro = _has_micro(brief, _expression_ids, 0.45)
    # Hairpin-specific check — only mention crescendo if wedge data exists (but keep generic phrase)
    has_wedge = any((m.get("feature_id") or "") in {"expression.wedge_start_count", "expression.crescendo_start_count", "expression.diminuendo_start_count"} and isinstance(m.get("raw_value"), (int, float)) and float(m.get("raw_value") or 0) > 0 for m in micros)
    if expr_v is not None and expr_v >= 0.40 and has_expr:
        motion_active = (hand_move_v is not None and hand_move_v >= 0.35) or (rhythm_v is not None and rhythm_v >= 0.35) or (finger_v is not None and finger_v >= 0.40)
        if motion_active:
            # Require both expression and motion families elevated
            if has_leap or has_rhythm or (hand_move_v or 0) >= 0.45 or (rhythm_v or 0) >= 0.45:
                ev = ["expression_sound_control", expr_micro.get("feature_id") if expr_micro else ""]
                # Add motion evidence
                if hand_move_v is not None and hand_move_v >= 0.35:
                    ev.append("hand_movement_position")
                if rhythm_v is not None and rhythm_v >= 0.35:
                    ev.append("rhythm_timing")
                # Text is generic — does NOT claim crescendo unless wedge data present, but phrase is same
                # If wedge present, still use generic dynamic shaping phrase (avoids unsupported crescendo claim)
                observations.append(
                    {
                        "kind": "expression_over_motion",
                        "text": "dynamic shaping happens while the notes are changing, so control has to stay consistent through the motion",
                        "confidence": "high" if expr_v >= 0.55 else "medium",
                        "support_level": "strong" if has_wedge else "moderate",
                        "evidence": [e for e in ev if e],
                    }
                )

    # 4. Hand movement with layer active — one hand wider shape while other keeps layer
    has_texture, texture_micro = _has_micro(brief, _texture_ids, 0.45)
    # Determine hand attribution only if micro carries scope_ref == left/right
    hand_attribution: str | None = None
    for m in micros:
        fid = m.get("feature_id") or ""
        if fid in _leap_ids and isinstance(m.get("normalized_value"), (int, float)) and float(m.get("normalized_value")) >= 0.55:
            sr = m.get("scope_ref") or m.get("hand") or ""
            if sr in ("left", "right"):
                hand_attribution = sr
                break
    if hand_move_v is not None and hand_move_v >= 0.45 and has_leap:
        # Need layers_coordination or texture as layer evidence
        layer_active = (coord_v is not None and coord_v >= 0.35) or has_texture or has_coord_async
        if layer_active:
            if hand_attribution == "left":
                text = "the left hand moves across a wider shape while the right hand keeps another layer active"
            elif hand_attribution == "right":
                text = "the right hand moves across a wider shape while the left hand keeps another layer active"
            else:
                text = "one hand moves across a wider shape while the other keeps another layer active"
            ev = ["hand_movement_position", "layers_coordination" if coord_v is not None and coord_v >= 0.35 else "texture"]
            if leap_micro:
                ev.append(leap_micro.get("feature_id") or "")
            if texture_micro:
                ev.append(texture_micro.get("feature_id") or "")
            observations.append(
                {
                    "kind": "hand_layer_active",
                    "text": text,
                    "confidence": "high" if hand_attribution and (coord_v or 0) >= 0.45 else "medium",
                    "support_level": "strong" if hand_attribution else "moderate",
                    "evidence": [e for e in ev if e],
                }
            )

    # 5. Sustained vs moving — one part sustains while another moves
    # Use texture simultaneity + async as evidence of sustained layer + moving layer
    # Need both texture and coordination signals
    if has_texture and has_coord_async and (coord_v is not None and coord_v >= 0.30):
        # Also need vertical density or notes_per_onset high
        has_sustained_candidate = any((m.get("feature_id") or "") in {"texture.vertical_density_proxy", "texture.simultaneity_density", "texture.notes_per_onset"} and isinstance(m.get("normalized_value"), (int, float)) and float(m.get("normalized_value")) >= 0.45 for m in micros)
        if has_sustained_candidate or (coord_v or 0) >= 0.40:
            ev = ["layers_coordination", texture_micro.get("feature_id") if texture_micro else "", coord_micro.get("feature_id") if coord_micro else ""]
            observations.append(
                {
                    "kind": "sustained_vs_moving",
                    "text": "one part sustains while another part moves, so balance and coordination matter",
                    "confidence": "medium",
                    "support_level": "moderate",
                    "evidence": [e for e in ev if e],
                }
            )

    # 6. Reading load semantic (optional, low priority) — only if notation signal clearly elevated
    if notation_v is not None and notation_v >= 0.55:
        has_notation, notation_micro = _micro_prefix_match(brief, "notation.", 0.50)
        if has_notation or notation_v >= 0.60:
            # Keep conservative generic reading phrase but this layer could specialize
            pass  # Phase 1 reading observation already covers; no new semantic needed

    # Deduplicate by text, prioritize high confidence
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    # Sort by confidence priority then support then kind specificity
    def _priority(o: dict[str, Any]) -> tuple[int, str]:
        conf = o.get("confidence") or "medium"
        order = {"high": 0, "medium": 1, "low": 2}
        return (order.get(conf, 1), o.get("kind") or "")

    observations.sort(key=_priority)
    for o in observations:
        txt = o.get("text") or ""
        if txt not in seen:
            seen.add(txt)
            deduped.append(o)
    # Cap to 2 most supported semantic observations (spec says 2-3 sentences)
    return deduped[:2]


def _build_observations(brief: dict[str, Any]) -> list[str]:
    """Conservative observation builder from existing brief signals.

    Phase 2: specific semantic observations take precedence when evidence
    supports them; Phase 1 generic mapping remains fallback.
    Returns up to 2 safe plain-language observation strings, ordered by
    supporting evidence strength. Uses only feature_ids / dimension_ids
    already present in the brief; does not invent contour/hand claims.
    """
    # Phase 2 semantic layer first
    semantic = _build_semantic_observations(brief)
    if semantic:
        texts = [o.get("text") or "" for o in semantic if o.get("text")]
        # Filter empty and return up to 2
        texts = [t for t in texts if t]
        if texts:
            return texts[:2]

    dims: list[dict] = brief.get("dimensions") or []
    micros: list[dict] = brief.get("micro_features") or []
    # Collect candidate observations from micro_features ranked by normalized_value
    candidates: list[tuple[float, str, str]] = []  # (strength, phrase, feature_id)
    for m in micros:
        fid = m.get("feature_id") or ""
        phrase = _FEATURE_OBSERVATION_MAP.get(fid)
        if not phrase:
            continue
        nv = m.get("normalized_value")
        strength = float(nv) if isinstance(nv, (int, float)) else -1.0
        candidates.append((strength, phrase, fid))
    # Sort by strength descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    observations: list[str] = []
    for _strength, phrase, _fid in candidates:
        if phrase not in seen:
            seen.add(phrase)
            observations.append(phrase)
        if len(observations) >= 2:
            break
    # Fallback to dimension mapping if no micro-based observation
    if not observations and dims:
        # Use primary dimension's fallback phrase
        for d in dims[:2]:
            did = d.get("dimension_id") or ""
            phrase = _DIMENSION_OBSERVATION_MAP.get(did)
            if phrase and phrase not in seen:
                seen.add(phrase)
                observations.append(phrase)
            if len(observations) >= 2:
                break
        # If still empty and we have a plain, synthesize a conservative generic
        if not observations:
            # Generic but safe: use the primary plain with an observation wrapper
            # Prefer a dimension-based generic phrase rather than inventing specifics
            primary = dims[0].get("dimension_id") or ""
            if primary in GRAPH_GLOSSARY:
                # Map any remaining graph dimension to its observation fallback already tried;
                # if not mapped, use a neutral demand phrase
                observations.append("control and coordination need to stay steady while the notes change")
            else:
                observations.append("control and coordination need to stay steady while the notes change")
    # If still empty (no dims/micros), return a neutral distributed phrase
    if not observations:
        observations.append("the musical texture shifts here, so steadiness and balance need attention")
    return observations[:2]


def _build_learner_summary(brief: dict[str, Any]) -> tuple[str, str]:
    """Build learner-facing summary and Why It Feels Hard.

    Returns (summary, why_text). Summary is 2-3 sentences: concrete demand,
    why it matters, optional classification. Why text is a short interplay
    sentence using the same observation vocabulary.
    """
    measure_range = brief.get("measure_range") or "this passage"
    dims: list[dict] = brief.get("dimensions") or []
    has_strong = any(isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5 for d in dims[:2])
    # Distributed case: no strong signal — keep learner language modest
    if dims and not has_strong:
        observations = _build_observations(brief)
        # If observations are still low-confidence, acknowledge balance
        s1 = f"In measures {measure_range}, {observations[0]}." if len(observations) == 1 else f"In measures {measure_range}, {observations[0]} and {observations[1]}."
        primary_obs = observations[0] if observations else "the musical texture shifts here, so steadiness and balance need attention"
        s2 = _OBSERVATION_REASON.get(primary_obs, "That pattern makes it harder to keep the playing steady and even.")
        # For distributed, add balanced caveat as third sentence rather than strong classification
        s3 = "Overall the demands are fairly balanced here, so no single type dominates."
        # Also handle second observation reason if present, similar to focused case
        if len(observations) == 2:
            second_reason = _OBSERVATION_REASON.get(observations[1], "")
            if second_reason and second_reason != s2:
                s2 = s2 + f" At the same time, {observations[1]} — {second_reason[0].lower() + second_reason[1:]}"
        parts = [s1, s2, s3]
        summary = " ".join(parts)
        if len(observations) == 1:
            why = _OBSERVATION_REASON.get(observations[0], s2)
        else:
            why = _OBSERVATION_REASON.get(observations[0], s2) + f" Here it coincides with {observations[1]}, so both demands need attention at once."
        return summary, why

    observations = _build_observations(brief)
    # Sentence 1 — concrete demand
    if len(observations) == 1:
        s1 = f"In measures {measure_range}, {observations[0]}."
    else:
        # Join two observations with "and"
        s1 = f"In measures {measure_range}, {observations[0]} and {observations[1]}."
    # Sentence 2 — why it creates playing difficulty (reason for primary observation)
    primary_obs = observations[0] if observations else "the musical texture shifts here, so steadiness and balance need attention"
    s2 = _OBSERVATION_REASON.get(primary_obs, "That pattern makes it harder to keep the playing steady and even.")
    # If two observations with distinct reasons, combine second reason as clause
    if len(observations) == 2:
        second_reason = _OBSERVATION_REASON.get(observations[1], "")
        # Avoid duplicating if same reason; otherwise append as second sentence
        if second_reason and second_reason != s2:
            s2 = s2 + f" At the same time, {observations[1]} — {_OBSERVATION_REASON[observations[1]][0].lower() + _OBSERVATION_REASON[observations[1]][1:]}"
    # Sentence 3 — classification (taxonomy label only after explaining demand)
    s3 = ""
    if dims:
        p_plain = dims[0].get("plain") or _resolve_plain({"dimension_id": dims[0].get("dimension_id")})
        # Determine if secondary is meaningfully present (normalized >= 0.33 or secondary strength moderate+)
        secondary_strong = False
        s_plain = ""
        if len(dims) >= 2:
            nv = dims[1].get("normalized_value")
            s_plain = dims[1].get("plain") or _resolve_plain({"dimension_id": dims[1].get("dimension_id")})
            if isinstance(nv, (int, float)) and float(nv) >= 0.33:
                secondary_strong = True
            elif dims[1].get("strength") in ("moderate", "high", "very high"):
                secondary_strong = True
        if secondary_strong and s_plain:
            s3 = f"That is why the passage is classified mainly as {p_plain}, with {s_plain} also involved."
        else:
            s3 = f"That is why the passage is classified mainly as {p_plain}."
    # Compose summary
    parts = [s1, s2]
    if s3:
        parts.append(s3)
    summary = " ".join(parts)
    # Why text — short interplay using observations
    if len(observations) == 1:
        why = _OBSERVATION_REASON.get(observations[0], s2)
    else:
        # Combined why: first reason + reference to second demand
        why = _OBSERVATION_REASON.get(observations[0], s2)
        # Add note about coincidence if two observations (keep period before Here)
        why = why + f" Here it coincides with {observations[1]}, so both demands need attention at once."
    return summary, why


def _build_provenance_summary(brief: dict[str, Any]) -> str:
    """System-centered provenance text (old score-derived language).

    Kept for debug/provenance drawer only; includes selection reason,
    contributors, and relative-within-piece caveat.
    """
    measure_range = brief.get("measure_range") or "this window"
    dims: list[dict] = brief.get("dimensions") or []
    micro: list[dict] = brief.get("micro_features") or []
    score_value = brief.get("score_value")
    rel = brief.get("relative_strength") or "unknown"
    if not dims:
        base = (
            "The score-derived evidence for this window is distributed — no single dimension stands out strongly. "
            "The trace suggests a modest, shared contribution across dimensions within this piece (not a calibrated grade)."
        )
    else:
        has_strong = any(isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5 for d in dims[:2])
        if not has_strong:
            names = ", ".join(d.get("plain") or "" for d in dims[:2])
            base = (
                f"The score-derived evidence points to a distributed pattern in measures {measure_range}: "
                f"{names} are the relatively higher signals, but all remain moderate or lower. "
                "This suggests no single demand dominates here — the window sits close to the piece average."
            )
        else:
            primary = dims[0]
            p_plain = primary.get("plain") or "unknown"
            p_strength = primary.get("strength") or "unknown"
            p_role = primary.get("role") or "primary"
            elevated = [d for d in dims if isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5]
            if len(dims) >= 2 and len(elevated) >= 2:
                secondary = dims[1]
                s_plain = secondary.get("plain") or "unknown"
                s_strength = secondary.get("strength") or "unknown"
                base = (
                    f"The score-derived evidence suggests measures {measure_range} stand out mainly for {p_plain} "
                    f"({p_strength}, {p_role}), with secondary support from {s_plain} ({s_strength}). "
                    "The signal is relative within this piece, not a calibrated grade or learner diagnosis."
                )
            else:
                base = (
                    f"The score-derived evidence points to {p_plain} as the primary contributor in measures {measure_range} "
                    f"({p_strength}). The other dimensions are lower in this window. The signal is relative within this piece."
                )
        if micro:
            sorted_micro = sorted(micro, key=lambda m: (m.get("normalized_value") if isinstance(m.get("normalized_value"), (int, float)) else -1), reverse=True)
            top_feats = sorted_micro[:3]
            clauses = "; ".join(_micro_clause(f) for f in top_feats)
            base += f" Supporting micro-features: {clauses}."
    # Append score/selection cue
    if isinstance(score_value, (int, float)):
        base += f" Composite around {float(score_value):.2f} — {rel} (relative within this piece, normalized)."
    if dims:
        # mention normalized values
        vals = ", ".join(f"{d.get('plain')} {d.get('normalized_value'):.2f}" if isinstance(d.get('normalized_value'), (int,float)) else f"{d.get('plain')} n/a" for d in dims[:3])
        base += f" Normalized contributors: {vals}."
    return base


# Versions
EVIDENCE_VERSION = "david_evidence.v1"
HEURISTIC_VERSION = "david_heuristic.v3"
LLM_PROMPT_VERSION = "david_llm_polish.v1"
LLM_SCHEMA_VERSION = "david_llm.v1"


def _plain_graph(dimension_id: str) -> str:
    entry = GRAPH_GLOSSARY.get(dimension_id)
    if entry:
        return entry["plain"]
    return dimension_id.replace("_", " ").replace("/", " / ")


def _plain_aspect(aspect_id: str) -> str:
    if aspect_id in GRAPH_GLOSSARY:
        return _plain_graph(aspect_id)
    entry = ASPECT_GLOSSARY.get(aspect_id)
    if entry:
        return entry["plain"]
    return aspect_id.replace("_", " ").replace("/", " / ")


def _resolve_plain(contrib: dict) -> str:
    dim_id = contrib.get("dimension_id") or contrib.get("graph_dimension_id") or contrib.get("aspect_id") or contrib.get("feature_id") or contrib.get("id") or ""
    if dim_id in GRAPH_GLOSSARY:
        return _plain_graph(dim_id)
    if dim_id in ASPECT_GLOSSARY:
        return _plain_aspect(dim_id)
    return str(dim_id).replace("_", " ").replace("/", " / ") if dim_id else "unknown"


def _plain_feature(feature_id: str, label: str | None = None) -> str:
    if feature_id in FEATURE_GLOSSARY:
        return FEATURE_GLOSSARY[feature_id]
    if label:
        return label.replace("_", " ").replace(".", " · ")
    return feature_id.replace("_", " ").replace(".", " · ")


def strength_label(normalized_value: float | None) -> str:
    if normalized_value is None or not isinstance(normalized_value, (int, float)):
        return "unknown"
    v = float(normalized_value)
    if v >= 0.75:
        return "very high"
    if v >= 0.55:
        return "high"
    if v >= 0.33:
        return "moderate"
    return "low"


def role_label(rank: int | None) -> str:
    if rank == 1:
        return "primary"
    if rank in (2, 3):
        return "secondary"
    return "supporting"


def _fmt_raw(raw: Any, units: str | None) -> str:
    if raw is None:
        return "—"
    if isinstance(raw, float):
        # keep 2-3 decimals but avoid spurious
        if abs(raw) >= 100:
            return f"{raw:.1f}"
        if abs(raw) >= 10:
            return f"{raw:.2f}"
        return f"{raw:.3f}"
    return str(raw)


def _evidence_hash(canonical: dict) -> str:
    """Stable hash of evidence brief (excluding its own hash field)."""
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Evidence brief
# ---------------------------------------------------------------------------

def build_evidence_brief(
    hotspot: dict[str, Any],
    chart: dict[str, Any] | None = None,
    piece: dict[str, Any] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    """Build compact deterministic evidence brief for one hotspot.

    Uses only existing manifest data; no new analysis.
    """
    measure_range = hotspot.get("measure_range") or ""
    if not measure_range or measure_range == "unknown":
        nums = hotspot.get("measure_numbers") or []
        if len(nums) >= 2:
            measure_range = f"{nums[0]}–{nums[-1]}"
        elif len(nums) == 1:
            measure_range = str(nums[0])
        else:
            measure_range = "this window"

    score_value = hotspot.get("score_value")
    if score_value is None:
        score_value = hotspot.get("score")

    # Contributors — prefer graph dimensions
    contributors = (
        hotspot.get("dimension_contributors")
        or hotspot.get("graph_dimension_contributors")
        or hotspot.get("top_contributors")
        or hotspot.get("contributions")
        or hotspot.get("aspect_contributors")
        or hotspot.get("feature_contributions")
        or []
    )
    try:
        contributors = sorted(contributors, key=lambda c: (c.get("rank") if isinstance(c.get("rank"), int) else 999))
    except Exception:
        pass

    # Chart context
    total_windows = None
    window_index = None
    if chart and isinstance(chart, dict):
        regions = chart.get("regions") or []
        if isinstance(regions, list):
            total_windows = len(regions)
        rep = hotspot.get("representative_region") or {}
        window_index = rep.get("window_index")
        if window_index is None:
            sw = hotspot.get("supporting_window_indices") or []
            if sw:
                window_index = sw[0]
        if window_index is None and hotspot.get("window_index") is not None:
            window_index = hotspot.get("window_index")

    # Relative strength label
    if isinstance(score_value, (int, float)):
        sv = float(score_value)
        if sv >= 0.55:
            rel_strength = "relatively high for this piece"
        elif sv >= 0.42:
            rel_strength = "above the piece average"
        elif sv >= 0.32:
            rel_strength = "near the piece average"
        else:
            rel_strength = "relatively modest for this piece"
    else:
        rel_strength = "unknown"

    # Position hint
    position_hint = None
    if isinstance(window_index, int) and isinstance(total_windows, int) and total_windows:
        pct = window_index / max(1, total_windows - 1)
        if pct < 0.2:
            position_hint = "near the opening"
        elif pct < 0.4:
            position_hint = "in the early-middle"
        elif pct < 0.6:
            position_hint = "around the middle"
        elif pct < 0.8:
            position_hint = "in the late-middle"
        else:
            position_hint = "toward the end"

    # Dimensions (top 3)
    dims: list[dict[str, Any]] = []
    for c in contributors[:3]:
        dim_id = c.get("dimension_id") or c.get("graph_dimension_id") or c.get("feature_id") or c.get("id") or c.get("aspect_id") or ""
        dims.append(
            {
                "rank": c.get("rank"),
                "dimension_id": dim_id,
                "label": c.get("label") or c.get("feature_name") or dim_id,
                "plain": _resolve_plain(c),
                "normalized_value": c.get("normalized_value"),
                "strength": strength_label(c.get("normalized_value")),
                "role": role_label(c.get("rank")),
                "contribution_share": c.get("contribution_share"),
                "is_peak_support": bool(c.get("is_peak_support")),
                "units": c.get("units") or "normalized_score",
            }
        )

    # Micro-features — collect top 3-6 across primary+secondary dimensions
    micro: list[dict[str, Any]] = []
    # Strategy: take up to 3 from rank 1, up to 2 from rank 2, up to 1 from rank 3
    budgets = [3, 2, 1]
    for idx, contrib in enumerate(contributors[:3]):
        budget = budgets[idx] if idx < len(budgets) else 0
        feats = contrib.get("feature_contributors") or contrib.get("supporting_feature_contributors") or contrib.get("graph_contributors") or []
        try:
            feats = sorted(feats, key=lambda f: (f.get("rank") if isinstance(f.get("rank"), int) else 999))
        except Exception:
            pass
        dim_id = contrib.get("dimension_id") or contrib.get("graph_dimension_id") or contrib.get("feature_id") or contrib.get("id") or ""
        for f in feats[:budget]:
            if len(micro) >= 6:
                break
            fid = f.get("feature_id") or ""
            micro.append(
                {
                    "rank": f.get("rank"),
                    "feature_id": fid,
                    "plain": _plain_feature(fid, f.get("label") or f.get("feature_name")),
                    "parent_dimension_id": dim_id,
                    "parent_dimension_plain": _plain_graph(dim_id) if dim_id in GRAPH_GLOSSARY else _plain_aspect(dim_id) if dim_id in ASPECT_GLOSSARY else dim_id,
                    "raw_value": f.get("raw_value"),
                    "normalized_value": f.get("normalized_value"),
                    "strength": strength_label(f.get("normalized_value")),
                    "weighted_value": f.get("weighted_value"),
                    "contribution_share": f.get("contribution_share"),
                    "units": f.get("units"),
                    "weight": f.get("weight"),
                    "scope": f.get("scope"),
                    "scope_ref": f.get("scope_ref") or f.get("hand"),
                }
            )
        if len(micro) >= 6:
            break
    # If still <3 and we have contributors with many feats, fill up to 6 from primary
    if len(micro) < 3 and contributors:
        primary_feats = contributors[0].get("feature_contributors") or contributors[0].get("supporting_feature_contributors") or contributors[0].get("graph_contributors") or []
        try:
            primary_feats = sorted(primary_feats, key=lambda f: (f.get("rank") if isinstance(f.get("rank"), int) else 999))
        except Exception:
            pass
        for f in primary_feats:
            if len(micro) >= 6:
                break
            fid = f.get("feature_id") or ""
            if any(m["feature_id"] == fid for m in micro):
                continue
            dim_id = contributors[0].get("dimension_id") or contributors[0].get("graph_dimension_id") or ""
            micro.append(
                {
                    "rank": f.get("rank"),
                    "feature_id": fid,
                    "plain": _plain_feature(fid, f.get("label") or f.get("feature_name")),
                    "parent_dimension_id": dim_id,
                    "parent_dimension_plain": _plain_graph(dim_id) if dim_id in GRAPH_GLOSSARY else dim_id,
                    "raw_value": f.get("raw_value"),
                    "normalized_value": f.get("normalized_value"),
                    "strength": strength_label(f.get("normalized_value")),
                    "weighted_value": f.get("weighted_value"),
                    "contribution_share": f.get("contribution_share"),
                    "units": f.get("units"),
                    "weight": f.get("weight"),
                    "scope": f.get("scope"),
                    "scope_ref": f.get("scope_ref") or f.get("hand"),
                }
            )

    # Peak flags
    peak_flags = [c.get("dimension_id") or c.get("graph_dimension_id") or c.get("aspect_id") or "" for c in contributors if c.get("is_peak_support")]
    peak_flags = [p for p in peak_flags if p]

    # Interpretation hints (short deterministic)
    hints: list[str] = []
    if not contributors:
        hints.append("distributed — no single dimension dominates")
    else:
        has_strong = any(isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.5 for c in contributors[:2])
        if not has_strong:
            hints.append("distributed — balanced, near piece average")
        elif len([c for c in contributors[:3] if isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.5]) >= 2:
            hints.append("combined — two or more dimensions elevated together")
            # detect specific combos
            plains = [_resolve_plain(c) for c in contributors[:3] if isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.5]
            if "hand shape and span" in plains and "texture and polyphony" in plains:
                hints.append("texture + span coincidence")
            if "finger dexterity" in plains and "hand position / movement" in plains:
                hints.append("dexterity + movement coincidence")
        else:
            hints.append("focused — single primary dimension shapes passage")
        if any(isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.75 for c in contributors[:3]):
            hints.append("one signal very high locally")

    # Claim boundaries (compact excerpt)
    cb: list[str] = []
    if caveats:
        # Keep most relevant boundaries, capped
        for c in caveats[:6]:
            if isinstance(c, str) and c.strip():
                cb.append(c.strip())
    if not cb:
        cb = [
            "Symbolic-score evidence only; no calibrated learner grade.",
            "Relative within this piece; not comparable across pieces.",
            "No learner diagnosis or measured benefit claimed.",
        ]

    piece_identity = {
        "piece_id": (piece or {}).get("piece_id") or (piece or {}).get("id") or (piece or {}).get("demo_id") or hotspot.get("piece_id") or None,
        "title": (piece or {}).get("title"),
        "composer": (piece or {}).get("composer"),
    }

    brief_no_hash = {
        "evidence_version": EVIDENCE_VERSION,
        "piece_identity": piece_identity,
        "hotspot_id": hotspot.get("id") or hotspot.get("section_id") or hotspot.get("hotspot_id"),
        "rank": hotspot.get("rank"),
        "measure_range": measure_range,
        "measure_numbers": hotspot.get("measure_numbers") or [],
        "window_index": window_index,
        "total_windows": total_windows,
        "position_hint": position_hint,
        "score_value": score_value,
        "relative_strength": rel_strength,
        "dimensions": dims,
        "micro_features": micro,
        "peak_support_flags": peak_flags,
        "interpretation_hints": hints,
        "claim_boundaries": cb[:6],
        "source": {
            "taxonomy_version": (chart or {}).get("taxonomy_version") or (chart or {}).get("graph_taxonomy_version") or "gradus.front_graph_taxonomy.v2",
            "method": hotspot.get("method") or "graph_composite_top_n.v1",
            "chart_window_count": total_windows,
        },
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    h = _evidence_hash(brief_no_hash)
    brief = dict(brief_no_hash)
    brief["evidence_hash"] = h
    return brief


# ---------------------------------------------------------------------------
# Heuristic explanation from brief
# ---------------------------------------------------------------------------

def _micro_clause(feat: dict) -> str:
    """Plain micro-feature clause with raw value and units."""
    plain = feat.get("plain") or _plain_feature(feat.get("feature_id") or "", None)
    raw = feat.get("raw_value")
    units = feat.get("units")
    norm = feat.get("normalized_value")
    strength = feat.get("strength") or strength_label(norm)
    if isinstance(raw, (int, float)) and units:
        # e.g. "largest melodic leap — 43 semitones (normalized 1.00, very high)"
        return f"{plain} — {_fmt_raw(raw, units)} {units} (normalized {norm:.2f}, {strength})" if isinstance(norm, (int, float)) else f"{plain} — {_fmt_raw(raw, units)} {units}"
    if isinstance(raw, (int, float)):
        return f"{plain} — {_fmt_raw(raw, units)} (normalized {norm:.2f}, {strength})" if isinstance(norm, (int, float)) else f"{plain} — {_fmt_raw(raw, units)}"
    if isinstance(norm, (int, float)):
        return f"{plain} (normalized {norm:.2f}, {strength})"
    return plain


def build_heuristic_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """Deterministic heuristic prose from evidence brief.

    Phase 1: learner-facing summary uses plain observation language;
    system-centered provenance is preserved in separate fields for the
    debug/provenance drawer only.
    """
    measure_range = brief.get("measure_range") or "this window"
    dims: list[dict] = brief.get("dimensions") or []
    score_value = brief.get("score_value")
    rank = brief.get("rank")
    total_windows = brief.get("total_windows")
    window_index = brief.get("window_index")
    position_hint = brief.get("position_hint")

    # Headline — keep plain, no system framing
    if dims:
        lead_plain = dims[0].get("plain") or "unknown"
        lead_strength = dims[0].get("strength") or "unknown"
        headline = f"Measures {measure_range} — {lead_plain} stands out ({lead_strength})"
    else:
        headline = f"Measures {measure_range} — distributed evidence"

    # Learner-facing summary + why (Phase 1 observation builder)
    learner_summary, learner_why = _build_learner_summary(brief)
    # Legacy provenance (debug drawer only) — retains score-derived language
    provenance_summary = _build_provenance_summary(brief)

    # Provenance interplay (old system language) — kept for debug
    # Reconstruct old interplay from provenance perspective for completeness
    if not dims:
        provenance_interplay = "No dimension contributor data is available for this window — the explanation is limited to position and composite."
    else:
        has_strong = any(isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5 for d in dims[:2])
        if not has_strong:
            provenance_interplay = (
                "The evidence is distributed — the score-derived signals are broadly similar across the top dimensions, "
                "so no clear interplay dominates. This window reflects a balanced, average passage (6-dimension graph; 9-aspect backend for provenance)."
            )
        elif len([d for d in dims if isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5]) >= 2:
            elevated_plains = [d.get("plain") for d in dims if isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.5]
            names = ", ".join(elevated_plains[:3])
            if "hand shape and span" in elevated_plains and "texture and polyphony" in elevated_plains:
                provenance_interplay = (
                    f"Two or more dimensions are elevated together — {', '.join(elevated_plains[:2])} — "
                    "which suggests that multiple notes sounding together coincides with wider hand shapes in this window. "
                    "The score-derived evidence points to a combined texture + span character, not a single cause."
                )
            elif "rhythm" in elevated_plains or "rhythm & timing" in elevated_plains:
                has_coord = any("coordination" in (p or "") for p in elevated_plains)
                if has_coord:
                    provenance_interplay = (
                        f"{', '.join(elevated_plains[:2]).capitalize()} both stand out here, which suggests rhythmic activity coincides with hands moving somewhat independently. "
                        "The combination is descriptive — it does not diagnose learner difficulty."
                    )
                else:
                    provenance_interplay = (
                        f"More than one dimension is elevated — {names} — which suggests these demands coincide in this window. "
                        "The overlap is descriptive within the 6-dimension graph (9-aspect backend provenance), not a weighted difficulty claim."
                    )
            elif "finger dexterity" in elevated_plains and "hand position / movement" in elevated_plains:
                provenance_interplay = (
                    f"{', '.join(elevated_plains[:2]).capitalize()} stand out together, suggesting dexterity demands coincide with larger relocations. "
                    "The interplay is relative to this piece."
                )
            else:
                provenance_interplay = (
                    f"More than one dimension is elevated — {names} — which suggests these demands coincide in this window. "
                    "The overlap is descriptive within the 6-dimension graph (9-aspect backend provenance), not a weighted difficulty claim."
                )
            if any(isinstance(d.get("normalized_value"), (int, float)) and float(d.get("normalized_value")) >= 0.75 for d in dims[:3]):
                provenance_interplay += " One signal reaches very high locally, which makes the combined character more noticeable on the chart."
        else:
            p_plain = dims[0].get("plain") or "unknown"
            provenance_interplay = (
                f"The primary signal is {p_plain}; the other dimensions are lower here, so the window's character is mainly shaped by that one demand. "
                "The score-derived evidence suggests a focused rather than combined pattern in this passage."
            )

    # Score cue — provenance only (contains normalized / relative language)
    if isinstance(score_value, (int, float)):
        sv = float(score_value)
        rel = brief.get("relative_strength") or "unknown"
        score_cue = (
            f"Composite around {sv:.2f} — {rel}. Hotspot rank #{rank or '?'}; "
            "the value is a descriptive mean within the 6-dimension graph (9-aspect backend provenance), not a calibrated grade."
        )
    else:
        score_cue = "Composite is not available for this window — the ranking is relative within the 6-dimension graph (9-aspect backend provenance), not a calibrated grade."

    # Timeline
    timeline_context: str | None = None
    if isinstance(window_index, int) and isinstance(total_windows, int) and total_windows:
        where = position_hint or "in the piece"
        timeline_context = (
            f"Window {window_index + 1} of {total_windows} {where} (measures {measure_range}). "
            "Position is descriptive — it does not imply a learning sequence."
        )
    elif isinstance(total_windows, int) and total_windows:
        timeline_context = f"One of {total_windows} windows (measures {measure_range}). Position is descriptive within this piece."

    observations = _build_observations(brief)
    semantic_structured = _build_semantic_observations(brief)

    # Optionally annotate provenance with semantic evidence (debug drawer only, not learner card)
    if semantic_structured:
        try:
            clauses = []
            for s in semantic_structured:
                ev = ", ".join(s.get("evidence") or [])
                kind = s.get("kind") or ""
                txt = s.get("text") or ""
                # shorten evidence list for debug
                if ev:
                    clauses.append(f"{kind}: \"{txt}\" [{ev}]")
                else:
                    clauses.append(f"{kind}: \"{txt}\"")
            provenance_summary = provenance_summary + f" Semantic observations (evidence-backed): {'; '.join(clauses)}."
        except Exception:
            pass

    return {
        "headline": headline,
        # Learner-facing (default card)
        "summary": learner_summary,
        "aspect_interplay": learner_why,
        "dimension_interplay": learner_why,
        # Provenance/debug (drawer only)
        "provenance_summary": provenance_summary,
        "provenance_interplay": provenance_interplay,
        "learner_observations": observations,
        "semantic_observations": semantic_structured,
        "score_cue": score_cue,
        "timeline_context": timeline_context,
        "confidence": "heuristic",
        "version": HEURISTIC_VERSION,
        "evidence_hash": brief.get("evidence_hash"),
        "evidence_version": brief.get("evidence_version"),
    }


def build_hotspot_explanation(
    hotspot: dict[str, Any],
    chart: dict[str, Any] | None = None,
    caveats: list[str] | None = None,
    piece: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic heuristic explanation from hotspot + chart context.

    Backward-compatible wrapper that builds a brief first.
    """
    brief = build_evidence_brief(hotspot, chart, piece, caveats)
    return build_heuristic_from_brief(brief)


# ---------------------------------------------------------------------------
# LLM polish layer — deterministic mock + validation helpers
# ---------------------------------------------------------------------------

# Forbidden inventions — if LLM text mentions these without evidence, flag.
# These mirror passage_practice claim boundaries but scoped to David demo.
FORBIDDEN_PHRASES = [
    r"\bfingering\b",
    r"\bfingerings\b",
    r"\bgrade\b",
    r"\bhenle\b",
    r"\bdiagnos",
    r"\blearner\b.*\bdifficulty\b",
    r"\bwill improve\b",
    r"\bshould practice\b.*\bhrs\b",
]


def build_llm_prompt(brief: dict[str, Any]) -> str:
    """Render conservative prompt that instructs LLM to narrate brief only."""
    import json as _json

    dims = brief.get("dimensions") or []
    micros = brief.get("micro_features") or []
    lines = [
        "You are a piano-score narrator. You must ONLY use the evidence brief below.",
        "Do not invent features, grades, fingerings, diagnoses, or benefits.",
        "Improve wording, connect facts musically, produce a short practice focus from the listed micro-features.",
        "Keep plain language; do not show raw feature IDs in prose (they are for the drawer).",
        "Cite at least one micro-feature with its raw value and units.",
        "",
        "EVIDENCE_BRIEF (JSON):",
        _json.dumps(brief, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False),
        "",
        "Return JSON with keys: summary, musical_connection, practice_focus (each 1-2 sentences).",
    ]
    return "\n".join(lines)


def validate_llm_output(text: str, brief: dict[str, Any]) -> list[str]:
    """Check LLM output for invented content; return violation messages."""
    import re

    violations: list[str] = []
    lower = (text or "").lower()
    # Check forbidden phrases
    for pat in FORBIDDEN_PHRASES:
        if re.search(pat, lower):
            # Allow boundary phrase "not a grade" / "not a calibrated grade" as legitimate claim-boundary language
            if pat == r"\bgrade\b" and ("not a grade" in lower or "not a calibrated grade" in lower):
                continue
            # Allow "learner diagnosis" boundary phrase
            if pat == r"\bdiagnos" and ("not a" in lower and "diagnos" in lower and "learner" in lower):
                # if the phrase is the standard boundary "not a calibrated grade or learner diagnosis", allow
                if "learner diagnosis" in lower or "learner-dependent" in lower:
                    continue
            violations.append(f"forbidden phrase matched {pat!r}")
    # Check feature hallucination: any feature_id mentioned that is not in brief's micro_features or dimensions?
    # We hide raw IDs in prose, so any occurrence of a dot-feature id is a leak, not invention — but we flag as style violation
    # For hallucination, check that plain micro-feature phrases are grounded: if LLM mentions a plain that is not in brief's glossary-mapped plains
    # Simpler: if LLM mentions a feature plain not in brief's micro_features plains, warn — but allow generic dimension plains
    allowed_plains = set()
    for d in brief.get("dimensions") or []:
        if d.get("plain"):
            allowed_plains.add(d["plain"].lower())
    for m in brief.get("micro_features") or []:
        if m.get("plain"):
            allowed_plains.add(m["plain"].lower())
    # Look for feature plain mentions that are clearly hallucinated? Hard to detect without NLU.
    # At minimum, ensure at least one micro plain is cited if brief has micro_features
    if brief.get("micro_features") and allowed_plains:
        cited = any(p in lower for p in allowed_plains)
        if not cited:
            violations.append("LLM summary does not cite any brief micro-feature plain")
    return violations


def build_llm_explanation(
    brief: dict[str, Any],
    llm_text: dict[str, str] | None = None,
    *,
    model: str = "mock",
    prompt_version: str = LLM_PROMPT_VERSION,
) -> dict[str, Any]:
    """Wrap LLM text dict into stored object with hash/model metadata.

    llm_text should have keys summary, musical_connection, practice_focus.
    If None, returns a deterministic mock polish (no network).
    """
    if llm_text is None:
        # Deterministic mock polish — rephrase heuristic using brief (learner-facing)
        heur = build_heuristic_from_brief(brief)
        # Phase 1: summary is already learner-facing; no score-derived framing to replace
        summary_polish = heur["summary"]
        # musical connection: connect primary + secondary if present
        dims = brief.get("dimensions") or []
        if len(dims) >= 2:
            conn = f"The elevated {dims[0].get('plain')} together with {dims[1].get('plain')} gives this window a combined character; treat them as coinciding demands, not a single cause."
        elif dims:
            conn = f"The character here is shaped mainly by {dims[0].get('plain')}; the other dimensions are lower, so the signal is focused."
        else:
            conn = "The evidence is distributed, so no single dimension dominates this window."
        micros = brief.get("micro_features") or []
        if micros:
            top = sorted(micros, key=lambda m: (m.get("normalized_value") or 0), reverse=True)[:2]
            parts = []
            for m in top:
                plain = m.get("plain") or ""
                raw = m.get("raw_value")
                units = m.get("units") or ""
                if isinstance(raw, (int, float)):
                    parts.append(f"{plain} ({_fmt_raw(raw, units)} {units})")
                else:
                    parts.append(plain)
            focus = f"Notice {', '.join(parts)} in this passage; observe them at a comfortable pace without prescribing technique."
        else:
            focus = "Scan the passage as written; no single micro-feature dominates, so keep the focus on the overall shape."
        llm_text = {
            "summary": summary_polish,
            "musical_connection": conn,
            "practice_focus": focus,
        }

    return {
        "schema_version": LLM_SCHEMA_VERSION,
        "model": model,
        "prompt_version": prompt_version,
        "evidence_hash": brief.get("evidence_hash"),
        "evidence_version": brief.get("evidence_version"),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "summary": llm_text.get("summary") or "",
        "musical_connection": llm_text.get("musical_connection") or "",
        "practice_focus": llm_text.get("practice_focus") or "",
        "violations": validate_llm_output(
            " ".join([llm_text.get("summary") or "", llm_text.get("musical_connection") or "", llm_text.get("practice_focus") or ""]),
            brief,
        ),
    }


# For JS parity, expose glossary via function
def get_glossaries() -> dict[str, Any]:
    return {"graph_dimensions": GRAPH_GLOSSARY, "aspects": ASPECT_GLOSSARY, "features": FEATURE_GLOSSARY}
