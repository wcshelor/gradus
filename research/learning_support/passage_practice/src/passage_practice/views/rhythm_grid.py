"""Rhythm grid view — S2.6.

Projects a passage's logical attacks into exact beat-relative placement
plus per-onset hand alignment. Consumes only normalized ``ScoreIR``
facts (``LogicalNoteIR`` timing, ``MeasureIR`` meter, written tuplet
flags); never parses MusicXML and never recomputes pitch, tie collapse,
or event identity (S0.4 R1/R2/R7/R11).

Design refs:
- docs/semantic_music_extraction_plan.md: Layer 3 ``rhythm_grid``
- docs/contracts.md: Derived view (view_type, source passage, method,
  included IDs, ordering, omissions, diagnostics)
- docs/decisions.md: D-011 (SourceRef), D-014 (half-open selection),
  D-018 (S-Q004: attack stream + ``MeasureIR`` meter + tuplet flags are
  sufficient; no ScoreIR promotion needed)
- views/attack_stream.py (S2.4): sibling conventions — strict ``Passage``
  input, ``source_ref`` identity, per-event schema versions, stable
  diagnostic codes

Semantics:
- One cell per resolved ``LOGICAL_NOTE`` ref, ordered by
  ``(onset, xml_order, note_id)``. Durations are tie-collapsed sounding
  durations, so ties across beats surface as multi-beat spans here
  (the S2.4 attack stream carries the same duration; this view places
  it on the beat grid).
- Beat placement is measure-local and exact: ``beat_index`` counts whole
  beats from the containing measure start with beat length
  ``4 / time_beat_type`` quarters; ``offset_in_beat`` is the exact
  ``Fraction`` remainder; ``on_beat`` is true only for zero offset.
  ``beat_boundaries_crossed`` counts beat lines strictly inside
  ``[onset, end)``, so notes ending exactly on a beat do not claim a
  crossing they never sound through.
- Meter provenance travels per cell (``beats_per_measure`` /
  ``beat_unit``). When the containing measure is missing or meterless,
  beat fields stay ``None`` (never zero or guessed) with a stable
  ``unknown_meter`` warning.
- ``from_tuplet`` marks cells whose tie chain includes tuplet-flagged
  written noteheads (read through ``source_note_ids``, never re-parsed).
  Tuplet interpretation belongs downstream (S2.10); here it is a fact
  plus an info diagnostic.
- Per-onset summaries group simultaneous cells with the sorted hands
  present and a ``both_hands`` flag (staggered vs. aligned hand
  analysis belongs to S2.10; this grid only reports who attacks when).
- Pitch, dynamics interpretation, and layout are declared omissions:
  this is a rhythm-only projection.
- The source score and passage are never mutated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage, ViewType
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import fraction_from_json, fraction_to_json

RHYTHM_GRID_SCHEMA_VERSION = "rhythm_grid.v1"
RHYTHM_CELL_SCHEMA_VERSION = "rhythm_cell.v1"
RHYTHM_ONSET_SCHEMA_VERSION = "rhythm_onset.v1"

SUPPORTED_RHYTHM_GRID_VERSIONS = {RHYTHM_GRID_SCHEMA_VERSION}
SUPPORTED_RHYTHM_CELL_VERSIONS = {RHYTHM_CELL_SCHEMA_VERSION}
SUPPORTED_RHYTHM_ONSET_VERSIONS = {RHYTHM_ONSET_SCHEMA_VERSION}

RHYTHM_GRID_METHOD_ID = "rhythm_grid_view"
RHYTHM_GRID_METHOD_VERSION = "v1"

#: Deterministic ordering shared with the S2.4 attack stream.
RHYTHM_GRID_ORDERING = "onset,xml_order,note_id"

#: Pitch content, dynamics interpretation, and page geometry never enter
#: the grid. Rests are not listed: rest facts live in the S2.5 written
#: stream; rest-based phrase evidence belongs to S2.12/S6.
RHYTHM_GRID_OMISSIONS = ("pitch", "directions", "layout")


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _order_key(note: Any) -> tuple[Fraction, int, str]:
    xml_order = getattr(note, "xml_order", None)
    order = xml_order if isinstance(xml_order, int) else 10**9
    return (note.onset, order, note.note_id)


def _locate_measure(measures: list, onset: Fraction) -> Any | None:
    for measure in measures:
        if measure.start <= onset < measure.end:
            return measure
    return None


def _beat_length(measure: Any) -> Fraction | None:
    beat_type = getattr(measure, "time_beat_type", None)
    if isinstance(beat_type, bool) or not isinstance(beat_type, int):
        return None
    if beat_type <= 0:
        return None
    return Fraction(4, beat_type)


def _boundaries_crossed(onset_rel: Fraction, end_rel: Fraction) -> int:
    """Count beat lines strictly inside ``[onset, end)`` in beat units."""
    first = math.floor(onset_rel) + 1
    last = math.ceil(end_rel) - 1
    return max(0, last - first + 1)


@dataclass(frozen=True, slots=True)
class RhythmCell:
    """One attack placed on its measure-local beat grid.

    Identity is the logical note's own ``source_ref`` — no new IDs are
    minted. Beat fields are ``None`` exactly when placement is unknown
    (missing measure or meterless measure), never guessed.
    """

    source_ref: SourceRef
    onset: Fraction
    duration: Fraction
    measure_index: int | None = None
    beats_per_measure: int | None = None
    beat_unit: int | None = None
    beat_index: int | None = None
    offset_in_beat: Fraction | None = None
    on_beat: bool | None = None
    beats_spanned: Fraction | None = None
    beat_boundaries_crossed: int | None = None
    from_tuplet: bool = False
    hand: str | None = None
    staff: int | None = None
    voice: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceRef):
            raise TypeError("source_ref must be SourceRef")
        if self.source_ref.kind != SourceKind.LOGICAL_NOTE:
            raise ValueError(
                "source_ref kind must be "
                f"'logical_note', got {self.source_ref.kind.value!r}"
            )
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        if not isinstance(self.duration, Fraction):
            raise TypeError("duration must be Fraction")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if self.measure_index is not None and not isinstance(
            self.measure_index, int
        ):
            raise TypeError("measure_index must be int or None")
        for field in ("beats_per_measure", "beat_unit", "beat_index"):
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise TypeError(f"{field} must be int or None")
        if self.offset_in_beat is not None and not isinstance(
            self.offset_in_beat, Fraction
        ):
            raise TypeError("offset_in_beat must be Fraction or None")
        if self.on_beat is not None and not isinstance(self.on_beat, bool):
            raise TypeError("on_beat must be bool or None")
        if self.beats_spanned is not None:
            if not isinstance(self.beats_spanned, Fraction):
                raise TypeError("beats_spanned must be Fraction or None")
            if self.beats_spanned <= 0:
                raise ValueError(
                    f"beats_spanned must be positive, got {self.beats_spanned}"
                )
        if self.beat_boundaries_crossed is not None and (
            isinstance(self.beat_boundaries_crossed, bool)
            or not isinstance(self.beat_boundaries_crossed, int)
            or self.beat_boundaries_crossed < 0
        ):
            raise TypeError("beat_boundaries_crossed must be non-negative int or None")
        if not isinstance(self.from_tuplet, bool):
            raise TypeError("from_tuplet must be bool")
        if self.hand is not None and self.hand not in {"left", "right"}:
            raise ValueError(f"hand must be 'left'/'right' or None, got {self.hand!r}")
        if self.staff is not None and (
            not isinstance(self.staff, int) or self.staff <= 0
        ):
            raise ValueError(f"staff must be positive int or None, got {self.staff!r}")
        if self.voice is not None and not isinstance(self.voice, str):
            raise TypeError("voice must be str or None")

    @property
    def end(self) -> Fraction:
        """Exact end time (onset + duration)."""
        return self.onset + self.duration

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": RHYTHM_CELL_SCHEMA_VERSION,
            "source_ref": self.source_ref.to_dict(),
            "onset": fraction_to_json(self.onset),
            "duration": fraction_to_json(self.duration),
        }
        if self.measure_index is not None:
            payload["measure_index"] = self.measure_index
        if self.beats_per_measure is not None:
            payload["beats_per_measure"] = self.beats_per_measure
        if self.beat_unit is not None:
            payload["beat_unit"] = self.beat_unit
        if self.beat_index is not None:
            payload["beat_index"] = self.beat_index
        if self.offset_in_beat is not None:
            payload["offset_in_beat"] = fraction_to_json(self.offset_in_beat)
        if self.on_beat is not None:
            payload["on_beat"] = self.on_beat
        if self.beats_spanned is not None:
            payload["beats_spanned"] = fraction_to_json(self.beats_spanned)
        if self.beat_boundaries_crossed is not None:
            payload["beat_boundaries_crossed"] = self.beat_boundaries_crossed
        if self.from_tuplet:
            payload["from_tuplet"] = True
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RhythmCell":
        if not isinstance(data, dict):
            raise TypeError(f"RhythmCell requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_RHYTHM_CELL_VERSIONS:
            raise ValueError(
                f"unsupported RhythmCell schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_RHYTHM_CELL_VERSIONS)}"
            )
        try:
            ref_data = data["source_ref"]
            onset_data = data["onset"]
            duration_data = data["duration"]
        except KeyError as exc:
            raise ValueError(
                f"missing RhythmCell field {exc.args[0]!r}"
            ) from exc
        offset_data = data.get("offset_in_beat")
        spanned_data = data.get("beats_spanned")
        return cls(
            source_ref=SourceRef.from_dict(ref_data),
            onset=fraction_from_json(onset_data),
            duration=fraction_from_json(duration_data),
            measure_index=data.get("measure_index"),
            beats_per_measure=data.get("beats_per_measure"),
            beat_unit=data.get("beat_unit"),
            beat_index=data.get("beat_index"),
            offset_in_beat=(
                fraction_from_json(offset_data) if offset_data is not None else None
            ),
            on_beat=data.get("on_beat"),
            beats_spanned=(
                fraction_from_json(spanned_data) if spanned_data is not None else None
            ),
            beat_boundaries_crossed=data.get("beat_boundaries_crossed"),
            from_tuplet=bool(data.get("from_tuplet", False)),
            hand=data.get("hand"),
            staff=data.get("staff"),
            voice=data.get("voice"),
        )


@dataclass(frozen=True, slots=True)
class RhythmOnset:
    """One attack time with the hands sounding there.

    Simultaneous cells (chords, two hands, two voices) share an onset;
    nothing is grouped beyond co-attack facts. ``hands`` excludes unknown
    (``None``) hands; ``both_hands`` is false whenever either hand is
    absent or unknown.
    """

    onset: Fraction
    cell_refs: tuple[SourceRef, ...] = ()
    hands: tuple[str, ...] = ()
    both_hands: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        if not isinstance(self.cell_refs, tuple) or not self.cell_refs:
            raise TypeError("cell_refs must be a non-empty tuple")
        for ref in self.cell_refs:
            if not isinstance(ref, SourceRef):
                raise TypeError(
                    f"cell_refs must contain SourceRef, got {type(ref).__name__}"
                )
            if ref.kind != SourceKind.LOGICAL_NOTE:
                raise ValueError(
                    "cell_refs must contain logical_note refs, "
                    f"got {ref.kind.value!r}"
                )
        if not isinstance(self.hands, tuple):
            raise TypeError("hands must be tuple")
        for hand in self.hands:
            if hand not in {"left", "right"}:
                raise ValueError(
                    f"hands must contain 'left'/'right', got {hand!r}"
                )
        if tuple(sorted(self.hands)) != self.hands or len(set(self.hands)) != len(
            self.hands
        ):
            raise ValueError("hands must be sorted unique hand names")
        if not isinstance(self.both_hands, bool):
            raise TypeError("both_hands must be bool")
        if self.both_hands and set(self.hands) != {"left", "right"}:
            raise ValueError("both_hands requires exactly hands ('left', 'right')")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RHYTHM_ONSET_SCHEMA_VERSION,
            "onset": fraction_to_json(self.onset),
            "cell_refs": [r.to_dict() for r in self.cell_refs],
            "hands": list(self.hands),
            "both_hands": self.both_hands,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RhythmOnset":
        if not isinstance(data, dict):
            raise TypeError(f"RhythmOnset requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_RHYTHM_ONSET_VERSIONS:
            raise ValueError(
                f"unsupported RhythmOnset schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_RHYTHM_ONSET_VERSIONS)}"
            )
        try:
            onset_data = data["onset"]
            refs_data = data["cell_refs"]
            hands_data = data["hands"]
            both_hands = data["both_hands"]
        except KeyError as exc:
            raise ValueError(
                f"missing RhythmOnset field {exc.args[0]!r}"
            ) from exc
        if not isinstance(refs_data, list):
            raise ValueError("RhythmOnset cell_refs must be list")
        if not isinstance(hands_data, list):
            raise ValueError("RhythmOnset hands must be list")
        return cls(
            onset=fraction_from_json(onset_data),
            cell_refs=tuple(SourceRef.from_dict(r) for r in refs_data),
            hands=tuple(str(h) for h in hands_data),
            both_hands=bool(both_hands),
        )


@dataclass(frozen=True, slots=True)
class RhythmGrid:
    """Beat-relative attack placement plus hand alignment for one passage.

    - cells: one entry per resolved logical attack, ordered by
      (onset, document order, note ID).
    - onsets: one entry per distinct attack time, in time order.
      Onset grouping here is co-attack bookkeeping for hand alignment;
      simultaneity interpretation belongs to the S2.7 texture grid.
    - ordering documents the sort; grouping is None (flat grid).
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    cells: tuple[RhythmCell, ...] = ()
    onsets: tuple[RhythmOnset, ...] = ()
    ordering: str = RHYTHM_GRID_ORDERING
    grouping: str | None = None
    omissions: tuple[str, ...] = RHYTHM_GRID_OMISSIONS
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.view_type != ViewType.RHYTHM_GRID:
            raise ValueError(
                "RhythmGrid view_type must be "
                f"{ViewType.RHYTHM_GRID.value!r}, got {self.view_type!r}"
            )
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.cells, tuple):
            raise TypeError("cells must be tuple")
        for cell in self.cells:
            if not isinstance(cell, RhythmCell):
                raise TypeError(
                    "cells must contain RhythmCell, "
                    f"got {type(cell).__name__}"
                )
        if not isinstance(self.onsets, tuple):
            raise TypeError("onsets must be tuple")
        for onset in self.onsets:
            if not isinstance(onset, RhythmOnset):
                raise TypeError(
                    "onsets must contain RhythmOnset, "
                    f"got {type(onset).__name__}"
                )
        onset_times = [o.onset for o in self.onsets]
        if onset_times != sorted(onset_times) or len(set(onset_times)) != len(
            onset_times
        ):
            raise ValueError("onsets must be sorted unique onset times")
        cell_ids = {c.source_ref.id for c in self.cells}
        for onset in self.onsets:
            for ref in onset.cell_refs:
                if ref.id not in cell_ids:
                    raise ValueError(
                        f"onset cell_ref {ref.id!r} matches no grid cell"
                    )
        if not isinstance(self.ordering, str) or not self.ordering:
            raise ValueError(
                f"ordering must be non-empty str, got {self.ordering!r}"
            )
        if self.grouping is not None and not isinstance(self.grouping, str):
            raise TypeError("grouping must be str or None")
        if not isinstance(self.omissions, tuple):
            raise TypeError("omissions must be tuple")
        for omission in ("pitch", "directions", "layout"):
            if omission not in self.omissions:
                raise ValueError(
                    f"omissions must declare {omission!r} "
                    "(never projected into the rhythm grid)"
                )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RHYTHM_GRID_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "cells": [c.to_dict() for c in self.cells],
            "onsets": [o.to_dict() for o in self.onsets],
            "ordering": self.ordering,
            "grouping": self.grouping,
            "omissions": list(self.omissions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RhythmGrid":
        if not isinstance(data, dict):
            raise TypeError(f"RhythmGrid requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_RHYTHM_GRID_VERSIONS:
            raise ValueError(
                f"unsupported RhythmGrid schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_RHYTHM_GRID_VERSIONS)}"
            )
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(f"missing RhythmGrid field {exc.args[0]!r}") from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        raw_cells = data.get("cells", [])
        if not isinstance(raw_cells, list):
            raise ValueError("RhythmGrid cells must be list")
        raw_onsets = data.get("onsets", [])
        if not isinstance(raw_onsets, list):
            raise ValueError("RhythmGrid onsets must be list")
        raw_omissions = data.get("omissions", [])
        if not isinstance(raw_omissions, list):
            raise ValueError("RhythmGrid omissions must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("RhythmGrid diagnostics must be list")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            cells=tuple(RhythmCell.from_dict(c) for c in raw_cells),
            onsets=tuple(RhythmOnset.from_dict(o) for o in raw_onsets),
            ordering=str(ordering),
            grouping=data.get("grouping"),
            omissions=tuple(str(o) for o in raw_omissions),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def build_rhythm_grid(
    passage: Passage,
    score: Any,
    *,
    method_id: str = RHYTHM_GRID_METHOD_ID,
    method_version: str = RHYTHM_GRID_METHOD_VERSION,
) -> RhythmGrid:
    """Build the rhythm grid for `passage` over `score`.

    Resolves the passage's logical-note refs (skipping non-logical refs
    and unresolvable refs with diagnostics, never failing), places each
    attack on its measure-local beat grid with exact fractions, flags
    tuplet-derived subdivisions, and summarizes per-onset hand
    alignment. Unknown beat placement stays ``None`` with an
    ``unknown_meter`` warning; an empty result is an explicit valid
    outcome with an info diagnostic. Reads only: neither the score nor
    the passage is mutated.
    """
    if not isinstance(passage, Passage):
        raise TypeError(f"passage must be Passage, got {type(passage).__name__}")
    diagnostics: list[Diagnostic] = []
    skipped_non_logical = 0
    resolved: list[Any] = []
    for ref in passage.event_refs:
        if ref.kind != SourceKind.LOGICAL_NOTE:
            skipped_non_logical += 1
            continue
        note = resolve_ref(score, ref)
        if note is None:
            diagnostics.append(
                Diagnostic(
                    code="unresolvable_attack_ref",
                    severity=Severity.WARNING,
                    message=(
                        f"passage ref {ref.id!r} does not resolve "
                        "in this score"
                    ),
                )
            )
            continue
        resolved.append(note)
    if skipped_non_logical:
        diagnostics.append(
            Diagnostic(
                code="non_logical_refs_skipped",
                severity=Severity.INFO,
                message=(
                    f"{skipped_non_logical} non-logical refs excluded "
                    "from the rhythm grid"
                ),
            )
        )

    measures = list(getattr(score, "measures", []) or [])
    written_by_id = {
        getattr(w, "note_id", None): w
        for w in (getattr(score, "written_notes", []) or [])
    }

    resolved.sort(key=_order_key)
    cells: list[RhythmCell] = []
    meterless_refs: list[SourceRef] = []
    tuplet_refs: list[SourceRef] = []
    for note in resolved:
        cell_ref = SourceRef(id=note.note_id, kind=SourceKind.LOGICAL_NOTE)
        measure = _locate_measure(measures, note.onset)
        beat_len = _beat_length(measure) if measure is not None else None
        if measure is None or beat_len is None:
            meterless_refs.append(cell_ref)
            cells.append(
                RhythmCell(
                    source_ref=cell_ref,
                    onset=note.onset,
                    duration=note.duration,
                    measure_index=getattr(note, "measure_index", None),
                    hand=getattr(note, "hand", None),
                    staff=getattr(note, "staff", None),
                    voice=getattr(note, "voice", None),
                )
            )
            continue
        rel = note.onset - measure.start
        beat_index = int(rel // beat_len)
        offset = rel - beat_index * beat_len
        end_rel = note.onset + note.duration - measure.start
        from_tuplet = False
        for written_id in getattr(note, "source_note_ids", None) or ():
            written = written_by_id.get(written_id)
            if written is None:
                continue
            if getattr(written, "tuplet_actual", None) is not None or getattr(
                written, "tuplet_normal", None
            ) is not None:
                from_tuplet = True
                break
        if from_tuplet:
            tuplet_refs.append(cell_ref)
        cells.append(
            RhythmCell(
                source_ref=cell_ref,
                onset=note.onset,
                duration=note.duration,
                measure_index=getattr(note, "measure_index", None),
                beats_per_measure=getattr(measure, "time_beats", None),
                beat_unit=getattr(measure, "time_beat_type", None),
                beat_index=beat_index,
                offset_in_beat=offset,
                on_beat=(offset == 0),
                beats_spanned=note.duration / beat_len,
                beat_boundaries_crossed=_boundaries_crossed(
                    rel / beat_len, end_rel / beat_len
                ),
                from_tuplet=from_tuplet,
                hand=getattr(note, "hand", None),
                staff=getattr(note, "staff", None),
                voice=getattr(note, "voice", None),
            )
        )
    if meterless_refs:
        meterless_refs.sort(key=lambda r: r.id)
        diagnostics.append(
            Diagnostic(
                code="unknown_meter",
                severity=Severity.WARNING,
                message=(
                    f"{len(meterless_refs)} attack(s) have no locatable "
                    "measure or meterless measure; beat placement omitted, "
                    "never guessed"
                ),
                source_refs=tuple(meterless_refs),
            )
        )
    if tuplet_refs:
        tuplet_refs.sort(key=lambda r: r.id)
        diagnostics.append(
            Diagnostic(
                code="tuplet_subdivision",
                severity=Severity.INFO,
                message=(
                    f"{len(tuplet_refs)} attack(s) derive from tuplet-flagged "
                    "notation; subdivision interpretation belongs downstream"
                ),
                source_refs=tuple(tuplet_refs),
            )
        )

    onsets: list[RhythmOnset] = []
    current_time: Fraction | None = None
    current_cells: list[RhythmCell] = []
    for cell in (*cells, None):
        time = cell.onset if cell is not None else None
        if time is not None and time == current_time:
            current_cells.append(cell)
            continue
        if current_cells and current_time is not None:
            hands = sorted({c.hand for c in current_cells if c.hand is not None})
            onsets.append(
                RhythmOnset(
                    onset=current_time,
                    cell_refs=tuple(c.source_ref for c in current_cells),
                    hands=tuple(hands),
                    both_hands=set(hands) == {"left", "right"},
                )
            )
        current_cells = [cell] if cell is not None else []
        current_time = time

    if not cells:
        diagnostics.append(
            Diagnostic(
                code="no_rhythm_cells",
                severity=Severity.INFO,
                message="no resolvable logical attacks in the passage interval",
            )
        )
    return RhythmGrid(
        view_type=ViewType.RHYTHM_GRID,
        source_passage_id=passage.passage_id,
        method_id=method_id,
        method_version=method_version,
        cells=tuple(cells),
        onsets=tuple(onsets),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "RHYTHM_CELL_SCHEMA_VERSION",
    "RHYTHM_GRID_METHOD_ID",
    "RHYTHM_GRID_METHOD_VERSION",
    "RHYTHM_GRID_OMISSIONS",
    "RHYTHM_GRID_ORDERING",
    "RHYTHM_GRID_SCHEMA_VERSION",
    "RHYTHM_ONSET_SCHEMA_VERSION",
    "RhythmCell",
    "RhythmGrid",
    "RhythmOnset",
    "build_rhythm_grid",
]
