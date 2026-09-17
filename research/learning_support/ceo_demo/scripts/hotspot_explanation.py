#!/usr/bin/env python3
"""Deterministic hotspot explanation helper for CEO demo (v0).

Thin presentation layer over existing manifest data. No LLM, no new analysis.
Only uses:
 - measure_range / measure_numbers
 - score_value
 - top_contributors / aspect_contributors
 - feature_contributors / supporting_feature_contributors
 - chart context (window count, aspect series)
 - caveats / warnings (for guardrail phrasing, not claimed as diagnosis)

Generates a safe, cautious explanation object per hotspot:
 {
   "headline": str,
   "summary": str,
   "aspect_interplay": str,
   "score_cue": str,
   "timeline_context": str | None,
   "confidence": "heuristic"
 }

Glossaries map technical aspect/feature labels to plain language.
All language is cautious: suggests / stands out / score-derived evidence points to.
No calibrated grade, learner diagnosis, measured benefit, or fingering advice is claimed.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Glossaries — plain language for the 9-aspect taxonomy and common features.
# Keep user-facing model as 9 aspects; features are supporting evidence only.
# ---------------------------------------------------------------------------

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

# Feature glossary — maps technical feature_id to short plain phrase.
# Unknown features fall back to a cleaned label.
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


def _plain_aspect(aspect_id: str) -> str:
    entry = ASPECT_GLOSSARY.get(aspect_id)
    if entry:
        return entry["plain"]
    # fallback: turn snake into words
    return aspect_id.replace("_", " ").replace("/", " / ")


def _plain_feature(feature_id: str, label: str | None = None) -> str:
    if feature_id in FEATURE_GLOSSARY:
        return FEATURE_GLOSSARY[feature_id]
    if label:
        # clean label fallback
        return label.replace("_", " ").replace(".", " · ")
    return feature_id.replace("_", " ").replace(".", " · ")


def strength_label(normalized_value: float | None) -> str:
    """Map normalized_value 0..1 to qualitative strength label."""
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


def _aspect_cue(aspect_id: str, normalized: float | None, rank: int | None) -> str:
    plain = _plain_aspect(aspect_id)
    strength = strength_label(normalized)
    role = role_label(rank)
    return f"{plain} ({strength}, {role})"


def build_hotspot_explanation(
    hotspot: dict[str, Any],
    chart: dict[str, Any] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    """Build deterministic heuristic explanation from hotspot + chart context.

    Only uses existing manifest data; no external model or learner claim.
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

    # Contributors — prefer aspect_contributors, fallback to top_contributors/contributions
    contributors = (
        hotspot.get("aspect_contributors")
        or hotspot.get("top_contributors")
        or hotspot.get("contributions")
        or []
    )
    # Ensure sorted by rank
    try:
        contributors = sorted(contributors, key=lambda c: (c.get("rank") if isinstance(c.get("rank"), int) else 999))
    except Exception:
        pass

    top = contributors[:3]
    top_ids = [c.get("aspect_id") or c.get("feature_id") or c.get("id") for c in top if c]

    # Strength heuristics
    elevated = [c for c in top if isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.5]
    very_high = [c for c in top if isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.75]
    has_strong = any(isinstance(c.get("normalized_value"), (int, float)) and float(c.get("normalized_value")) >= 0.5 for c in contributors[:2])

    # Headline — mention measure and top aspect plain
    if top:
        lead_plain = _plain_aspect(top[0].get("aspect_id") or top[0].get("feature_id") or "")
        lead_strength = strength_label(top[0].get("normalized_value"))
        headline = f"Measures {measure_range} — {lead_plain} stands out ({lead_strength})"
    else:
        headline = f"Measures {measure_range} — distributed evidence"

    # Summary
    if not contributors:
        summary = (
            "The score-derived evidence for this window is distributed — no single aspect stands out strongly. "
            "The trace suggests a modest, shared contribution across aspects within this piece (not a calibrated grade)."
        )
    elif not has_strong:
        # distributed
        aspects_phrase = ", ".join(_plain_aspect(c.get("aspect_id") or "") for c in top[:2])
        summary = (
            f"The score-derived evidence points to a distributed pattern in measures {measure_range}: "
            f"{aspects_phrase} are the relatively higher signals, but all remain moderate or lower. "
            "This suggests no single demand dominates here — the window sits close to the piece average."
        )
    else:
        # has primary/secondary
        primary = top[0]
        primary_plain = _plain_aspect(primary.get("aspect_id") or "")
        primary_strength = strength_label(primary.get("normalized_value"))
        # Use cautious language
        if len(top) >= 2 and len(elevated) >= 2:
            secondary_plain = _plain_aspect(top[1].get("aspect_id") or "")
            secondary_strength = strength_label(top[1].get("normalized_value"))
            summary = (
                f"The score-derived evidence suggests measures {measure_range} stand out mainly for {primary_plain} "
                f"({primary_strength}, primary), with secondary support from {secondary_plain} ({secondary_strength}). "
                "The signal is relative within this piece, not a calibrated grade or learner diagnosis."
            )
        else:
            summary = (
                f"The score-derived evidence points to {primary_plain} as the primary contributor in measures {measure_range} "
                f"({primary_strength}). The other aspects are lower in this window. The signal is relative within this piece."
            )
        # Optionally add feature hint if available and strong
        feat_contribs = primary.get("feature_contributors") or primary.get("supporting_feature_contributors") or []
        if feat_contribs:
            # take top feature with high normalized
            feat_top = sorted(feat_contribs, key=lambda f: (f.get("rank") if isinstance(f.get("rank"), int) else 999))[0] if feat_contribs else None
            if feat_top and isinstance(feat_top.get("normalized_value"), (int, float)) and float(feat_top.get("normalized_value")) >= 0.5:
                feat_plain = _plain_feature(feat_top.get("feature_id") or "", feat_top.get("label"))
                # append gentle feature cue without prescribing practice
                summary += f" Among supporting signals, {feat_plain} is relatively elevated here."

    # Aspect interplay
    if not contributors:
        aspect_interplay = "No aspect contributor data is available for this window — the explanation is limited to position and composite."
    elif not has_strong:
        aspect_interplay = (
            "The evidence is distributed — the score-derived signals are broadly similar across the top aspects, "
            "so no clear interplay dominates. This window reflects a balanced, average passage in the 9-aspect view."
        )
    elif len(elevated) >= 2:
        # describe combine
        names = [_plain_aspect(c.get("aspect_id") or "") for c in elevated[:3]]
        # safe plain language combine description
        if "hand shape and span" in names and "texture and polyphony" in names:
            aspect_interplay = (
                f"Two or more aspects are elevated together — {', '.join(names[:2])} — "
                "which suggests that multiple notes sounding together coincides with wider hand shapes in this window. "
                "The score-derived evidence points to a combined texture + span character, not a single cause."
            )
        elif "rhythm" in names and "hand coordination" in names:
            aspect_interplay = (
                f"{', '.join(names[:2]).capitalize()} both stand out here, which suggests rhythmic activity coincides with hands moving somewhat independently. "
                "The combination is descriptive — it does not diagnose learner difficulty."
            )
        elif "pitch movement" in names and "texture and polyphony" in names:
            aspect_interplay = (
                f"{', '.join(names[:2]).capitalize()} stand out together, suggesting larger relocations happen while multiple voices are active. "
                "The interplay is relative to this piece."
            )
        else:
            aspect_interplay = (
                f"More than one aspect is elevated — {', '.join(names)} — which suggests these demands coincide in this window. "
                "The overlap is descriptive within the 9-aspect model, not a weighted difficulty claim."
            )
        # Add note if very high present
        if very_high:
            aspect_interplay += " One signal reaches very high locally, which makes the combined character more noticeable on the chart."
    else:
        # single dominant
        primary_plain = _plain_aspect(top[0].get("aspect_id") or "")
        aspect_interplay = (
            f"The primary signal is {primary_plain}; the other aspects are lower here, so the window's character is mainly shaped by that one demand. "
            "The score-derived evidence suggests a focused rather than combined pattern in this passage."
        )

    # Score cue — cautious, relative
    if isinstance(score_value, (int, float)):
        sv = float(score_value)
        # thresholds for cue
        if sv >= 0.55:
            level = "relatively high for this piece"
        elif sv >= 0.42:
            level = "above the piece average"
        elif sv >= 0.32:
            level = "near the piece average"
        else:
            level = "relatively modest for this piece"
        score_cue = (
            f"Composite around {sv:.2f} — {level}. Hotspot rank #{hotspot.get('rank') or '?'} of {len(contributors)} supporting aspects considered; "
            "the value is a descriptive mean within the 9-aspect model, not a calibrated grade."
        )
    else:
        score_cue = "Composite is not available for this window — the ranking is relative within the 9-aspect model, not a calibrated grade."

    # Timeline context — if chart available
    timeline_context: str | None = None
    if chart and isinstance(chart, dict):
        regions = chart.get("regions") or []
        total = len(regions) if isinstance(regions, list) else None
        rep = hotspot.get("representative_region") or {}
        win_idx = rep.get("window_index")
        if win_idx is None:
            sw = hotspot.get("supporting_window_indices") or []
            if sw:
                win_idx = sw[0]
        if isinstance(win_idx, int) and isinstance(total, int) and total:
            # position description
            pct = win_idx / max(1, total - 1)
            if pct < 0.2:
                where = "near the opening"
            elif pct < 0.4:
                where = "in the early-middle"
            elif pct < 0.6:
                where = "around the middle"
            elif pct < 0.8:
                where = "in the late-middle"
            else:
                where = "toward the end"
            # aspect peak note: compare to chart series if possible
            timeline_context = (
                f"Window {win_idx + 1} of {total} {where} (measures {measure_range}). "
                "Position is descriptive — it does not imply a learning sequence."
            )
        elif isinstance(total, int) and total:
            timeline_context = f"One of {total} windows (measures {measure_range}). Position is descriptive within this piece."

    return {
        "headline": headline,
        "summary": summary,
        "aspect_interplay": aspect_interplay,
        "score_cue": score_cue,
        "timeline_context": timeline_context,
        "confidence": "heuristic",
    }


# For JS parity, expose glossary via function
def get_glossaries() -> dict[str, Any]:
    return {"aspects": ASPECT_GLOSSARY, "features": FEATURE_GLOSSARY}
