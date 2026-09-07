"""Exact passage selection over ScoreIR — WP-02 T02.3–T02.5.

Selects logical attacks in `[start, end)` with sustaining boundary context,
inherited score context, and refinement lineage. Produces the existing
`Passage` contract; never mutates the source score.

Design refs:
- docs/contracts.md: Passage selection (invariants), Identity and time
- docs/architecture.md: Region semantics (half-open, four purposes)
- WORK_PACKAGES.md WP-02; IMPLEMENTATION_CHECKLIST.md T02.3–T02.5
- docs/decisions.md: D-011 (SourceRef), D-012 (region ownership), D-014
  (Q-003 selection-side partial-measure proposal)

Key invariants:
- Attacks are tie-collapsed logical notes; rests are declared omissions.
- Sustaining boundary notes are context, not new attacks (written-note refs).
- Context is the state active at the passage start (measure, meter, key,
  clef, tempo, co-located or spanning directions).
- Unresolvable locations raise `UnresolvableRegion` with a stable reason
  code; malformed intervals raise `ValueError`. Nothing is guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import PASSAGE_SCHEMA_VERSION, Passage, PassagePurpose
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import (
    SCORE_INTERVAL_SCHEMA_VERSION,
    ScoreInterval,
    ScorePosition,
)

SELECTION_METHOD_ID = "exact_region_selection"
SELECTION_METHOD_VERSION = "v1"

PASSAGE_CONTEXT_SCHEMA_VERSION = "passage_context.v1"
SELECTED_PASSAGE_SCHEMA_VERSION = "selected_passage.v1"

SUPPORTED_CONTEXT_VERSIONS = {PASSAGE_CONTEXT_SCHEMA_VERSION}
SUPPORTED_SELECTION_VERSIONS = {SELECTED_PASSAGE_SCHEMA_VERSION}


class UnresolvableRegion(ValueError):
    """Explicit outcome for a region that cannot be resolved to events.

    Reason codes: `empty_interval`, `out_of_range`, `no_measures`,
    `unknown_measure`, `ambiguous_measure`, `outside_parent`.
    Carries structured diagnostics; never fabricates a region.
    """

    def __init__(self, reason: str, message: str, diagnostics: tuple[Diagnostic, ...] = ()) -> None:
        super().__init__(message)
        self.reason = reason
        self.diagnostics = diagnostics


def _fail(reason: str, message: str) -> UnresolvableRegion:
    diagnostic = Diagnostic(
        code=f"region_{reason}", severity=Severity.ERROR, message=message
    )
    return UnresolvableRegion(reason, message, (diagnostic,))


@dataclass(frozen=True, slots=True)
class ClefState:
    staff: int | None
    sign: str
    line: int | None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"sign": self.sign}
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.line is not None:
            payload["line"] = self.line
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClefState":
        if not isinstance(data, dict):
            raise TypeError(f"ClefState requires dict, got {type(data).__name__}")
        try:
            sign = data["sign"]
        except KeyError as exc:
            raise ValueError(f"missing ClefState field {exc.args[0]!r}") from exc
        return cls(staff=data.get("staff"), sign=str(sign), line=data.get("line"))


@dataclass(frozen=True, slots=True)
class PassageContext:
    """Score state active at the passage start (inherited, not selected)."""

    measure_index: int
    measure_number: str
    time_signature: str | None = None
    key_fifths: int | None = None
    key_mode: str | None = None
    clefs: tuple[ClefState, ...] = ()
    tempo_bpm: float | None = None
    tempo_text: str | None = None
    direction_refs: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.measure_index, int):
            raise TypeError("measure_index must be int")
        if not isinstance(self.measure_number, str) or not self.measure_number:
            raise ValueError("measure_number must be non-empty str")
        if not isinstance(self.clefs, tuple):
            raise TypeError("clefs must be tuple")
        for c in self.clefs:
            if not isinstance(c, ClefState):
                raise TypeError(f"clefs must contain ClefState, got {type(c).__name__}")
        if not isinstance(self.direction_refs, tuple):
            raise TypeError("direction_refs must be tuple")
        for r in self.direction_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(
                    f"direction_refs must contain SourceRef, got {type(r).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": PASSAGE_CONTEXT_SCHEMA_VERSION,
            "measure_index": self.measure_index,
            "measure_number": self.measure_number,
        }
        if self.time_signature is not None:
            payload["time_signature"] = self.time_signature
        if self.key_fifths is not None:
            payload["key_fifths"] = self.key_fifths
        if self.key_mode is not None:
            payload["key_mode"] = self.key_mode
        if self.clefs:
            payload["clefs"] = [c.to_dict() for c in self.clefs]
        if self.tempo_bpm is not None:
            payload["tempo_bpm"] = self.tempo_bpm
        if self.tempo_text is not None:
            payload["tempo_text"] = self.tempo_text
        if self.direction_refs:
            payload["direction_refs"] = [r.to_dict() for r in self.direction_refs]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PassageContext":
        if not isinstance(data, dict):
            raise TypeError(f"PassageContext requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_CONTEXT_VERSIONS:
            raise ValueError(
                f"unsupported PassageContext schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_CONTEXT_VERSIONS)}"
            )
        try:
            measure_index = data["measure_index"]
            measure_number = data["measure_number"]
        except KeyError as exc:
            raise ValueError(f"missing PassageContext field {exc.args[0]!r}") from exc
        raw_clefs = data.get("clefs", [])
        if not isinstance(raw_clefs, list):
            raise ValueError("PassageContext clefs must be list")
        raw_refs = data.get("direction_refs", [])
        if not isinstance(raw_refs, list):
            raise ValueError("PassageContext direction_refs must be list")
        return cls(
            measure_index=int(measure_index),
            measure_number=str(measure_number),
            time_signature=data.get("time_signature"),
            key_fifths=data.get("key_fifths"),
            key_mode=data.get("key_mode"),
            clefs=tuple(ClefState.from_dict(c) for c in raw_clefs),
            tempo_bpm=data.get("tempo_bpm"),
            tempo_text=data.get("tempo_text"),
            direction_refs=tuple(SourceRef.from_dict(r) for r in raw_refs),
        )


@dataclass(frozen=True, slots=True)
class SelectedPassage:
    """One exact selection: passage, boundary context, inherited context."""

    passage: Passage
    boundary_context: tuple[SourceRef, ...] = ()
    context: PassageContext | None = None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.passage, Passage):
            raise TypeError("passage must be Passage")
        if not isinstance(self.boundary_context, tuple):
            raise TypeError("boundary_context must be tuple")
        for r in self.boundary_context:
            if not isinstance(r, SourceRef):
                raise TypeError(
                    f"boundary_context must contain SourceRef, got {type(r).__name__}"
                )
        if self.context is not None and not isinstance(self.context, PassageContext):
            raise TypeError("context must be PassageContext or None")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SELECTED_PASSAGE_SCHEMA_VERSION,
            "passage": self.passage.to_dict(),
        }
        if self.boundary_context:
            payload["boundary_context"] = [r.to_dict() for r in self.boundary_context]
        if self.context is not None:
            payload["context"] = self.context.to_dict()
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectedPassage":
        if not isinstance(data, dict):
            raise TypeError(f"SelectedPassage requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_SELECTION_VERSIONS:
            raise ValueError(
                f"unsupported SelectedPassage schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SELECTION_VERSIONS)}"
            )
        try:
            passage_data = data["passage"]
        except KeyError as exc:
            raise ValueError(f"missing SelectedPassage field {exc.args[0]!r}") from exc
        passage = Passage.from_dict(passage_data)
        raw_boundary = data.get("boundary_context", [])
        if not isinstance(raw_boundary, list):
            raise ValueError("SelectedPassage boundary_context must be list")
        context_data = data.get("context")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("SelectedPassage diagnostics must be list")
        return cls(
            passage=passage,
            boundary_context=tuple(SourceRef.from_dict(r) for r in raw_boundary),
            context=PassageContext.from_dict(context_data) if context_data is not None else None,
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def _order_key(note: Any) -> tuple[Fraction, int, str]:
    xml_order = getattr(note, "xml_order", None)
    order = xml_order if isinstance(xml_order, int) else 10**9
    return (note.onset, order, note.note_id)


def _locate(score: Any, quarters: Fraction) -> tuple[Any, ScorePosition]:
    measures = list(getattr(score, "measures", []) or [])
    if not measures:
        raise _fail("no_measures", "score has no measures to locate")
    if quarters < 0:
        raise _fail("out_of_range", f"quarters {quarters} is negative")
    for measure in measures:
        if measure.start <= quarters < measure.end:
            return measure, ScorePosition(
                quarters=quarters,
                measure_index=measure.measure_index,
                measure_number=measure.measure_number,
                offset_in_measure=quarters - measure.start,
            )
    last = measures[-1]
    if quarters == last.end:
        return last, ScorePosition(
            quarters=quarters,
            measure_index=last.measure_index,
            measure_number=last.measure_number,
            offset_in_measure=quarters - last.start,
        )
    raise _fail(
        "out_of_range",
        f"quarters {quarters} lies outside score range "
        f"[{measures[0].start}, {last.end}]",
    )


def _active_directions(score: Any, start: Fraction) -> tuple[SourceRef, ...]:
    refs = []
    for direction in getattr(score, "directions", []) or []:
        d_start = direction.start
        d_end = direction.end
        if d_start <= start and (d_end is None or d_end > start or d_start == start):
            refs.append(SourceRef(id=direction.direction_id, kind=SourceKind.DIRECTION))
    return tuple(refs)


def _inherited_context(score: Any, start: Fraction) -> PassageContext:
    measure, _ = _locate(score, start)
    clefs = tuple(
        ClefState(staff=c.staff, sign=c.sign, line=c.line)
        for c in (getattr(score, "clefs", []) or [])
        if c.measure_index is None or c.measure_index <= measure.measure_index
    )
    return PassageContext(
        measure_index=measure.measure_index,
        measure_number=measure.measure_number,
        time_signature=measure.time_signature,
        key_fifths=measure.key_fifths,
        key_mode=measure.key_mode,
        clefs=clefs,
        tempo_bpm=measure.tempo_bpm,
        tempo_text=measure.tempo_text,
        direction_refs=_active_directions(score, start),
    )


def select_passage(
    score: Any,
    *,
    score_id: str,
    start: Fraction,
    end: Fraction,
    purpose: PassagePurpose = PassagePurpose.DETECTION,
    method_id: str = SELECTION_METHOD_ID,
    method_version: str = SELECTION_METHOD_VERSION,
    passage_id: str | None = None,
    parent_id: str | None = None,
) -> SelectedPassage:
    """Select logical attacks with `start <= onset < end` from `score`.

    Sustaining written notes crossing either boundary become
    `boundary_context`, never new attacks. Raises `UnresolvableRegion` for
    unlocatable bounds and `ValueError` for malformed intervals. The score
    is never mutated.
    """
    if not isinstance(start, Fraction) or not isinstance(end, Fraction):
        raise TypeError("start/end must be Fraction (exact score time)")
    if not isinstance(purpose, PassagePurpose):
        raise TypeError(f"purpose must be PassagePurpose, got {type(purpose).__name__}")
    if not (isinstance(score_id, str) and score_id):
        raise ValueError(f"score_id must be non-empty str, got {score_id!r}")
    if not start < end:
        raise _fail(
            "empty_interval",
            f"selection interval must have start < end, got [{start}, {end})",
        )
    _, start_pos = _locate(score, start)
    _, end_pos = _locate(score, end)

    attacks = sorted(
        (
            n for n in (getattr(score, "logical_notes", []) or [])
            if start <= n.onset < end
        ),
        key=_order_key,
    )
    event_refs = tuple(
        SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in attacks
    )
    boundary = sorted(
        {
            n.note_id: n
            for n in (getattr(score, "written_notes", []) or [])
            if n.onset < start < n.onset + n.duration
            or n.onset < end < n.onset + n.duration
        }.values(),
        key=_order_key,
    )
    boundary_refs = tuple(
        SourceRef(id=n.note_id, kind=SourceKind.WRITTEN_NOTE) for n in boundary
    )
    context = _inherited_context(score, start)
    diagnostics: list[Diagnostic] = []
    if not attacks:
        diagnostics.append(
            Diagnostic(
                code="empty_selection",
                severity=Severity.INFO,
                message=f"no attacks in [{start}, {end})",
            )
        )
    resolved_id = (
        passage_id
        if passage_id is not None
        else f"{score_id}@[{start},{end})/{purpose.value}"
    )
    passage = Passage(
        passage_id=resolved_id,
        score_id=score_id,
        start=start_pos,
        end=end_pos,
        purpose=purpose,
        method_id=method_id,
        method_version=method_version,
        parent_id=parent_id,
        event_refs=event_refs,
        omissions=("rests",),
        diagnostics=tuple(diagnostics),
    )
    return SelectedPassage(
        passage=passage,
        boundary_context=boundary_refs,
        context=context,
        diagnostics=tuple(diagnostics),
    )


def refine_selection(
    score: Any,
    parent: SelectedPassage,
    *,
    start: Fraction,
    end: Fraction,
    purpose: PassagePurpose,
    score_id: str | None = None,
    method_id: str = SELECTION_METHOD_ID,
    method_version: str = SELECTION_METHOD_VERSION,
) -> SelectedPassage:
    """Refine `parent` to a narrower interval, preserving lineage."""
    if not isinstance(parent, SelectedPassage):
        raise TypeError("parent must be SelectedPassage")
    if not (parent.passage.start.quarters <= start and end <= parent.passage.end.quarters):
        raise _fail(
            "outside_parent",
            f"refinement [{start}, {end}) lies outside parent "
            f"[{parent.passage.start.quarters}, {parent.passage.end.quarters})",
        )
    return select_passage(
        score,
        score_id=score_id or parent.passage.score_id,
        start=start,
        end=end,
        purpose=purpose,
        method_id=method_id,
        method_version=method_version,
        parent_id=parent.passage.passage_id,
    )


def whole_piece_range(score: Any) -> ScoreInterval:
    """Exact range covering all measures (D-014 selection-side policy)."""
    measures = list(getattr(score, "measures", []) or [])
    if not measures:
        raise _fail("no_measures", "score has no measures to cover")
    first, last = measures[0], measures[-1]
    _, start_pos = _locate(score, first.start)
    _, end_pos = _locate(score, last.end)
    return ScoreInterval(start=start_pos, end=end_pos)


def locate_measure_by_number(score: Any, number: str) -> Any:
    """Resolve a printed measure number; ambiguous or missing is explicit."""
    matches = [
        m for m in (getattr(score, "measures", []) or [])
        if m.measure_number == number
    ]
    if not matches:
        raise _fail("unknown_measure", f"no measure numbered {number!r}")
    if len(matches) > 1:
        raise _fail(
            "ambiguous_measure",
            f"measure number {number!r} matches {len(matches)} measures; "
            "resolve with exact score time",
        )
    return matches[0]


__all__ = [
    "PASSAGE_CONTEXT_SCHEMA_VERSION",
    "SELECTED_PASSAGE_SCHEMA_VERSION",
    "SELECTION_METHOD_ID",
    "SELECTION_METHOD_VERSION",
    "ClefState",
    "PassageContext",
    "SelectedPassage",
    "UnresolvableRegion",
    "locate_measure_by_number",
    "refine_selection",
    "select_passage",
    "whole_piece_range",
]
