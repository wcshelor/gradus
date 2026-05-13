"""Typed intermediate representation for normalized score data.

These classes are intentionally small and conservative. They exist to anchor the
rest of the repository around stable concepts before extractor implementation
begins in earnest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


@dataclass(slots=True)
class DiagnosticIR:
    """A warning, error, or ambiguity notice tied to score content."""

    code: str
    severity: str
    message: str
    measure_start: int | None = None
    measure_end: int | None = None


@dataclass(slots=True)
class MeasureIR:
    """A normalized measure with stable indexing and printed numbering."""

    measure_index: int
    measure_number: str
    start: Fraction
    end: Fraction
    time_signature: str | None = None
    key_signature: str | None = None
    tempo_text: str | None = None


@dataclass(slots=True)
class WrittenNoteIR:
    """A notated note token before tie collapsing.

    This representation should remain close to the visible score so notation and
    reading-related features can work directly on it.
    """

    note_id: str
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    staff: int | None
    voice: str | None
    hand: str | None = None
    hand_confidence: str | None = None
    is_grace: bool = False
    tie_start: bool = False
    tie_stop: bool = False
    articulations: tuple[str, ...] = ()
    accidental: str | None = None
    measure_index: int | None = None


@dataclass(slots=True)
class LogicalNoteIR:
    """A tie-collapsed attack-level note event for analysis views."""

    note_id: str
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    staff: int | None
    voice: str | None
    hand: str | None = None
    hand_confidence: str | None = None
    measure_index: int | None = None


@dataclass(slots=True)
class DirectionIR:
    """A normalized tempo, dynamic, pedal, or free-text score direction."""

    direction_id: str
    kind: str
    value: str
    start: Fraction
    end: Fraction | None = None
    measure_index: int | None = None


@dataclass(slots=True)
class OnsetGroupIR:
    """A simultaneity or grouped attack event used by multiple extractors."""

    onset: Fraction
    hand: str | None
    note_ids: tuple[str, ...]
    measure_index: int | None = None


@dataclass(slots=True)
class ScoreIR:
    """Top-level normalized score container."""

    source_path: Path | None = None
    title: str | None = None
    composer: str | None = None
    measures: list[MeasureIR] = field(default_factory=list)
    written_notes: list[WrittenNoteIR] = field(default_factory=list)
    logical_notes: list[LogicalNoteIR] = field(default_factory=list)
    directions: list[DirectionIR] = field(default_factory=list)
    onset_groups: list[OnsetGroupIR] = field(default_factory=list)
    diagnostics: list[DiagnosticIR] = field(default_factory=list)

