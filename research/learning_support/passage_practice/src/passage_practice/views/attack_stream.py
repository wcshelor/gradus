"""Tie-collapsed attack stream view — S2.4.

Projects a passage's logical-note refs into one deterministic,
time-ordered attack sequence with exact rational timing and stable source
refs. Ties arrive already collapsed (`LogicalNoteIR` keeps the full
`source_note_ids` chain); rests are not attacks and are recorded as
documented omissions, never synthesized into the stream. No inference is
performed, so the view carries no confidence.

Design refs:
- docs/semantic_music_extraction_plan.md: Layer 3 `attack_stream`
- docs/contracts.md: Derived view (view_type, source passage, method,
  included IDs, ordering, omissions, diagnostics)
- docs/decisions.md: D-018 (no ScoreIR promotion needed for S2 views)
- models/passage.py: `ViewType.LOGICAL_ATTACK_STREAM` (reused, not copied)
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage, ViewType
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import (
    fraction_from_json,
    fraction_to_json,
)

ATTACK_STREAM_SCHEMA_VERSION = "attack_stream.v1"
ATTACK_EVENT_SCHEMA_VERSION = "attack_event.v1"

SUPPORTED_ATTACK_STREAM_VERSIONS = {ATTACK_STREAM_SCHEMA_VERSION}
SUPPORTED_ATTACK_EVENT_VERSIONS = {ATTACK_EVENT_SCHEMA_VERSION}

ATTACK_STREAM_METHOD_ID = "attack_stream_view"
ATTACK_STREAM_METHOD_VERSION = "v1"


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


@dataclass(frozen=True, slots=True)
class AttackEvent:
    """One tie-collapsed attack: exact timing plus source provenance.

    Identity is the logical note's own `SourceRef` — no new IDs are
    minted. `source_note_ids` preserves the tie chain behind the attack.
    Staff, encoded voice, and inferred hand travel as separate qualifiers;
    musical role is never inferred here.
    """

    source_ref: SourceRef
    onset: Fraction
    duration: Fraction
    pitch_midi: int
    staff: int | None = None
    voice: str | None = None
    hand: str | None = None
    measure_index: int | None = None
    source_note_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, SourceRef):
            raise TypeError("source_ref must be SourceRef")
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        if not isinstance(self.duration, Fraction):
            raise TypeError("duration must be Fraction")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if isinstance(self.pitch_midi, bool) or not isinstance(
            self.pitch_midi, int
        ):
            raise TypeError(f"pitch_midi must be int, got {self.pitch_midi!r}")
        if self.staff is not None and (
            not isinstance(self.staff, int) or self.staff <= 0
        ):
            raise ValueError(f"staff must be positive int or None, got {self.staff!r}")
        if self.voice is not None and not isinstance(self.voice, str):
            raise TypeError("voice must be str or None")
        if self.hand is not None and self.hand not in {"left", "right"}:
            raise ValueError(f"hand must be 'left'/'right' or None, got {self.hand!r}")
        if self.measure_index is not None and not isinstance(
            self.measure_index, int
        ):
            raise TypeError("measure_index must be int or None")
        if not isinstance(self.source_note_ids, tuple):
            raise TypeError("source_note_ids must be tuple")
        for note_id in self.source_note_ids:
            if not isinstance(note_id, str) or not note_id:
                raise ValueError(
                    "source_note_ids must contain non-empty str, "
                    f"got {note_id!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": ATTACK_EVENT_SCHEMA_VERSION,
            "source_ref": self.source_ref.to_dict(),
            "onset": fraction_to_json(self.onset),
            "duration": fraction_to_json(self.duration),
            "pitch_midi": self.pitch_midi,
        }
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.measure_index is not None:
            payload["measure_index"] = self.measure_index
        if self.source_note_ids:
            payload["source_note_ids"] = list(self.source_note_ids)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackEvent":
        if not isinstance(data, dict):
            raise TypeError(f"AttackEvent requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_ATTACK_EVENT_VERSIONS:
            raise ValueError(
                f"unsupported AttackEvent schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_ATTACK_EVENT_VERSIONS)}"
            )
        try:
            ref_data = data["source_ref"]
            onset_data = data["onset"]
            duration_data = data["duration"]
            pitch_midi = data["pitch_midi"]
        except KeyError as exc:
            raise ValueError(
                f"missing AttackEvent field {exc.args[0]!r}"
            ) from exc
        raw_chain = data.get("source_note_ids", [])
        if not isinstance(raw_chain, list):
            raise ValueError("AttackEvent source_note_ids must be list")
        return cls(
            source_ref=SourceRef.from_dict(ref_data),
            onset=fraction_from_json(onset_data),
            duration=fraction_from_json(duration_data),
            pitch_midi=pitch_midi,
            staff=data.get("staff"),
            voice=data.get("voice"),
            hand=data.get("hand"),
            measure_index=data.get("measure_index"),
            source_note_ids=tuple(str(v) for v in raw_chain),
        )


@dataclass(frozen=True, slots=True)
class AttackStream:
    """Deterministic tie-collapsed attack sequence for one passage.

    - attacks: one entry per resolved logical attack, ordered by
      (onset, document order, note ID). Simultaneous attacks (chords)
      share an onset and keep document order; nothing is grouped.
    - omitted_rest_refs: rests sounding anywhere in the passage interval.
      Rests are declared omissions (mirroring passage selection), listed
      for audit, never converted into attacks.
    - ordering documents the sort; grouping is None (flat stream —
      onset grouping belongs to the S2.7 texture grid).
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    attacks: tuple[AttackEvent, ...] = ()
    omitted_rest_refs: tuple[SourceRef, ...] = ()
    ordering: str = "onset"
    grouping: str | None = None
    omissions: tuple[str, ...] = ("rests",)
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.view_type != ViewType.LOGICAL_ATTACK_STREAM:
            raise ValueError(
                "AttackStream view_type must be "
                f"{ViewType.LOGICAL_ATTACK_STREAM.value!r}, got {self.view_type!r}"
            )
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.attacks, tuple):
            raise TypeError("attacks must be tuple")
        for attack in self.attacks:
            if not isinstance(attack, AttackEvent):
                raise TypeError(
                    "attacks must contain AttackEvent, "
                    f"got {type(attack).__name__}"
                )
        if not isinstance(self.omitted_rest_refs, tuple):
            raise TypeError("omitted_rest_refs must be tuple")
        for r in self.omitted_rest_refs:
            if not isinstance(r, SourceRef) or r.kind != SourceKind.REST:
                raise ValueError(
                    "omitted_rest_refs must contain REST SourceRefs, "
                    f"got {r!r}"
                )
        if not isinstance(self.ordering, str) or not self.ordering:
            raise ValueError(
                f"ordering must be non-empty str, got {self.ordering!r}"
            )
        if self.grouping is not None and not isinstance(self.grouping, str):
            raise TypeError("grouping must be str or None")
        if not isinstance(self.omissions, tuple):
            raise TypeError("omissions must be tuple")
        for o in self.omissions:
            if not isinstance(o, str) or not o:
                raise ValueError(
                    f"omissions must contain non-empty str, got {o!r}"
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
            "schema_version": ATTACK_STREAM_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "attacks": [a.to_dict() for a in self.attacks],
            "omitted_rest_refs": [r.to_dict() for r in self.omitted_rest_refs],
            "ordering": self.ordering,
            "grouping": self.grouping,
            "omissions": list(self.omissions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackStream":
        if not isinstance(data, dict):
            raise TypeError(
                f"AttackStream requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_ATTACK_STREAM_VERSIONS:
            raise ValueError(
                f"unsupported AttackStream schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_ATTACK_STREAM_VERSIONS)}"
            )
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            attacks_data = data["attacks"]
            omitted_data = data["omitted_rest_refs"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(
                f"missing AttackStream field {exc.args[0]!r}"
            ) from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        if not isinstance(attacks_data, list):
            raise ValueError("AttackStream attacks must be list")
        if not isinstance(omitted_data, list):
            raise ValueError("AttackStream omitted_rest_refs must be list")
        raw_omissions = data.get("omissions", ["rests"])
        if not isinstance(raw_omissions, list):
            raise ValueError("AttackStream omissions must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("AttackStream diagnostics must be list")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            attacks=tuple(AttackEvent.from_dict(a) for a in attacks_data),
            omitted_rest_refs=tuple(SourceRef.from_dict(r) for r in omitted_data),
            ordering=str(ordering),
            grouping=data.get("grouping"),
            omissions=tuple(str(o) for o in raw_omissions),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def build_attack_stream(
    passage: Passage,
    score: Any,
    *,
    method_id: str = ATTACK_STREAM_METHOD_ID,
    method_version: str = ATTACK_STREAM_METHOD_VERSION,
) -> AttackStream:
    """Build the deterministic attack sequence for `passage` over `score`.

    Resolves the passage's logical-note refs (skipping non-logical refs
    and unresolvable refs with diagnostics, never failing), orders attacks
    by (onset, document order, note ID), and records rests sounding in the
    passage interval as documented omissions. Reads only: neither the
    score nor the passage is mutated.
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
                    "from the attack stream"
                ),
            )
        )
    resolved.sort(key=_order_key)
    attacks = tuple(
        AttackEvent(
            source_ref=SourceRef(id=note.note_id, kind=SourceKind.LOGICAL_NOTE),
            onset=note.onset,
            duration=note.duration,
            pitch_midi=note.pitch_midi,
            staff=note.staff,
            voice=note.voice,
            hand=note.hand,
            measure_index=note.measure_index,
            source_note_ids=tuple(note.source_note_ids),
        )
        for note in resolved
    )
    start = passage.start.quarters
    end = passage.end.quarters
    omitted_rests = tuple(
        SourceRef(id=rest.rest_id, kind=SourceKind.REST)
        for rest in sorted(
            getattr(score, "rests", []) or [],
            key=lambda r: (r.onset, r.rest_id),
        )
        if rest.onset < end and rest.onset + rest.duration > start
    )
    if omitted_rests:
        diagnostics.append(
            Diagnostic(
                code="rests_omitted",
                severity=Severity.INFO,
                message=(
                    f"{len(omitted_rests)} rest(s) sound in the passage "
                    "interval; attacks only, rests listed as omissions"
                ),
            )
        )
    if not attacks:
        diagnostics.append(
            Diagnostic(
                code="no_attacks",
                severity=Severity.INFO,
                message="no resolvable logical attacks in the passage interval",
            )
        )
    return AttackStream(
        view_type=ViewType.LOGICAL_ATTACK_STREAM,
        source_passage_id=passage.passage_id,
        method_id=method_id,
        method_version=method_version,
        attacks=attacks,
        omitted_rest_refs=omitted_rests,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "ATTACK_EVENT_SCHEMA_VERSION",
    "ATTACK_STREAM_METHOD_ID",
    "ATTACK_STREAM_METHOD_VERSION",
    "ATTACK_STREAM_SCHEMA_VERSION",
    "AttackEvent",
    "AttackStream",
    "build_attack_stream",
]
