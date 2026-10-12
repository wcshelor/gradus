"""Local Semantic Inspection builder and markdown renderer.

Deterministic, no LLM. Every claim must be tied to evidence_event_ids.

Matches template:

  # Local Semantic Inspection: Measures A-B

  ## Passage Scope
  ## Instruction Units (1. LH Leap To Chord, 2. RH Chord Shape / Voicing)
  ## Supporting Local Objects
  ## Broad Context / Low Local Specificity
  ## Evidence Summary
  <details>Raw object/component evidence</details>

See docs/local_passage_semantics.md and musical_object_catalog.md.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .models import MusicalObject, ObjectComponent, PracticeChunk, ScoreEvent, SemanticBundle

# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstructionUnit:
    title: str
    instruction: str
    anatomy: tuple[str, ...]
    evidence: str
    caveats: str
    # provenance
    object_id: str | None = None
    component_ids: tuple[str, ...] = ()
    evidence_event_ids: tuple[str, ...] = ()
    measure_numbers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LocalObjectCard:
    object_id: str
    label: str
    measures: str
    local_reason: str
    why_not_promoted: str
    confidence: float
    evidence_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BroadObjectCard:
    object_id: str
    span: str
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    token_kind_counts: dict[str, int]
    gesture_kind_counts: dict[str, int]
    component_type_counts: dict[str, int]
    musical_object_count: int
    component_count: int
    top_components: tuple[str, ...]
    practice_chunk_count: int = 0
    chunk_kind_counts: dict[str, int] | None = None


@dataclass(frozen=True, slots=True)
class SurfaceField:
    """Provenance for a single rendered surface field."""

    name: str
    value: Any
    event_ids: tuple[str, ...] = ()
    component_id: str | None = None
    component_type: str | None = None
    measure_numbers: tuple[str, ...] = ()
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "event_ids": list(self.event_ids),
            "component_id": self.component_id,
            "component_type": self.component_type,
            "measure_numbers": list(self.measure_numbers),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class InstructionSurface:
    """Validated instruction surface for a promoted musical object.

    Built chronologically from ScoreEvent onset/measure/beat; rendering must
    consume this surface, not raw evidence ordering or unrelated component
    evidence. If is_valid is False, the unit must not be promoted as an
    instruction (rejected/demoted) and rejection_reason explains why.
    """

    object_id: str
    hand: str | None
    launch_event_ids: tuple[str, ...]
    target_event_ids: tuple[str, ...]
    start_onset: Fraction | None
    end_onset: Fraction | None
    launch_measure: str | None
    target_measure: str | None
    launch_beat: Fraction | None
    target_beat: Fraction | None
    interval_semitones: int | None
    duration_quarters: Fraction | None
    is_valid: bool
    rejection_reason: str | None = None
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "hand": self.hand,
            "launch_event_ids": list(self.launch_event_ids),
            "target_event_ids": list(self.target_event_ids),
            "start_onset": str(self.start_onset) if self.start_onset is not None else None,
            "end_onset": str(self.end_onset) if self.end_onset is not None else None,
            "launch_measure": self.launch_measure,
            "target_measure": self.target_measure,
            "launch_beat": str(self.launch_beat) if self.launch_beat is not None else None,
            "target_beat": str(self.target_beat) if self.target_beat is not None else None,
            "interval_semitones": self.interval_semitones,
            "duration_quarters": str(self.duration_quarters) if self.duration_quarters is not None else None,
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class LocalInspection:
    report_span: tuple[int, int]  # (A,B) inclusive
    flagged_measures: tuple[str, ...]
    source_score: str
    instruction_units: tuple[InstructionUnit, ...]
    supporting_local_objects: tuple[LocalObjectCard, ...]
    broad_context: tuple[BroadObjectCard, ...]
    evidence_summary: EvidenceSummary
    raw_evidence: dict[str, Any]
    # instruction_unit_diagnostics: parallel to instruction_units, optional for backward compat
    instruction_unit_diagnostics: tuple[dict[str, Any], ...] = ()
    # rejected promotion candidates that failed chronological validation
    rejected_instruction_candidates: tuple[dict[str, Any], ...] = ()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPANDED_OBJECT_LABELS: dict[str, str] = {
    "leap_to_chord": "LH Leap To Chord",
    "chord_landing": "Chord Landing",
    "melody_with_accompaniment": "Melody with Accompaniment",
    "melody_voicing_over_accompaniment": "RH Chord Shape / Voicing",
    "chordal_homophonic_texture": "RH Chord Shape / Voicing",
    "broken_chord_accompaniment": "Broken-Chord Accompaniment",
    "arpeggiated_accompaniment": "Arpeggiated Accompaniment",
    "repeated_position_pattern": "Repeated Position Pattern",
}

# Map object_id to instruction title override — hand may be adjusted later
TITLE_MAP = {
    "leap_to_chord": "LH Leap To Chord",
    "chord_landing": "Chord Landing",
    "chordal_homophonic_texture": "Chordal Homophonic Texture",
    "melody_embedded_in_chords": "Melody Embedded in Chords",
    "melody_voicing_over_accompaniment": "Melody Voicing over Accompaniment",
    "broken_chord_accompaniment": "Broken-Chord Pattern",
    "alberti_bass": "Alberti / Broken-Chord Pattern",
    "arpeggiated_accompaniment": "Arpeggiated Accompaniment",
    "ascending_scalar_run": "Ascending Scalar Run",
    "descending_scalar_run": "Descending Scalar Run",
    "repeated_rhythm_cell": "Repeated Rhythm Cell",
    "rhythm_pattern_break": "Rhythm Pattern Break",
    "octave_doubled_melody": "Octave-Doubled Melody",
    "single_hand_multi_voice_texture": "Single-Hand Multi-Voice Texture",
    "octaves": "Octaves",
}

# ---------------------------------------------------------------------------
# Musical surface helpers — note names, placements, durations
# ---------------------------------------------------------------------------

_SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_INTERVAL_BASE = {
    0: "unison",
    1: "minor second",
    2: "major second",
    3: "minor third",
    4: "major third",
    5: "perfect fourth",
    6: "tritone",
    7: "perfect fifth",
    8: "minor sixth",
    9: "major sixth",
    10: "minor seventh",
    11: "major seventh",
    12: "octave",
}


def _midi_to_pitch_name(midi: int | None, event: Any | None = None) -> str | None:
    if midi is None:
        return None
    # Prefer MusicXML spelling when available via alter/accidental
    if event is not None:
        alter = getattr(event, "alter", None)
        accidental = getattr(event, "accidental", None)
        if alter == -1 or (isinstance(accidental, str) and "flat" in accidental.lower()):
            return f"{_FLAT_NAMES[midi % 12]}{(midi // 12) - 1}"
        if alter == 1 or (isinstance(accidental, str) and "sharp" in accidental.lower()):
            return f"{_SHARP_NAMES[midi % 12]}{(midi // 12) - 1}"
        # natural on white keys — either mapping works; keep sharp map for consistency
        if event.pitch_name:
            # If event already has a name and alter is neutral, trust it (could be natural)
            return event.pitch_name
    # Fallback to sharp spelling
    return f"{_SHARP_NAMES[midi % 12]}{(midi // 12) - 1}"


def _format_pitch_event(ev: Any | None) -> str | None:
    if ev is None:
        return None
    midi = getattr(ev, "pitch_midi", None)
    if midi is None:
        return None
    name = _midi_to_pitch_name(midi, ev)
    return name


def _format_chord_tones(events: list[Any]) -> str | None:
    if not events:
        return None
    # sort low to high
    sorted_evs = sorted([e for e in events if getattr(e, "pitch_midi", None) is not None], key=lambda e: e.pitch_midi)
    if not sorted_evs:
        return None
    names = [_format_pitch_event(e) for e in sorted_evs if _format_pitch_event(e)]
    if not names:
        return None
    # join with hyphen for compact chord spelling (e.g., A3-C4, or A3-C4-E4)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}-{names[1]}"
    # 3+ notes: join with dash
    return "-".join(names)


def _beat_number_str(beat: Fraction | None) -> str | None:
    if beat is None:
        return None
    try:
        bn = Fraction(beat) + Fraction(1)
        if bn.denominator == 1:
            return str(int(bn))
        # fractional beat — render as decimal trimmed
        return f"{float(bn):g}"
    except Exception:
        return str(beat)


def _placement_str(ev: Any | None, fallback_measure: str | None = None) -> str | None:
    if ev is None and fallback_measure is None:
        return None
    m = getattr(ev, "measure_number", None) if ev is not None else fallback_measure
    if m is None:
        m = fallback_measure
    beat = getattr(ev, "beat", None) if ev is not None else None
    bn = _beat_number_str(beat)
    if m is not None and bn is not None:
        return f"m.{m}, beat {bn}"
    if m is not None:
        return f"m.{m}"
    if bn is not None:
        return f"beat {bn}"
    return None


def _duration_str(ev: Any | None) -> str | None:
    if ev is None:
        return None
    dt = getattr(ev, "duration_type", None)
    dur = getattr(ev, "duration", None)
    dur_q = getattr(ev, "duration_quarter", None)
    parts: list[str] = []
    if dt:
        parts.append(str(dt))
    if dur is not None:
        try:
            f = Fraction(dur)
            # show both fraction and decimal if not integral
            if f.denominator == 1:
                q_str = f"{int(f)} quarter" + ("s" if int(f) != 1 else "")
            else:
                q_str = f"{f} quarters ({float(f):g} q)"
            if dt:
                parts.append(f"({q_str})")
            else:
                parts.append(q_str)
        except Exception:
            if dur_q is not None:
                parts.append(f"{dur_q:g} quarters")
    elif dur_q is not None:
        parts.append(f"{dur_q:g} quarters")
    if not parts:
        return None
    return " ".join(parts)


def _interval_name(semitones: int) -> str:
    abs_s = abs(int(semitones))
    octs = abs_s // 12
    rem = abs_s % 12
    base = _INTERVAL_BASE.get(rem, f"{rem} semitones")
    if abs_s == 0:
        return base
    if octs == 0:
        return base
    if rem == 0:
        if octs == 1:
            return "octave"
        return f"{octs} octaves"
    # e.g., 16 = octave + major third
    if octs == 1:
        return f"octave + {base}"
    return f"{octs} octaves + {base}"


def _format_time_to_land(frac: Any | None) -> str | None:
    if frac is None or frac == "?":
        return None
    try:
        f = Fraction(str(frac))
        if f == 0:
            return "0 quarters"
        if f.denominator == 1:
            q = int(f)
            return f"{q} quarter{'s' if q != 1 else ''} ({q} q)"
        return f"{f} quarters ({float(f):g} q)"
    except Exception:
        return str(frac)


def _title_for_object(obj: MusicalObject) -> str:
    base = TITLE_MAP.get(obj.object_id, obj.label)
    # Hand-aware adjustment for voicing/chord families to avoid RH vs LH contradiction
    if obj.object_id in ("chord_landing", "chordal_homophonic_texture", "melody_embedded_in_chords", "melody_voicing_over_accompaniment"):
        if obj.hand == "left":
            return f"LH {base}"
        if obj.hand == "right":
            return f"RH {base}"
        return base
    if obj.object_id == "leap_to_chord":
        if obj.hand == "right":
            return "RH Leap To Chord"
        if obj.hand == "left":
            return "LH Leap To Chord"
        return base
    if obj.object_id in ("broken_chord_accompaniment", "arpeggiated_accompaniment", "wide_broken_chord", "alberti_bass"):
        if obj.hand == "left":
            return f"LH {base}"
        if obj.hand == "right":
            return f"RH {base}"
    return base

ACTIONABLE_FAMILIES: set[str] = {
    "leap_to_chord",
    "chord_landing",
    "hand_shift",
    "hand_expansion_contraction",
    "ascending_scalar_run",
    "descending_scalar_run",
    "broken_chord_accompaniment",
    "arpeggiated_accompaniment",
    "wide_broken_chord",
    "alberti_bass",
    "melody_with_accompaniment",
    "melody_embedded_in_chords",
    "melody_voicing_over_accompaniment",
    "syncopation",
    "repeated_rhythm_cell",
    "rhythm_pattern_break",
    "polyrhythm",
    "octave_doubled_melody",
    "single_hand_multi_voice_texture",
    "octaves",
}

BROAD_FAMILIES: set[str] = {
    "two_voice_counterpoint",
    "balance_between_voices",
    "dynamic_swell_across_phrase",
    "phrase_shaping_over_repeated_pattern",
    "pedal_point_accompaniment",
    "repeated_chord_accompaniment",
    "chordal_homophonic_texture",
    "left_hand_stride_like_motion",
    "inner_voice_movement",
    "hand_to_hand_imitation",
    "call_and_response",
    "cantabile_line",
    "legato_with_detached_accompaniment",
    "articulation_contrast_between_hands",
    "accent_pattern",
    "dynamic_swell_across_phrase",
}


def _int_measures(measure_numbers: tuple[str, ...]) -> list[int]:
    out: list[int] = []
    for m in measure_numbers:
        try:
            out.append(int(m))
        except Exception:
            continue
    return out


def _span_intersects_object(obj: Any, a: int, b: int) -> bool:
    mnums = getattr(obj, "measure_numbers", ())
    ints = _int_measures(tuple(mnums))
    if ints:
        return any(a <= x <= b for x in ints)
    ms = getattr(obj, "measure_start", None)
    me = getattr(obj, "measure_end", None)
    if ms is not None and me is not None:
        return not (me < a or ms > b)
    if ms is not None:
        return a <= ms <= b
    # fallback to onset — caller should handle onset bounds
    return False


def _format_measures_compact(measure_numbers: tuple[str, ...]) -> str:
    if not measure_numbers:
        return "?"
    # stable dedup
    seen: dict[str, None] = {}
    for m in measure_numbers:
        if m not in seen:
            seen[m] = None
    # separate numeric and non-numeric
    numeric: list[int] = []
    non_numeric: list[str] = []
    for m in seen.keys():
        try:
            numeric.append(int(m))
        except Exception:
            non_numeric.append(m)
    numeric = sorted(set(numeric))
    non_numeric = sorted(set(non_numeric))

    parts: list[str] = []
    if numeric:
        # compress consecutive runs
        start = numeric[0]
        prev = numeric[0]
        for n in numeric[1:]:
            if n == prev + 1:
                prev = n
                continue
            # close run
            if start == prev:
                parts.append(str(start))
            else:
                parts.append(f"{start}-{prev}")
            start = n
            prev = n
        # final run
        if start == prev:
            parts.append(str(start))
        else:
            parts.append(f"{start}-{prev}")
        # add count annotation for single large contiguous span? Keep simple: no annotation unless 1 range and count >=10
        # The spec example "1..72 -> 1-72 (72 measures)" — we add annotation for large single-range spans
        if len(parts) == 1 and "-" in parts[0] and len(numeric) >= 10:
            # parts[0] like "1-72"
            parts[0] = f"{parts[0]} ({len(numeric)} measures)"
    if non_numeric:
        parts.extend(non_numeric)
    if not parts:
        return "?"
    return ",".join(parts)


def _span_width_measures(obj: Any) -> int:
    ints = _int_measures(tuple(getattr(obj, "measure_numbers", ())))
    if ints:
        return max(ints) - min(ints) + 1
    ms = getattr(obj, "measure_start", None)
    me = getattr(obj, "measure_end", None)
    if ms is not None and me is not None:
        try:
            return int(me) - int(ms) + 1
        except Exception:
            return 1
    return 1


def _onset_bounds_for_span(bundle: SemanticBundle, a: int, b: int) -> tuple[Fraction | None, Fraction | None]:
    evs = [e for e in bundle.events if e.measure_index is not None and a <= e.measure_index <= b]
    if not evs:
        # try measure_number
        evs = [e for e in bundle.events if e.measure_number is not None and e.measure_number.isdigit() and a <= int(e.measure_number) <= b]
    if not evs:
        return None, None
    return min(e.onset for e in evs), max(e.end for e in evs)


def _in_onset_window(obj: Any, start: Fraction | None, end: Fraction | None) -> bool:
    if start is None or end is None:
        return True
    o_start = getattr(obj, "start_onset", None)
    o_end = getattr(obj, "end_onset", None)
    if o_start is None or o_end is None:
        return False
    # overlap, not just containment — evidence touching span counts
    return not (o_end <= start or o_start >= end)


def _component_attaches_to_object(comp: ObjectComponent, obj: MusicalObject) -> bool:
    """Check if component belongs to specific object instance.

    Requires same parent_object_id plus at least one of:
    - evidence_event_ids intersect
    - onset span overlaps
    - token/gesture IDs intersect
    For leap_to_chord/chord_landing the attachment is strict: only
    evidence or gesture overlap is considered strong; token-only or
    onset-only overlap is treated as weak (different instance).
    """
    if comp.parent_object_id != obj.object_id:
        return False
    # evidence intersect — strongest signal
    has_evidence_overlap = False
    if comp.evidence_event_ids and obj.evidence_event_ids:
        if set(comp.evidence_event_ids) & set(obj.evidence_event_ids):
            has_evidence_overlap = True
            return True
    # gesture intersect — also strong (gesture_id links the specific bass_to_chord instance)
    has_gesture_overlap = False
    if comp.gesture_ids and obj.gesture_ids:
        if set(comp.gesture_ids) & set(obj.gesture_ids):
            has_gesture_overlap = True
            return True
    # For leap families, token-only or onset-only is insufficient (cross-instance contamination)
    if obj.object_id in ("leap_to_chord", "chord_landing"):
        # Allow token overlap only if it also has evidence/gesture (already handled) — otherwise reject
        return False
    # For other families, token or onset overlap is acceptable (existing behavior)
    if comp.token_ids and obj.token_ids:
        if set(comp.token_ids) & set(obj.token_ids):
            return True
    # onset overlap
    o_start = getattr(obj, "start_onset", None)
    o_end = getattr(obj, "end_onset", None)
    c_start = getattr(comp, "start_onset", None)
    c_end = getattr(comp, "end_onset", None)
    if o_start is not None and o_end is not None and c_start is not None and c_end is not None:
        # overlap if not disjoint
        if not (c_end <= o_start or c_start >= o_end):
            return True
        # also handle point components
        if c_start == o_start or c_end == o_end:
            return True
    return False


# ---------------------------------------------------------------------------
# Consistency Diagnostics — provenance-aware surface checks
# ---------------------------------------------------------------------------

# Mapping for pitch-name -> pc / midi parsing
_PITCH_PC = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11,
}

# Written duration_type -> expected quarters (base, without dots). Dotted values multiply.
_DURATION_BASE: dict[str, Fraction] = {
    "whole": Fraction(4),
    "half": Fraction(2),
    "quarter": Fraction(1),
    "eighth": Fraction(1, 2),
    "16th": Fraction(1, 4),
    "16th_": Fraction(1, 4),
    "sixteenth": Fraction(1, 4),
    "32nd": Fraction(1, 8),
    "32nd_": Fraction(1, 8),
    "64th": Fraction(1, 16),
    "breve": Fraction(8),
}


def _parse_pitch_name_to_midi(name: str | None) -> int | None:
    if not name or not isinstance(name, str):
        return None
    name = name.strip()
    if not name:
        return None
    # extract pitch class + octave, e.g., Db3, F#4, C5, Bb3
    # pitch class is letters possibly #/b, octave is trailing digits (may be negative)
    idx = len(name) - 1
    while idx >= 0 and (name[idx].isdigit() or name[idx] == "-"):
        idx -= 1
    if idx < 0 or idx == len(name) - 1 and not name[-1].isdigit():
        return None
    pc_str = name[: idx + 1]
    oct_str = name[idx + 1 :]
    pc = _PITCH_PC.get(pc_str)
    if pc is None:
        # try uppercase first letter
        pc = _PITCH_PC.get(pc_str[0].upper() + pc_str[1:] if len(pc_str) > 1 else pc_str.upper())
    if pc is None:
        return None
    try:
        octv = int(oct_str)
    except Exception:
        return None
    return (octv + 1) * 12 + pc


def _chord_pitch_count(chord_name: str | None) -> int | None:
    if not chord_name:
        return None
    # split by hyphen — our renderer uses hyphen for 2+ notes
    parts = [p.strip() for p in chord_name.split("-") if p.strip()]
    if not parts:
        return None
    return len(parts)


def _chord_span_semitones_from_names(chord_name: str | None) -> int | None:
    if not chord_name:
        return None
    mids = [_parse_pitch_name_to_midi(p.strip()) for p in chord_name.split("-") if p.strip()]
    mids = [m for m in mids if m is not None]
    if len(mids) < 2:
        return 0 if len(mids) == 1 else None
    return max(mids) - min(mids)


def _chord_span_semitones_from_events(events: list[Any]) -> int | None:
    mids = [getattr(e, "pitch_midi", None) for e in events if getattr(e, "pitch_midi", None) is not None]
    if len(mids) < 2:
        return 0 if len(mids) == 1 else None
    return int(max(mids) - min(mids))


def _expected_quarters_for_duration_type(duration_type: str | None) -> Fraction | None:
    if not duration_type or not isinstance(duration_type, str):
        return None
    dt = duration_type.strip().lower()
    # handle dotted: "dotted_quarter", "quarter.", "eighth."
    dotted = False
    if dt.startswith("dotted_"):
        dotted = True
        dt = dt[len("dotted_") :]
    if dt.endswith("."):
        dotted = True
        dt = dt.rstrip(".")
    base = _DURATION_BASE.get(dt)
    if base is None:
        # try without case, e.g., "Quarter" vs "quarter"
        base = _DURATION_BASE.get(dt.lower())
    if base is None:
        return None
    if dotted:
        return base * Fraction(3, 2)
    return base


def _diagnose_component_instance_mismatch(
    obj: MusicalObject,
    comp: ObjectComponent,
) -> dict[str, Any] | None:
    """Return warning dict if component attaches only via weak signal."""
    evidence_overlap = bool(set(comp.evidence_event_ids) & set(obj.evidence_event_ids)) if comp.evidence_event_ids and obj.evidence_event_ids else False
    token_overlap = bool(set(comp.token_ids) & set(obj.token_ids)) if comp.token_ids and obj.token_ids else False
    gesture_overlap = bool(set(comp.gesture_ids) & set(obj.gesture_ids)) if comp.gesture_ids and obj.gesture_ids else False

    o_start = getattr(obj, "start_onset", None)
    o_end = getattr(obj, "end_onset", None)
    c_start = getattr(comp, "start_onset", None)
    c_end = getattr(comp, "end_onset", None)
    onset_overlap = False
    if o_start is not None and o_end is not None and c_start is not None and c_end is not None:
        if not (c_end <= o_start or c_start >= o_end) or c_start == o_start or c_end == o_end:
            onset_overlap = True

    hand_conflict = False
    if obj.hand in ("left", "right") and comp.hand in ("left", "right") and obj.hand != comp.hand:
        hand_conflict = True

    onset_outside = False
    if o_start is not None and o_end is not None and c_start is not None:
        if c_start < o_start or c_start >= o_end:
            # point component outside span
            if not onset_overlap:
                onset_outside = True

    measure_outside = False
    if comp.measure_numbers and obj.measure_numbers:
        # if no numeric measure overlap, flag
        try:
            obj_ints = {int(m) for m in obj.measure_numbers if str(m).isdigit()}
            comp_ints = {int(m) for m in comp.measure_numbers if str(m).isdigit()}
            if obj_ints and comp_ints and not (obj_ints & comp_ints):
                # token-only overlap is weak, so treat measure mismatch as suspicious if no evidence/gesture
                if not evidence_overlap and not gesture_overlap:
                    measure_outside = True
        except Exception:
            pass

    # Strong attachment: evidence or gesture overlap (token-only is weak)
    strong = evidence_overlap or gesture_overlap

    if strong and not hand_conflict and not measure_outside and not onset_outside:
        # No warning if strong evidence link, hand agrees, and onset/measure inside
        return None

    # Token-only overlap with onset/measure outside is suspicious even if token matches
    if token_overlap and not strong and (onset_outside or measure_outside):
        return {
            "code": "component_instance_mismatch",
            "component_type": comp.component_type,
            "component_id": comp.component_id,
            "severity": "warning",
            "reason": "component shares only token overlap but onset/measure does not align with promoted object; likely different instance",
            "detail": {
                "evidence_overlap": evidence_overlap,
                "token_overlap": token_overlap,
                "gesture_overlap": gesture_overlap,
                "onset_overlap": onset_overlap,
                "onset_outside": onset_outside,
                "measure_outside": measure_outside,
                "hand_conflict": hand_conflict,
            },
        }

    # Weak attachment cases
    if not strong and onset_overlap:
        return {
            "code": "component_instance_mismatch",
            "component_type": comp.component_type,
            "component_id": comp.component_id,
            "severity": "warning",
            "reason": "component has no shared evidence/token/gesture with promoted object; attached by onset overlap only",
            "detail": {
                "evidence_overlap": evidence_overlap,
                "token_overlap": token_overlap,
                "gesture_overlap": gesture_overlap,
                "onset_overlap": onset_overlap,
                "hand_conflict": hand_conflict,
                "measure_outside": measure_outside,
            },
        }
    if hand_conflict:
        return {
            "code": "component_instance_mismatch",
            "component_type": comp.component_type,
            "component_id": comp.component_id,
            "severity": "warning",
            "reason": f"component hand {comp.hand!r} conflicts with object hand {obj.hand!r}",
            "detail": {
                "evidence_overlap": evidence_overlap,
                "token_overlap": token_overlap,
                "gesture_overlap": gesture_overlap,
                "onset_overlap": onset_overlap,
                "hand_conflict": hand_conflict,
            },
        }
    if measure_outside:
        return {
            "code": "component_instance_mismatch",
            "component_type": comp.component_type,
            "component_id": comp.component_id,
            "severity": "warning",
            "reason": "component measure does not intersect promoted object measures and shares no evidence/token/gesture",
            "detail": {
                "evidence_overlap": evidence_overlap,
                "token_overlap": token_overlap,
                "gesture_overlap": gesture_overlap,
                "measure_outside": measure_outside,
            },
        }
    if not strong and not onset_overlap:
        # Attached but via no signal? Should not happen if _component_attaches_to_object returned True,
        # but we flag for diagnostics
        if _component_attaches_to_object(comp, obj):
            return {
                "code": "component_instance_mismatch",
                "component_type": comp.component_type,
                "component_id": comp.component_id,
                "severity": "warning",
                "reason": "component attached via weak/no shared provenance signal",
                "detail": {
                    "evidence_overlap": evidence_overlap,
                    "token_overlap": token_overlap,
                    "gesture_overlap": gesture_overlap,
                    "onset_overlap": onset_overlap,
                },
            }
    return None


def diagnose_instruction_unit_consistency(
    obj: MusicalObject,
    selected_components: dict[str, ObjectComponent] | list[ObjectComponent],
    event_by_id: dict[str, Any],
    selected_surface_fields: dict[str, SurfaceField] | None = None,
    *,
    chord_name: str | None = None,
    chord_note_count: Any = None,
    target_span_semitones: Any = None,
    leap_interval_semitones: Any = None,
    launch_event_ids: tuple[str, ...] | None = None,
    target_event_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Validate surface anatomy of a promoted instruction unit.

    Inspects object, selected components, selected events and rendered fields.
    Returns list of warning dicts with code/reason/detail.
    """
    warnings: list[dict[str, Any]] = []

    # Normalize selected_components to dict values list
    if isinstance(selected_components, dict):
        comps = list(selected_components.values())
    else:
        comps = list(selected_components)

    # A. Mixed-source component warnings
    for comp in comps:
        w = _diagnose_component_instance_mismatch(obj, comp)
        if w is not None:
            warnings.append(w)

    # Resolve events for further checks
    def _resolve(ids: tuple[str, ...] | list[str] | None) -> list[Any]:
        if not ids:
            return []
        out = []
        for eid in ids:
            ev = event_by_id.get(eid) if event_by_id else None
            if ev is not None:
                out.append(ev)
        return out

    # If selected_surface_fields provided, extract from there as priority
    if selected_surface_fields is not None:
        # allow caller to pass rendered chord fields
        if chord_name is None and "landing_chord" in selected_surface_fields:
            chord_name = str(selected_surface_fields["landing_chord"].value) if selected_surface_fields["landing_chord"].value is not None else None
            if target_event_ids is None:
                target_event_ids = tuple(selected_surface_fields["landing_chord"].event_ids)
        elif chord_name is None and "chord_tones" in selected_surface_fields:
            chord_name = str(selected_surface_fields["chord_tones"].value) if selected_surface_fields["chord_tones"].value is not None else None
        if chord_note_count is None and "chord_note_count" in selected_surface_fields:
            chord_note_count = selected_surface_fields["chord_note_count"].value
        if target_span_semitones is None and "target_span" in selected_surface_fields:
            target_span_semitones = selected_surface_fields["target_span"].value
        if leap_interval_semitones is None and "leap_interval" in selected_surface_fields:
            leap_interval_semitones = selected_surface_fields["leap_interval"].value
        if leap_interval_semitones is None and "interval" in selected_surface_fields:
            leap_interval_semitones = selected_surface_fields["interval"].value
        if launch_event_ids is None and "launch" in selected_surface_fields:
            launch_event_ids = tuple(selected_surface_fields["launch"].event_ids)
        if target_event_ids is None and "landing" in selected_surface_fields:
            target_event_ids = tuple(selected_surface_fields["landing"].event_ids)

    # B. Pitch/count mismatch
    if chord_name is not None and chord_note_count is not None and chord_note_count != "?" and chord_note_count != "":
        try:
            implied = _chord_pitch_count(chord_name)
            stated = int(chord_note_count) if isinstance(chord_note_count, (int, float, str)) and str(chord_note_count).lstrip("-").isdigit() else None
            if implied is not None and stated is not None and implied != stated:
                warnings.append({
                    "code": "pitch_count_mismatch",
                    "severity": "warning",
                    "reason": f"rendered chord {chord_name!r} implies {implied} pitches but chord_note_count={stated}",
                    "detail": {
                        "chord_name": chord_name,
                        "implied_count": implied,
                        "stated_count": stated,
                        "event_ids": list(target_event_ids or []),
                    },
                })
        except Exception:
            pass

    # C. Pitch/span mismatch
    if chord_name is not None and target_span_semitones is not None and target_span_semitones != "?" and target_span_semitones != "":
        try:
            stated_span = int(target_span_semitones) if str(target_span_semitones).lstrip("-").isdigit() else None
            if stated_span is not None:
                # Prefer event-derived span if target events available, else name-derived
                actual_span: int | None = None
                if target_event_ids:
                    evs = _resolve(target_event_ids)
                    if evs:
                        s = _chord_span_semitones_from_events(evs)
                        if s is not None:
                            actual_span = s
                if actual_span is None:
                    actual_span = _chord_span_semitones_from_names(chord_name)
                if actual_span is not None and actual_span != stated_span:
                    warnings.append({
                        "code": "pitch_span_mismatch",
                        "severity": "warning",
                        "reason": f"rendered chord {chord_name!r} spans {actual_span} semitones but target_span={stated_span}",
                        "detail": {
                            "chord_name": chord_name,
                            "actual_span": actual_span,
                            "stated_span": stated_span,
                            "event_ids": list(target_event_ids or []),
                        },
                    })
        except Exception:
            pass

    # D. Interval direction mismatch
    if leap_interval_semitones is not None and leap_interval_semitones != "?" and leap_interval_semitones != "":
        try:
            iv = int(leap_interval_semitones)
            if iv != 0 and launch_event_ids and target_event_ids:
                launch_evs = _resolve(launch_event_ids)
                target_evs = _resolve(target_event_ids)
                if launch_evs and target_evs:
                    src_midi = getattr(launch_evs[0], "pitch_midi", None)
                    # use median and lowest destination methods
                    dest_mids = sorted([getattr(e, "pitch_midi", None) for e in target_evs if getattr(e, "pitch_midi", None) is not None])
                    if src_midi is not None and dest_mids:
                        lowest = dest_mids[0]
                        median = dest_mids[len(dest_mids)//2]
                        # Conservative: check both; if both disagree with interval sign, warn
                        iv_dir = 1 if iv > 0 else -1
                        lowest_dir = 1 if lowest > src_midi else -1 if lowest < src_midi else 0
                        median_dir = 1 if median > src_midi else -1 if median < src_midi else 0
                        # Only warn if interval direction is opposite to evidence; level (0) is not warn
                        if lowest_dir != 0 and median_dir != 0 and lowest_dir != iv_dir and median_dir != iv_dir:
                            warnings.append({
                                "code": "interval_direction_mismatch",
                                "severity": "warning",
                                "reason": f"surface movement src {src_midi} -> dest lowest {lowest} median {median} suggests {'up' if lowest_dir>0 else 'down'} but interval says {'up' if iv_dir>0 else 'down'} ({iv} semitones)",
                                "detail": {
                                    "interval_semitones": iv,
                                    "src_midi": src_midi,
                                    "dest_lowest_midi": lowest,
                                    "dest_median_midi": median,
                                    "method": "lowest_and_median_both_disagree",
                                    "launch_event_ids": list(launch_event_ids),
                                    "target_event_ids": list(target_event_ids),
                                },
                            })
                        elif lowest_dir != 0 and lowest_dir != iv_dir and median_dir == 0:
                            # ambiguous — flag low-confidence
                            pass
        except Exception:
            pass

    # E. Duration type/logical duration mismatch
    # Check all launch/target events for tie-merged or duration vs type mismatch
    for eid_list, label in [(launch_event_ids, "launch"), (target_event_ids, "landing")]:
        if not eid_list:
            continue
        for eid in eid_list:
            ev = event_by_id.get(eid) if event_by_id else None
            if ev is None:
                continue
            dt = getattr(ev, "duration_type", None)
            dur = getattr(ev, "duration", None)
            tie_merged = getattr(ev, "tie_merged", False)
            if dt is not None and dur is not None:
                try:
                    expected = _expected_quarters_for_duration_type(str(dt))
                    actual = Fraction(dur)
                    if expected is not None:
                        # Allow small tuple/dotted variance; flag if actual differs >50% or tie_merged
                        ratio = float(actual / expected) if expected != 0 else 0
                        if tie_merged and actual != expected:
                            warnings.append({
                                "code": "duration_representation_mismatch",
                                "severity": "info",
                                "reason": f"{label} event {eid} duration_type {dt!r} expects {expected} quarters but logical duration is {actual} quarters (tie_merged={tie_merged}) — written and logical durations disagree",
                                "detail": {
                                    "event_id": eid,
                                    "duration_type": dt,
                                    "expected_quarters": str(expected),
                                    "actual_quarters": str(actual),
                                    "tie_merged": tie_merged,
                                },
                            })
                        elif ratio < 0.66 or ratio > 1.5:
                            warnings.append({
                                "code": "duration_representation_mismatch",
                                "severity": "info",
                                "reason": f"{label} event {eid} duration_type {dt!r} expects {expected} quarters but duration is {actual} quarters (ratio {ratio:.2f})",
                                "detail": {
                                    "event_id": eid,
                                    "duration_type": dt,
                                    "expected_quarters": str(expected),
                                    "actual_quarters": str(actual),
                                    "tie_merged": tie_merged,
                                },
                            })
                except Exception:
                    pass

    return warnings


# Alias per task suggestion
surface_consistency_checks = diagnose_instruction_unit_consistency


# ---------------------------------------------------------------------------
# Validated Instruction Surface — chronological launch→target model
# ---------------------------------------------------------------------------


def _measure_int(m: str | None) -> int | None:
    if m is None:
        return None
    try:
        return int(str(m).strip())
    except Exception:
        return None


def _is_component_evidence_consistent_with_surface(
    comp: ObjectComponent,
    surface_launch_ids: tuple[str, ...],
    surface_target_ids: tuple[str, ...],
) -> bool:
    """Check that component evidence does not cross launch/target roles."""
    if comp.component_type == "launch_note":
        # Must be subset of launch ids or at least intersect launch
        if not comp.evidence_event_ids:
            return True
        # If component has any target ids mixed in, it's cross-role
        has_launch = bool(set(comp.evidence_event_ids) & set(surface_launch_ids))
        has_target = bool(set(comp.evidence_event_ids) & set(surface_target_ids))
        # launch component should not contain target evidence
        if has_target and not has_launch:
            return False
        if has_target and has_launch:
            # mixed — suspicious
            return False
        return has_launch
    if comp.component_type in ("target_chord", "target_span", "chord_note_count", "landing_onset", "landing_beat"):
        if not comp.evidence_event_ids:
            return True
        has_launch = bool(set(comp.evidence_event_ids) & set(surface_launch_ids))
        has_target = bool(set(comp.evidence_event_ids) & set(surface_target_ids))
        if has_launch and not has_target:
            return False
        if has_launch and has_target:
            return False
        return has_target or not surface_target_ids  # allow if no target ids yet?
    if comp.component_type in ("leap_interval", "leap_interval_semitones"):
        # Should span both but not mix other roles incorrectly — allow both
        return True
    return True


def build_validated_instruction_surface(
    obj: MusicalObject,
    event_by_id: dict[str, Any] | None = None,
    *,
    selected_components: dict[str, ObjectComponent] | None = None,
) -> InstructionSurface:
    """Build a validated instruction surface for obj from ScoreEvent chronology.

    For leap_to_chord (and chord_landing) this enforces launch→target chronology:
    - launch = earliest onset group, target = latest onset group from obj.evidence_event_ids
    - target onset must be strictly after launch onset
    - measure numbers must be non-decreasing with onset (if numeric)
    - beat ordering must be consistent when same measure
    - component evidence must not cross launch/target roles

    Returns InstructionSurface with is_valid=False and rejection_reason if any
    check fails. Rendering must consume this surface, not raw component ordering.
    Other object_ids that are not leap-like are returned as valid trivially.
    """
    event_by_id = event_by_id or {}
    # Only strict validation for leap_to_chord (per task start scope), but also lightly for chord_landing
    if obj.object_id not in ("leap_to_chord", "chord_landing"):
        # For other objects, return trivial valid surface from object span
        # still compute basic launch/target for diagnostics if possible
        evs = [event_by_id.get(eid) for eid in obj.evidence_event_ids if event_by_id.get(eid) is not None]
        if evs:
            earliest = min(e.onset for e in evs)
            latest = max(e.onset for e in evs)
            launch_ids = tuple(e.event_id for e in evs if e.onset == earliest)
            target_ids = tuple(e.event_id for e in evs if e.onset == latest)
            launch_ev = next((e for e in evs if e.onset == earliest), None)
            target_ev = next((e for e in evs if e.onset == latest), None)
            return InstructionSurface(
                object_id=obj.object_id,
                hand=obj.hand,
                launch_event_ids=launch_ids,
                target_event_ids=target_ids,
                start_onset=earliest,
                end_onset=latest,
                launch_measure=str(launch_ev.measure_number) if launch_ev and launch_ev.measure_number else None,
                target_measure=str(target_ev.measure_number) if target_ev and target_ev.measure_number else None,
                launch_beat=launch_ev.beat if launch_ev else None,
                target_beat=target_ev.beat if target_ev else None,
                interval_semitones=None,
                duration_quarters=latest - earliest if earliest is not None and latest is not None else None,
                is_valid=True,
                rejection_reason=None,
                diagnostics=(),
            )
        return InstructionSurface(
            object_id=obj.object_id,
            hand=obj.hand,
            launch_event_ids=(),
            target_event_ids=(),
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            launch_measure=obj.measure_numbers[0] if obj.measure_numbers else None,
            target_measure=obj.measure_numbers[-1] if obj.measure_numbers else None,
            launch_beat=None,
            target_beat=None,
            interval_semitones=None,
            duration_quarters=obj.end_onset - obj.start_onset if obj.start_onset is not None and obj.end_onset is not None else None,
            is_valid=True,
            rejection_reason=None,
            diagnostics=(),
        )

    # Resolve evidence events
    evs = []
    missing = []
    for eid in obj.evidence_event_ids:
        ev = event_by_id.get(eid)
        if ev is None:
            missing.append(eid)
        else:
            evs.append(ev)
    if not evs:
        return InstructionSurface(
            object_id=obj.object_id, hand=obj.hand,
            launch_event_ids=(), target_event_ids=(),
            start_onset=None, end_onset=None,
            launch_measure=None, target_measure=None,
            launch_beat=None, target_beat=None,
            interval_semitones=None, duration_quarters=None,
            is_valid=False, rejection_reason="no_evidence_events_resolved", diagnostics=tuple(missing),
        )
    # Sort by onset for chronological grouping
    evs_sorted = sorted(evs, key=lambda e: (e.onset, e.pitch_midi or 0, e.event_id))
    earliest_onset = min(e.onset for e in evs)
    latest_onset = max(e.onset for e in evs)
    launch_events = [e for e in evs if e.onset == earliest_onset]
    target_events = [e for e in evs if e.onset == latest_onset]
    diagnostics: list[str] = []
    if missing:
        diagnostics.append(f"missing_event_ids:{missing}")
    # If earliest == latest, no movement
    if earliest_onset == latest_onset:
        return InstructionSurface(
            object_id=obj.object_id, hand=obj.hand,
            launch_event_ids=tuple(e.event_id for e in launch_events),
            target_event_ids=tuple(e.event_id for e in target_events),
            start_onset=earliest_onset, end_onset=latest_onset,
            launch_measure=str(launch_events[0].measure_number) if launch_events and launch_events[0].measure_number else None,
            target_measure=str(target_events[0].measure_number) if target_events and target_events[0].measure_number else None,
            launch_beat=launch_events[0].beat if launch_events else None,
            target_beat=target_events[0].beat if target_events else None,
            interval_semitones=None, duration_quarters=Fraction(0),
            is_valid=False, rejection_reason="target_does_not_follow_launch__same_onset", diagnostics=tuple(diagnostics),
        )
    if latest_onset <= earliest_onset:
        return InstructionSurface(
            object_id=obj.object_id, hand=obj.hand,
            launch_event_ids=tuple(e.event_id for e in launch_events),
            target_event_ids=tuple(e.event_id for e in target_events),
            start_onset=earliest_onset, end_onset=latest_onset,
            launch_measure=str(launch_events[0].measure_number) if launch_events else None,
            target_measure=str(target_events[0].measure_number) if target_events else None,
            launch_beat=launch_events[0].beat if launch_events else None,
            target_beat=target_events[0].beat if target_events else None,
            interval_semitones=None, duration_quarters=latest_onset - earliest_onset,
            is_valid=False, rejection_reason="target_precedes_launch", diagnostics=tuple(diagnostics),
        )
    # Measure label consistency: numeric measure numbers must be non-decreasing with onset
    launch_measure = str(launch_events[0].measure_number) if launch_events and launch_events[0].measure_number else None
    target_measure = str(target_events[0].measure_number) if target_events and target_events[0].measure_number else None
    lm_int = _measure_int(launch_measure)
    tm_int = _measure_int(target_measure)
    if lm_int is not None and tm_int is not None and tm_int < lm_int:
        return InstructionSurface(
            object_id=obj.object_id, hand=obj.hand,
            launch_event_ids=tuple(e.event_id for e in launch_events),
            target_event_ids=tuple(e.event_id for e in target_events),
            start_onset=earliest_onset, end_onset=latest_onset,
            launch_measure=launch_measure, target_measure=target_measure,
            launch_beat=launch_events[0].beat if launch_events else None,
            target_beat=target_events[0].beat if target_events else None,
            interval_semitones=None, duration_quarters=latest_onset - earliest_onset,
            is_valid=False, rejection_reason=f"measure_label_contradicts_onset_order__launch_m{launch_measure}_target_m{target_measure}", diagnostics=tuple(diagnostics),
        )
    # Beat ordering within same measure
    launch_beat = launch_events[0].beat if launch_events else None
    target_beat = target_events[0].beat if target_events else None
    if lm_int is not None and tm_int is not None and lm_int == tm_int and launch_beat is not None and target_beat is not None:
        if target_beat <= launch_beat and latest_onset > earliest_onset:
            # If same measure but beat goes backwards, still suspect (unless grace etc). Flag as invalid if beat reversal contradicts onset order
            # Allow equal beats if chord? But strict for leap_to_chord
            if target_beat < launch_beat:
                return InstructionSurface(
                    object_id=obj.object_id, hand=obj.hand,
                    launch_event_ids=tuple(e.event_id for e in launch_events),
                    target_event_ids=tuple(e.event_id for e in target_events),
                    start_onset=earliest_onset, end_onset=latest_onset,
                    launch_measure=launch_measure, target_measure=target_measure,
                    launch_beat=launch_beat, target_beat=target_beat,
                    interval_semitones=None, duration_quarters=latest_onset - earliest_onset,
                    is_valid=False, rejection_reason=f"beat_contradicts_onset_order__launch_beat_{launch_beat}_target_beat_{target_beat}_same_measure_m{launch_measure}", diagnostics=tuple(diagnostics),
                )
    # Interval calculation and direction check
    interval = None
    if launch_events and target_events:
        launch_midi = launch_events[0].pitch_midi
        # For target, use median pitch
        target_midis = sorted([e.pitch_midi for e in target_events if e.pitch_midi is not None])
        if launch_midi is not None and target_midis:
            target_median = target_midis[len(target_midis)//2]
            interval = target_median - launch_midi
            # If object payload specifies interval, ensure direction matches (optional strict)
            # We already have direction mismatch diagnostics elsewhere, but here we enforce that if interval is 0 and launch!=target etc? Not needed
    duration = latest_onset - earliest_onset
    # Enforce genuine difficult leap thresholds for leap_to_chord
    if obj.object_id == "leap_to_chord":
        if interval is None or abs(interval) < 7:
            return InstructionSurface(
                object_id=obj.object_id, hand=obj.hand,
                launch_event_ids=tuple(e.event_id for e in launch_events),
                target_event_ids=tuple(e.event_id for e in target_events),
                start_onset=earliest_onset, end_onset=latest_onset,
                launch_measure=launch_measure, target_measure=target_measure,
                launch_beat=launch_beat, target_beat=target_beat,
                interval_semitones=interval, duration_quarters=duration,
                is_valid=False, rejection_reason=f"interval_below_leap_threshold_7__interval_{interval}", diagnostics=tuple(diagnostics),
            )
        # Target must be a real chord (>=3 notes or span >=7)
        target_midis_for_chord = sorted([e.pitch_midi for e in target_events if e.pitch_midi is not None])
        _t_count = len(target_midis_for_chord)
        _t_span = (max(target_midis_for_chord) - min(target_midis_for_chord)) if len(target_midis_for_chord) >= 2 else 0
        if _t_count < 3 and _t_span < 7:
            return InstructionSurface(
                object_id=obj.object_id, hand=obj.hand,
                launch_event_ids=tuple(e.event_id for e in launch_events),
                target_event_ids=tuple(e.event_id for e in target_events),
                start_onset=earliest_onset, end_onset=latest_onset,
                launch_measure=launch_measure, target_measure=target_measure,
                launch_beat=launch_beat, target_beat=target_beat,
                interval_semitones=interval, duration_quarters=duration,
                is_valid=False, rejection_reason=f"target_not_real_chord__count_{_t_count}_span_{_t_span}", diagnostics=tuple(diagnostics),
            )
        # Short preparation window (quick displacement)
        if duration > Fraction(1):
            return InstructionSurface(
                object_id=obj.object_id, hand=obj.hand,
                launch_event_ids=tuple(e.event_id for e in launch_events),
                target_event_ids=tuple(e.event_id for e in target_events),
                start_onset=earliest_onset, end_onset=latest_onset,
                launch_measure=launch_measure, target_measure=target_measure,
                launch_beat=launch_beat, target_beat=target_beat,
                interval_semitones=interval, duration_quarters=duration,
                is_valid=False, rejection_reason=f"preparation_window_too_long__{duration}_gt_1_quarter", diagnostics=tuple(diagnostics),
            )
        if abs(interval) == 7 and duration > Fraction(1, 2):
            return InstructionSurface(
                object_id=obj.object_id, hand=obj.hand,
                launch_event_ids=tuple(e.event_id for e in launch_events),
                target_event_ids=tuple(e.event_id for e in target_events),
                start_onset=earliest_onset, end_onset=latest_onset,
                launch_measure=launch_measure, target_measure=target_measure,
                launch_beat=launch_beat, target_beat=target_beat,
                interval_semitones=interval, duration_quarters=duration,
                is_valid=False, rejection_reason=f"preparation_window_too_long_for_minimal_leap_7__{duration}_gt_1/2", diagnostics=tuple(diagnostics),
            )
    # Component role-cross check — record as diagnostic but do not reject;
    # rendering will filter inconsistent components (cross-instance contamination)
    if selected_components is not None:
        for ctype, comp in selected_components.items():
            if not _is_component_evidence_consistent_with_surface(comp, tuple(e.event_id for e in launch_events), tuple(e.event_id for e in target_events)):
                diagnostics.append(f"component_cross_role_{ctype}:{comp.evidence_event_ids}")
    return InstructionSurface(
        object_id=obj.object_id, hand=obj.hand,
        launch_event_ids=tuple(e.event_id for e in launch_events),
        target_event_ids=tuple(e.event_id for e in target_events),
        start_onset=earliest_onset, end_onset=latest_onset,
        launch_measure=launch_measure, target_measure=target_measure,
        launch_beat=launch_beat, target_beat=target_beat,
        interval_semitones=interval, duration_quarters=duration,
        is_valid=True, rejection_reason=None, diagnostics=tuple(diagnostics),
    )


def _is_valid_for_promotion(surface: InstructionSurface) -> bool:
    return surface.is_valid


def _instruction_for_object(
    obj: MusicalObject,
    components: list[ObjectComponent],
    event_by_id: dict[str, Any] | None = None,
) -> tuple[str, tuple[str, ...], str, str]:
    """Return (instruction, anatomy bullets, evidence string, caveats string).

    Instruction is a semantic playing-action description, not practice advice.
    Renders actual musical surface: note names, chord tones, measure/beat placements,
    durations and rhythmic relationships where evidence exists.
    """
    hand = obj.hand or "both"
    hand_label = "left hand" if hand == "left" else "right hand" if hand == "right" else "both hands"
    meas = _format_measures_compact(obj.measure_numbers) if obj.measure_numbers else str(obj.measure_start or "?")
    event_by_id = event_by_id or {}

    def _resolve_events(ids: tuple[str, ...] | list[str]) -> list[Any]:
        out: list[Any] = []
        for eid in ids:
            ev = event_by_id.get(eid)
            if ev is not None:
                out.append(ev)
        return out

    def _midi_list_to_names(midis: Any) -> str | None:
        if not isinstance(midis, list) or not midis:
            return None
        # filter ints
        ints = [int(x) for x in midis if isinstance(x, (int, float)) or (isinstance(x, str) and x.lstrip("-").isdigit())]
        if not ints:
            return None
        names = [_midi_to_pitch_name(m, None) for m in ints]
        names = [n for n in names if n]
        if not names:
            return None
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]}-{names[1]}"
        return "-".join(names)

    # Find relevant components using instance-specific attachment
    related = [c for c in components if _component_attaches_to_object(c, obj)]
    comp_map: dict[str, ObjectComponent] = {}
    for c in related:
        if c.component_type not in comp_map or float(c.confidence) > float(comp_map[c.component_type].confidence):
            comp_map[c.component_type] = c

    # Default caveats from object + components
    caveats_parts: list[str] = list(obj.caveats)
    for c in related:
        caveats_parts.extend(list(c.caveats))
    caveats_str = "; ".join(dict.fromkeys(caveats_parts)) if caveats_parts else "none — score-derived evidence"

    evidence_ids = list(obj.evidence_event_ids)[:3]
    token_ids = list(obj.token_ids)[:2]
    evidence_str = f"object: {obj.object_id} [{obj.gesture_ids[0] if obj.gesture_ids else (token_ids[0] if token_ids else 'evidence')}]; evidence_event_ids={evidence_ids}; confidence={obj.confidence:.2f}"
    if comp_map:
        comp_refs = ", ".join(f"{ct}:{c.component_id.split(':')[-1]}" for ct, c in list(comp_map.items())[:3])
        evidence_str += f"; components: {comp_refs}"

    # Build instruction + anatomy per family — descriptive only, no practice advice
    if obj.object_id == "leap_to_chord":
        # First build validated chronological surface from ScoreEvents (rendering must consume this, not raw component ordering)
        _validated_surface = build_validated_instruction_surface(obj, event_by_id, selected_components=comp_map if comp_map else None)
        # Filter comp_map to only strong attachments (evidence/gesture overlap) to avoid cross-instance contamination
        # For leap_to_chord, require component evidence to intersect surface launch/target
        if _validated_surface.is_valid:
            # Keep only components that are consistent with surface (no role crossing)
            filtered_map: dict[str, ObjectComponent] = {}
            for k, c in comp_map.items():
                if _is_component_evidence_consistent_with_surface(c, _validated_surface.launch_event_ids, _validated_surface.target_event_ids):
                    filtered_map[k] = c
                # leap_interval components are allowed even if they span both, but still must have gesture/evidence overlap?
                elif k in ("leap_interval", "leap_interval_semitones") and set(c.evidence_event_ids) & set(obj.evidence_event_ids):
                    filtered_map[k] = c
            comp_map = filtered_map
            # Use surface-derived events for rendering (chronological truth)
            launch_events = _resolve_events(_validated_surface.launch_event_ids)
            target_events = _resolve_events(_validated_surface.target_event_ids)
            # Derive interval/span/duration directly from validated surface (chronological truth)
            leap_iv = _validated_surface.interval_semitones
            # Compute span/count directly from target_events to avoid mismatched component values
            target_span = None
            dest_note_count: Any = "?"
            if target_events:
                mids = sorted([e.pitch_midi for e in target_events if e.pitch_midi is not None])
                if len(mids) >= 2:
                    target_span = max(mids) - min(mids)
                    dest_note_count = len(mids)
                elif len(mids) == 1:
                    target_span = 0
                    dest_note_count = 1
                elif len(mids) == 0:
                    target_span = None
                    dest_note_count = "?"
            time_to_land: Any = str(_validated_surface.duration_quarters) if _validated_surface.duration_quarters is not None else None
            # If surface interval is None, fallback to component
            if leap_iv is None:
                if "leap_interval" in comp_map:
                    leap_iv = comp_map["leap_interval"].measurements.get("leap_interval_semitones")
                elif "leap_interval_semitones" in comp_map:
                    leap_iv = comp_map["leap_interval_semitones"].measurements.get("leap_interval_semitones")
                if leap_iv is None:
                    leap_iv = obj.payload.get("movement") or obj.payload.get("movement_semitones") or obj.payload.get("leap_interval_semitones")
            # Re-derive launch/target comps from filtered map for placement fallback
            launch_comp = comp_map.get("launch_note")
            target_comp = comp_map.get("target_chord")
        else:
            # Surface invalid — still render but mark as rejected and use fallback logic that respects chronology where possible
            # Use surface's attempted launch/target (which failed validation) for transparency, but add caveat
            launch_events = _resolve_events(_validated_surface.launch_event_ids) if _validated_surface.launch_event_ids else []
            target_events = _resolve_events(_validated_surface.target_event_ids) if _validated_surface.target_event_ids else []
            if not launch_events and obj.evidence_event_ids:
                cand = _resolve_events((obj.evidence_event_ids[0],))
                if cand:
                    launch_events = cand[:1]
            if not target_events and obj.evidence_event_ids:
                all_evs = _resolve_events(tuple(obj.evidence_event_ids))
                if all_evs:
                    max_onset = max(e.onset for e in all_evs)
                    target_events = [e for e in all_evs if e.onset == max_onset]
            leap_iv = None
            target_span = None
            dest_note_count: Any = "?"
            time_to_land: Any = None
            if "leap_interval" in comp_map:
                leap_iv = comp_map["leap_interval"].measurements.get("leap_interval_semitones")
                time_to_land = comp_map["leap_interval"].measurements.get("time_to_land_quarters")
            if leap_iv is None and "leap_interval_semitones" in comp_map:
                leap_iv = comp_map["leap_interval_semitones"].measurements.get("leap_interval_semitones")
            if "target_span" in comp_map:
                target_span = comp_map["target_span"].measurements.get("target_span_semitones")
                dest_note_count = comp_map["target_span"].measurements.get("chord_note_count", dest_note_count)
            launch_comp = comp_map.get("launch_note")
            target_comp = comp_map.get("target_chord")
        launch_name = _format_pitch_event(launch_events[0]) if launch_events else None
        if launch_name is None and launch_comp is not None:
            pm = launch_comp.measurements.get("pitch_midi")
            if isinstance(pm, list) and pm:
                launch_name = _midi_list_to_names([pm[0]])
            elif isinstance(pm, (int, float)):
                launch_name = _midi_to_pitch_name(int(pm), None)
        if launch_name is None and launch_comp is None:
            # try payload midi
            pm = obj.payload.get("pitch_midi") or obj.payload.get("launch_pitch_midi")
            if isinstance(pm, (int, float)):
                launch_name = _midi_to_pitch_name(int(pm), None)
        chord_name = _format_chord_tones(target_events) if target_events else None
        if chord_name is None and target_comp is not None:
            pm = target_comp.measurements.get("pitch_midi")
            chord_name = _midi_list_to_names(pm) if isinstance(pm, list) else None
            if chord_name is None and isinstance(pm, (int, float)):
                chord_name = _midi_to_pitch_name(int(pm), None)
            if chord_name is None:
                dest_note_count_tmp = target_comp.measurements.get("chord_note_count")
                if dest_note_count_tmp and dest_note_count == "?":
                    dest_note_count = dest_note_count_tmp
            if chord_name and dest_note_count == "?":
                # infer count from name
                dest_note_count = chord_name.count("-") + 1
        if target_comp is not None and dest_note_count == "?":
            dc = target_comp.measurements.get("chord_note_count")
            if dc is not None:
                dest_note_count = dc
        if "target_chord" in comp_map:
            pm = target_comp.measurements.get("pitch_midi") if target_comp else None
            if isinstance(pm, list) and pm and dest_note_count == "?":
                dest_note_count = len(pm)
            if target_span is None or target_span == "?":
                target_span = (target_comp.measurements.get("target_span_semitones") if target_comp else None)
        if leap_iv is None:
            leap_iv = obj.payload.get("movement") or obj.payload.get("movement_semitones") or obj.payload.get("leap_interval_semitones")
        if target_span is None:
            target_span = obj.payload.get("span") or obj.payload.get("target_span_semitones")
        if time_to_land is None:
            time_to_land = obj.payload.get("time_to_land_quarters") or obj.payload.get("duration_total") or None
        # Compute time to land from onsets if still missing
        if (time_to_land is None or time_to_land == "?") and launch_events and target_events:
            try:
                delta = target_events[0].onset - launch_events[0].onset
                time_to_land = str(delta)
            except Exception:
                pass
        # Beat/measure placements
        launch_place = _placement_str(launch_events[0] if launch_events else None, fallback_measure=None)
        landing_place = _placement_str(target_events[0] if target_events else None, fallback_measure=None)
        # If placement missing, fallback to component beat_start
        if launch_place is None and launch_comp is not None and launch_comp.beat_start is not None:
            bn = _beat_number_str(launch_comp.beat_start)
            launch_place = f"beat {bn}" if bn else None
        if landing_place is None and target_comp is not None and target_comp.beat_start is not None:
            bn = _beat_number_str(target_comp.beat_start)
            landing_place = f"beat {bn}" if bn else None
        # Duration strings
        launch_dur = _duration_str(launch_events[0] if launch_events else None)
        landing_dur = _duration_str(target_events[0] if target_events else None) if len(target_events) == 1 else None
        # Instruction sentence — textbook style with note names and placements
        # e.g., "The left hand moves from F4 on m.9, beat 1 to an A3-C4 chord on m.10, beat 3."
        if launch_name and chord_name and launch_place and landing_place:
            instruction = f"The {hand_label} moves from {launch_name} on {launch_place} to an {chord_name} chord on {landing_place}."
        elif launch_name and chord_name and landing_place:
            instruction = f"The {hand_label} moves from {launch_name} to an {chord_name} chord on {landing_place}."
        elif launch_name and chord_name:
            instruction = f"The {hand_label} moves from {launch_name} to an {chord_name} chord at m.{meas}."
        elif chord_name and dest_note_count != "?":
            landing_qual = f" — {landing_place}" if landing_place else ""
            instruction = f"The {hand_label} lands on an {chord_name} chord ({dest_note_count} notes){landing_qual} at m.{meas}."
        elif dest_note_count != "?":
            instruction = f"The {hand_label} moves into a {dest_note_count}-note chord landing at m.{meas}" + (f" on {landing_place}" if landing_place else "") + "."
        elif chord_name:
            instruction = f"The {hand_label} moves into an {chord_name} chord at m.{meas}" + (f" on {landing_place}" if landing_place else "") + "."
        else:
            instruction = f"The {hand_label} moves into a chord landing at m.{meas}" + (f" on {landing_place}" if landing_place else "") + "."

        anatomy: list[str] = []
        anatomy.append(f"Hand / voice: {hand} ({hand_label})")
        if launch_name:
            launch_detail = f"Launch: {launch_name}"
            if launch_place:
                launch_detail += f" on {launch_place}"
            if launch_dur:
                launch_detail += f" — {launch_dur}"
            else:
                # fallback shape
                launch_detail += " (single note)"
            anatomy.append(launch_detail)
        else:
            anatomy.append("Launch: not detected yet")
        if chord_name:
            dest_detail = f"Landing: {chord_name}"
            if dest_note_count != "?" and dest_note_count is not None:
                dest_detail += f" ({dest_note_count} notes"
                if target_span is not None and target_span != "?" and target_span != "":
                    dest_detail += f", span {target_span} semitones"
                dest_detail += ")"
            elif target_span is not None and target_span != "?" and target_span != "":
                dest_detail += f" (span {target_span} semitones)"
            if landing_place:
                dest_detail += f" on {landing_place}"
            if landing_dur:
                dest_detail += f" — {landing_dur}"
            anatomy.append(dest_detail)
        else:
            fallback_dest = f"Destination: chord" + (f" ({dest_note_count} notes)" if dest_note_count != "?" else " — not detected yet")
            anatomy.append(fallback_dest)
            if target_span is not None and target_span != "?" and target_span != "":
                anatomy.append(f"Destination span: {target_span} semitones")
            else:
                anatomy.append("Destination span: not detected yet")
        if leap_iv is not None and leap_iv != "?":
            try:
                iv_int = int(leap_iv)
                direction = "up" if iv_int > 0 else "down" if iv_int < 0 else "level"
                name = _interval_name(iv_int)
                anatomy.append(f"Interval: {abs(iv_int)} semitones {direction} — {name}")
            except Exception:
                anatomy.append(f"Interval: {leap_iv} semitones")
        else:
            anatomy.append("Interval: not detected yet")
        # Timing / rhythmic relationship
        time_str = _format_time_to_land(time_to_land)
        if launch_place and landing_place and time_str:
            anatomy.append(f"Timing: {time_str} from {launch_place} to {landing_place}")
        elif time_str:
            anatomy.append(f"Timing: {time_str} to landing")
        elif launch_place and landing_place:
            # try compute from onsets
            anatomy.append(f"Placement: {launch_place} → {landing_place}")
        else:
            # fallback beat relation if we have beat numbers
            if launch_comp and target_comp and launch_comp.beat_start is not None and target_comp.beat_start is not None:
                bf = _beat_number_str(launch_comp.beat_start)
                bt = _beat_number_str(target_comp.beat_start)
                if bf and bt:
                    anatomy.append(f"Placement: beat {bf} → beat {bt}")
        anatomy.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy), evidence_str, caveats_str

    if obj.object_id in ("chord_landing", "chordal_homophonic_texture", "melody_embedded_in_chords"):
        span_semi: Any = "?"
        note_ct: Any = "?"
        if "target_span" in comp_map:
            span_semi = comp_map["target_span"].measurements.get("target_span_semitones", "?")
            note_ct = comp_map["target_span"].measurements.get("chord_note_count", "?")
        if "target_chord" in comp_map:
            span_semi = comp_map["target_chord"].measurements.get("target_span_semitones", span_semi)
            note_ct = comp_map["target_chord"].measurements.get("chord_note_count", note_ct)
        if span_semi == "?":
            span_semi = obj.payload.get("span_semitones") or obj.payload.get("span") or "?"
        if note_ct == "?":
            note_ct = obj.payload.get("note_count") or obj.payload.get("chord_note_count") or "?"
        # Resolve chord tones from evidence
        all_events = _resolve_events(tuple(obj.evidence_event_ids))
        # Prefer latest onset group as landing chord
        chord_events: list[Any] = []
        if all_events:
            # group by onset, pick max onset
            max_on = max(e.onset for e in all_events)
            chord_events = [e for e in all_events if e.onset == max_on and e.pitch_midi is not None]
            if not chord_events:
                chord_events = [e for e in all_events if e.pitch_midi is not None]
        chord_name = _format_chord_tones(chord_events) if chord_events else None
        if chord_name is None and "target_chord" in comp_map:
            pm = comp_map["target_chord"].measurements.get("pitch_midi")
            chord_name = _midi_list_to_names(pm) if isinstance(pm, list) else None
        landing_place = _placement_str(chord_events[0] if chord_events else None, fallback_measure=meas if meas != "?" else None)
        if landing_place is None:
            # fallback to component landing_beat
            lb = comp_map.get("landing_beat")
            if lb and lb.beat_start is not None:
                bn = _beat_number_str(lb.beat_start)
                landing_place = f"m.{meas}, beat {bn}" if bn else f"m.{meas}"
            elif comp_map.get("landing_onset") and comp_map["landing_onset"].beat_start is not None:
                bn = _beat_number_str(comp_map["landing_onset"].beat_start)
                landing_place = f"m.{meas}, beat {bn}" if bn else f"m.{meas}"
        dur_str = _duration_str(chord_events[0] if chord_events else None)
        if chord_name and note_ct != "?":
            instruction = f"The {hand_label} sounds {chord_name} ({note_ct} notes, span {span_semi} semitones)" + (f" on {landing_place}" if landing_place else f" at m.{meas}") + "."
        elif chord_name:
            instruction = f"The {hand_label} sounds {chord_name}" + (f" on {landing_place}" if landing_place else f" at m.{meas}") + "."
        elif note_ct != "?":
            instruction = f"The {hand_label} presents a {note_ct}-note chord at m.{meas} spanning {span_semi} semitones" + (f" on {landing_place}" if landing_place and landing_place != f"m.{meas}" else "") + "."
        else:
            instruction = f"The {hand_label} presents a chord sonority at m.{meas}" + (f" on {landing_place}" if landing_place and landing_place != f"m.{meas}" else "") + "."
        anatomy_list: list[str] = []
        anatomy_list.append(f"Hand / voice: {hand}")
        if chord_name:
            anatomy_list.append(f"Chord tones: {chord_name}" + (f" ({note_ct} notes)" if note_ct != "?" else "") + (f", span {span_semi} semitones" if span_semi != "?" else ""))
        else:
            anatomy_list.append(f"Shape: {note_ct}-note chord, span {span_semi} semitones" if note_ct != "?" else "Shape: not detected yet")
        if landing_place:
            anatomy_list.append(f"Placement: {landing_place}" + (f" — {dur_str}" if dur_str else ""))
        else:
            anatomy_list.append("Placement: not detected yet")
        if dur_str and chord_name is None:
            anatomy_list.append(f"Duration: {dur_str}")
        anatomy_list.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy_list), evidence_str, caveats_str

    if obj.object_id in ("melody_with_accompaniment", "melody_voicing_over_accompaniment"):
        gap: Any = "not detected yet"
        for c in related:
            if c.component_type == "register_separation":
                rg = c.measurements.get("register_gap_semitones")
                if rg is not None:
                    gap = f"{rg} semitones"
                break
        # Resolve melody vs accompaniment events for pitch ranges
        melody_comp = comp_map.get("melody_layer")
        acc_comp = comp_map.get("accompaniment_layer")
        melody_events = _resolve_events(tuple(melody_comp.evidence_event_ids)) if melody_comp else []
        acc_events = _resolve_events(tuple(acc_comp.evidence_event_ids)) if acc_comp else []
        melody_range = None
        acc_range = None
        if melody_events:
            mids = sorted(e.pitch_midi for e in melody_events if e.pitch_midi is not None)
            if mids:
                lo = _midi_to_pitch_name(mids[0], next((e for e in melody_events if e.pitch_midi == mids[0]), None))
                hi = _midi_to_pitch_name(mids[-1], next((e for e in melody_events if e.pitch_midi == mids[-1]), None))
                melody_range = f"{lo}-{hi}" if lo != hi else f"{lo}"
        if acc_events:
            mids = sorted(e.pitch_midi for e in acc_events if e.pitch_midi is not None)
            if mids:
                lo = _midi_to_pitch_name(mids[0], next((e for e in acc_events if e.pitch_midi == mids[0]), None))
                hi = _midi_to_pitch_name(mids[-1], next((e for e in acc_events if e.pitch_midi == mids[-1]), None))
                acc_range = f"{lo}-{hi}" if lo != hi else f"{lo}"
        # Use payload ranges if still missing
        if melody_range is None and melody_comp:
            rng = melody_comp.measurements.get("melody_pitch_range")
            if isinstance(rng, list) and len(rng) == 2 and rng[0] is not None:
                melody_range = f"{_midi_to_pitch_name(rng[0], None)}-{_midi_to_pitch_name(rng[1], None)}"
        if acc_range is None and acc_comp:
            rng = acc_comp.measurements.get("accompaniment_pitch_range")
            if isinstance(rng, list) and len(rng) == 2 and rng[0] is not None:
                acc_range = f"{_midi_to_pitch_name(rng[0], None)}-{_midi_to_pitch_name(rng[1], None)}"
        # Determine placement and durations
        onset_comp = comp_map.get("onset_alignment")
        align_ratio = onset_comp.measurements.get("alignment_ratio") if onset_comp else None
        if obj.object_id == "melody_with_accompaniment":
            instruction = f"Both hands form a melody-with-accompaniment texture at m.{meas}: one layer carries the melodic line while another supplies aligned support."
        else:
            instruction = f"The texture presents a melody voicing over accompaniment at m.{meas}: the upper line projects while lower tones provide harmonic support."
        # Enrich instruction with pitch ranges if available
        if melody_range and acc_range:
            instruction += f" Melody {melody_range} over accompaniment {acc_range}."
        elif melody_range:
            instruction += f" Melody {melody_range}."
        anatomy = []
        anatomy.append(f"Hand / voice: {hand}")
        if melody_range or acc_range:
            if melody_range:
                anatomy.append(f"Melody tones: {melody_range}" + (f" ({len(melody_events)} notes)" if melody_events else ""))
            if acc_range:
                anatomy.append(f"Accompaniment tones: {acc_range}" + (f" ({len(acc_events)} notes)" if acc_events else ""))
        else:
            anatomy.append(f"Texture: melody with accompaniment ({len(obj.evidence_event_ids)} events)")
        anatomy.append(f"Register separation: {gap}")
        if align_ratio is not None:
            try:
                anatomy.append(f"Onset alignment: {float(align_ratio):.2f} of melody onsets coincide with accompaniment")
            except Exception:
                pass
        anatomy.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy), evidence_str, caveats_str

    if obj.object_id in ("alberti_bass", "broken_chord_accompaniment", "arpeggiated_accompaniment", "wide_broken_chord"):
        # harmonic collection and interval path with pitch spelling
        chord_events = _resolve_events(tuple(obj.evidence_event_ids))
        # Determine pitch collection from events
        coll_name: str | None = None
        if chord_events:
            mids = sorted({e.pitch_midi for e in chord_events if e.pitch_midi is not None})
            if mids:
                coll_name = "-".join(_midi_to_pitch_name(m, next((e for e in chord_events if e.pitch_midi == m), None)) for m in mids)
        if coll_name is None:
            for c in related:
                if c.component_type == "harmonic_collection":
                    pm = c.measurements.get("pitch_midi")
                    if isinstance(pm, list) and pm:
                        coll_name = _midi_list_to_names(pm)
                        break
                    pcs = c.measurements.get("pitch_classes") or c.measurements.get("harmonic_set")
                    if pcs and pcs != "?":
                        coll_name = f"pitch classes {pcs}"
                        break
        interval_path: Any = "not detected yet"
        span_val: Any = "?"
        total_span: Any = None
        for c in related:
            if c.component_type == "interval_path":
                ip = c.measurements.get("interval_sequence", "?")
                if ip != "?" and ip is not None:
                    interval_path = ip
                total_span = c.measurements.get("total_span_semitones")
                break
        for c in related:
            if c.component_type == "hand_relocation" and "total_span_semitones" in c.measurements:
                span_val = c.measurements.get("total_span_semitones", "?")
                break
            if c.component_type == "interval_path" and "total_span_semitones" in c.measurements:
                span_val = c.measurements.get("total_span_semitones", "?")
                break
        if span_val == "?" and total_span is not None:
            span_val = total_span
        if span_val == "?":
            fallback = obj.payload.get("span_semitones") or obj.payload.get("total_span_semitones")
            if fallback is not None:
                span_val = fallback
        # Beat placement for figure
        beat_start = None
        beat_end = None
        for c in related:
            if c.beat_start is not None:
                beat_start = c.beat_start
                beat_end = c.beat_end
                break
        beat_place = None
        if beat_start is not None:
            bn_s = _beat_number_str(beat_start)
            bn_e = _beat_number_str(beat_end) if beat_end else None
            if bn_s and bn_e and bn_s != bn_e:
                beat_place = f"beats {bn_s}-{bn_e}"
            elif bn_s:
                beat_place = f"beat {bn_s}"
        # Interval rendering: convert list to semitone steps with sign
        interval_str = "not detected yet"
        if isinstance(interval_path, list) and interval_path:
            interval_str = ", ".join(f"{int(x):+d}" for x in interval_path[:8])
            if len(interval_path) > 8:
                interval_str += f" … ({len(interval_path)} steps)"
        elif isinstance(interval_path, str) and interval_path != "not detected yet":
            interval_str = interval_path
        instruction = f"The {hand_label} outlines a harmony as a broken-chord figure at m.{meas}" + (f" on {beat_place}" if beat_place else "") + (f", spanning {span_val} semitones" if span_val != "?" else "") + "."
        if coll_name:
            instruction += f" Pitch collection {coll_name}."
        anatomy = []
        anatomy.append(f"Hand / voice: {hand}")
        if coll_name:
            anatomy.append(f"Pitch collection: {coll_name}" + (f", span {span_val} semitones" if span_val != "?" else ""))
        else:
            anatomy.append(f"Pattern: broken-chord" + (f", span {span_val} semitones" if span_val != "?" else ""))
        anatomy.append(f"Interval steps: {interval_str}")
        if beat_place:
            anatomy.append(f"Placement: m.{meas} {beat_place}")
        anatomy.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy), evidence_str, caveats_str

    if obj.object_id in ("ascending_scalar_run", "descending_scalar_run"):
        direction = "up" if obj.object_id == "ascending_scalar_run" else "down"
        span: Any = "not detected yet"
        steps: Any = obj.payload.get("steps") or "not detected yet"
        step_comp = comp_map.get("step_pattern")
        span_comp = comp_map.get("span_semitones")
        chosen_span = None
        interval_seq: Any = None
        if step_comp:
            chosen_span = step_comp.measurements.get("span_semitones")
            interval_seq = step_comp.measurements.get("interval_sequence")
            steps_val = step_comp.measurements.get("note_count") or step_comp.measurements.get("steps")
            if steps_val:
                steps = steps_val
        if span_comp and chosen_span is None:
            chosen_span = span_comp.measurements.get("span_semitones")
        if chosen_span is not None:
            span = f"{chosen_span} semitones"
        # Resolve start/end pitches from events
        all_evs = _resolve_events(tuple(obj.evidence_event_ids))
        start_name = None
        end_name = None
        dur_pat = None
        if all_evs:
            sorted_evs = sorted(all_evs, key=lambda e: e.onset)
            if sorted_evs[0].pitch_midi is not None:
                start_name = _format_pitch_event(sorted_evs[0])
            if sorted_evs[-1].pitch_midi is not None:
                end_name = _format_pitch_event(sorted_evs[-1])
            # duration pattern
            durs = [e.duration for e in sorted_evs if e.duration is not None]
            if durs and len(set(durs)) == 1:
                dur_pat = _duration_str(sorted_evs[0])
        interval_str = None
        if isinstance(interval_seq, list) and interval_seq:
            interval_str = ", ".join(f"{int(x):+d}" for x in interval_seq[:8])
            if len(interval_seq) > 8:
                interval_str += f" … ({len(interval_seq)} steps)"
        # Build instruction with actual surface
        if start_name and end_name:
            instruction = f"The {hand_label} moves stepwise {direction} from {start_name} to {end_name} at m.{meas}, covering {span} across {steps} notes."
        else:
            instruction = f"The {hand_label} moves stepwise {direction} at m.{meas}, covering {span} across {steps} notes."
        if interval_str:
            instruction += f" Steps: {interval_str}."
        anatomy = []
        anatomy.append(f"Hand / voice: {hand}")
        if start_name and end_name:
            anatomy.append(f"Pitch line: {start_name} → {end_name} ({direction}, span {span}, {steps} notes)")
        else:
            anatomy.append(f"Direction: {direction}, steps {steps}")
            anatomy.append(f"Span: {span}")
        if interval_str:
            anatomy.append(f"Step intervals: {interval_str}")
        if dur_pat:
            anatomy.append(f"Note values: {dur_pat}")
        anatomy.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy), evidence_str, caveats_str

    if obj.object_id in ("hand_shift", "hand_expansion_contraction"):
        all_evs = _resolve_events(tuple(obj.evidence_event_ids))
        start_name = _format_pitch_event(all_evs[0]) if all_evs and all_evs[0].pitch_midi is not None else None
        # span from measurements
        span_val = None
        for c in related:
            if c.component_type in ("hand_relocation", "span_semitones", "target_span") and "total_span_semitones" in c.measurements:
                span_val = c.measurements.get("total_span_semitones")
                break
            if c.component_type == "span_semitones":
                span_val = c.measurements.get("span_semitones")
                break
        span_str = f", span {span_val} semitones" if span_val is not None else ""
        place = _placement_str(all_evs[0] if all_evs else None, fallback_measure=meas)
        if start_name and place:
            instruction = f"The {hand_label} shifts hand position on {place} around {start_name}{span_str}."
        elif place:
            instruction = f"The {hand_label} shifts hand position on {place}{span_str}."
        else:
            instruction = f"The {hand_label} shifts hand position at m.{meas}, changing span or register{span_str}."
        anatomy_list = [f"Hand / voice: {hand}"]
        if start_name:
            anatomy_list.append(f"Anchor pitch: {start_name}" + (f" on {place}" if place else ""))
        if span_val is not None:
            anatomy_list.append(f"Span change: {span_val} semitones")
        anatomy_list.append(f"Span: m.{meas}, confidence {obj.confidence:.2f}")
        anatomy_list.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy_list), evidence_str, caveats_str

    if obj.object_id in ("syncopation", "repeated_rhythm_cell", "rhythm_pattern_break", "polyrhythm"):
        all_evs = _resolve_events(tuple(obj.evidence_event_ids))
        # Build duration pattern with actual note values
        dur_pattern = None
        beat_pattern = None
        if all_evs:
            # collect durations in order
            sorted_evs = sorted(all_evs, key=lambda e: e.onset)
            durs = []
            beats = []
            for e in sorted_evs[:6]:
                dt = getattr(e, "duration_type", None)
                bn = _beat_number_str(getattr(e, "beat", None))
                if dt:
                    durs.append(dt)
                elif e.duration is not None:
                    durs.append(f"{e.duration}q")
                if bn:
                    beats.append(f"beat {bn}")
            if durs:
                dur_pattern = "-".join(durs)
            if beats:
                beat_pattern = ", ".join(beats)
        # Fallback to component rhythm_cell
        if dur_pattern is None:
            rc = comp_map.get("rhythm_cell") or comp_map.get("duration_pattern")
            if rc:
                durs = rc.measurements.get("duration_pattern") or rc.measurements.get("beat_positions")
                if isinstance(durs, list) and durs:
                    dur_pattern = "-".join(str(x) for x in durs[:6])
        place = _placement_str(all_evs[0] if all_evs else None, fallback_measure=meas)
        label = obj.label.lower()
        if dur_pattern and place:
            instruction = f"The texture presents a {label} on {place} with {dur_pattern}."
        elif dur_pattern:
            instruction = f"The texture presents a {label} at m.{meas} — {dur_pattern}."
        elif place:
            instruction = f"The texture presents a {label} on {place}."
        else:
            instruction = f"The texture presents a {label} at m.{meas}."
        anatomy_list = [f"Hand / voice: {hand}", f"Object: {obj.label} ({obj.object_id})"]
        if dur_pattern:
            anatomy_list.append(f"Rhythm: {dur_pattern}" + (f" on {beat_pattern}" if beat_pattern else ""))
        if place:
            anatomy_list.append(f"Placement: {place}")
        else:
            anatomy_list.append(f"Span: m.{meas}, confidence {obj.confidence:.2f}")
        # add repetition count etc
        rep = comp_map.get("repetition_count")
        if rep:
            rc = rep.measurements.get("repetition_count")
            if rc:
                anatomy_list.append(f"Repetitions: {rc}×")
        anatomy_list.append(f"Evidence: {evidence_str}")
        return instruction, tuple(anatomy_list), evidence_str, caveats_str

    if obj.object_id == "octave_doubled_melody":
        all_evs = _resolve_events(tuple(obj.evidence_event_ids))
        # Resolve doubled pairs for naming: show lower->upper progression
        # Use object's payload for details
        octave_count = obj.payload.get("octave_count", len({e.onset for e in all_evs}))
        direction = obj.payload.get("direction", "mixed")
        span_val = obj.payload.get("pitch_span_semitones") or obj.payload.get("span_semitones") or "?"
        doubling_type = obj.payload.get("doubling_type", "exact_octave" if obj.payload.get("is_exact_doubling") else "mixed_octave_plus_other_tones")
        # Build note range from evidence
        low_name = None
        high_name = None
        if all_evs:
            # per onset min/max
            by_onset_local: dict[Fraction, list[Any]] = {}
            for e in all_evs:
                by_onset_local.setdefault(e.onset, []).append(e)
            # sorted onsets extremes
            sorted_o = sorted(by_onset_local.keys())
            if sorted_o:
                first_o = by_onset_local[sorted_o[0]]
                last_o = by_onset_local[sorted_o[-1]]
                fm = sorted([x for x in first_o if getattr(x, "pitch_midi", None) is not None], key=lambda x: x.pitch_midi)  # type: ignore
                lm = sorted([x for x in last_o if getattr(x, "pitch_midi", None) is not None], key=lambda x: x.pitch_midi)  # type: ignore
                if fm and len(fm) >= 2:
                    # find octave pair in first
                    for i in range(len(fm)):
                        for j in range(i+1, len(fm)):
                            if fm[j].pitch_midi - fm[i].pitch_midi == 12:
                                low_name = _format_pitch_event(fm[i])
                                high_name = _format_pitch_event(fm[j])
                                break
                if lm and not low_name:
                    # fallback to overall min/max
                    pass
                if not low_name and fm:
                    low_name = _format_pitch_event(fm[0])
                    high_name = _format_pitch_event(fm[-1]) if len(fm) > 1 else low_name
                if lm and len(lm) >= 2:
                    # last octave for range display
                    last_low = None
                    last_high = None
                    for i in range(len(lm)):
                        for j in range(i+1, len(lm)):
                            if lm[j].pitch_midi - lm[i].pitch_midi == 12:
                                last_low = _format_pitch_event(lm[i])
                                last_high = _format_pitch_event(lm[j])
                                break
                    if last_low and low_name and last_low != low_name:
                        high_name_display = f"{low_name}-{high_name} → {last_low}-{last_high}"
                    else:
                        high_name_display = f"{low_name}-{high_name}" if low_name and high_name and low_name != high_name else (low_name or "?")
                else:
                    high_name_display = f"{low_name}-{high_name}" if low_name and high_name else (low_name or "?")
            else:
                high_name_display = "?"
        else:
            high_name_display = "?"
        place = _placement_str(all_evs[0] if all_evs else None, fallback_measure=meas)
        # Instruction as one structural unit, not parallel notes
        if place:
            instruction = f"The {hand_label} projects an octave-doubled melody on {place} as one structural unit: {octave_count} doubled octaves {direction} (span {span_val} semitones, {doubling_type})."
        else:
            instruction = f"The {hand_label} projects an octave-doubled melody at m.{meas} as one structural unit: {octave_count} doubled octaves {direction} (span {span_val} semitones, {doubling_type})."
        # Add contour detail if available
        contour = obj.payload.get("contour") or obj.payload.get("interval_sequence_low") or ()
        contour_str = ", ".join(f"{int(x):+d}" for x in contour[:6]) if isinstance(contour, (list, tuple)) and contour else "not detected"
        anatomy_list = [
            f"Hand / voice: {hand} ({hand_label}) — one structural octave-doubled line, not separate parallel notes",
            f"Doubled octaves: {octave_count} consecutive octave pairs ({doubling_type})",
            f"Direction/contour: {direction} — intervals {contour_str}",
            f"Pitch span: {span_val} semitones",
            f"Voicing: octave (12 semitones) doubling {'exact' if doubling_type=='exact_octave' else 'mixed with inner tones'}",
            f"Evidence: {evidence_str}",
        ]
        if high_name_display and high_name_display != "?":
            anatomy_list.insert(2, f"Pitch range (sample): {high_name_display}")
        if place:
            anatomy_list.append(f"Placement: {place}")
        return instruction, tuple(anatomy_list), evidence_str, caveats_str

    if obj.object_id == "single_hand_multi_voice_texture":
        all_evs = _resolve_events(tuple(obj.evidence_event_ids))
        gap = obj.payload.get("pitch_band_gap_semitones", "?")
        low_r = obj.payload.get("low_band_range", [])
        high_r = obj.payload.get("high_band_range", [])
        reasons = obj.payload.get("reasons", ())
        reason_str = ", ".join(reasons) if isinstance(reasons, (list, tuple)) and reasons else "voice_assignment_inferred"
        # Build range strings
        def _range_name(rng):
            if not rng or len(rng) != 2:
                return "?"
            try:
                return f"{_midi_to_pitch_name(int(rng[0]), None)}-{_midi_to_pitch_name(int(rng[1]), None)} ({rng[0]}-{rng[1]})"
            except Exception:
                return str(rng)
        low_name = _range_name(low_r)
        high_name = _range_name(high_r)
        place = _placement_str(all_evs[0] if all_evs else None, fallback_measure=meas)
        ratio = obj.payload.get("duration_ratio", "?")
        overlap = obj.payload.get("overlap_ratio", "?")
        if place:
            instruction = f"The {hand_label} appears to carry multiple voices on {place} (gap {gap} semitones): low {low_name} and high {high_name} show independent rhythmic behavior — {reason_str}."
        else:
            instruction = f"The {hand_label} appears to carry multiple voices at m.{meas} (gap {gap} semitones): low {low_name} and high {high_name} — {reason_str}."
        anatomy_list = [
            f"Hand / voice: {hand} ({hand_label}) — single hand, multiple inferred roles",
            f"Pitch bands separated by {gap} semitones (roughly an octave or more): low {low_name}, high {high_name}",
            f"Evidence of independence: duration ratio {ratio}, onset overlap {overlap}; reasons: {reason_str}",
            f"Caveat: voice assignment is inferred from texture (not notated voice separation)",
            f"Evidence: {evidence_str}",
        ]
        if place:
            anatomy_list.append(f"Placement: {place}")
        # Ensure caveats mention voice_assignment_inferred
        if "voice_assignment_inferred" not in caveats_str:
            caveats_str = (caveats_str + "; voice_assignment_inferred" if caveats_str != "none — score-derived evidence" else "voice_assignment_inferred")
        return instruction, tuple(anatomy_list), evidence_str, caveats_str

    # Generic fallback — descriptive, not prescriptive
    all_evs = _resolve_events(tuple(obj.evidence_event_ids))
    place = _placement_str(all_evs[0] if all_evs else None, fallback_measure=meas)
    chord_name = _format_chord_tones(all_evs) if all_evs else None
    if chord_name and place:
        instruction = f"A {obj.label.lower()} with {chord_name} is present on {place} involving {hand_label}."
    elif chord_name:
        instruction = f"A {obj.label.lower()} with {chord_name} is present at m.{meas} involving {hand_label}."
    elif place:
        instruction = f"A {obj.label.lower()} is present on {place} involving {hand_label}."
    else:
        instruction = f"A {obj.label.lower()} is present at m.{meas} involving {hand_label}."
    anatomy = (
        f"Hand / voice: {hand}",
        f"Object: {obj.label} ({obj.object_id})",
        f"Span: m.{meas}, confidence {obj.confidence:.2f}",
        f"Evidence: {evidence_str}",
    )
    return instruction, anatomy, evidence_str, caveats_str


