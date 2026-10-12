"""Texture grid view — S2.7.

Projects a passage's logical attacks into per-onset simultaneity slices
plus grid-level density summaries. Consumes only normalized ``ScoreIR``
facts (``LogicalNoteIR`` timing, staff/voice/hand qualifiers); never
parses MusicXML and never recomputes pitch, tie collapse, or event
identity (S0.4 R2/R3/R4/R5).

Design refs:
- docs/contracts.md: Derived view (view_type, source passage, method,
  included IDs, ordering, omissions, diagnostics)
- docs/practice_chunk_objects.md: views provide chunk-citable evidence
- docs/decisions.md: D-011 (SourceRef), D-014 (half-open selection),
  D-015 (two encoded voices do not imply two musical roles),
  D-018 (S-Q004: attack/written streams + onset groups + durations are
  sufficient; no ScoreIR promotion needed)
- views/attack_stream.py (S2.4): sibling conventions — strict ``Passage``
  input, ``source_ref`` identity, per-event schema versions, stable
  diagnostic codes

Semantics:
- One slice per distinct attack onset in the passage, in time order.
  ``attack_refs`` are the logical attacks starting exactly at the slice
  onset (chords stay separate entries sharing an onset, in document
  order); ``chord_size`` is their count. Simultaneity here is co-attack
  bookkeeping — chord-vs-arpeggiation interpretation belongs downstream
  (S2.11/S3), which reads chord sizes against inter-onset timing.
- ``sustained_refs`` are passage attacks that started strictly before
  the slice onset and still sound through it (``onset < t < end`` with
  exact fractions). ``sustained_under_moving`` is true exactly when a
  slice has both new attacks (always, by construction) and sustained
  material — the melody-plus-accompaniment shape. Notes sustaining
  from before the passage start are out of scope: they live in
  ``SelectedPassage.boundary_context``, and this view, like its
  siblings, is a pure function of (``Passage``, ``ScoreIR``).
- ``voices`` and ``hands`` are sorted unique encoded-voice / inferred-hand
  facts across attacks plus sustained notes, kept separate per the
  architecture rule. Voice count never implies role count (D-015).
- ``summary()`` derives grid-level density facts (total attacks, onset
  count, max chord size, chordal onsets, sustained-under-moving count,
  distinct voices/hands) deterministically from the slices — no stored
  duplicate state, no version drift.
- Pitch content, dynamics interpretation, and layout are declared
  omissions. Rest facts live in the S2.5 written stream.
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

TEXTURE_GRID_SCHEMA_VERSION = "texture_grid.v1"
TEXTURE_SLICE_SCHEMA_VERSION = "texture_slice.v1"

SUPPORTED_TEXTURE_GRID_VERSIONS = {TEXTURE_GRID_SCHEMA_VERSION}
SUPPORTED_TEXTURE_SLICE_VERSIONS = {TEXTURE_SLICE_SCHEMA_VERSION}

TEXTURE_GRID_METHOD_ID = "texture_grid_view"
TEXTURE_GRID_METHOD_VERSION = "v1"

#: Slices ordered by onset; refs within a slice in document order.
TEXTURE_GRID_ORDERING = "onset,xml_order,note_id"

#: Pitch content, dynamics interpretation, and page geometry never enter
#: the grid. Rest facts live in the S2.5 written stream.
TEXTURE_GRID_OMISSIONS = ("pitch", "directions", "layout")


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


def _check_refs(refs: Any, field: str, *, allow_empty: bool) -> tuple[SourceRef, ...]:
    if not isinstance(refs, tuple) or (not allow_empty and not refs):
        raise TypeError(
            f"{field} must be a {'possibly-empty' if allow_empty else 'non-empty'} tuple"
        )
    for ref in refs:
        if not isinstance(ref, SourceRef):
            raise TypeError(
                f"{field} must contain SourceRef, got {type(ref).__name__}"
            )
        if ref.kind != SourceKind.LOGICAL_NOTE:
            raise ValueError(
                f"{field} must contain logical_note refs, "
                f"got {ref.kind.value!r}"
            )
    return refs


def _check_names(values: Any, field: str, allowed: set[str] | None) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"{field} must contain non-empty str, got {value!r}"
            )
        if allowed is not None and value not in allowed:
            raise ValueError(
                f"{field} must contain one of {sorted(allowed)}, got {value!r}"
            )
    if tuple(sorted(values)) != values or len(set(values)) != len(values):
        raise ValueError(f"{field} must be sorted unique names")
    return values


@dataclass(frozen=True, slots=True)
class TextureSlice:
    """One attack onset with simultaneity and sustain facts.

    Identity of every event is its logical note's own ``source_ref`` —
    no new IDs are minted. ``attack_refs`` is non-empty by construction
    (slices exist only where attacks start); ``sustained_refs`` holds
    earlier-starting passage attacks sounding through the onset.
    """

    onset: Fraction
    attack_refs: tuple[SourceRef, ...] = ()
    sustained_refs: tuple[SourceRef, ...] = ()
    voices: tuple[str, ...] = ()
    hands: tuple[str, ...] = ()
    sustained_under_moving: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.onset, Fraction):
            raise TypeError("onset must be Fraction")
        object.__setattr__(
            self, "attack_refs", _check_refs(self.attack_refs, "attack_refs", allow_empty=False)
        )
        object.__setattr__(
            self,
            "sustained_refs",
            _check_refs(self.sustained_refs, "sustained_refs", allow_empty=True),
        )
        object.__setattr__(
            self, "voices", _check_names(self.voices, "voices", None)
        )
        object.__setattr__(
            self, "hands", _check_names(self.hands, "hands", {"left", "right"})
        )
        if not isinstance(self.sustained_under_moving, bool):
            raise TypeError("sustained_under_moving must be bool")

    @property
    def chord_size(self) -> int:
        """Number of attacks starting at the slice onset."""
        return len(self.attack_refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TEXTURE_SLICE_SCHEMA_VERSION,
            "onset": fraction_to_json(self.onset),
            "attack_refs": [r.to_dict() for r in self.attack_refs],
            "sustained_refs": [r.to_dict() for r in self.sustained_refs],
            "voices": list(self.voices),
            "hands": list(self.hands),
            "sustained_under_moving": self.sustained_under_moving,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextureSlice":
        if not isinstance(data, dict):
            raise TypeError(f"TextureSlice requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_TEXTURE_SLICE_VERSIONS:
            raise ValueError(
                f"unsupported TextureSlice schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_TEXTURE_SLICE_VERSIONS)}"
            )
        try:
            onset_data = data["onset"]
            attack_data = data["attack_refs"]
            sustained_data = data["sustained_refs"]
            voices_data = data["voices"]
            hands_data = data["hands"]
            sustained_under_moving = data["sustained_under_moving"]
        except KeyError as exc:
            raise ValueError(
                f"missing TextureSlice field {exc.args[0]!r}"
            ) from exc
        for field, raw in (
            ("attack_refs", attack_data),
            ("sustained_refs", sustained_data),
            ("voices", voices_data),
            ("hands", hands_data),
        ):
            if not isinstance(raw, list):
                raise ValueError(f"TextureSlice {field} must be list")
        return cls(
            onset=fraction_from_json(onset_data),
            attack_refs=tuple(SourceRef.from_dict(r) for r in attack_data),
            sustained_refs=tuple(SourceRef.from_dict(r) for r in sustained_data),
            voices=tuple(str(v) for v in voices_data),
            hands=tuple(str(h) for h in hands_data),
            sustained_under_moving=bool(sustained_under_moving),
        )


@dataclass(frozen=True, slots=True)
class TextureGrid:
    """Per-onset simultaneity slices for one passage, in time order.

    - slices: one entry per distinct attack onset. Slice onsets are
      sorted unique; every passage attack appears in exactly one slice's
      ``attack_refs``.
    - ordering documents the sort; grouping is None (flat grid).
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    slices: tuple[TextureSlice, ...] = ()
    ordering: str = TEXTURE_GRID_ORDERING
    grouping: str | None = None
    omissions: tuple[str, ...] = TEXTURE_GRID_OMISSIONS
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.view_type != ViewType.TEXTURE_GRID:
            raise ValueError(
                "TextureGrid view_type must be "
                f"{ViewType.TEXTURE_GRID.value!r}, got {self.view_type!r}"
            )
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.slices, tuple):
            raise TypeError("slices must be tuple")
        for sliver in self.slices:
            if not isinstance(sliver, TextureSlice):
                raise TypeError(
                    "slices must contain TextureSlice, "
                    f"got {type(sliver).__name__}"
                )
        onset_times = [s.onset for s in self.slices]
        if onset_times != sorted(onset_times) or len(set(onset_times)) != len(
            onset_times
        ):
            raise ValueError("slices must be sorted unique onset times")
        seen: set[str] = set()
        for sliver in self.slices:
            for ref in sliver.attack_refs:
                if ref.id in seen:
                    raise ValueError(
                        f"attack ref {ref.id!r} appears in multiple slices"
                    )
                seen.add(ref.id)
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
                    "(never projected into the texture grid)"
                )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def summary(self) -> dict[str, Any]:
        """Grid-level density facts derived deterministically from slices.

        Keys are stable for S2.11 texture observations: total attacks,
        onset count, max chord size, chordal onsets (size > 1),
        sustained-under-moving slices, and distinct voices/hands.
        """
        chord_sizes = [s.chord_size for s in self.slices]
        voices = sorted({v for s in self.slices for v in s.voices})
        hands = sorted({h for s in self.slices for h in s.hands})
        return {
            "total_attacks": sum(chord_sizes),
            "onset_count": len(self.slices),
            "max_chord_size": max(chord_sizes) if chord_sizes else 0,
            "chordal_onset_count": sum(1 for size in chord_sizes if size > 1),
            "sustained_under_moving_count": sum(
                1 for s in self.slices if s.sustained_under_moving
            ),
            "voices": voices,
            "hands": hands,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TEXTURE_GRID_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "slices": [s.to_dict() for s in self.slices],
            "ordering": self.ordering,
            "grouping": self.grouping,
            "omissions": list(self.omissions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextureGrid":
        if not isinstance(data, dict):
            raise TypeError(f"TextureGrid requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_TEXTURE_GRID_VERSIONS:
            raise ValueError(
                f"unsupported TextureGrid schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_TEXTURE_GRID_VERSIONS)}"
            )
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(f"missing TextureGrid field {exc.args[0]!r}") from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        raw_slices = data.get("slices", [])
        if not isinstance(raw_slices, list):
            raise ValueError("TextureGrid slices must be list")
        raw_omissions = data.get("omissions", [])
        if not isinstance(raw_omissions, list):
            raise ValueError("TextureGrid omissions must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("TextureGrid diagnostics must be list")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            slices=tuple(TextureSlice.from_dict(s) for s in raw_slices),
            ordering=str(ordering),
            grouping=data.get("grouping"),
            omissions=tuple(str(o) for o in raw_omissions),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


def build_texture_grid(
    passage: Passage,
    score: Any,
    *,
    method_id: str = TEXTURE_GRID_METHOD_ID,
    method_version: str = TEXTURE_GRID_METHOD_VERSION,
) -> TextureGrid:
    """Build the texture grid for `passage` over `score`.

    Resolves the passage's logical-note refs (skipping non-logical refs
    and unresolvable refs with diagnostics, never failing), groups
    attacks by onset, and marks earlier-starting passage attacks that
    sound through each onset as sustained. An empty result is an
    explicit valid outcome with an info diagnostic. Reads only:
    neither the score nor the passage is mutated.
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
                    "from the texture grid"
                ),
            )
        )
    resolved.sort(key=_order_key)

    slices: list[TextureSlice] = []
    current_time: Fraction | None = None
    current_attacks: list[Any] = []
    for note in (*resolved, None):
        time = note.onset if note is not None else None
        if time is not None and time == current_time:
            current_attacks.append(note)
            continue
        if current_attacks and current_time is not None:
            sustained = sorted(
                (
                    other
                    for other in resolved
                    if other.onset < current_time < other.onset + other.duration
                ),
                key=_order_key,
            )
            participants = (*current_attacks, *sustained)
            voices = sorted(
                {n.voice for n in participants if n.voice is not None}
            )
            hands = sorted(
                {n.hand for n in participants if n.hand is not None}
            )
            slices.append(
                TextureSlice(
                    onset=current_time,
                    attack_refs=tuple(
                        SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE)
                        for n in current_attacks
                    ),
                    sustained_refs=tuple(
                        SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE)
                        for n in sustained
                    ),
                    voices=tuple(voices),
                    hands=tuple(hands),
                    sustained_under_moving=bool(sustained),
                )
            )
        current_attacks = [note] if note is not None else []
        current_time = time

    if not slices:
        diagnostics.append(
            Diagnostic(
                code="no_texture_slices",
                severity=Severity.INFO,
                message="no resolvable logical attacks in the passage interval",
            )
        )
    return TextureGrid(
        view_type=ViewType.TEXTURE_GRID,
        source_passage_id=passage.passage_id,
        method_id=method_id,
        method_version=method_version,
        slices=tuple(slices),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "TEXTURE_GRID_METHOD_ID",
    "TEXTURE_GRID_METHOD_VERSION",
    "TEXTURE_GRID_OMISSIONS",
    "TEXTURE_GRID_ORDERING",
    "TEXTURE_GRID_SCHEMA_VERSION",
    "TEXTURE_SLICE_SCHEMA_VERSION",
    "TextureGrid",
    "TextureSlice",
    "build_texture_grid",
]
