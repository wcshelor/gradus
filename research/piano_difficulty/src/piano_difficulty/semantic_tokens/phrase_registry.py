"""Central phrase/template registry for semantic narration.

Phase 5: prototypes polish — one place for learner-facing phrasing templates,
naming conventions, and guardrail constants.  narration.py renders via these
templates; no LLM polishing.

Design goals
- Prefer "left hand"/"right hand"/"both hands" over abbreviations (LH/RH).
- Include measure/beat only when reliable (non-"?" measures).
- Include note names (pitch_name, MIDI) only when evidence supports them;
  default is interval / shape / count, not invented note names.
- No templated claim uses "hard/difficult/challenging" — difficulty framing
  belongs to difficulty_analysis/events.

This module is small and deterministic; tests import registry to assert
snapshot phrasing and guardrails.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Naming — learner-facing hand labels
# ---------------------------------------------------------------------------
HAND_LABELS: dict[str | None, str] = {
    "left": "left hand",
    "right": "right hand",
    "both": "both hands",
    None: "both hands",
}

def format_hand(hand: str | None) -> str:
    """Normalize hand tag to learner-facing label.  Never returns LH/RH."""
    if hand in HAND_LABELS:
        return HAND_LABELS[hand]
    # Defensive: strip abbreviations if upstream ever passes LH/RH
    normalized = str(hand).lower().strip()
    if normalized in ("lh", "l.h.", "l"):
        return "left hand"
    if normalized in ("rh", "r.h.", "r"):
        return "right hand"
    return HAND_LABELS.get(normalized, f"{hand} hand" if hand else "both hands")


def format_other_hand(hand: str | None) -> str:
    """Return the opposite hand label for interaction phrases."""
    if hand == "left":
        return "right hand"
    if hand == "right":
        return "left hand"
    return "other hand"


# ---------------------------------------------------------------------------
# Measure / beat reliability
# ---------------------------------------------------------------------------

def is_measure_reliable(measure_numbers: tuple[str, ...]) -> bool:
    """True iff at least one measure_number is real (not "?" / empty)."""
    for m in measure_numbers:
        if m and m != "?" and m.strip().lower() != "unknown":
            return True
    return False


def measure_clause(measure_numbers: tuple[str, ...], fallback: int | None = None) -> str | None:
    """Return measure text if reliable, else None (caller omits clause)."""
    if is_measure_reliable(measure_numbers):
        # Already sorted/deduped by caller; just join
        return "-".join(str(m) for m in measure_numbers if m and m != "?")
    if fallback is not None:
        try:
            # fallback is numeric measure index; convert to 1-based string only if >0
            if int(fallback) > 0:
                return str(int(fallback))
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Guardrail constants
# ---------------------------------------------------------------------------
# Banned difficulty adjectives in observation text — those claims belong to
# difficulty events (difficulty_analysis/events), not standalone musical facts.
BANNED_DIFFICULTY_WORDS: tuple[str, ...] = (
    "hard",
    "difficult",
    "challenging",
    "demanding",
    "tricky",
    "very hard",
    "very difficult",
)

# Generic labels that must not appear without concrete simultaneous-action evidence.
# If present, observation must cite both hands / simultaneous activity.
GENERIC_LABELS_REQUIRING_CONCRETE: tuple[str, ...] = (
    "hand independence",
    "independence",
    "finger independence",
)

# For validation helpers, we also consider bare "coordination" as generic unless
# paired with concrete action phrasing (e.g., "while the ... continues").
GENERIC_COORDINATION_PHRASE = "coordination"


# ---------------------------------------------------------------------------
# Central template registry
# ---------------------------------------------------------------------------
# Each template uses Python format placeholders rendered by narration.py helpers.
# Templates are concise, learner-facing, and evidence-backed.  Note names
# (pitch_name / MIDI) are only interpolated when payload provides them; otherwise
# the template omits that clause.
#
# Keep keywords stable for snapshot tests: "semitone", "measure", "notes per quarter",
# "expected"/"actual", "pattern", "bass"/"chord", "melody", "wider"/"shape".
PHRASE_TEMPLATES: dict[str, str] = {
    # Single-token observations
    "leap": "The {hand} leaps {abs_interval} semitones {direction} (measure {measure}).",
    # Alternative with note names (only when evidence supports — narration chooses)
    # "leap_with_notes": "The {hand} leaps {abs_interval} semitones {direction} from {from_name} to {to_name} (measure {measure})."
    "density_spike": "Many notes close together — {count} notes per quarter ({hand}, measure {measure}) density {density} notes/quarter.",
    "pattern_break": "Pattern break ({hand}, measure {measure}): expected interval {expected} semitones, actual {actual} semitones, breaking pattern {pattern}.",
    "wide_chord_shape": "The {hand} spans a wider hand shape of {span} semitones (measure {measure}, {shape} with {note_count} notes) — prepare the shape rather than reading isolated notes.",

    # Interaction / gesture observations
    "leap_with_other_hand_active": "The {hand} has a large move of {abs_interval} semitones {direction} (measure {measure}) while the {other_hand} continues, so the landing has to be coordinated without interrupting the line.",
    "bass_to_chord_relocation": "The {hand} moves from a bass note into a chord shape ({chord_shape}, {movement} semitones, measure {measure}) — a quick relocation.",
    "melody_with_accompaniment_voicing": "The right hand carries the melody while the left hand supports it with other notes (measures {measure}) — keep the melody clear instead of playing everything equally.",
    "repeated_pattern_then_break": "A repeated pattern {pattern} changes here ({hand}, measure {measure}, expected {expected} semitones, actual {actual} semitones) — easy to play the expected shape instead of the written one.",

    # Musical object observations (conservative, minimal — rest stay as raw payload)
    "ascending_scalar_run": "Ascending scalar run — stepwise motion upward ({hand}, measure {measure}, {steps} notes) — practice in small groups for evenness.",
    "descending_scalar_run": "Descending scalar run — stepwise motion downward ({hand}, measure {measure}, {steps} notes) — keep the descent controlled and even.",
    "alberti_bass": "Alberti bass pattern in the {hand} (measure {measure}) — broken-chord accompaniment low-high-middle-high — block the harmony first, then rebuild the pattern.",
    "broken_chord_accompaniment": "Broken-chord accompaniment ({hand}, measure {measure}) — chord tones spread over time — block into chords, then practice the broken groups.",
    "arpeggiated_accompaniment": "Arpeggiated accompaniment ({hand}, measure {measure}) — flowing broken chord spanning {span} semitones — practice hand-shape placement in groups.",
    "leap_to_chord": "Leap to chord ({hand}, measure {measure}, {movement} semitones into {chord_shape}) — prepare the landing shape before playing.",
    "syncopation": "Syncopation ({hand}, measure {measure}) — accents or held notes on weak beats — count the pulse and place the off-beat deliberately.",
    "octaves": "Octaves ({hand}, measure {measure}) — octave shapes requiring span and release — practice single line then add the octave.",
}

# For docs / introspection: which kinds are supported by registry
SUPPORTED_TEMPLATE_KINDS: tuple[str, ...] = tuple(PHRASE_TEMPLATES.keys()) + ("leap", "density_spike", "pattern_break")


# ---------------------------------------------------------------------------
# Validation helpers (exported for tests to assert guardrails)
# ---------------------------------------------------------------------------

def contains_banned_difficulty_claim(text: str) -> bool:
    lower = text.lower()
    for word in BANNED_DIFFICULTY_WORDS:
        # word-boundary check: ensure standalone adjective, not "hard" inside other word
        # Simple: check padded spaces / punctuation around.
        if f" {word} " in f" {lower} " or f" {word}," in f" {lower} " or f" {word}." in f" {lower} ":
            return True
        # also check exact word surrounded by punctuation
        # fallback: substring for multi-word banned like "very hard"
        if word in lower:
            # for single words, verify token boundary
            import re

            if re.search(rf"\b{re.escape(word)}\b", lower):
                return True
    return False


def contains_generic_label_without_concrete(text: str, has_concrete_simultaneous: bool = False, **kwargs) -> bool:  # type: ignore[no-untyped-def]
    """True iff text uses a generic label but lacks concrete simultaneous-action evidence.

    Concrete simultaneous evidence = mentions both hands / "while the ... continues"
    or similar; caller passes flag computed from evidence_event_ids / hand coverage.
    """
    # Backward compat: allow has_concrete alias (tests misuse keyword)
    if "has_concrete" in kwargs:
        has_concrete_simultaneous = bool(kwargs["has_concrete"])
    lower = text.lower()
    for label in GENERIC_LABELS_REQUIRING_CONCRETE:
        if label in lower and not has_concrete_simultaneous:
            return True
    # Special case: bare "coordination" without "while" / both-hand mention is generic
    if GENERIC_COORDINATION_PHRASE in lower:
        if not has_concrete_simultaneous:
            # Allow "coordinated" inside leap_with_other_hand_active which is concrete
            if "while the" not in lower or ("left" not in lower and "right" not in lower):
                # For leap_with_other_hand_active the template already contains both + while,
                # so has_concrete would be True.  Otherwise flag.
                return True
    return False


def has_concrete_simultaneous_evidence(text: str, evidence_hand_coverage: set[str] | None = None) -> bool:
    """Heuristic: does text cite concrete simultaneous actions?"""
    lower = text.lower()
    has_both_hands = "left" in lower and "right" in lower
    has_while_continues = "while the" in lower and "continues" in lower
    has_while_supports = "while the" in lower and ("supports" in lower or "carries" in lower)
    if evidence_hand_coverage is not None:
        if {"left", "right"}.issubset(evidence_hand_coverage):
            return True
    return has_both_hands or has_while_continues or has_while_supports