# ---------------------------------------------------------------------------
# Surface provenance collector (for diagnostics and JSON payload)
# ---------------------------------------------------------------------------


def _collect_surface_fields_for_object(
    obj: MusicalObject,
    comp_map: dict[str, ObjectComponent],
    event_by_id: dict[str, Any],
) -> dict[str, SurfaceField]:
    """Collect SurfaceField provenance mirroring _instruction_for_object surface picks.
    
    Keeps each rendered field tied to its source event_ids and component_id.
    Used for diagnostics and JSON debug payload.
    """
    fields: dict[str, SurfaceField] = {}

    def _resolve(ids: tuple[str, ...] | list[str]) -> list[Any]:
        out: list[Any] = []
        for eid in ids:
            ev = event_by_id.get(eid)
            if ev is not None:
                out.append(ev)
        return out

    def _midi_list_to_names_inner(midis: Any) -> str | None:
        if not isinstance(midis, list) or not midis:
            return None
        ints = [int(x) for x in midis if isinstance(x, (int, float)) or (isinstance(x, str) and x.lstrip("-").isdigit())]
        if not ints:
            return None
        names = [_midi_to_pitch_name(m, None) for m in ints]
        names = [n for n in names if n]
        if not names:
            return None
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]}-{names[1]}"
        return "-".join(names)

    # Per-family provenance
    if obj.object_id == "leap_to_chord":
        # Use validated surface for chronological truth; fallback to component if surface invalid
        _surf = build_validated_instruction_surface(obj, event_by_id, selected_components=comp_map if comp_map else None)
        if _surf.is_valid:
            # Filter comps to those consistent with surface (no role crossing)
            _filtered = {k: v for k, v in comp_map.items() if _is_component_evidence_consistent_with_surface(v, _surf.launch_event_ids, _surf.target_event_ids) or k in ("leap_interval", "leap_interval_semitones")}
            # Use filtered for subsequent lookups
            comp_map = _filtered
            launch_comp = comp_map.get("launch_note")
            target_comp = comp_map.get("target_chord")
            leap_comp = comp_map.get("leap_interval") or comp_map.get("leap_interval_semitones")
            span_comp = comp_map.get("target_span") or comp_map.get("target_chord")
            launch_events = _resolve(_surf.launch_event_ids)
            target_events = _resolve(_surf.target_event_ids)
            # If surface interval exists, prefer it; will be handled later
        else:
            launch_comp = comp_map.get("launch_note")
            target_comp = comp_map.get("target_chord")
            leap_comp = comp_map.get("leap_interval") or comp_map.get("leap_interval_semitones")
            span_comp = comp_map.get("target_span") or comp_map.get("target_chord")
            launch_events = _resolve(tuple(launch_comp.evidence_event_ids)) if launch_comp else []
            target_events = _resolve(tuple(target_comp.evidence_event_ids)) if target_comp else []
            # fallback like renderer
            if not launch_events and obj.evidence_event_ids:
                cand = _resolve((obj.evidence_event_ids[0],))
                if cand:
                    launch_events = cand[:1]
            if not target_events and obj.evidence_event_ids:
                all_evs = _resolve(tuple(obj.evidence_event_ids))
                if all_evs:
                    max_onset = max(e.onset for e in all_evs)
                    target_events = [e for e in all_evs if e.onset == max_onset]
        # launch field
        if launch_events:
            launch_name = _format_pitch_event(launch_events[0])
            if launch_name:
                fields["launch"] = SurfaceField(
                    name="launch",
                    value=launch_name,
                    event_ids=tuple(e.event_id for e in launch_events),
                    component_id=launch_comp.component_id if launch_comp else None,
                    component_type=launch_comp.component_type if launch_comp else None,
                    measure_numbers=tuple(launch_events[0].measure_number,) if getattr(launch_events[0], "measure_number", None) else (),
                )
        elif launch_comp:
            pm = launch_comp.measurements.get("pitch_midi")
            name = None
            if isinstance(pm, list) and pm:
                name = _midi_list_to_names_inner([pm[0]])
            elif isinstance(pm, (int, float)):
                name = _midi_to_pitch_name(int(pm), None)
            if name:
                fields["launch"] = SurfaceField(
                    name="launch", value=name, event_ids=tuple(launch_comp.evidence_event_ids),
                    component_id=launch_comp.component_id, component_type=launch_comp.component_type,
                    measure_numbers=tuple(launch_comp.measure_numbers),
                )
        # landing chord field
        chord_name = _format_chord_tones(target_events) if target_events else None
        if chord_name is None and target_comp is not None:
            pm = target_comp.measurements.get("pitch_midi")
            chord_name = _midi_list_to_names_inner(pm) if isinstance(pm, list) else None
            if chord_name is None and isinstance(pm, (int, float)):
                chord_name = _midi_to_pitch_name(int(pm), None)
        if chord_name:
            fields["landing"] = SurfaceField(
                name="landing_chord",
                value=chord_name,
                event_ids=tuple(e.event_id for e in target_events) if target_events else tuple(target_comp.evidence_event_ids) if target_comp else (),
                component_id=target_comp.component_id if target_comp else None,
                component_type=target_comp.component_type if target_comp else None,
                measure_numbers=tuple(target_events[0].measure_number,) if target_events and getattr(target_events[0], "measure_number", None) else tuple(target_comp.measure_numbers) if target_comp else (),
            )
            # also expose raw landing events via separate field for diagnostics
            fields["landing_chord"] = fields["landing"]
        # interval — prefer validated surface (chronological truth)
        leap_iv = None
        if _surf.is_valid and _surf.interval_semitones is not None:
            leap_iv = _surf.interval_semitones
        if leap_iv is None and leap_comp is not None:
            leap_iv = leap_comp.measurements.get("leap_interval_semitones")
        if leap_iv is None:
            leap_iv = obj.payload.get("movement") or obj.payload.get("movement_semitones") or obj.payload.get("leap_interval_semitones")
        if leap_iv is not None and leap_iv != "?":
            # Use surface event ids for provenance when valid
            if _surf.is_valid:
                iv_event_ids = tuple(_surf.launch_event_ids[:1]) + tuple(_surf.target_event_ids[:1])
                iv_comp_id = None
                iv_comp_type = None
            else:
                iv_event_ids = tuple(launch_events[0].event_id for launch_events in [launch_events] if launch_events) + tuple(target_events[0].event_id for target_events in [target_events] if target_events) if launch_events or target_events else ()
                iv_comp_id = leap_comp.component_id if leap_comp else None
                iv_comp_type = leap_comp.component_type if leap_comp else None
            fields["interval"] = SurfaceField(
                name="leap_interval",
                value=str(leap_iv),
                event_ids=iv_event_ids,
                component_id=iv_comp_id,
                component_type=iv_comp_type,
            )
        # span / count — prefer surface-derived actuals when valid
        if _surf.is_valid and target_events:
            # Compute actual span/count from validated target_events
            mids = sorted([e.pitch_midi for e in target_events if e.pitch_midi is not None])
            if mids:
                actual_span = (max(mids) - min(mids)) if len(mids) >= 2 else 0
                actual_count = len(mids)
                fields["target_span"] = SurfaceField(
                    name="target_span_semitones",
                    value=actual_span,
                    event_ids=tuple(e.event_id for e in target_events),
                    component_id=None,
                    component_type=None,
                    measure_numbers=tuple(target_events[0].measure_number,) if getattr(target_events[0], "measure_number", None) else (),
                )
                fields["chord_note_count"] = SurfaceField(
                    name="chord_note_count",
                    value=actual_count,
                    event_ids=tuple(e.event_id for e in target_events),
                    component_id=None,
                    component_type=None,
                    measure_numbers=tuple(target_events[0].measure_number,) if getattr(target_events[0], "measure_number", None) else (),
                )
        elif span_comp is not None:
            span_val = span_comp.measurements.get("target_span_semitones")
            count_val = span_comp.measurements.get("chord_note_count")
            if span_val is not None:
                fields["target_span"] = SurfaceField(
                    name="target_span_semitones",
                    value=span_val,
                    event_ids=tuple(span_comp.evidence_event_ids),
                    component_id=span_comp.component_id,
                    component_type=span_comp.component_type,
                    measure_numbers=tuple(span_comp.measure_numbers),
                )
            if count_val is not None:
                fields["chord_note_count"] = SurfaceField(
                    name="chord_note_count",
                    value=count_val,
                    event_ids=tuple(span_comp.evidence_event_ids),
                    component_id=span_comp.component_id,
                    component_type=span_comp.component_type,
                    measure_numbers=tuple(span_comp.measure_numbers),
                )
        # duration fields for launch/landing
        if launch_events:
            ev = launch_events[0]
            dt = getattr(ev, "duration_type", None)
            dur = getattr(ev, "duration", None)
            if dt is not None or dur is not None:
                fields["launch_duration"] = SurfaceField(
                    name="launch_duration",
                    value=_duration_str(ev),
                    event_ids=(ev.event_id,),
                    detail=f"duration_type={dt!r} duration={dur!r} tie_merged={getattr(ev,'tie_merged',False)}",
                )
        if target_events:
            ev = target_events[0]
            dt = getattr(ev, "duration_type", None)
            dur = getattr(ev, "duration", None)
            if dt is not None or dur is not None:
                fields["landing_duration"] = SurfaceField(
                    name="landing_duration",
                    value=_duration_str(ev),
                    event_ids=(ev.event_id,),
                    detail=f"duration_type={dt!r} duration={dur!r} tie_merged={getattr(ev,'tie_merged',False)}",
                )

    elif obj.object_id in ("chord_landing", "chordal_homophonic_texture", "melody_embedded_in_chords"):
        # Use same logic as renderer: pick latest onset group
        all_events = _resolve(tuple(obj.evidence_event_ids))
        chord_events: list[Any] = []
        if all_events:
            max_on = max(e.onset for e in all_events)
            chord_events = [e for e in all_events if e.onset == max_on and getattr(e, "pitch_midi", None) is not None]
            if not chord_events:
                chord_events = [e for e in all_events if getattr(e, "pitch_midi", None) is not None]
        chord_name = _format_chord_tones(chord_events) if chord_events else None
        if chord_name is None and "target_chord" in comp_map:
            pm = comp_map["target_chord"].measurements.get("pitch_midi")
            chord_name = _midi_list_to_names_inner(pm) if isinstance(pm, list) else None
        span_comp = comp_map.get("target_span") or comp_map.get("target_chord")
        if chord_name:
            fields["landing"] = SurfaceField(
                name="landing_chord",
                value=chord_name,
                event_ids=tuple(e.event_id for e in chord_events) if chord_events else tuple(comp_map["target_chord"].evidence_event_ids) if "target_chord" in comp_map else (),
                component_id=comp_map["target_chord"].component_id if "target_chord" in comp_map else None,
                component_type=comp_map["target_chord"].component_type if "target_chord" in comp_map else None,
                measure_numbers=tuple(chord_events[0].measure_number,) if chord_events and getattr(chord_events[0], "measure_number", None) else (),
            )
            fields["landing_chord"] = fields["landing"]
        if span_comp is not None:
            span_val = span_comp.measurements.get("target_span_semitones")
            count_val = span_comp.measurements.get("chord_note_count")
            if span_val is not None:
                fields["target_span"] = SurfaceField(
                    name="target_span_semitones",
                    value=span_val,
                    event_ids=tuple(span_comp.evidence_event_ids),
                    component_id=span_comp.component_id,
                    component_type=span_comp.component_type,
                )
            if count_val is not None:
                fields["chord_note_count"] = SurfaceField(
                    name="chord_note_count",
                    value=count_val,
                    event_ids=tuple(span_comp.evidence_event_ids),
                    component_id=span_comp.component_id,
                    component_type=span_comp.component_type,
                )
        if chord_events:
            ev = chord_events[0]
            fields["duration"] = SurfaceField(
                name="duration",
                value=_duration_str(ev),
                event_ids=(ev.event_id,),
                detail=f"duration_type={getattr(ev,'duration_type',None)!r} duration={getattr(ev,'duration',None)!r}",
            )
    elif obj.object_id == "octave_doubled_melody":
        # Provenance: octave count, direction, pitch span, doubling type all tied to evidence
        all_events = _resolve(tuple(obj.evidence_event_ids))
        fields["octave_count"] = SurfaceField(
            name="octave_count",
            value=obj.payload.get("octave_count"),
            event_ids=tuple(obj.evidence_event_ids),
            measure_numbers=tuple(obj.measure_numbers),
            detail=f"direction={obj.payload.get('direction')} doubling_type={obj.payload.get('doubling_type')}",
        )
        fields["direction"] = SurfaceField(
            name="direction",
            value=obj.payload.get("direction"),
            event_ids=tuple(e.event_id for e in all_events[:2]) if all_events else (),
            measure_numbers=tuple(obj.measure_numbers),
        )
        fields["pitch_span"] = SurfaceField(
            name="pitch_span_semitones",
            value=obj.payload.get("pitch_span_semitones") or obj.payload.get("span_semitones"),
            event_ids=tuple(obj.evidence_event_ids),
            measure_numbers=tuple(obj.measure_numbers),
        )
        fields["doubling_type"] = SurfaceField(
            name="doubling_type",
            value=obj.payload.get("doubling_type"),
            event_ids=tuple(obj.evidence_event_ids),
            measure_numbers=tuple(obj.measure_numbers),
            detail=f"is_exact={obj.payload.get('is_exact_doubling')} is_mixed={obj.payload.get('is_mixed')}",
        )
        # Also expose components if present
        for ct, comp in comp_map.items():
            fields[f"component:{ct}"] = SurfaceField(
                name=ct,
                value=comp.measurements,
                event_ids=tuple(comp.evidence_event_ids),
                component_id=comp.component_id,
                component_type=ct,
                measure_numbers=tuple(comp.measure_numbers),
            )

    elif obj.object_id == "single_hand_multi_voice_texture":
        all_events = _resolve(tuple(obj.evidence_event_ids))
        fields["pitch_band_gap"] = SurfaceField(
            name="pitch_band_gap_semitones",
            value=obj.payload.get("pitch_band_gap_semitones"),
            event_ids=tuple(obj.evidence_event_ids),
            measure_numbers=tuple(obj.measure_numbers),
            detail=f"reasons={obj.payload.get('reasons')} ratio={obj.payload.get('duration_ratio')}",
        )
        fields["low_high_ranges"] = SurfaceField(
            name="voice_ranges",
            value={"low": obj.payload.get("low_band_range"), "high": obj.payload.get("high_band_range")},
            event_ids=tuple(e.event_id for e in all_events[:4]) if all_events else (),
            measure_numbers=tuple(obj.measure_numbers),
        )
        for ct, comp in comp_map.items():
            fields[f"component:{ct}"] = SurfaceField(
                name=ct,
                value=comp.measurements,
                event_ids=tuple(comp.evidence_event_ids),
                component_id=comp.component_id,
                component_type=ct,
                measure_numbers=tuple(comp.measure_numbers),
            )

    else:
        # Generic: expose object evidence and component evidence for completeness
        for ct, comp in comp_map.items():
            fields[f"component:{ct}"] = SurfaceField(
                name=ct,
                value=comp.measurements,
                event_ids=tuple(comp.evidence_event_ids),
                component_id=comp.component_id,
                component_type=ct,
                measure_numbers=tuple(comp.measure_numbers),
            )

    return fields


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_local_inspection(
    bundle: SemanticBundle,
    *,
    report_span: tuple[int, int],
    flagged_measures: tuple[str, ...] | list[str] | None = None,
    source_score: str = "unknown",
    max_instruction_units: int = 3,
) -> LocalInspection:
    """Build a Local Semantic Inspection for measures A-B (inclusive).

    Args:
        bundle: SemanticBundle from build_semantic_bundle
        report_span: (A, B) inclusive, 1-indexed score measure numbers
        flagged_measures: subset of measures already flagged as difficult
        source_score: file/asset label (e.g., music/... or evaluation_scores/...)
        max_instruction_units: cap for promoted instruction units (1-3 recommended)
    """
    a, b = report_span
    if a > b:
        a, b = b, a
    flagged_measures = tuple(str(x) for x in (flagged_measures or ()))
    if not flagged_measures:
        # default to report span if not provided
        flagged_measures = tuple(str(x) for x in range(a, b + 1))

    onset_start, onset_end = _onset_bounds_for_span(bundle, a, b)

    # Filter to span — overlap, not strict containment
    # Musical objects
    all_objects: list[MusicalObject] = list(bundle.musical_objects)
    in_span_objects: list[MusicalObject] = [
        o for o in all_objects if _span_intersects_object(o, a, b) or _in_onset_window(o, onset_start, onset_end)
    ]
    # Components (belong to objects, but filter by onset or measure)
    all_components: list[ObjectComponent] = list(bundle.object_components)
    in_span_components: list[ObjectComponent] = [
        c for c in all_components if _span_intersects_object(c, a, b) or _in_onset_window(c, onset_start, onset_end)
    ]
    # Derived tokens
    in_span_tokens = [
        t for t in bundle.derived_tokens if _span_intersects_object(t, a, b) or _in_onset_window(t, onset_start, onset_end)
    ]
    # Gestures
    in_span_gestures = [
        g for g in bundle.gestures if _span_intersects_object(g, a, b) or _in_onset_window(g, onset_start, onset_end)
    ]
    # PracticeChunks
    practice_chunks_all: list[PracticeChunk] = list(getattr(bundle, "practice_chunks", ()) or ())
    in_span_chunks: list[PracticeChunk] = [
        c for c in practice_chunks_all if _span_intersects_object(c, a, b) or _in_onset_window(c, onset_start, onset_end)
    ]

    # Evidence summary
    token_counts = Counter(t.kind for t in in_span_tokens)
    gesture_counts = Counter(g.kind for g in in_span_gestures)
    comp_counts = Counter(c.component_type for c in in_span_components)
    # top components: most frequent component types with example value
    top_comps: list[str] = []
    for ctype, cnt in comp_counts.most_common(3):
        # pick one example measurement value
        example = next((c for c in in_span_components if c.component_type == ctype), None)
        val = ""
        if example and example.measurements:
            # first numeric measurement
            for k, v in example.measurements.items():
                if isinstance(v, (int, float)):
                    val = f"{k}={v}"
                    break
                if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                    val = f"{k}={v[:3]}"
                    break
        top_comps.append(f"{ctype} ×{cnt}" + (f" ({val})" if val else ""))

    chunk_counts = Counter(c.kind for c in in_span_chunks)
    evidence_summary = EvidenceSummary(
        token_kind_counts=dict(token_counts),
        gesture_kind_counts=dict(gesture_counts),
        component_type_counts=dict(comp_counts),
        musical_object_count=len(in_span_objects),
        component_count=len(in_span_components),
        top_components=tuple(top_comps),
        practice_chunk_count=len(in_span_chunks),
        chunk_kind_counts=dict(chunk_counts),
    )

    # ---- Ranking: prefer local overlap, actionable families, tighter span, confidence, diversity ----
    def _overlap_score(o: MusicalObject) -> float:
        # ratio of object measures intersecting report span
        ints = _int_measures(tuple(o.measure_numbers))
        if ints:
            overlap = sum(1 for x in ints if a <= x <= b)
            return overlap / len(ints) if ints else 0.0
        # fallback to onset overlap length vs object length
        # if object width unknown, treat as 1
        if o.start_onset is not None and o.end_onset is not None and onset_start is not None and onset_end is not None:
            obj_len = float(o.end_onset - o.start_onset) if o.end_onset > o.start_onset else 1.0
            # overlap interval
            lo = max(o.start_onset, onset_start)
            hi = min(o.end_onset, onset_end)
            if hi > lo:
                return float(hi - lo) / obj_len if obj_len else 0.0
        return 0.0

    def _is_actionable(o: MusicalObject) -> bool:
        return o.object_id in ACTIONABLE_FAMILIES

    def _is_broad(o: MusicalObject) -> bool:
        if o.object_id in BROAD_FAMILIES:
            return True
        # also broad if spans much larger than report
        if _span_width_measures(o) >= 8:
            return True
        return False

    def _is_left_fast_scalar(o: MusicalObject) -> bool:
        # Left-hand fast directional run should outrank generic leap/chord when present
        if o.object_id in ("ascending_scalar_run", "descending_scalar_run") and o.hand == "left":
            # Fast run flag or dense steps
            if o.payload.get("fast_run"):
                return True
            steps = o.payload.get("steps", 0) or 0
            if steps >= 4 and float(o.confidence) >= 0.70:
                # Also consider notes_per_quarter for fast runs
                if o.payload.get("notes_per_quarter", 0) and float(o.payload.get("notes_per_quarter", 0)) >= 2.5:
                    return True
                # If steps >=4 and not broad, consider it fast scalar
                return True
        return False

    def _is_octave_doubled_salience(o: MusicalObject) -> bool:
        if o.object_id == "octave_doubled_melody":
            cnt = o.payload.get("octave_count", 0) or 0
            if cnt >= 3 and float(o.confidence) >= 0.60:
                return True
            if cnt >= 4:
                return True
        return False

    def _is_multi_voice_salience(o: MusicalObject) -> bool:
        if o.object_id == "single_hand_multi_voice_texture":
            gap = o.payload.get("pitch_band_gap_semitones", 0) or 0
            if gap >= 12 and float(o.confidence) >= 0.60:
                return True
        return False

    def rank_key(o: MusicalObject) -> tuple[Any, ...]:
        overlap = _overlap_score(o)
        actionable = 0 if _is_actionable(o) else 1
        broad = 1 if _is_broad(o) else 0
        width = _span_width_measures(o)
        # Boost left fast scalar so it beats low-confidence leap_to_chord in dense LH passages (mm.27-28)
        left_scalar_boost = -1 if _is_left_fast_scalar(o) else 0
        octave_boost = -1 if _is_octave_doubled_salience(o) else 0
        multi_boost = -0.5 if _is_multi_voice_salience(o) else 0
        # actionable and non-broad first, higher overlap first, tighter width, higher confidence
        # left fast scalar gets extra priority (more negative actionable)
        return (broad, actionable + left_scalar_boost + octave_boost + multi_boost, -overlap, width, -float(o.confidence))

    ranked = sorted(in_span_objects, key=rank_key)

    # Filter out broad from promotion candidates (keep them as broad context only)
    promotion_candidates = [o for o in ranked if not _is_broad(o)]
    # If no actionable non-broad, allow actionable fallback
    if not promotion_candidates:
        promotion_candidates = [o for o in ranked if _is_actionable(o)]
    if not promotion_candidates:
        promotion_candidates = ranked

    # Early event map for validation
    _event_by_id_for_validation: dict[str, Any] = {e.event_id: e for e in bundle.events}

    # Build validated surfaces for promotion candidates (leap_to_chord strict)
    # Track rejected candidates with reason so they never render impossible relationships
    rejected_candidates: list[dict[str, Any]] = []
    validated_candidates: list[MusicalObject] = []
    for o in promotion_candidates:
        if o.object_id in ("leap_to_chord", "chord_landing"):
            # Build surface using in-span components that would be considered for this object
            # Collect related components for this object (strong attachment only) for role-cross check
            _related_for_surface = [c for c in in_span_components if _component_attaches_to_object(c, o)]
            _comp_map_for_surface: dict[str, ObjectComponent] = {}
            for c in _related_for_surface:
                if c.component_type not in _comp_map_for_surface or float(c.confidence) > float(_comp_map_for_surface[c.component_type].confidence):
                    _comp_map_for_surface[c.component_type] = c
            surf = build_validated_instruction_surface(o, _event_by_id_for_validation, selected_components=_comp_map_for_surface if _comp_map_for_surface else None)
            if not surf.is_valid:
                rejected_candidates.append({
                    "object_id": o.object_id,
                    "hand": o.hand,
                    "measure_numbers": list(o.measure_numbers),
                    "evidence_event_ids": list(o.evidence_event_ids),
                    "rejection_reason": surf.rejection_reason,
                    "surface": surf.to_dict(),
                })
                continue
            # Also reject if component evidence would cross roles (surface would have flagged, but double-check)
            # If surface valid, keep candidate
        validated_candidates.append(o)
    promotion_candidates = validated_candidates

    # Promote up to max_instruction_units, preferring distinct object_ids/hand (diversity)
    promoted: list[MusicalObject] = []
    seen_keys: set[tuple[str, str | None]] = set()  # (object_id, hand)
    for o in promotion_candidates:
        if len(promoted) >= max_instruction_units:
            break
        key = (o.object_id, o.hand)
        if key in seen_keys:
            continue
        # also ensure not duplicate onset exact
        if any(o.object_id == p.object_id and o.start_onset == p.start_onset for p in promoted):
            continue
        promoted.append(o)
        seen_keys.add(key)
    # Second pass: fill remaining slots with next best, allowing duplicate family but distinct onset
    if len(promoted) < max_instruction_units:
        for o in promotion_candidates:
            if len(promoted) >= max_instruction_units:
                break
            if any(o.object_id == p.object_id and o.start_onset == p.start_onset and o.hand == p.hand for p in promoted):
                continue
            # allow duplicate family now
            # but still prefer not broad
            promoted.append(o)
            seen_keys.add((o.object_id, o.hand))

    # Build instruction units using instance-specific components + score surface (note names, beats, durations)
    event_by_id: dict[str, Any] = {e.event_id: e for e in bundle.events}
    instruction_units: list[InstructionUnit] = []
    instruction_unit_diagnostics: list[dict[str, Any]] = []
    for idx, obj in enumerate(promoted, start=1):
        related_comps = [c for c in in_span_components if _component_attaches_to_object(c, obj)]
        instr, anatomy, evidence, caveats = _instruction_for_object(obj, in_span_components, event_by_id)
        # _instruction_for_object internally filters again; use related_comps for provenance
        # Build comp_map for diagnostics (same logic as _instruction_for_object)
        comp_map: dict[str, ObjectComponent] = {}
        for c in related_comps:
            if c.component_type not in comp_map or float(c.confidence) > float(comp_map[c.component_type].confidence):
                comp_map[c.component_type] = c
        # Collect surface provenance
        selected_fields = _collect_surface_fields_for_object(obj, comp_map, event_by_id)
        # Run diagnostics — extract rendered values for consistency checks
        # Build args for diagnose_instruction_unit_consistency
        chord_name_val = None
        chord_cnt_val = None
        span_val = None
        leap_val = None
        launch_ids: tuple[str, ...] | None = None
        target_ids: tuple[str, ...] | None = None
        if "landing" in selected_fields:
            chord_name_val = str(selected_fields["landing"].value) if selected_fields["landing"].value is not None else None
            target_ids = tuple(selected_fields["landing"].event_ids)
        if "landing_chord" in selected_fields and chord_name_val is None:
            chord_name_val = str(selected_fields["landing_chord"].value) if selected_fields["landing_chord"].value is not None else None
            target_ids = tuple(selected_fields["landing_chord"].event_ids)
        if "chord_note_count" in selected_fields:
            chord_cnt_val = selected_fields["chord_note_count"].value
        if "target_span" in selected_fields:
            span_val = selected_fields["target_span"].value
        if "interval" in selected_fields:
            leap_val = selected_fields["interval"].value
        if "leap_interval" in selected_fields:
            leap_val = selected_fields["leap_interval"].value
        if "launch" in selected_fields:
            launch_ids = tuple(selected_fields["launch"].event_ids)
        # Also consider landing_duration vs launch_duration for duration checks (handled via target_ids/launch_ids)
        warnings = diagnose_instruction_unit_consistency(
            obj,
            comp_map,
            event_by_id,
            selected_fields,
            chord_name=chord_name_val,
            chord_note_count=chord_cnt_val,
            target_span_semitones=span_val,
            leap_interval_semitones=leap_val,
            launch_event_ids=launch_ids,
            target_event_ids=target_ids,
        )
        # Build validated surface for this promoted unit (chronological truth)
        _surface_for_diag = build_validated_instruction_surface(obj, event_by_id, selected_components=comp_map if comp_map else None)
        # Build diagnostic payload for JSON
        diag_entry: dict[str, Any] = {
            "title": _title_for_object(obj),
            "numbered_title": f"{idx}. {_title_for_object(obj)}",
            "object_id": obj.object_id,
            "object_evidence_event_ids": list(obj.evidence_event_ids),
            "object_gesture_ids": list(obj.gesture_ids),
            "object_token_ids": list(obj.token_ids),
            "object_measures": list(obj.measure_numbers),
            "selected_surface_fields": {k: v.to_dict() for k, v in selected_fields.items()},
            "selected_comp_map": {k: {"component_id": v.component_id, "evidence_event_ids": list(v.evidence_event_ids), "measure_numbers": list(v.measure_numbers), "confidence": v.confidence, "measurements": dict(v.measurements)} for k, v in comp_map.items()},
            "validated_surface": _surface_for_diag.to_dict(),
            "consistency_warnings": warnings,
        }
        instruction_unit_diagnostics.append(diag_entry)
        title = _title_for_object(obj)
        numbered_title = f"{idx}. {title}"
        instruction_units.append(
            InstructionUnit(
                title=numbered_title,
                instruction=instr,
                anatomy=tuple(anatomy),
                evidence=evidence,
                caveats=caveats,
                object_id=obj.object_id,
                component_ids=tuple(c.component_id for c in related_comps),
                evidence_event_ids=tuple(obj.evidence_event_ids),
                measure_numbers=tuple(obj.measure_numbers),
            )
        )

    # Supporting local objects: in-span objects not promoted, but whose span width is local (<= report span width +1)
    report_width = b - a + 1
    supporting: list[LocalObjectCard] = []
    broad: list[BroadObjectCard] = []
    for o in in_span_objects:
        is_promoted = any(o.object_id == p.object_id and o.start_onset == p.start_onset and o.hand == p.hand for p in promoted)
        if is_promoted:
            continue
        width = _span_width_measures(o)
        meas_str = _format_measures_compact(o.measure_numbers) if o.measure_numbers else str(o.measure_start or "?")
        # Broad if spans much larger than report span
        if width > report_width + 2 or width >= 8 or o.object_id in BROAD_FAMILIES:
            # Ensure compressed span used
            broad.append(BroadObjectCard(object_id=o.object_id, span=meas_str, reason=f"span {width} measures exceeds local span {report_width}; piece-level or long gesture"))
            continue
        local_reason = f"local overlap m.{meas_str}, confidence {o.confidence:.2f}, {len(o.evidence_event_ids)} events"
        if o.confidence < 0.6:
            why = "below promotion confidence threshold"
        elif width > report_width:
            why = "span slightly broader than report — useful context but not actionable here"
        else:
            why = "relevant locally but not top-ranked; kept as supporting"
        supporting.append(
            LocalObjectCard(
                object_id=o.object_id,
                label=o.label,
                measures=meas_str,
                local_reason=local_reason,
                why_not_promoted=why,
                confidence=float(o.confidence),
                evidence_event_ids=tuple(o.evidence_event_ids),
            )
        )

    # Build chunk tree mapping for UI helper
    chunk_by_id = {c.chunk_id: c for c in in_span_chunks}
    # Raw evidence (compact but complete for span)
    raw_evidence: dict[str, Any] = {
        "span": f"{a}-{b}",
        "flagged_measures": list(flagged_measures),
        "source_score": source_score,
        "musical_objects": [o.to_dict() for o in in_span_objects],
        "object_components": [c.to_dict() for c in in_span_components],
        "derived_tokens": [t.to_dict() for t in in_span_tokens],
        "gestures": [g.to_dict() for g in in_span_gestures],
        "practice_chunks": [c.to_dict() for c in in_span_chunks],
        "practice_chunk_tree": {cid: {"label": ch.label, "kind": ch.kind, "hand": ch.hand, "child_chunk_ids": list(ch.child_chunk_ids), "parent_chunk_id": ch.parent_chunk_id, "primary_event_ids": list(ch.primary_event_ids), "context_event_ids": list(ch.context_event_ids), "traits": list(ch.traits), "practice_affordances": list(ch.practice_affordances)} for cid, ch in chunk_by_id.items()},
        "instruction_unit_diagnostics": instruction_unit_diagnostics,
        "rejected_instruction_candidates": rejected_candidates,
        "instruction_units": [
            {
                "title": u.title,
                "instruction": u.instruction,
                "object_id": u.object_id,
                "evidence_event_ids": list(u.evidence_event_ids),
                "component_ids": list(u.component_ids),
                "measure_numbers": list(u.measure_numbers),
            }
            for u in instruction_units
        ],
    }

    return LocalInspection(
        report_span=(a, b),
        flagged_measures=tuple(flagged_measures),
        source_score=source_score,
        instruction_units=tuple(instruction_units),
        supporting_local_objects=tuple(supporting),
        broad_context=tuple(broad),
        evidence_summary=evidence_summary,
        raw_evidence=raw_evidence,
        instruction_unit_diagnostics=tuple(instruction_unit_diagnostics),
        rejected_instruction_candidates=tuple(rejected_candidates),
    )


