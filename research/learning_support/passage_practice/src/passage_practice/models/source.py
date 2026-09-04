"""Stable source identity primitives for passage practice.

Implements T01.2: decision and implementation for Q-001.

Inspected existing ScoreIR IDs:
- WrittenNoteIR.note_id = child.get("id") or f"n{xml_order}"  (converters.py:426)
- RestEventIR.rest_id = child.get("id") or f"r{xml_order}"   (325)
- LogicalNoteIR.note_id = first.note_id of chain, source_note_ids tracks constituents (522/531)
- DirectionIR.direction_id, ClefIR.clef_id similarly use xml_order fallback.
All IDs are deterministic from XML order; explicit MusicXML @id is preserved when present.
Tie collapse preserves first note_id, so logical notes are traceable to written notes
without new opaque IDs; source_note_ids keeps the written-note provenance.

Decision D-011 (Q-001):
  Use normalized generated IDs as canonical stable references. Preserve explicit
  MusicXML @id when present (already done by ScoreIR), but treat generated
  f"n{xml_order}" / f"r{xml_order}" as the stable form. Do not use XML paths
  or retained node identities. Each reference is a pair (kind, id) so kind
  is required to resolve (e.g., 'r1' vs 'n1' are distinct). Resolver is a
  pure lookup over ScoreIR collections; no XML mutation. This survives
  selection and serialization because passage containers store only IDs, not
  live objects, and resolver re-attaches to the same ScoreIR.

Consequences:
- Uniqueness is inherited from ScoreIR generation (xml_order unique per type).
- Deterministic regeneration holds because xml_order depends only on document order.
- Missing references are explicit (resolver returns None) rather than silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

SOURCE_REF_SCHEMA_VERSION = "source_ref.v1"
SUPPORTED_SOURCE_REF_VERSIONS = {SOURCE_REF_SCHEMA_VERSION}


class SourceKind(str, Enum):
    """Discrete kinds for stable references. Distinct concepts kept separate."""

    WRITTEN_NOTE = "written_note"
    LOGICAL_NOTE = "logical_note"
    REST = "rest"
    MEASURE = "measure"
    DIRECTION = "direction"
    CLEF = "clef"
    ONSET_GROUP = "onset_group"


# Map kind to ScoreIR collection attribute and id field for resolver.
_KIND_TO_ATTR: dict[SourceKind, tuple[str, str]] = {
    SourceKind.WRITTEN_NOTE: ("written_notes", "note_id"),
    SourceKind.LOGICAL_NOTE: ("logical_notes", "note_id"),
    SourceKind.REST: ("rests", "rest_id"),
    SourceKind.MEASURE: ("measures", "measure_index"),  # special: id is str(int)
    SourceKind.DIRECTION: ("directions", "direction_id"),
    SourceKind.CLEF: ("clefs", "clef_id"),
    SourceKind.ONSET_GROUP: ("onset_groups", "onset"),  # onset is not id; resolver handles specially
}

# For MEASURE, the canonical id is str(measure_index) or measure_number? Use index for stability.
# For ONSET_GROUP, no stable single id exists; we treat source_ref for those as unsupported in T01.2 minimal set.


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Immutable stable reference to a canonical score fact.

    Keeps kind separate from id so 'n1' vs 'r1' never collide, and staff vs
    hand remain distinct elsewhere. No XML mutation.
    """

    id: str
    kind: SourceKind

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or self.id == "":
            raise ValueError(f"SourceRef id must be non-empty str, got {self.id!r}")
        if not isinstance(self.kind, SourceKind):
            raise TypeError(f"SourceRef kind must be SourceKind, got {type(self.kind).__name__}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_REF_SCHEMA_VERSION,
            "id": self.id,
            "kind": self.kind.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceRef":
        if not isinstance(data, dict):
            raise TypeError(f"SourceRef requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_SOURCE_REF_VERSIONS:
            raise ValueError(
                f"unsupported SourceRef schema_version {version!r}; supported: {sorted(SUPPORTED_SOURCE_REF_VERSIONS)}"
            )
        try:
            raw_id = data["id"]
            raw_kind = data["kind"]
        except KeyError as exc:
            raise ValueError(f"missing SourceRef field {exc.args[0]!r}") from exc
        try:
            kind = SourceKind(raw_kind)
        except ValueError as exc:
            raise ValueError(f"unknown SourceKind {raw_kind!r}") from exc
        return cls(id=str(raw_id), kind=kind)


def is_resolvable(score: Any, ref: SourceRef) -> bool:
    """Return True if ref can be resolved against score (without raising on missing)."""
    if not isinstance(ref, SourceRef):
        raise TypeError("ref must be SourceRef")
    return resolve_ref(score, ref) is not None


def resolve_ref(score: Any, ref: SourceRef) -> Any | None:
    """Resolve a SourceRef to its live ScoreIR object or None if missing.

    Pure lookup; does not mutate score or parse XML.
    Supported kinds in T01.2 minimal set: WRITTEN_NOTE, LOGICAL_NOTE, REST,
    MEASURE, DIRECTION, CLEF. ONSET_GROUP is intentionally unsupported
    until derived views define stable grouping semantics (returns None).
    """
    if not isinstance(ref, SourceRef):
        raise TypeError("ref must be SourceRef")

    # Defensive: ScoreIR duck-typing so tests can pass synthetic scores
    # without importing concrete class at runtime.
    kind = ref.kind

    if kind == SourceKind.ONSET_GROUP:
        return None

    attr_info = _KIND_TO_ATTR.get(kind)
    if attr_info is None:
        return None
    attr_name, id_field = attr_info

    collection = getattr(score, attr_name, None)
    if collection is None:
        return None

    # Special handling for MEASURE where id is str(measure_index)
    if kind == SourceKind.MEASURE:
        # Find by index equality after converting id to int
        try:
            target_index = int(ref.id)
        except ValueError:
            return None
        for m in collection:
            # measure_index is int on MeasureIR
            if getattr(m, "measure_index", None) == target_index:
                return m
        return None

    # Generic: match by id field
    for obj in collection:
        if getattr(obj, id_field, None) == ref.id:
            return obj
    return None


def refs_for_score(score: Any) -> list[SourceRef]:
    """Enumerate all stable refs for a score (canonical ID inventory).

    Used for uniqueness checks and deterministic regeneration tests.
    """
    refs: list[SourceRef] = []
    for kind in (SourceKind.WRITTEN_NOTE, SourceKind.LOGICAL_NOTE, SourceKind.REST, SourceKind.DIRECTION, SourceKind.CLEF, SourceKind.MEASURE):
        attr_info = _KIND_TO_ATTR.get(kind)
        if attr_info is None:
            continue
        attr_name, id_field = attr_info
        collection = getattr(score, attr_name, None)
        if not collection:
            continue
        for obj in collection:
            raw_id = getattr(obj, id_field, None)
            # Measure uses int index; normalize to str
            if kind == SourceKind.MEASURE:
                raw_id = str(raw_id)
            if raw_id is None:
                continue
            refs.append(SourceRef(id=str(raw_id), kind=kind))
    return refs
