"""Candidate salience view — S2.8.

Projects a passage's logical attacks into per-event candidate salience
factors: register (pitch height against sounding material), duration,
metric accent (beat placement), explicit accent/dynamic evidence where
available, and pattern-exclusion markers. Consumes only normalized
``ScoreIR`` facts (``LogicalNoteIR`` timing/pitch, ``MeasureIR`` meter,
``WrittenNoteIR`` articulations, ``DirectionIR`` dynamics); never parses
MusicXML and never recomputes pitch, tie collapse, or event identity
(S0.4 R2/R3/R4/R5).

Design refs:
- docs/semantic_music_extraction_plan.md: Layer 3 ``salience_view``
  ("candidate events scored for melodic, bass, or inner-voice salience")
- docs/contracts.md: Derived view (view_type, source passage, method,
  included IDs, ordering, omissions, diagnostics)
- docs/decisions.md: D-011 (SourceRef), D-014 (half-open selection),
  D-015 (two encoded voices do not imply two musical roles),
  D-016 (missing evidence recorded, never zeroed),
  D-018 (S-Q004: attack/written streams + articulation tuples +
  ``DirectionIR`` dynamics are sufficient; slurs are unavailable)
- views/attack_stream.py (S2.4), views/rhythm_grid.py (S2.6),
  views/texture_grid.py (S2.7): sibling conventions — strict ``Passage``
  input, ``source_ref`` identity, per-event schema versions, stable
  diagnostic codes

Semantics:
- One ``SalienceEvent`` per logical attack in the passage, in time order.
  Identity is the logical note's own ``source_ref`` — no new IDs are
  minted.
- ``is_onset_top_note`` is register prominence against all material
  sounding at the attack onset (co-attacks plus earlier attacks still
  sounding through the onset, with exact fractions) — never a role claim.
  In the left-hand-melody negative fixture, a sustained higher RH note
  therefore keeps every LH quarter from being "top", exactly as
  register-only salience must lose there.
- ``is_longest_in_passage`` is the passage-maximum sounding duration —
  a deterministic duration factor, not an interpretation.
- ``beat_index``/``offset_in_beat``/``on_beat`` are metric-placement
  facts from ``MeasureIR`` meter. Unknown meter leaves them ``None``,
  never guessed (D-018/rhythm-grid policy).
- ``accent_marks`` lists explicit accent-like articulation names
  (``accent``, ``strong-accent``) found on the written noteheads of the
  attack. ``dynamic_levels`` lists the dynamics direction values in
  effect at the onset (latest ``kind="dynamics"`` direction at/before
  onset). Both are facts; neither is a score.
- ``slur_evidence`` is always empty with a diagnostic: slur phrase-marking
  is absent upstream (gated task U1 in D-018), so slur salience is
  unavailable, not zero.
- ``pattern_exclusion_markers`` is always empty with a diagnostic:
  accompaniment-pattern detection belongs to the S3.4 detector; this view
  exposes only the *candidate* factors the detector may later use to
  exclude events, and none are computed here.
- The view preserves contradictory cues (e.g., top-of-onset and
  longest-duration pointing at different notes) rather than collapsing
  them; contradiction resolution belongs downstream (S1.3/D-015).
- Rest facts live in the S2.5 written stream; layout and harmony never
  enter. Only ``dynamics`` direction values are projected; other
  direction kinds are not read.
- The source score and passage are never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage, ViewType
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import fraction_from_json, fraction_to_json

SALIENCE_VIEW_SCHEMA_VERSION = "salience_view.v1"
SALIENCE_EVENT_SCHEMA_VERSION = "salience_event.v1"

SUPPORTED_SALIENCE_VIEW_VERSIONS = {SALIENCE_VIEW_SCHEMA_VERSION}
SUPPORTED_SALIENCE_EVENT_VERSIONS = {SALIENCE_EVENT_SCHEMA_VERSION}

SALIENCE_VIEW_METHOD_ID = "salience_view"
SALIENCE_VIEW_METHOD_VERSION = "v1"

#: Events ordered by onset; ties broken by document order, then note ID.
SALIENCE_VIEW_ORDERING = "onset,xml_order,note_id"

#: Layout and harmony never enter; rest facts live in the S2.5 written
#: stream. Only ``dynamics`` direction values are projected — other
#: direction kinds are not read.
SALIENCE_VIEW_OMISSIONS = ("layout", "harmony", "rests")

#: Explicit accent-like articulation names treated as accent salience
#: evidence. Names come from the MusicXML articulation element tags
#: normalized upstream (e.g. "accent", "strong-accent").
_ACCENT_MARKS = {"accent", "strong-accent"}


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


def _check_names(values: Any, field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} must contain non-empty str, got {value!r}")
    if tuple(sorted(values)) != values or len(set(values)) != len(values):
        raise ValueError(f"{field} must be sorted unique names")
    return values


def _locate_measure(measures: list[Any], onset: Fraction) -> Any | None:
    for measure in measures:
        start = getattr(measure, "start", None)
        end = getattr(measure, "end", None)
        if isinstance(start, Fraction) and isinstance(end, Fraction):
            if start <= onset < end:
                return measure
    return None


def _beat_length(measure: Any | None) -> Fraction | None:
    """Length of one beat in quarters, or None when the meter is unknown."""
    if measure is None:
        return None
    beat_type = getattr(measure, "time_beat_type", None)
    if not isinstance(beat_type, int) or beat_type <= 0:
        return None
    return Fraction(4, beat_type)


@dataclass(frozen=True, slots=True)
class SalienceEvent:
    """One logical attack with its candidate salience factors.

    All factors are deterministic projections of score facts or of
    sounding-material bookkeeping; none is a fused salience score (that is
    S3.2 detector work). ``slur_evidence`` and ``pattern_exclusion_markers``
    are always empty in v1 and are documented as unavailable diagnostics on
    the view, never silently zeroed.
    """

    source_ref: SourceRef
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    staff: int | None = None
    voice: str | None = None
    hand: str | None = None
    measure_index: int | None = None
    beat_index: int | None = None
    offset_in_beat: Fraction | None = None
    on_beat: bool | None = None
    accent_marks: tuple[str, ...] = ()
    dynamic_levels: tuple[str, ...] = ()
    slur_evidence: tuple[str, ...] = ()
    pattern_exclusion_markers: tuple[str, ...] = ()
    is_onset_top_note: bool = False
    is_longest_in_passage: bool = False
    xml_order: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceRef):
            raise TypeError("source_ref must be SourceRef")
        if self.source_ref.kind != SourceKind.LOGICAL_NOTE:
            raise ValueError(
                "source_ref kind must be "
                f"'logical_note', got {self.source_ref.kind.value!r}"
            )
        if isinstance(self.pitch_midi, bool) or not isinstance(self.pitch_midi, int):
            raise TypeError(f"pitch_midi must be int, got {self.pitch_midi!r}")
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
        beat_fields = (self.beat_index, self.offset_in_beat, self.on_beat)
        if any(b is None for b in beat_fields) and any(b is not None for b in beat_fields):
            raise ValueError(
                "beat_index, offset_in_beat, and on_beat must be all set or all None"
            )
        if self.beat_index is not None:
            if not isinstance(self.beat_index, int):
                raise TypeError("beat_index must be int or None")
            if not isinstance(self.offset_in_beat, Fraction):
                raise TypeError("offset_in_beat must be Fraction or None")
            if not isinstance(self.on_beat, bool):
                raise TypeError("on_beat must be bool or None")
        object.__setattr__(
            self, "accent_marks", _check_names(self.accent_marks, "accent_marks")
        )
        object.__setattr__(
            self, "dynamic_levels", _check_names(self.dynamic_levels, "dynamic_levels")
        )
        object.__setattr__(
            self, "slur_evidence", _check_names(self.slur_evidence, "slur_evidence")
        )
        object.__setattr__(
            self,
            "pattern_exclusion_markers",
            _check_names(
                self.pattern_exclusion_markers, "pattern_exclusion_markers"
            ),
        )
        for flag in ("is_onset_top_note", "is_longest_in_passage"):
            if not isinstance(getattr(self, flag), bool):
                raise TypeError(f"{flag} must be bool")
        if self.xml_order is not None and not isinstance(self.xml_order, int):
            raise TypeError("xml_order must be int or None")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SALIENCE_EVENT_SCHEMA_VERSION,
            "source_ref": self.source_ref.to_dict(),
            "pitch_midi": self.pitch_midi,
            "onset": fraction_to_json(self.onset),
            "duration": fraction_to_json(self.duration),
            "is_onset_top_note": self.is_onset_top_note,
            "is_longest_in_passage": self.is_longest_in_passage,
        }
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.measure_index is not None:
            payload["measure_index"] = self.measure_index
        if self.beat_index is not None:
            payload["beat_index"] = self.beat_index
        if self.offset_in_beat is not None:
            payload["offset_in_beat"] = fraction_to_json(self.offset_in_beat)
        if self.on_beat is not None:
            payload["on_beat"] = self.on_beat
        if self.accent_marks:
            payload["accent_marks"] = list(self.accent_marks)
        if self.dynamic_levels:
            payload["dynamic_levels"] = list(self.dynamic_levels)
        if self.slur_evidence:
            payload["slur_evidence"] = list(self.slur_evidence)
        if self.pattern_exclusion_markers:
            payload["pattern_exclusion_markers"] = list(
                self.pattern_exclusion_markers
            )
        if self.xml_order is not None:
            payload["xml_order"] = self.xml_order
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SalienceEvent":
        if not isinstance(data, dict):
            raise TypeError(
                f"SalienceEvent requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_SALIENCE_EVENT_VERSIONS:
            raise ValueError(
                f"unsupported SalienceEvent schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SALIENCE_EVENT_VERSIONS)}"
            )
        try:
            ref_data = data["source_ref"]
            pitch_midi = data["pitch_midi"]
            onset_data = data["onset"]
            duration_data = data["duration"]
            is_onset_top_note = data["is_onset_top_note"]
            is_longest_in_passage = data["is_longest_in_passage"]
        except KeyError as exc:
            raise ValueError(
                f"missing SalienceEvent field {exc.args[0]!r}"
            ) from exc
        for field in ("accent_marks", "dynamic_levels", "slur_evidence",
                      "pattern_exclusion_markers"):
            raw = data.get(field, [])
            if not isinstance(raw, list):
                raise ValueError(f"SalienceEvent {field} must be list")
        return cls(
            source_ref=SourceRef.from_dict(ref_data),
            pitch_midi=int(pitch_midi),
            onset=fraction_from_json(onset_data),
            duration=fraction_from_json(duration_data),
            staff=data.get("staff"),
            voice=data.get("voice"),
            hand=data.get("hand"),
            measure_index=data.get("measure_index"),
            beat_index=data.get("beat_index"),
            offset_in_beat=(
                fraction_from_json(data["offset_in_beat"])
                if "offset_in_beat" in data
                else None
            ),
            on_beat=data.get("on_beat"),
            accent_marks=tuple(str(v) for v in data.get("accent_marks", [])),
            dynamic_levels=tuple(str(v) for v in data.get("dynamic_levels", [])),
            slur_evidence=tuple(str(v) for v in data.get("slur_evidence", [])),
            pattern_exclusion_markers=tuple(
                str(v) for v in data.get("pattern_exclusion_markers", [])
            ),
            is_onset_top_note=bool(is_onset_top_note),
            is_longest_in_passage=bool(is_longest_in_passage),
            xml_order=data.get("xml_order"),
        )


@dataclass(frozen=True, slots=True)
class SalienceView:
    """Candidate salience factors for one passage, in time order.

    - events: one entry per logical attack. ``is_onset_top_note`` and
      ``is_longest_in_passage`` are candidate markers only — no fused
      salience score, no role claim (that is S3 detector work).
    - ordering documents the sort; grouping is None (flat view).
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    events: tuple[SalienceEvent, ...] = ()
    ordering: str = SALIENCE_VIEW_ORDERING
    grouping: str | None = None
    omissions: tuple[str, ...] = SALIENCE_VIEW_OMISSIONS
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.view_type != ViewType.SALIENCE_VIEW:
            raise ValueError(
                "SalienceView view_type must be "
                f"{ViewType.SALIENCE_VIEW.value!r}, got {self.view_type!r}"
            )
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.events, tuple):
            raise TypeError("events must be tuple")
        for event in self.events:
            if not isinstance(event, SalienceEvent):
                raise TypeError(
                    "events must contain SalienceEvent, "
                    f"got {type(event).__name__}"
                )
        keys = [_event_key(e) for e in self.events]
        if keys != sorted(keys):
            raise ValueError("events must be sorted by (onset, xml_order, note_id)")
        if not isinstance(self.ordering, str) or not self.ordering:
            raise ValueError(
                f"ordering must be non-empty str, got {self.ordering!r}"
            )
        if self.grouping is not None and not isinstance(self.grouping, str):
            raise TypeError("grouping must be str or None")
        if not isinstance(self.omissions, tuple):
            raise TypeError("omissions must be tuple")
        for omission in ("layout", "harmony", "rests"):
            if omission not in self.omissions:
                raise ValueError(
                    f"omissions must declare {omission!r} "
                    "(never projected into the salience view)"
                )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def summary(self) -> dict[str, Any]:
        """Passage-level candidate-factor facts derived deterministically
        from the events. Keys are stable for S3.2 detector tests."""
        return {
            "event_count": len(self.events),
            "onset_count": len({e.onset for e in self.events}),
            "top_note_refs": sorted(
                {e.source_ref.id for e in self.events if e.is_onset_top_note}
            ),
            "longest_duration_refs": sorted(
                {e.source_ref.id for e in self.events if e.is_longest_in_passage}
            ),
            "events_with_accent_marks": sum(
                1 for e in self.events if e.accent_marks
            ),
            "events_with_dynamic_evidence": sum(
                1 for e in self.events if e.dynamic_levels
            ),
            "events_without_dynamic_evidence": sum(
                1 for e in self.events if not e.dynamic_levels
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SALIENCE_VIEW_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "events": [e.to_dict() for e in self.events],
            "ordering": self.ordering,
            "grouping": self.grouping,
            "omissions": list(self.omissions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SalienceView":
        if not isinstance(data, dict):
            raise TypeError(f"SalienceView requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_SALIENCE_VIEW_VERSIONS:
            raise ValueError(
                f"unsupported SalienceView schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SALIENCE_VIEW_VERSIONS)}"
            )
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(f"missing SalienceView field {exc.args[0]!r}") from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        raw_events = data.get("events", [])
        if not isinstance(raw_events, list):
            raise ValueError("SalienceView events must be list")
        raw_omissions = data.get("omissions", [])
        if not isinstance(raw_omissions, list):
            raise ValueError("SalienceView omissions must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("SalienceView diagnostics must be list")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            events=tuple(SalienceEvent.from_dict(e) for e in raw_events),
            ordering=str(ordering),
            grouping=data.get("grouping"),
            omissions=tuple(str(o) for o in raw_omissions),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def _event_key(event: SalienceEvent) -> tuple[Fraction, int, str]:
    order = event.xml_order if event.xml_order is not None else 10**9
    return (event.onset, order, event.source_ref.id)


def _articulations_for(written_by_id: dict[str, Any], logical: Any) -> tuple[str, ...]:
    """Union of articulation names across the attack's written noteheads."""
    marks: set[str] = set()
    for written_id in getattr(logical, "source_note_ids", None) or ():
        written = written_by_id.get(str(written_id))
        if written is None:
            continue
        for name in getattr(written, "articulations", None) or ():
            if name in _ACCENT_MARKS:
                marks.add(name)
    return tuple(sorted(marks))


def _dynamic_levels_at(score: Any, onset: Fraction) -> tuple[str, ...]:
    """Dynamics-direction values in effect at `onset` (latest at/before
    onset with a matching start). Empty when no dynamic evidence exists —
    recorded by the builder as a diagnostic, never treated as zero."""
    candidates = [
        d
        for d in getattr(score, "directions", []) or []
        if getattr(d, "kind", None) == "dynamics"
        and isinstance(getattr(d, "start", None), Fraction)
        and d.start <= onset
        and (getattr(d, "end", None) is None or onset < d.end)
    ]
    if not candidates:
        return ()
    latest = max(candidates, key=lambda d: d.start)
    levels = {
        part.strip()
        for part in str(latest.value).split(",")
        if part.strip()
    }
    return tuple(sorted(levels))


def build_salience_view(
    passage: Passage,
    score: Any,
    *,
    method_id: str = SALIENCE_VIEW_METHOD_ID,
    method_version: str = SALIENCE_VIEW_METHOD_VERSION,
) -> SalienceView:
    """Build the candidate salience view for `passage` over `score`.

    Resolves the passage's logical-note refs (skipping non-logical refs
    and unresolvable refs with diagnostics, never failing), computes
    per-event candidate factors from score facts, and preserves
    contradictory cues rather than resolving them. Slur and
    pattern-exclusion evidence are declared unavailable with diagnostics
    (never silently zeroed); an empty result is an explicit valid outcome
    with an info diagnostic. Reads only: neither the score nor the
    passage is mutated.
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
                    "from the salience view"
                ),
            )
        )
    resolved.sort(key=_order_key)

    measures = getattr(score, "measures", []) or []
    written_by_id: dict[str, Any] = {}
    for written in getattr(score, "written_notes", []) or []:
        written_by_id.setdefault(str(getattr(written, "note_id", None)), written)

    # Register prominence: for each onset, the top pitch among all material
    # sounding at that onset (co-attacks plus sustained-through-onset),
    # including notes outside the passage that began earlier and sustain in.
    all_logical = list(getattr(score, "logical_notes", []) or [])
    sounding_top: dict[Fraction, int] = {}
    for note in resolved:
        top = note.pitch_midi
        for other in all_logical:
            if other.onset <= note.onset < other.onset + other.duration:
                if other.pitch_midi > top:
                    top = other.pitch_midi
        sounding_top[note.onset] = max(
            sounding_top.get(note.onset, top), top
        )

    longest = max((n.duration for n in resolved), default=None)

    missing_dynamic_refs: list[SourceRef] = []
    meterless_refs: list[SourceRef] = []
    events: list[SalienceEvent] = []
    for note in resolved:
        measure = _locate_measure(measures, note.onset)
        beat_len = _beat_length(measure)
        cell_ref = SourceRef(id=note.note_id, kind=SourceKind.LOGICAL_NOTE)
        if measure is None or beat_len is None:
            meterless_refs.append(cell_ref)
            beat_index = None
            offset_in_beat = None
            on_beat = None
        else:
            rel = note.onset - measure.start
            beat_index = int(rel // beat_len)
            offset_in_beat = rel - Fraction(beat_index) * beat_len
            on_beat = offset_in_beat == 0
        dynamics = _dynamic_levels_at(score, note.onset)
        if not dynamics:
            missing_dynamic_refs.append(cell_ref)
        events.append(
            SalienceEvent(
                source_ref=cell_ref,
                pitch_midi=int(note.pitch_midi),
                onset=note.onset,
                duration=note.duration,
                staff=getattr(note, "staff", None),
                voice=getattr(note, "voice", None),
                hand=getattr(note, "hand", None),
                measure_index=getattr(note, "measure_index", None),
                beat_index=beat_index,
                offset_in_beat=offset_in_beat,
                on_beat=on_beat,
                accent_marks=_articulations_for(written_by_id, note),
                dynamic_levels=dynamics,
                is_onset_top_note=note.pitch_midi == sounding_top.get(note.onset),
                is_longest_in_passage=(
                    longest is not None and note.duration == longest
                ),
                xml_order=getattr(note, "xml_order", None),
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

    if events:
        if missing_dynamic_refs:
            missing_dynamic_refs.sort(key=lambda r: r.id)
            diagnostics.append(
                Diagnostic(
                    code="missing_dynamic_evidence",
                    severity=Severity.INFO,
                    message=(
                        f"{len(missing_dynamic_refs)} event(s) have no "
                        "dynamics-direction evidence at onset; recorded, "
                        "never zeroed"
                    ),
                    source_refs=tuple(missing_dynamic_refs),
                )
            )
        diagnostics.append(
            Diagnostic(
                code="slur_evidence_unavailable",
                severity=Severity.INFO,
                message=(
                    "slur phrase-marking is not supported upstream "
                    "(gated task U1, D-018); slur salience is unavailable, "
                    "not zero"
                ),
            )
        )
        diagnostics.append(
            Diagnostic(
                code="pattern_exclusion_not_available",
                severity=Severity.INFO,
                message=(
                    "accompaniment-pattern detection belongs to the S3.4 "
                    "detector; no pattern-exclusion markers are computed "
                    "in this view"
                ),
            )
        )
    else:
        diagnostics.append(
            Diagnostic(
                code="no_salience_events",
                severity=Severity.INFO,
                message="no resolvable logical attacks in the passage interval",
            )
        )
    return SalienceView(
        view_type=ViewType.SALIENCE_VIEW,
        source_passage_id=passage.passage_id,
        method_id=method_id,
        method_version=method_version,
        events=tuple(events),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "SALIENCE_EVENT_SCHEMA_VERSION",
    "SALIENCE_VIEW_METHOD_ID",
    "SALIENCE_VIEW_METHOD_VERSION",
    "SALIENCE_VIEW_OMISSIONS",
    "SALIENCE_VIEW_ORDERING",
    "SALIENCE_VIEW_SCHEMA_VERSION",
    "SalienceEvent",
    "SalienceView",
    "build_salience_view",
]