# ---------------------------------------------------------------------------
# Markdown renderer — matches requested template exactly
# ---------------------------------------------------------------------------


def render_markdown(inspection: LocalInspection) -> str:
    a, b = inspection.report_span
    lines: list[str] = []
    lines.append(f"# Local Semantic Inspection: Measures {a}-{b}")
    lines.append("")
    lines.append("## Passage Scope")
    lines.append(f"- Report span: {a}-{b}")
    flagged = ", ".join(inspection.flagged_measures) if inspection.flagged_measures else "—"
    lines.append(f"- Flagged measures: {flagged}")
    lines.append(f"- Source score: {inspection.source_score}")
    lines.append("")
    # Instruction Units
    lines.append("## Instruction Units")
    if inspection.instruction_units:
        for idx, unit in enumerate(inspection.instruction_units):
            lines.append(f"### {unit.title}")
            lines.append(f"{unit.instruction}")
            lines.append("")
            for bullet in unit.anatomy:
                lines.append(f"- {bullet}")
            lines.append(f"- Caveats: {unit.caveats}")
            # Consistency diagnostics — compact per-unit, details in JSON
            diags = inspection.instruction_unit_diagnostics[idx] if idx < len(inspection.instruction_unit_diagnostics) else None  # type: ignore
            if diags and diags.get("consistency_warnings"):
                warnings = diags["consistency_warnings"]
                lines.append(f"- Consistency: {len(warnings)} warning(s) — see JSON diagnostics and details below")
                lines.append("<details>")
                lines.append("<summary>Consistency warnings</summary>")
                lines.append("")
                for w in warnings:
                    code = w.get("code", "unknown")
                    reason = w.get("reason", "")
                    ct = w.get("component_type")
                    ct_str = f" [{ct}]" if ct else ""
                    lines.append(f"  - **{code}**{ct_str}: {reason}")
                lines.append("")
                lines.append("</details>")
            else:
                lines.append("- Consistency: no warnings")
            lines.append("")
    else:
        lines.append("_No promoted instruction unit in this span — see Supporting Local Objects._")
        lines.append("")

    # Supporting Local Objects — grouped view
    lines.append("## Supporting Local Objects")
    if inspection.supporting_local_objects:
        # Group by (object_id, label, hand) derived from local_reason? Use object_id + measures hand approximation
        # Since LocalObjectCard lacks hand, derive hand from label? Instead group by object_id
        groups: dict[tuple[str, str], list[LocalObjectCard]] = defaultdict(list)
        for card in inspection.supporting_local_objects:
            # group key: object_id + label
            key = (card.object_id, card.label)
            groups[key].append(card)
        # Build compact summary rows for groups
        group_rows: list[dict[str, Any]] = []
        for (oid, label), cards in groups.items():
            count = len(cards)
            best_conf = max(c.confidence for c in cards)
            # merge measure coverage
            all_measures: list[str] = []
            for c in cards:
                # c.measures may already be compressed like "8-9" or "8,9" — expand? Keep as raw list
                # For accurate coverage, collect numeric parts
                # We'll parse measures string split by "," and "-" ranges to collect ints
                parts = c.measures.split(",")
                for p in parts:
                    p = p.strip()
                    if "-" in p and " " not in p:
                        # range like "8-9" or "1-72 (72 measures)" — extract first part
                        rng = p.split(" ")[0]
                        try:
                            s, e = rng.split("-")
                            s_i, e_i = int(s), int(e)
                            for v in range(s_i, e_i+1):
                                all_measures.append(str(v))
                        except Exception:
                            all_measures.append(p)
                    else:
                        # handle "(72 measures)" suffix
                        base = p.split(" ")[0]
                        all_measures.append(base)
            coverage = _format_measures_compact(tuple(all_measures)) if all_measures else cards[0].measures
            # why not promoted: most common
            whys = Counter(c.why_not_promoted for c in cards)
            common_why = whys.most_common(1)[0][0]
            group_rows.append({
                "object_id": oid,
                "label": label,
                "count": count,
                "best_conf": best_conf,
                "coverage": coverage,
                "why": common_why,
                "cards": cards,
            })
        # Sort groups by best_conf desc, then count
        group_rows.sort(key=lambda r: (-r["best_conf"], -r["count"]))
        # Cap visible rows to 8
        visible = group_rows[:8]
        hidden = group_rows[8:]

        lines.append(f"_Showing {len(visible)} of {len(group_rows)} object groups (compact). Full details in <details>._")
        lines.append("")
        lines.append("| # | Object | Count | Best conf | Measures | Why not promoted |")
        lines.append("|---|--------|-------|-----------|----------|------------------|")
        for idx, gr in enumerate(visible, start=1):
            label = gr["label"].replace("|", "/")
            lines.append(f"| G{idx} | {gr['object_id']} ({label}) | {gr['count']} | {gr['best_conf']:.2f} | {gr['coverage']} | {gr['why'].replace('|','/')} |")
        lines.append("")
        # Full per-object rows inside details
        lines.append("<details>")
        lines.append("<summary>All supporting objects (ungrouped)</summary>")
        lines.append("")
        lines.append("| # | Object | Measures | Local reason | Why not promoted |")
        lines.append("|---|--------|----------|--------------|------------------|")
        for idx, card in enumerate(inspection.supporting_local_objects, start=1):
            reason = card.local_reason.replace("|", "/")
            why = card.why_not_promoted.replace("|", "/")
            label = card.label.replace("|", "/")
            lines.append(f"| S{idx} | {card.object_id} ({label}) | {card.measures} | {reason} | {why} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        if hidden:
            lines.append(f"_+{len(hidden)} additional groups hidden in full table above; top 8 shown for readability._")
            lines.append("")
    else:
        lines.append("_None — all overlapping local objects were promoted or classified as broad._")
        lines.append("")

    lines.append("## Broad Context / Low Local Specificity")
    if inspection.broad_context:
        lines.append("| Object | Span | Reason for exclusion |")
        lines.append("|--------|------|----------------------|")
        for card in inspection.broad_context:
            lines.append(f"| {card.object_id} | {card.span} | {card.reason} |")
        lines.append("")
    else:
        lines.append("_No broad objects overlapping this span._")
        lines.append("")
        lines.append("| Object | Span | Reason for exclusion |")
        lines.append("|--------|------|----------------------|")
        lines.append("| — | — | no piece-global metric in span; timing/key/dynamics are measure-local here |")
        lines.append("")

    # PracticeChunks section — for UI: icons, highlight primary/context, subchunks, practice actions
    lines.append("## Practice Chunks")
    # raw chunks from raw_evidence (in-span)
    raw_chunks = inspection.raw_evidence.get("practice_chunks", []) if isinstance(inspection.raw_evidence, dict) else []
    if raw_chunks:
        # group by parent
        # build maps
        chunk_map = {c.get("chunk_id"): c for c in raw_chunks}
        top_chunks = [c for c in raw_chunks if not c.get("parent_chunk_id")]
        # if top_chunks empty due to no parent linkage, treat all as top
        if not top_chunks:
            top_chunks = raw_chunks
        lines.append(f"- Practice chunks in span: {len(raw_chunks)} (top-level: {len(top_chunks)})")
        # kinds summary
        kind_counts: dict[str, int] = {}
        for c in raw_chunks:
            kind_counts[c.get("kind", "?")] = kind_counts.get(c.get("kind", "?"), 0) + 1
        if kind_counts:
            kc_str = ", ".join(f"{k}: {v}" for k, v in sorted(kind_counts.items()))
            lines.append(f"- Chunk kinds: {kc_str}")
        lines.append("")
        # Table per chunk (compact)
        lines.append("| Chunk | Kind | Hand | Measures | Primary | Context | Subchunks | Affordances |")
        lines.append("|-------|------|------|----------|---------|---------|-----------|-------------|")
        for ch in sorted(raw_chunks, key=lambda x: (x.get("start_onset", ""), x.get("kind", ""))):
            cid = ch.get("chunk_id", "?")
            kind = ch.get("kind", "?")
            hand = ch.get("hand") or "both"
            meas = ",".join(ch.get("measure_numbers", [])) or "?"
            prim = len(ch.get("primary_event_ids", []))
            ctx = len(ch.get("context_event_ids", []))
            sub = len(ch.get("child_chunk_ids", []))
            aff = ",".join(ch.get("practice_affordances", [])[:3])
            label = ch.get("label", "")
            # escape pipe
            label = label.replace("|", "/")
            lines.append(f"| {cid} ({label}) | {kind} | {hand} | {meas} | {prim} primary | {ctx} context | {sub} | {aff} |")
        lines.append("")
        # Detailed tree for top-level parents
        if top_chunks:
            lines.append("<details>")
            lines.append("<summary>Practice chunk tree (parent → children)</summary>")
            lines.append("")
            for p in sorted(top_chunks, key=lambda x: x.get("start_onset", "")):
                pid = p.get("chunk_id")
                label = p.get("label", "")
                traits = ",".join(p.get("traits", []))
                afford = ",".join(p.get("practice_affordances", []))
                lines.append(f"- **{pid}** ({p.get('kind')}): {label} — traits: {traits or '—'} — affordances: {afford or '—'} — primary: {len(p.get('primary_event_ids', []))} notes, context: {len(p.get('context_event_ids', []))} — children: {', '.join(p.get('child_chunk_ids', [])) or '—'}")
                # show children details
                for cid in p.get("child_chunk_ids", []):
                    child = chunk_map.get(cid)
                    if child:
                        clabel = child.get("label", "")
                        ctrait = ",".join(child.get("traits", []))
                        lines.append(f"  - {cid} ({child.get('kind')}): {clabel} — traits: {ctrait or '—'} — affordances: {','.join(child.get('practice_affordances', []))} — m.{'/'.join(child.get('measure_numbers', []))} primary:{len(child.get('primary_event_ids', []))}")
            lines.append("")
            lines.append("</details>")
            lines.append("")
            lines.append("- Icons: place at `start_onset`/`measure_start` per `kind` mapping (e.g., run→scalar icon, octave→octave icon).")
            lines.append("- Highlight: use `primary_event_ids` for colored notes; `context_event_ids` optionally dimmed.")
            lines.append("- Subchunks: expand via `child_chunk_ids` → isolates `ascent/descent/turn/landing/layer` slices.")
            lines.append("- Practice actions: buttons from `practice_affordances` (e.g., isolate, loop, block, skeletonize, reduce_rhythm, layer_back, hands_separate, add_context).")
            lines.append("")
    else:
        lines.append("_No practice chunks in this span._")
        lines.append("")
    lines.append("## Evidence Summary")
    es = inspection.evidence_summary
    if es.token_kind_counts:
        tok_str = ", ".join(f"{k}: {v}" for k, v in sorted(es.token_kind_counts.items()))
    else:
        tok_str = "0"
    lines.append(f"- Token kind counts: {tok_str}")
    if es.gesture_kind_counts:
        gest_str = ", ".join(f"{k}: {v}" for k, v in sorted(es.gesture_kind_counts.items()))
    else:
        gest_str = "0"
    lines.append(f"- Gesture kind counts: {gest_str}")
    if es.component_type_counts:
        comp_str = ", ".join(f"{k}: {v}" for k, v in sorted(es.component_type_counts.items()))
    else:
        comp_str = "0"
    lines.append(f"- Component type counts: {comp_str}")
    lines.append(f"- Musical objects in span: {es.musical_object_count}")
    lines.append(f"- Components in span: {es.component_count}")
    # practice chunk summary
    if getattr(es, "practice_chunk_count", 0) or getattr(es, "chunk_kind_counts", None):
        lines.append(f"- Practice chunks in span: {getattr(es, 'practice_chunk_count', 0)}")
        if getattr(es, "chunk_kind_counts", None):
            ck_str = ", ".join(f"{k}: {v}" for k, v in sorted(es.chunk_kind_counts.items()))  # type: ignore[union-attr]
            lines.append(f"- Chunk kind counts: {ck_str}")
    if es.top_components:
        lines.append(f"- Top components: {'; '.join(es.top_components)}")
    # Consistency warnings summary (if any)
    total_warnings = sum(len(d.get("consistency_warnings", [])) for d in inspection.instruction_unit_diagnostics) if inspection.instruction_unit_diagnostics else 0
    if total_warnings:
        lines.append(f"- Consistency warnings: {total_warnings} (see Instruction Units and JSON diagnostics)")
    else:
        # also check raw_evidence fallback
        raw_diags = inspection.raw_evidence.get("instruction_unit_diagnostics", []) if isinstance(inspection.raw_evidence, dict) else []
        rw = sum(len(d.get("consistency_warnings", [])) for d in raw_diags) if raw_diags else 0
        if rw:
            lines.append(f"- Consistency warnings: {rw} (see Instruction Units and JSON diagnostics)")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>Raw object/component evidence</summary>")
    lines.append("")
    json_str = json.dumps(inspection.raw_evidence, indent=2, sort_keys=False)
    # Truncate for readability if huge
    max_chars = 12000
    if len(json_str) > max_chars:
        truncated = json_str[:max_chars]
        # try to cut at line boundary
        truncated = truncated.rsplit("\n", 1)[0]
        lines.append(f"_Raw JSON truncated for readability ({len(json_str)} chars total, showing first {max_chars}). Full payload written to sibling .json when generated via script._")
        lines.append("")
        lines.append("```json")
        lines.append(truncated)
        lines.append("... (truncated)")
        lines.append("```")
    else:
        lines.append("```json")
        lines.append(json_str)
        lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return "\n".join(lines)
