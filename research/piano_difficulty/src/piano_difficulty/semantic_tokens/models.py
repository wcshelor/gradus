"""Models for the semantic token layer.

Inspired by mxltoolbox.core.events.EVENT_COLUMNS but adapted to ScoreIR
naming and provenance guarantees. Does not copy implementation; licensing
of musicology-toolbox is unclear/unstable so ideas are re-implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

# Local column naming — stable, ScoreIR-aligned. Mirrors the intent of
# mxltoolbox EVENT_COLUMNS (measure, beat, staff, voice, onset/end,
# duration, pitch, chord/rest flags, ties, dynamics, harmony, key/time,
# articulation) but uses Fraction-based timing and explicit provenance.
LOCAL_EVENT_COLUMNS = [
    "event_id",
    "score_id",
    "measure_index",
    "measure_number",
    "staff",
    "voice",
    "hand",
    "hand_confidence",
    "beat",
    "offset_quarter",
    "duration_quarter",
    "onset",
    "end",
    "is_rest",
    "is_chord_tone",
    "chord_id",
    "pitch_midi",
    "pitch_name",
    "pitch_class",
    "octave",
    "accidental",
    "alter",
    "tie_merged",
    "source_note_ids",
    "xml_order",
    "measure_staff_order",
    "is_grace",
    "duration_type",
    "key_signature",
    "time_signature",
    "clef",
    "tempo_bpm",
    "dynamics",
    "articulation",
    "tuplet",
    "is_arpeggiated",
    "has_slur_start",
    "has_slur_stop",
    "phrase_start",
    "phrase_stop",
]

DERIVED_TOKEN_KINDS = (
    "melodic_interval",
    "harmonic_simultaneity",
    "hand_movement",
    "leap",
    "repeated_note",
    "density_spike",
    "register_shift",
    "onset_alignment",
    "chord_shape",
    "pattern_repetition",
    "pattern_break",
)

GESTURE_KINDS = (
    "bass_to_chord",
    "melody_with_accompaniment",
    "block_chord_landing",
    "arpeggio",
    "scalar_run",
    "repeated_note_figure",
    "cadence_like_arrival",
    "accompaniment_pattern",
)

# ---------------------------------------------------------------------------
# Expanded musical object catalog — 56 stable IDs (54 as catalog.md + 2 for octave/multi-voice textures)
# (catalog.md contains 54 headings; plan states 53 but file shows 54; extended with octave_doubled_melody, single_hand_multi_voice_texture)
# ---------------------------------------------------------------------------

CATALOG_OBJECT_IDS: tuple[str, ...] = (
    # Melodic (9)
    "ascending_scalar_run",
    "descending_scalar_run",
    "stepwise_melody",
    "intervallic_melody",
    "sequence",
    "repeated_note_melody",
    "ornamented_melody",
    "chromatic_line",
    "turn_mordent_trill_like_figure",
    # Accompaniment (9)
    "alberti_bass",
    "broken_chord_accompaniment",
    "waltz_bass",
    "oom_pah_bass_chord_pattern",
    "repeated_chord_accompaniment",
    "arpeggiated_accompaniment",
    "left_hand_stride_like_motion",
    "pedal_point_accompaniment",
    "tremolo_accompaniment",
    # Texture / Layer (10)
    "melody_with_accompaniment",
    "two_voice_counterpoint",
    "inner_voice_movement",
    "chordal_homophonic_texture",
    "parallel_thirds",
    "parallel_sixths",
    "octaves",
    "octave_doubled_melody",
    "single_hand_multi_voice_texture",
    "hand_to_hand_imitation",
    "call_and_response",
    "melody_embedded_in_chords",
    # Physical Gesture (9)
    "leap_to_chord",
    "chord_landing",
    "hand_shift",
    "hand_expansion_contraction",
    "thumb_under_scale_passage",
    "repeated_finger_substitution_candidate",
    "wide_broken_chord",
    "repeated_position_pattern",
    "awkward_redistribution_cross_staff_passage",
    # Rhythmic / Coordination (9)
    "syncopation",
    "dotted_rhythm",
    "offbeat_accompaniment",
    "polyrhythm",
    "hand_alternation",
    "contrary_rhythmic_layers",
    "tied_over_barline_pattern",
    "repeated_rhythm_cell",
    "rhythm_pattern_break",
    # Expression / Control (8)
    "melody_voicing_over_accompaniment",
    "legato_with_detached_accompaniment",
    "dynamic_swell_across_phrase",
    "accent_pattern",
    "articulation_contrast_between_hands",
    "balance_between_voices",
    "cantabile_line",
    "phrase_shaping_over_repeated_pattern",
)

OBJECT_LABELS: dict[str, str] = {
    "ascending_scalar_run": "Ascending scalar run",
    "descending_scalar_run": "Descending scalar run",
    "stepwise_melody": "Stepwise melody",
    "intervallic_melody": "Intervallic melody",
    "sequence": "Sequence",
    "repeated_note_melody": "Repeated-note melody",
    "ornamented_melody": "Ornamented melody",
    "chromatic_line": "Chromatic line",
    "turn_mordent_trill_like_figure": "Turn/mordent/trill-like figure",
    "alberti_bass": "Alberti bass",
    "broken_chord_accompaniment": "Broken-chord accompaniment",
    "waltz_bass": "Waltz bass",
    "oom_pah_bass_chord_pattern": "Oom-pah bass-chord pattern",
    "repeated_chord_accompaniment": "Repeated chord accompaniment",
    "arpeggiated_accompaniment": "Arpeggiated accompaniment",
    "left_hand_stride_like_motion": "Left-hand stride-like motion",
    "pedal_point_accompaniment": "Pedal-point accompaniment",
    "tremolo_accompaniment": "Tremolo accompaniment",
    "melody_with_accompaniment": "Melody with accompaniment",
    "two_voice_counterpoint": "Two-voice counterpoint",
    "inner_voice_movement": "Inner-voice movement",
    "chordal_homophonic_texture": "Chordal homophonic texture",
    "parallel_thirds": "Parallel thirds",
    "parallel_sixths": "Parallel sixths",
    "octaves": "Octaves",
    "octave_doubled_melody": "Octave-doubled melody",
    "single_hand_multi_voice_texture": "Single-hand multi-voice texture",
    "hand_to_hand_imitation": "Hand-to-hand imitation",
    "call_and_response": "Call and response",
    "melody_embedded_in_chords": "Melody embedded in chords",
    "leap_to_chord": "Leap to chord",
    "chord_landing": "Chord landing",
    "hand_shift": "Hand shift",
    "hand_expansion_contraction": "Hand expansion/contraction",
    "thumb_under_scale_passage": "Thumb-under scale passage",
    "repeated_finger_substitution_candidate": "Repeated finger substitution candidate",
    "wide_broken_chord": "Wide broken chord",
    "repeated_position_pattern": "Repeated position pattern",
    "awkward_redistribution_cross_staff_passage": "Awkward redistribution / cross-staff passage",
    "syncopation": "Syncopation",
    "dotted_rhythm": "Dotted rhythm",
    "offbeat_accompaniment": "Offbeat accompaniment",
    "polyrhythm": "Polyrhythm",
    "hand_alternation": "Hand alternation",
    "contrary_rhythmic_layers": "Contrary rhythmic layers",
    "tied_over_barline_pattern": "Tied-over-barline pattern",
    "repeated_rhythm_cell": "Repeated rhythm cell",
    "rhythm_pattern_break": "Rhythm pattern break",
    "melody_voicing_over_accompaniment": "Melody voicing over accompaniment",
    "legato_with_detached_accompaniment": "Legato with detached accompaniment",
    "dynamic_swell_across_phrase": "Dynamic swell across phrase",
    "accent_pattern": "Accent pattern",
    "articulation_contrast_between_hands": "Articulation contrast between hands",
    "balance_between_voices": "Balance between voices",
    "cantabile_line": "Cantabile line",
    "phrase_shaping_over_repeated_pattern": "Phrase shaping over repeated pattern",
}

# Related difficulty dimensions (front_facing IDs, not redefined)
OBJECT_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "ascending_scalar_run": ("finger_dexterity", "hand_movement_position"),
    "descending_scalar_run": ("finger_dexterity", "hand_movement_position"),
    "stepwise_melody": ("finger_dexterity", "expression_sound_control"),
    "intervallic_melody": ("hand_movement_position", "notation_reading"),
    "sequence": ("notation_reading", "finger_dexterity"),
    "repeated_note_melody": ("finger_dexterity", "rhythm_timing"),
    "ornamented_melody": ("finger_dexterity", "rhythm_timing"),
    "chromatic_line": ("notation_reading", "finger_dexterity"),
    "turn_mordent_trill_like_figure": ("finger_dexterity", "rhythm_timing"),
    "alberti_bass": ("hand_movement_position", "finger_dexterity", "layers_coordination"),
    "broken_chord_accompaniment": ("hand_movement_position", "finger_dexterity"),
    "waltz_bass": ("hand_movement_position", "rhythm_timing"),
    "oom_pah_bass_chord_pattern": ("hand_movement_position", "rhythm_timing"),
    "repeated_chord_accompaniment": ("hand_movement_position", "rhythm_timing", "finger_dexterity"),
    "arpeggiated_accompaniment": ("hand_movement_position", "finger_dexterity"),
    "left_hand_stride_like_motion": ("hand_movement_position", "rhythm_timing"),
    "pedal_point_accompaniment": ("hand_movement_position", "layers_coordination", "expression_sound_control"),
    "tremolo_accompaniment": ("finger_dexterity", "hand_movement_position", "expression_sound_control"),
    "melody_with_accompaniment": ("layers_coordination", "expression_sound_control"),
    "two_voice_counterpoint": ("layers_coordination", "notation_reading"),
    "inner_voice_movement": ("layers_coordination", "expression_sound_control", "notation_reading"),
    "chordal_homophonic_texture": ("hand_movement_position", "expression_sound_control"),
    "parallel_thirds": ("finger_dexterity", "hand_movement_position"),
    "parallel_sixths": ("hand_movement_position", "finger_dexterity"),
    "octaves": ("hand_movement_position", "finger_dexterity"),
    "octave_doubled_melody": ("hand_movement_position", "finger_dexterity", "expression_sound_control"),
    "single_hand_multi_voice_texture": ("layers_coordination", "hand_movement_position", "expression_sound_control"),
    "hand_to_hand_imitation": ("layers_coordination", "notation_reading"),
    "call_and_response": ("layers_coordination", "expression_sound_control"),
    "melody_embedded_in_chords": ("hand_movement_position", "expression_sound_control", "notation_reading"),
    "leap_to_chord": ("hand_movement_position", "rhythm_timing"),
    "chord_landing": ("hand_movement_position", "rhythm_timing"),
    "hand_shift": ("hand_movement_position", "finger_dexterity"),
    "hand_expansion_contraction": ("hand_movement_position", "finger_dexterity"),
    "thumb_under_scale_passage": ("finger_dexterity", "hand_movement_position"),
    "repeated_finger_substitution_candidate": ("finger_dexterity", "expression_sound_control"),
    "wide_broken_chord": ("hand_movement_position", "finger_dexterity"),
    "repeated_position_pattern": ("finger_dexterity", "notation_reading"),
    "awkward_redistribution_cross_staff_passage": ("notation_reading", "layers_coordination", "hand_movement_position"),
    "syncopation": ("rhythm_timing", "layers_coordination"),
    "dotted_rhythm": ("rhythm_timing", "finger_dexterity"),
    "offbeat_accompaniment": ("rhythm_timing", "layers_coordination"),
    "polyrhythm": ("rhythm_timing", "layers_coordination"),
    "hand_alternation": ("layers_coordination", "rhythm_timing"),
    "contrary_rhythmic_layers": ("layers_coordination", "rhythm_timing"),
    "tied_over_barline_pattern": ("rhythm_timing", "notation_reading"),
    "repeated_rhythm_cell": ("rhythm_timing", "finger_dexterity"),
    "rhythm_pattern_break": ("rhythm_timing", "notation_reading"),
    "melody_voicing_over_accompaniment": ("expression_sound_control", "layers_coordination"),
    "legato_with_detached_accompaniment": ("expression_sound_control", "layers_coordination"),
    "dynamic_swell_across_phrase": ("expression_sound_control", "rhythm_timing"),
    "accent_pattern": ("expression_sound_control", "rhythm_timing"),
    "articulation_contrast_between_hands": ("expression_sound_control", "layers_coordination"),
    "balance_between_voices": ("expression_sound_control", "layers_coordination"),
    "cantabile_line": ("expression_sound_control", "hand_movement_position"),
    "phrase_shaping_over_repeated_pattern": ("expression_sound_control", "finger_dexterity"),
}

# Exercise hints / caveat templates (doc-driven, not yet executable)
OBJECT_CATALOG: dict[str, dict] = {
    oid: {
        "label": OBJECT_LABELS[oid],
        "related_dimensions": OBJECT_DIMENSIONS[oid],
        "exercise_hints": [],
        "caveat_templates": [],
    }
    for oid in CATALOG_OBJECT_IDS
}
# Populate a few representative hints (kept minimal, doc-driven)
OBJECT_CATALOG["ascending_scalar_run"]["exercise_hints"] = ["slow rhythmic variants", "hand-alone practice", "grouped scale fragments"]
OBJECT_CATALOG["alberti_bass"]["exercise_hints"] = ["block the harmony", "bass anchors only", "transpose the pattern"]
OBJECT_CATALOG["melody_with_accompaniment"]["exercise_hints"] = ["melody alone", "ghosted accompaniment", "layered rebuild"]
OBJECT_CATALOG["syncopation"]["exercise_hints"] = ["clap pulse", "tap strong beats while playing syncopation"]
OBJECT_CATALOG["polyrhythm"]["exercise_hints"] = ["tap each layer", "map composite rhythm"]
OBJECT_CATALOG["thumb_under_scale_passage"]["caveat_templates"] = ["fingering_not_in_score", "hand_position_inferred_from_span"]
OBJECT_CATALOG["turn_mordent_trill_like_figure"]["caveat_templates"] = ["no_explicit_ornament_marking", "heuristic_neighbor_motion_only"]


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    """One normalized score row — note or rest — with provenance."""

    event_id: str
    score_id: str | None
    measure_index: int | None
    measure_number: str | None
    staff: int | None
    voice: str | None
    hand: str | None
    hand_confidence: str | None
    beat: Fraction | None  # offset inside measure
    offset_quarter: float | None
    duration_quarter: float | None
    onset: Fraction
    end: Fraction
    duration: Fraction
    is_rest: bool
    is_chord_tone: bool
    chord_id: str | None
    pitch_midi: int | None
    pitch_name: str | None
    pitch_class: int | None
    octave: int | None
    accidental: str | None
    alter: int | None
    tie_merged: bool
    source_note_ids: tuple[str, ...]
    xml_order: int | None
    measure_staff_order: int | None
    is_grace: bool
    duration_type: str | None
    key_signature: str | None
    time_signature: str | None
    clef: str | None
    tempo_bpm: float | None
    dynamics: str | None
    articulation: tuple[str, ...]
    tuplet: str | None
    is_arpeggiated: bool = False
    has_slur_start: bool = False
    has_slur_stop: bool = False
    phrase_start: bool = False
    phrase_stop: bool = False
    # extra provenance for debugging
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "score_id": self.score_id,
            "measure_index": self.measure_index,
            "measure_number": self.measure_number,
            "staff": self.staff,
            "voice": self.voice,
            "hand": self.hand,
            "hand_confidence": self.hand_confidence,
            "beat": str(self.beat) if self.beat is not None else None,
            "offset_quarter": self.offset_quarter,
            "duration_quarter": self.duration_quarter,
            "onset": str(self.onset),
            "end": str(self.end),
            "duration": str(self.duration),
            "is_rest": self.is_rest,
            "is_chord_tone": self.is_chord_tone,
            "chord_id": self.chord_id,
            "pitch_midi": self.pitch_midi,
            "pitch_name": self.pitch_name,
            "pitch_class": self.pitch_class,
            "octave": self.octave,
            "accidental": self.accidental,
            "alter": self.alter,
            "tie_merged": self.tie_merged,
            "source_note_ids": list(self.source_note_ids),
            "xml_order": self.xml_order,
            "measure_staff_order": self.measure_staff_order,
            "is_grace": self.is_grace,
            "duration_type": self.duration_type,
            "key_signature": self.key_signature,
            "time_signature": self.time_signature,
            "clef": self.clef,
            "tempo_bpm": self.tempo_bpm,
            "dynamics": self.dynamics,
            "articulation": list(self.articulation),
            "tuplet": self.tuplet,
            "is_arpeggiated": bool(self.is_arpeggiated),
            "has_slur_start": bool(self.has_slur_start),
            "has_slur_stop": bool(self.has_slur_stop),
            "phrase_start": bool(self.phrase_start),
            "phrase_stop": bool(self.phrase_stop),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True, slots=True)
class DerivedToken:
    """A semantic token derived from the normalized event table."""

    token_id: str
    kind: str
    hand: str | None
    staff: int | None
    start_onset: Fraction
    end_onset: Fraction
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    confidence: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "kind": self.kind,
            "hand": self.hand,
            "staff": self.staff,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "evidence_event_ids": list(self.evidence_event_ids),
            "confidence": self.confidence,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class Gesture:
    """A grouped musical gesture built from derived tokens."""

    gesture_id: str
    kind: str
    hand: str | None
    start_onset: Fraction
    end_onset: Fraction
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...]
    token_ids: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    confidence: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gesture_id": self.gesture_id,
            "kind": self.kind,
            "hand": self.hand,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "token_ids": list(self.token_ids),
            "evidence_event_ids": list(self.evidence_event_ids),
            "confidence": self.confidence,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class MusicalObject:
    """Typed, serializable musical object from expanded catalog.

    Keeps DerivedToken/Gesture untouched for backward compat.
    """

    object_id: str  # stable catalog ID e.g. "alberti_bass"
    kind: str  # alias = object_id (for Gesture parity)
    label: str  # e.g. "Alberti bass"
    hand: str | None
    start_onset: Fraction
    end_onset: Fraction
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]  # required, never empty when emitted
    token_ids: tuple[str, ...]
    gesture_ids: tuple[str, ...]
    confidence: float  # 0..1 heuristic confidence
    payload: dict[str, Any] = field(default_factory=dict)  # detector specifics + related_dimensions + detection_heuristic id
    caveats: tuple[str, ...] = ()  # e.g. "heuristic_only_no_fingering", "no_explicit_marking"

    def __post_init__(self) -> None:
        if self.object_id not in CATALOG_OBJECT_IDS:
            raise ValueError(f"unknown object_id {self.object_id!r}")
        if not self.evidence_event_ids:
            raise ValueError("evidence_event_ids must be non-empty")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be in [0,1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "kind": self.kind,
            "label": self.label,
            "hand": self.hand,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "evidence_event_ids": list(self.evidence_event_ids),
            "token_ids": list(self.token_ids),
            "gesture_ids": list(self.gesture_ids),
            "confidence": float(self.confidence),
            "payload": dict(self.payload),
            "caveats": list(self.caveats),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MusicalObject:
        def _frac(v: Any) -> Fraction:
            return Fraction(str(v))

        return cls(
            object_id=str(data["object_id"]),
            kind=str(data.get("kind", data["object_id"])),
            label=str(data.get("label", OBJECT_LABELS.get(str(data["object_id"]), str(data["object_id"])))),
            hand=data.get("hand"),
            start_onset=_frac(data["start_onset"]),
            end_onset=_frac(data["end_onset"]),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            measure_numbers=tuple(str(x) for x in data.get("measure_numbers", [])),
            evidence_event_ids=tuple(str(x) for x in data.get("evidence_event_ids", [])),
            token_ids=tuple(str(x) for x in data.get("token_ids", [])),
            gesture_ids=tuple(str(x) for x in data.get("gesture_ids", [])),
            confidence=float(data.get("confidence", 0.0)),
            payload=dict(data.get("payload", {})),
            caveats=tuple(str(x) for x in data.get("caveats", [])),
        )


@dataclass(frozen=True, slots=True)
class ObjectComponent:
    """Typed musical object component — internal trait of a MusicalObject.

    Deterministic, evidence-backed. Each component isolates a single trait
    (e.g., interval_path, harmonic_collection) for practice targeting.
    """

    component_id: str
    component_type: str
    parent_object_id: str  # object_id of parent MusicalObject
    parent_object_kind: str  # alias for parent_object_id
    label: str
    hand: str | None
    role: str | None
    start_onset: Fraction
    end_onset: Fraction
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...]
    beat_start: Fraction | None
    beat_end: Fraction | None
    evidence_event_ids: tuple[str, ...]
    token_ids: tuple[str, ...]
    gesture_ids: tuple[str, ...]
    confidence: float
    measurements: dict[str, Any] = field(default_factory=dict)
    related_dimensions: tuple[str, ...] = ()
    practice_implications: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.component_id:
            raise ValueError("component_id must be non-empty")
        if not self.component_type:
            raise ValueError("component_type must be non-empty")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be in [0,1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "parent_object_id": self.parent_object_id,
            "parent_object_kind": self.parent_object_kind,
            "label": self.label,
            "hand": self.hand,
            "role": self.role,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "beat_start": str(self.beat_start) if self.beat_start is not None else None,
            "beat_end": str(self.beat_end) if self.beat_end is not None else None,
            "evidence_event_ids": list(self.evidence_event_ids),
            "token_ids": list(self.token_ids),
            "gesture_ids": list(self.gesture_ids),
            "confidence": float(self.confidence),
            "measurements": dict(self.measurements),
            "related_dimensions": list(self.related_dimensions),
            "practice_implications": list(self.practice_implications),
            "caveats": list(self.caveats),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectComponent:
        def _frac(v: Any) -> Fraction | None:
            if v is None:
                return None
            return Fraction(str(v))

        return cls(
            component_id=str(data["component_id"]),
            component_type=str(data["component_type"]),
            parent_object_id=str(data.get("parent_object_id") or data.get("parent_object_kind") or data.get("object_id") or ""),
            parent_object_kind=str(data.get("parent_object_kind") or data.get("parent_object_id") or data.get("object_id") or ""),
            label=str(data.get("label", data["component_type"])),
            hand=data.get("hand"),
            role=data.get("role"),
            start_onset=Fraction(str(data["start_onset"])),
            end_onset=Fraction(str(data["end_onset"])),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            measure_numbers=tuple(str(x) for x in data.get("measure_numbers", [])),
            beat_start=_frac(data.get("beat_start")),
            beat_end=_frac(data.get("beat_end")),
            evidence_event_ids=tuple(str(x) for x in data.get("evidence_event_ids", [])),
            token_ids=tuple(str(x) for x in data.get("token_ids", [])),
            gesture_ids=tuple(str(x) for x in data.get("gesture_ids", [])),
            confidence=float(data.get("confidence", 0.0)),
            measurements=dict(data.get("measurements", {})),
            related_dimensions=tuple(str(x) for x in data.get("related_dimensions", [])),
            practice_implications=tuple(str(x) for x in data.get("practice_implications", [])),
            caveats=tuple(str(x) for x in data.get("caveats", [])),
        )


@dataclass(frozen=True, slots=True)
class MicroMoment:
    """Tiny difficult moment inside a hotspot — groups nearby components."""

    moment_id: str
    label: str
    start_onset: Fraction
    end_onset: Fraction
    measure_numbers: tuple[str, ...]
    beat_start: Fraction | None
    beat_end: Fraction | None
    musical_object_ids: tuple[str, ...]
    component_ids: tuple[str, ...]
    primary_component_types: tuple[str, ...]
    related_dimensions: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    confidence: float
    summary: str
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.moment_id:
            raise ValueError("moment_id must be non-empty")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be in [0,1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "moment_id": self.moment_id,
            "label": self.label,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_numbers": list(self.measure_numbers),
            "beat_start": str(self.beat_start) if self.beat_start is not None else None,
            "beat_end": str(self.beat_end) if self.beat_end is not None else None,
            "musical_object_ids": list(self.musical_object_ids),
            "component_ids": list(self.component_ids),
            "primary_component_types": list(self.primary_component_types),
            "related_dimensions": list(self.related_dimensions),
            "evidence_event_ids": list(self.evidence_event_ids),
            "confidence": float(self.confidence),
            "summary": self.summary,
            "caveats": list(self.caveats),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MicroMoment:
        def _frac(v: Any) -> Fraction | None:
            if v is None:
                return None
            return Fraction(str(v))

        return cls(
            moment_id=str(data["moment_id"]),
            label=str(data.get("label", data["moment_id"])),
            start_onset=Fraction(str(data["start_onset"])),
            end_onset=Fraction(str(data["end_onset"])),
            measure_numbers=tuple(str(x) for x in data.get("measure_numbers", [])),
            beat_start=_frac(data.get("beat_start")),
            beat_end=_frac(data.get("beat_end")),
            musical_object_ids=tuple(str(x) for x in data.get("musical_object_ids", [])),
            component_ids=tuple(str(x) for x in data.get("component_ids", [])),
            primary_component_types=tuple(str(x) for x in data.get("primary_component_types", [])),
            related_dimensions=tuple(str(x) for x in data.get("related_dimensions", [])),
            evidence_event_ids=tuple(str(x) for x in data.get("evidence_event_ids", [])),
            confidence=float(data.get("confidence", 0.0)),
            summary=str(data.get("summary", "")),
            caveats=tuple(str(x) for x in data.get("caveats", [])),
        )


# ---------------------------------------------------------------------------
# PracticeChunk — musically coherent unit for practice (LLM/UI/generation)
# ---------------------------------------------------------------------------

CHUNK_KINDS: tuple[str, ...] = (
    "phrase",
    "run",
    "arpeggio_sweep",
    "ascent",
    "descent",
    "turn",
    "landing",
    "leap",
    "chord_shape",
    "layered_texture",
    "layer",
    "octave_doubled_melody",
    "octave_doubled_run",
    "coordination",
    "scalar_run",
    "arpeggio",
    "single_hand_multi_voice",
    "chordal_texture",
    "hand_stream",
    "passage",
    "cell",
    "reset",
)

CHUNK_LABELS: dict[str, str] = {
    "phrase": "Phrase",
    "run": "Run",
    "arpeggio_sweep": "Arpeggio sweep",
    "ascent": "Ascent",
    "descent": "Descent",
    "turn": "Turn",
    "landing": "Landing",
    "leap": "Leap",
    "chord_shape": "Chord shape",
    "layered_texture": "Layered texture",
    "layer": "Layer",
    "octave_doubled_melody": "Octave-doubled melody",
    "octave_doubled_run": "Octave-doubled run",
    "coordination": "Coordination",
    "scalar_run": "Scalar run",
    "arpeggio": "Arpeggio",
    "single_hand_multi_voice": "Single-hand multi-voice",
    "chordal_texture": "Chordal texture",
    "hand_stream": "Hand stream",
    "passage": "Passage",
    "cell": "Cell",
    "reset": "Reset",
}

# Valid practice affordances (deterministic vocabulary for UI/generation)
PRACTICE_AFFORDANCES: tuple[str, ...] = (
    "isolate",
    "loop",
    "split_ascent_descent",
    "split_contour",
    "block",
    "skeletonize",
    "reduce_rhythm",
    "layer_back",
    "hands_separate",
    "add_context",
    "transpose",
    "ghost_accompaniment",
    "progressive_layer_rebuild",
    "keep_rhythm_simplify_pitch",
    "keep_pitch_contour_simplify_intervals",
    "block_chords",
    "roll_evenly",
    "block_then_roll",
    "shape_dynamics",
    "isolate_hands",
    "hands_together",
)


@dataclass(frozen=True, slots=True)
class PracticeChunk:
    """Musically coherent unit a pianist can name, highlight, isolate, subdivide."""

    chunk_id: str
    kind: str
    label: str
    hand: str | None
    voice: str | None
    role: str | None
    staff: int | None
    start_onset: Fraction
    end_onset: Fraction
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...]
    beat_start: Fraction | None
    beat_end: Fraction | None
    primary_event_ids: tuple[str, ...]
    context_event_ids: tuple[str, ...]
    child_chunk_ids: tuple[str, ...]
    parent_chunk_id: str | None
    source_object_ids: tuple[str, ...]
    source_feature_refs: tuple[str, ...]  # token_ids / gesture_ids
    traits: tuple[str, ...]
    practice_affordances: tuple[str, ...]
    confidence: float
    caveats: tuple[str, ...]
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raise ValueError("chunk_id must be non-empty")
        if not self.kind:
            raise ValueError("kind must be non-empty")
        if not self.primary_event_ids:
            raise ValueError("primary_event_ids must be non-empty")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be in [0,1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "kind": self.kind,
            "label": self.label,
            "hand": self.hand,
            "voice": self.voice,
            "role": self.role,
            "staff": self.staff,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "beat_start": str(self.beat_start) if self.beat_start is not None else None,
            "beat_end": str(self.beat_end) if self.beat_end is not None else None,
            "primary_event_ids": list(self.primary_event_ids),
            "context_event_ids": list(self.context_event_ids),
            "child_chunk_ids": list(self.child_chunk_ids),
            "parent_chunk_id": self.parent_chunk_id,
            "source_object_ids": list(self.source_object_ids),
            "source_feature_refs": list(self.source_feature_refs),
            "traits": list(self.traits),
            "practice_affordances": list(self.practice_affordances),
            "confidence": float(self.confidence),
            "caveats": list(self.caveats),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PracticeChunk:
        def _frac(v: Any) -> Fraction | None:
            if v is None:
                return None
            return Fraction(str(v))

        return cls(
            chunk_id=str(data["chunk_id"]),
            kind=str(data["kind"]),
            label=str(data.get("label", CHUNK_LABELS.get(str(data["kind"]), str(data["kind"])))),
            hand=data.get("hand"),
            voice=data.get("voice"),
            role=data.get("role"),
            staff=data.get("staff"),
            start_onset=Fraction(str(data["start_onset"])),
            end_onset=Fraction(str(data["end_onset"])),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            measure_numbers=tuple(str(x) for x in data.get("measure_numbers", [])),
            beat_start=_frac(data.get("beat_start")),
            beat_end=_frac(data.get("beat_end")),
            primary_event_ids=tuple(str(x) for x in data.get("primary_event_ids", [])),
            context_event_ids=tuple(str(x) for x in data.get("context_event_ids", [])),
            child_chunk_ids=tuple(str(x) for x in data.get("child_chunk_ids", [])),
            parent_chunk_id=data.get("parent_chunk_id"),
            source_object_ids=tuple(str(x) for x in data.get("source_object_ids", [])),
            source_feature_refs=tuple(str(x) for x in data.get("source_feature_refs", [])),
            traits=tuple(str(x) for x in data.get("traits", [])),
            practice_affordances=tuple(str(x) for x in data.get("practice_affordances", [])),
            confidence=float(data.get("confidence", 0.0)),
            caveats=tuple(str(x) for x in data.get("caveats", [])),
            payload=dict(data.get("payload", {})),
        )


@dataclass(frozen=True, slots=True)
class SemanticBundle:
    """Container for the three layers plus provenance."""

    events: tuple[ScoreEvent, ...]
    derived_tokens: tuple[DerivedToken, ...]
    gestures: tuple[Gesture, ...]
    musical_objects: tuple[MusicalObject, ...] = ()
    object_components: tuple[ObjectComponent, ...] = ()
    micro_moments: tuple[MicroMoment, ...] = ()
    practice_chunks: tuple[PracticeChunk, ...] = ()
    score_id: str | None = None
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "event_count": len(self.events),
            "derived_token_count": len(self.derived_tokens),
            "gesture_count": len(self.gestures),
            "musical_object_count": len(self.musical_objects),
            "object_component_count": len(self.object_components),
            "micro_moment_count": len(self.micro_moments),
            "practice_chunk_count": len(self.practice_chunks),
            "events": [e.to_dict() for e in self.events],
            "derived_tokens": [t.to_dict() for t in self.derived_tokens],
            "gestures": [g.to_dict() for g in self.gestures],
            "musical_objects": [o.to_dict() for o in self.musical_objects],
            "object_components": [c.to_dict() for c in self.object_components],
            "micro_moments": [m.to_dict() for m in self.micro_moments],
            "practice_chunks": [c.to_dict() for c in self.practice_chunks],
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> SemanticBundle:
        # Tolerant reconstruction for backward compatibility
        def _frac(v: Any) -> Fraction:
            return Fraction(str(v))

        events = tuple(ScoreEvent(
            event_id=str(e["event_id"]),
            score_id=e.get("score_id"),
            measure_index=e.get("measure_index"),
            measure_number=e.get("measure_number"),
            staff=e.get("staff"),
            voice=e.get("voice"),
            hand=e.get("hand"),
            hand_confidence=e.get("hand_confidence"),
            beat=Fraction(str(e["beat"])) if e.get("beat") is not None else None,
            offset_quarter=e.get("offset_quarter"),
            duration_quarter=e.get("duration_quarter"),
            onset=_frac(e["onset"]),
            end=_frac(e["end"]),
            duration=_frac(e["duration"]),
            is_rest=bool(e.get("is_rest", False)),
            is_chord_tone=bool(e.get("is_chord_tone", False)),
            chord_id=e.get("chord_id"),
            pitch_midi=e.get("pitch_midi"),
            pitch_name=e.get("pitch_name"),
            pitch_class=e.get("pitch_class"),
            octave=e.get("octave"),
            accidental=e.get("accidental"),
            alter=e.get("alter"),
            tie_merged=bool(e.get("tie_merged", False)),
            source_note_ids=tuple(str(x) for x in e.get("source_note_ids", [])),
            xml_order=e.get("xml_order"),
            measure_staff_order=e.get("measure_staff_order"),
            is_grace=bool(e.get("is_grace", False)),
            duration_type=e.get("duration_type"),
            key_signature=e.get("key_signature"),
            time_signature=e.get("time_signature"),
            clef=e.get("clef"),
            tempo_bpm=e.get("tempo_bpm"),
            dynamics=e.get("dynamics"),
            articulation=tuple(str(x) for x in e.get("articulation", [])),
            tuplet=e.get("tuplet"),
            is_arpeggiated=bool(e.get("is_arpeggiated", False)),
            has_slur_start=bool(e.get("has_slur_start", False)),
            has_slur_stop=bool(e.get("has_slur_stop", False)),
            phrase_start=bool(e.get("phrase_start", False)),
            phrase_stop=bool(e.get("phrase_stop", False)),
            extra=dict(e.get("extra", {})),
        ) for e in data.get("events", []))
        derived = tuple(DerivedToken(
            token_id=str(t["token_id"]),
            kind=str(t["kind"]),
            hand=t.get("hand"),
            staff=t.get("staff"),
            start_onset=_frac(t["start_onset"]),
            end_onset=_frac(t["end_onset"]),
            measure_start=t.get("measure_start"),
            measure_end=t.get("measure_end"),
            measure_numbers=tuple(str(x) for x in t.get("measure_numbers", [])),
            evidence_event_ids=tuple(str(x) for x in t.get("evidence_event_ids", [])),
            confidence=float(t.get("confidence", 0.0)),
            payload=dict(t.get("payload", {})),
        ) for t in data.get("derived_tokens", []))
        gestures = tuple(Gesture(
            gesture_id=str(g["gesture_id"]),
            kind=str(g["kind"]),
            hand=g.get("hand"),
            start_onset=_frac(g["start_onset"]),
            end_onset=_frac(g["end_onset"]),
            measure_start=g.get("measure_start"),
            measure_end=g.get("measure_end"),
            measure_numbers=tuple(str(x) for x in g.get("measure_numbers", [])),
            token_ids=tuple(str(x) for x in g.get("token_ids", [])),
            evidence_event_ids=tuple(str(x) for x in g.get("evidence_event_ids", [])),
            confidence=float(g.get("confidence", 0.0)),
            payload=dict(g.get("payload", {})),
        ) for g in data.get("gestures", []))
        musical_objects = tuple(MusicalObject.from_dict(o) for o in data.get("musical_objects", []))
        object_components = tuple(ObjectComponent.from_dict(c) for c in data.get("object_components", []))
        micro_moments = tuple(MicroMoment.from_dict(m) for m in data.get("micro_moments", []))
        practice_chunks = tuple(PracticeChunk.from_dict(c) for c in data.get("practice_chunks", []))
        return cls(
            events=events,
            derived_tokens=derived,
            gestures=gestures,
            musical_objects=musical_objects,
            object_components=object_components,
            micro_moments=micro_moments,
            practice_chunks=practice_chunks,
            score_id=data.get("score_id"),
            diagnostics=tuple(str(x) for x in data.get("diagnostics", [])),
        )
