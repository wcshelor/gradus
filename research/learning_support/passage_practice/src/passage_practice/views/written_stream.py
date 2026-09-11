"""Written-event stream view — S2.5.

Projects a passage's written notes and notated rests into exact time order,
preserving staff, encoded voice, notation details, and links to the
tie-collapsed logical attacks from S2.4. Consumes only normalized
``ScoreIR`` facts; never parses MusicXML and never recomputes pitch,
timing, tie collapse, or event identity (S0.4 R1/R2/R6/R9/R10/R11).

Design refs:
- docs/semantic_music_extraction_plan.md: Layer 3 ``written_stream`` family
- docs/contracts.md: Derived view + ``written_event_stream`` ("ordered
  written notes and rests")
- docs/decisions.md: D-011 (SourceRef), D-014 (half-open selection),
  D-018 (S-Q004: written-note fields + rests need no ScoreIR promotion;
  whether rests join the stream is S2.5-internal policy)
- views/attack_stream.py (S2.4): sibling conventions — strict ``Passage``
  input, ``source_ref`` identity, per-event schema versions, stable
  diagnostic codes

Semantics:
- Inclusion is half-open on written onset: written notes and rests with
  ``start <= onset < end`` over the passage interval, ordered by
  ``(onset, xml_order, id)``. Simultaneous noteheads (chords, two voices)
  stay separate entries sharing an onset, ordered by document order.
- Timing stays exact ``Fraction`` throughout; durations are written
  (per-notehead), never tie-collapsed. The collapsed sounding duration
  lives on the linked logical attack (S2.4).
- Each note entry links to its collapsed logical attack
  (``logical_ref``). When the linked attack starts outside the passage —
  the tie-continuation-over-boundary case — the entry is still included
  (its notehead is notated inside the passage) with
  ``attack_in_passage=False`` and a stable info diagnostic.
- Sustaining-across-start notes are excluded here; they already live in
  ``SelectedPassage.boundary_context``, never as new attacks or noteheads.
- Staff, encoded voice, and inferred hand are carried as separate facts.
  No musical role is inferred here.
- Rests are first-class entries (per the ``written_event_stream``
  contract — the complement of S2.4, where rests are documented
  omissions). Declared omissions are ``directions``, ``clefs``, and
  ``layout``: dynamics/articulation *interpretation*, clef-change
  tracking, and page geometry never enter the stream.
- The source score and passage are never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Union

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage, ViewType
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import fraction_from_json, fraction_to_json

WRITTEN_STREAM_SCHEMA_VERSION = "written_stream.v1"
WRITTEN_NOTE_EVENT_SCHEMA_VERSION = "written_note_event.v1"
WRITTEN_REST_EVENT_SCHEMA_VERSION = "written_rest_event.v1"

SUPPORTED_WRITTEN_STREAM_VERSIONS = {WRITTEN_STREAM_SCHEMA_VERSION}
SUPPORTED_WRITTEN_NOTE_EVENT_VERSIONS = {WRITTEN_NOTE_EVENT_SCHEMA_VERSION}
SUPPORTED_WRITTEN_REST_EVENT_VERSIONS = {WRITTEN_REST_EVENT_SCHEMA_VERSION}

WRITTEN_STREAM_METHOD_ID = "written_stream_view"
WRITTEN_STREAM_METHOD_VERSION = "v1"

#: Deterministic ordering over notes and rests alike.
WRITTEN_STREAM_ORDERING = "onset,xml_order,id"

#: Directions, clefs, and layout never enter the stream. Rests are entries,
#: not omissions (contracts.md: "ordered written notes and rests").
WRITTEN_STREAM_OMISSIONS = ("directions", "clefs", "layout")


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _order_key(event: Any) -> tuple[Fraction, int, str]:
    xml_order = getattr(event, "xml_order", None)
    order = xml_order if isinstance(xml_order, int) else 10**9
    ident = getattr(event, "note_id", None)
    if ident is None:
        ident = getattr(event, "rest_id", "")
    return (event.onset, order, ident)


def _str_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field} must be tuple")
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field} must contain str, got {item!r}")
    return value


@dataclass(frozen=True, slots=True)
class WrittenNoteEvent:
    """One notated notehead in exact score time.

    Identity is the written note's own ``source_ref`` — no new IDs are
    minted. Durations are written (per notehead); tie collapse is
    referenced, not repeated, through ``logical_ref``.
    ``attack_in_passage`` is False only for tie continuations whose
    collapsed attack starts outside the passage; such entries carry
    notation but no new attack.
    """

    source_ref: SourceRef
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    logical_ref: SourceRef | None
    attack_in_passage: bool
    staff: int | None = None
    voice: str | None = None
    hand: str | None = None
    measure_index: int | None = None
    articulations: tuple[str, ...] = ()
    accidental: str | None = None
    pitch_step: str | None = None
    pitch_octave: int | None = None
    alter: int | None = None
    duration_type: str | None = None
    is_grace: bool = False
    is_chord_continuation: bool = False
    tuplet_actual: int | None = None
    tuplet_normal: int | None = None
    tie_start: bool = False
    tie_stop: bool = False
    xml_order: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceRef):
            raise TypeError("source_ref must be SourceRef")
        if self.source_ref.kind != SourceKind.WRITTEN_NOTE:
            raise ValueError(
                "source_ref kind must be "
                f"'written_note', got {self.source_ref.kind.value!r}"
            )
        if isinstance(self.pitch_midi, bool) or not isinstance(self.pitch_midi, int):
            raise TypeError(f"pitch_midi must be int, got {self.pitch_midi!r}")
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        if not isinstance(self.duration, Fraction):
            raise TypeError("duration must be Fraction")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if self.logical_ref is not None:
            if not isinstance(self.logical_ref, SourceRef):
                raise TypeError("logical_ref must be SourceRef or None")
            if self.logical_ref.kind != SourceKind.LOGICAL_NOTE:
                raise ValueError(
                    "logical_ref kind must be "
                    f"'logical_note', got {self.logical_ref.kind.value!r}"
                )
        if not isinstance(self.attack_in_passage, bool):
            raise TypeError("attack_in_passage must be bool")
        if self.logical_ref is None and self.attack_in_passage:
            raise ValueError("attack_in_passage requires a logical_ref")
        if self.staff is not None and (
            not isinstance(self.staff, int) or self.staff <= 0
        ):
            raise ValueError(f"staff must be positive int or None, got {self.staff!r}")
        if self.voice is not None and not isinstance(self.voice, str):
            raise TypeError("voice must be str or None")
        if self.hand is not None and self.hand not in {"left", "right"}:
            raise ValueError(f"hand must be 'left'/'right' or None, got {self.hand!r}")
        if self.measure_index is not None and not isinstance(self.measure_index, int):
            raise TypeError("measure_index must be int or None")
        object.__setattr__(
            self, "articulations", _str_tuple(self.articulations, "articulations")
        )
        if self.accidental is not None and not isinstance(self.accidental, str):
            raise TypeError("accidental must be str or None")
        if self.pitch_step is not None and not isinstance(self.pitch_step, str):
            raise TypeError("pitch_step must be str or None")
        if self.pitch_octave is not None and not isinstance(self.pitch_octave, int):
            raise TypeError("pitch_octave must be int or None")
        if self.alter is not None and not isinstance(self.alter, int):
            raise TypeError("alter must be int or None")
        if self.duration_type is not None and not isinstance(self.duration_type, str):
            raise TypeError("duration_type must be str or None")
        for flag in ("is_grace", "is_chord_continuation", "tie_start", "tie_stop"):
            if not isinstance(getattr(self, flag), bool):
                raise TypeError(f"{flag} must be bool")
        if self.tuplet_actual is not None and not isinstance(self.tuplet_actual, int):
            raise TypeError("tuplet_actual must be int or None")
        if self.tuplet_normal is not None and not isinstance(self.tuplet_normal, int):
            raise TypeError("tuplet_normal must be int or None")
        if self.xml_order is not None and not isinstance(self.xml_order, int):
            raise TypeError("xml_order must be int or None")

    @property
    def end(self) -> Fraction:
        """Exact written end time (onset + written duration)."""
        return self.onset + self.duration

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": WRITTEN_NOTE_EVENT_SCHEMA_VERSION,
            "kind": "note",
            "source_ref": self.source_ref.to_dict(),
            "pitch_midi": self.pitch_midi,
            "onset": fraction_to_json(self.onset),
            "duration": fraction_to_json(self.duration),
            "attack_in_passage": self.attack_in_passage,
        }
        if self.logical_ref is not None:
            payload["logical_ref"] = self.logical_ref.to_dict()
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.measure_index is not None:
            payload["measure_index"] = self.measure_index
        if self.articulations:
            payload["articulations"] = list(self.articulations)
        if self.accidental is not None:
            payload["accidental"] = self.accidental
        if self.pitch_step is not None:
            payload["pitch_step"] = self.pitch_step
        if self.pitch_octave is not None:
            payload["pitch_octave"] = self.pitch_octave
        if self.alter is not None:
            payload["alter"] = self.alter
        if self.duration_type is not None:
            payload["duration_type"] = self.duration_type
        if self.is_grace:
            payload["is_grace"] = True
        if self.is_chord_continuation:
            payload["is_chord_continuation"] = True
        if self.tuplet_actual is not None:
            payload["tuplet_actual"] = self.tuplet_actual
        if self.tuplet_normal is not None:
            payload["tuplet_normal"] = self.tuplet_normal
        if self.tie_start:
            payload["tie_start"] = True
        if self.tie_stop:
            payload["tie_stop"] = True
        if self.xml_order is not None:
            payload["xml_order"] = self.xml_order
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrittenNoteEvent":
        if not isinstance(data, dict):
            raise TypeError(
                f"WrittenNoteEvent requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_WRITTEN_NOTE_EVENT_VERSIONS:
            raise ValueError(
                f"unsupported WrittenNoteEvent schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_WRITTEN_NOTE_EVENT_VERSIONS)}"
            )
        if data.get("kind", "note") != "note":
            raise ValueError(
                f"WrittenNoteEvent kind must be 'note', got {data.get('kind')!r}"
            )
        try:
            ref_data = data["source_ref"]
            pitch_midi = data["pitch_midi"]
            onset_data = data["onset"]
            duration_data = data["duration"]
            attack_in_passage = data["attack_in_passage"]
        except KeyError as exc:
            raise ValueError(
                f"missing WrittenNoteEvent field {exc.args[0]!r}"
            ) from exc
        raw_articulations = data.get("articulations", [])
        if not isinstance(raw_articulations, list):
            raise ValueError("WrittenNoteEvent articulations must be list")
        logical_data = data.get("logical_ref")
        return cls(
            source_ref=SourceRef.from_dict(ref_data),
            pitch_midi=int(pitch_midi),
            onset=fraction_from_json(onset_data),
            duration=fraction_from_json(duration_data),
            logical_ref=(
                SourceRef.from_dict(logical_data)
                if logical_data is not None
                else None
            ),
            attack_in_passage=bool(attack_in_passage),
            staff=data.get("staff"),
            voice=data.get("voice"),
            hand=data.get("hand"),
            measure_index=data.get("measure_index"),
            articulations=tuple(str(v) for v in raw_articulations),
            accidental=data.get("accidental"),
            pitch_step=data.get("pitch_step"),
            pitch_octave=data.get("pitch_octave"),
            alter=data.get("alter"),
            duration_type=data.get("duration_type"),
            is_grace=bool(data.get("is_grace", False)),
            is_chord_continuation=bool(data.get("is_chord_continuation", False)),
            tuplet_actual=data.get("tuplet_actual"),
            tuplet_normal=data.get("tuplet_normal"),
            tie_start=bool(data.get("tie_start", False)),
            tie_stop=bool(data.get("tie_stop", False)),
            xml_order=data.get("xml_order"),
        )


@dataclass(frozen=True, slots=True)
class WrittenRestEvent:
    """One notated rest in exact score time.

    Rests carry no pitch and no logical-attack link (S0.4 R10: a notated
    rest is a fact; inter-onset gaps are not rests and are never
    synthesized here).
    """

    source_ref: SourceRef
    onset: Fraction
    duration: Fraction
    staff: int | None = None
    voice: str | None = None
    hand: str | None = None
    measure_index: int | None = None
    duration_type: str | None = None
    xml_order: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceRef):
            raise TypeError("source_ref must be SourceRef")
        if self.source_ref.kind != SourceKind.REST:
            raise ValueError(
                f"source_ref kind must be 'rest', got {self.source_ref.kind.value!r}"
            )
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        if not isinstance(self.duration, Fraction):
            raise TypeError("duration must be Fraction")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if self.staff is not None and (
            not isinstance(self.staff, int) or self.staff <= 0
        ):
            raise ValueError(f"staff must be positive int or None, got {self.staff!r}")
        if self.voice is not None and not isinstance(self.voice, str):
            raise TypeError("voice must be str or None")
        if self.hand is not None and self.hand not in {"left", "right"}:
            raise ValueError(f"hand must be 'left'/'right' or None, got {self.hand!r}")
        if self.measure_index is not None and not isinstance(self.measure_index, int):
            raise TypeError("measure_index must be int or None")
        if self.duration_type is not None and not isinstance(self.duration_type, str):
            raise TypeError("duration_type must be str or None")
        if self.xml_order is not None and not isinstance(self.xml_order, int):
            raise TypeError("xml_order must be int or None")

    @property
    def end(self) -> Fraction:
        """Exact rest end time (onset + duration)."""
        return self.onset + self.duration

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": WRITTEN_REST_EVENT_SCHEMA_VERSION,
            "kind": "rest",
            "source_ref": self.source_ref.to_dict(),
            "onset": fraction_to_json(self.onset),
            "duration": fraction_to_json(self.duration),
        }
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.measure_index is not None:
            payload["measure_index"] = self.measure_index
        if self.duration_type is not None:
            payload["duration_type"] = self.duration_type
        if self.xml_order is not None:
            payload["xml_order"] = self.xml_order
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrittenRestEvent":
        if not isinstance(data, dict):
            raise TypeError(
                f"WrittenRestEvent requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_WRITTEN_REST_EVENT_VERSIONS:
            raise ValueError(
                f"unsupported WrittenRestEvent schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_WRITTEN_REST_EVENT_VERSIONS)}"
            )
        if data.get("kind") != "rest":
            raise ValueError(
                f"WrittenRestEvent kind must be 'rest', got {data.get('kind')!r}"
            )
        try:
            ref_data = data["source_ref"]
            onset_data = data["onset"]
            duration_data = data["duration"]
        except KeyError as exc:
            raise ValueError(
                f"missing WrittenRestEvent field {exc.args[0]!r}"
            ) from exc
        return cls(
            source_ref=SourceRef.from_dict(ref_data),
            onset=fraction_from_json(onset_data),
            duration=fraction_from_json(duration_data),
            staff=data.get("staff"),
            voice=data.get("voice"),
            hand=data.get("hand"),
            measure_index=data.get("measure_index"),
            duration_type=data.get("duration_type"),
            xml_order=data.get("xml_order"),
        )


WrittenEvent = Union[WrittenNoteEvent, WrittenRestEvent]


def _event_from_dict(data: dict[str, Any]) -> WrittenEvent:
    if not isinstance(data, dict):
        raise TypeError(f"written event requires dict, got {type(data).__name__}")
    kind = data.get("kind")
    if kind == "note":
        return WrittenNoteEvent.from_dict(data)
    if kind == "rest":
        return WrittenRestEvent.from_dict(data)
    raise ValueError(f"unknown written event kind {kind!r}")


@dataclass(frozen=True, slots=True)
class WrittenStream:
    """Written notes and notated rests for one passage in exact time order.

    - notes: one entry per written notehead with onset in the passage
      interval, ordered by (onset, document order, note ID).
    - rests: one entry per notated rest with onset in the passage
      interval, ordered the same way. Rests are entries here — the
      complement of the S2.4 attack stream, where they are documented
      omissions.
    - ordering documents the sort; grouping is None (flat stream).
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    notes: tuple[WrittenNoteEvent, ...] = ()
    rests: tuple[WrittenRestEvent, ...] = ()
    ordering: str = WRITTEN_STREAM_ORDERING
    grouping: str | None = None
    omissions: tuple[str, ...] = WRITTEN_STREAM_OMISSIONS
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.view_type != ViewType.WRITTEN_EVENT_STREAM:
            raise ValueError(
                "WrittenStream view_type must be "
                f"{ViewType.WRITTEN_EVENT_STREAM.value!r}, got {self.view_type!r}"
            )
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.notes, tuple):
            raise TypeError("notes must be tuple")
        for note in self.notes:
            if not isinstance(note, WrittenNoteEvent):
                raise TypeError(
                    "notes must contain WrittenNoteEvent, "
                    f"got {type(note).__name__}"
                )
        if not isinstance(self.rests, tuple):
            raise TypeError("rests must be tuple")
        for rest in self.rests:
            if not isinstance(rest, WrittenRestEvent):
                raise TypeError(
                    "rests must contain WrittenRestEvent, "
                    f"got {type(rest).__name__}"
                )
        if not isinstance(self.ordering, str) or not self.ordering:
            raise ValueError(
                f"ordering must be non-empty str, got {self.ordering!r}"
            )
        if self.grouping is not None and not isinstance(self.grouping, str):
            raise TypeError("grouping must be str or None")
        if not isinstance(self.omissions, tuple):
            raise TypeError("omissions must be tuple")
        for omission in ("directions", "clefs", "layout"):
            if omission not in self.omissions:
                raise ValueError(
                    f"omissions must declare {omission!r} "
                    "(never projected into the written stream)"
                )
        if "rests" in self.omissions:
            raise ValueError("omissions must not contain 'rests' (rests are entries)")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for diagnostic in self.diagnostics:
            if not isinstance(diagnostic, Diagnostic):
                raise TypeError(
                    "diagnostics must contain Diagnostic, "
                    f"got {type(diagnostic).__name__}"
                )

    def ordered_events(self) -> tuple[WrittenEvent, ...]:
        """All entries (notes and rests) in stream order."""
        return tuple(sorted((*self.notes, *self.rests), key=_order_key))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WRITTEN_STREAM_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "ordering": self.ordering,
            "grouping": self.grouping,
            "omissions": list(self.omissions),
            "notes": [n.to_dict() for n in self.notes],
            "rests": [r.to_dict() for r in self.rests],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrittenStream":
        if not isinstance(data, dict):
            raise TypeError(f"WrittenStream requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_WRITTEN_STREAM_VERSIONS:
            raise ValueError(
                f"unsupported WrittenStream schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_WRITTEN_STREAM_VERSIONS)}"
            )
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(f"missing WrittenStream field {exc.args[0]!r}") from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        raw_notes = data.get("notes", [])
        if not isinstance(raw_notes, list):
            raise ValueError("WrittenStream notes must be list")
        raw_rests = data.get("rests", [])
        if not isinstance(raw_rests, list):
            raise ValueError("WrittenStream rests must be list")
        raw_omissions = data.get("omissions", [])
        if not isinstance(raw_omissions, list):
            raise ValueError("WrittenStream omissions must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("WrittenStream diagnostics must be list")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            notes=tuple(WrittenNoteEvent.from_dict(n) for n in raw_notes),
            rests=tuple(WrittenRestEvent.from_dict(r) for r in raw_rests),
            ordering=str(ordering),
            grouping=data.get("grouping"),
            omissions=tuple(str(o) for o in raw_omissions),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def build_written_stream(
    passage: Passage,
    score: Any,
    *,
    method_id: str = WRITTEN_STREAM_METHOD_ID,
    method_version: str = WRITTEN_STREAM_METHOD_VERSION,
) -> WrittenStream:
    """Build the written-event stream for `passage` over `score`.

    Includes written notes and notated rests with ``start <= onset < end``
    over the passage interval, ordered by ``(onset, xml_order, id)``. Each
    note links to its collapsed logical attack; tie continuations whose
    attack starts outside the passage are kept (notation inside the
    passage) with ``attack_in_passage=False`` and a stable info
    diagnostic. Unmapped written notes and unresolvable passage refs emit
    warnings; an empty result is an explicit valid outcome with an info
    diagnostic. Reads only: neither the score nor the passage is mutated.
    """
    if not isinstance(passage, Passage):
        raise TypeError(f"passage must be Passage, got {type(passage).__name__}")
    start = passage.start.quarters
    end = passage.end.quarters

    in_passage_logical_ids = {
        ref.id
        for ref in passage.event_refs
        if isinstance(ref, SourceRef) and ref.kind == SourceKind.LOGICAL_NOTE
    }

    logical_by_written: dict[str, Any] = {}
    for logical in getattr(score, "logical_notes", []) or []:
        for written_id in getattr(logical, "source_note_ids", None) or ():
            logical_by_written.setdefault(str(written_id), logical)

    diagnostics: list[Diagnostic] = []
    for ref in passage.event_refs:
        if (
            isinstance(ref, SourceRef)
            and ref.kind == SourceKind.LOGICAL_NOTE
            and resolve_ref(score, ref) is None
        ):
            diagnostics.append(
                Diagnostic(
                    code="unresolvable_attack_ref",
                    severity=Severity.WARNING,
                    message=(
                        f"passage ref {ref.id!r} does not resolve "
                        "in this score; written links checked against score facts"
                    ),
                )
            )

    notes: list[WrittenNoteEvent] = []
    outside_attack_refs: list[SourceRef] = []
    for written in getattr(score, "written_notes", []) or []:
        if not start <= written.onset < end:
            continue
        logical = logical_by_written.get(getattr(written, "note_id", None))
        if logical is None:
            diagnostics.append(
                Diagnostic(
                    code="unmapped_written_note",
                    severity=Severity.WARNING,
                    message=(
                        f"written note {getattr(written, 'note_id', '?')!r} maps to "
                        "no collapsed logical attack; link omitted"
                    ),
                )
            )
            logical_ref = None
            attack_in_passage = False
        else:
            logical_ref = SourceRef(id=logical.note_id, kind=SourceKind.LOGICAL_NOTE)
            attack_in_passage = logical.note_id in in_passage_logical_ids
            if not attack_in_passage:
                outside_attack_refs.append(
                    SourceRef(id=written.note_id, kind=SourceKind.WRITTEN_NOTE)
                )
        notes.append(
            WrittenNoteEvent(
                source_ref=SourceRef(
                    id=written.note_id, kind=SourceKind.WRITTEN_NOTE
                ),
                pitch_midi=int(written.pitch_midi),
                onset=written.onset,
                duration=written.duration,
                logical_ref=logical_ref,
                attack_in_passage=attack_in_passage,
                staff=getattr(written, "staff", None),
                voice=getattr(written, "voice", None),
                hand=getattr(written, "hand", None),
                measure_index=getattr(written, "measure_index", None),
                articulations=tuple(getattr(written, "articulations", None) or ()),
                accidental=getattr(written, "accidental", None),
                pitch_step=getattr(written, "pitch_step", None),
                pitch_octave=getattr(written, "pitch_octave", None),
                alter=getattr(written, "alter", None),
                duration_type=getattr(written, "duration_type", None),
                is_grace=bool(getattr(written, "is_grace", False)),
                is_chord_continuation=bool(
                    getattr(written, "is_chord_continuation", False)
                ),
                tuplet_actual=getattr(written, "tuplet_actual", None),
                tuplet_normal=getattr(written, "tuplet_normal", None),
                tie_start=bool(getattr(written, "tie_start", False)),
                tie_stop=bool(getattr(written, "tie_stop", False)),
                xml_order=getattr(written, "xml_order", None),
            )
        )
    if outside_attack_refs:
        outside_attack_refs.sort(key=lambda r: r.id)
        diagnostics.append(
            Diagnostic(
                code="linked_attack_outside_passage",
                severity=Severity.INFO,
                message=(
                    f"{len(outside_attack_refs)} written note(s) link to a "
                    "collapsed attack starting outside the passage "
                    "(tie continuation over the boundary); notation kept, "
                    "no new attack implied"
                ),
                source_refs=tuple(outside_attack_refs),
            )
        )

    rests: list[WrittenRestEvent] = []
    for rest in getattr(score, "rests", []) or []:
        if not start <= rest.onset < end:
            continue
        rests.append(
            WrittenRestEvent(
                source_ref=SourceRef(id=rest.rest_id, kind=SourceKind.REST),
                onset=rest.onset,
                duration=rest.duration,
                staff=getattr(rest, "staff", None),
                voice=getattr(rest, "voice", None),
                hand=getattr(rest, "hand", None),
                measure_index=getattr(rest, "measure_index", None),
                duration_type=getattr(rest, "duration_type", None),
                xml_order=getattr(rest, "xml_order", None),
            )
        )

    notes.sort(key=_order_key)
    rests.sort(key=_order_key)
    if not notes and not rests:
        diagnostics.append(
            Diagnostic(
                code="no_written_events",
                severity=Severity.INFO,
                message="no written notes or rests in the passage interval",
            )
        )
    return WrittenStream(
        view_type=ViewType.WRITTEN_EVENT_STREAM,
        source_passage_id=passage.passage_id,
        method_id=method_id,
        method_version=method_version,
        notes=tuple(notes),
        rests=tuple(rests),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "WRITTEN_NOTE_EVENT_SCHEMA_VERSION",
    "WRITTEN_REST_EVENT_SCHEMA_VERSION",
    "WRITTEN_STREAM_METHOD_ID",
    "WRITTEN_STREAM_METHOD_VERSION",
    "WRITTEN_STREAM_OMISSIONS",
    "WRITTEN_STREAM_ORDERING",
    "WRITTEN_STREAM_SCHEMA_VERSION",
    "WrittenEvent",
    "WrittenNoteEvent",
    "WrittenRestEvent",
    "WrittenStream",
    "build_written_stream",
]
