"""Exact-time value objects for passage practice.

Implements T01.1: score position and strict non-empty half-open interval
validation with exact fraction serialization.

Design refs:
- docs/contracts.md: Identity and time
- docs/architecture.md: Region semantics (half-open)
- WORK_PACKAGES.md WP-01
- IMPLEMENTATION_CHECKLIST.md T01.1

Key invariants:
- Fractions are exact, never floats in canonical payloads.
- Intervals are half-open [start, end) and strictly non-empty (start < end).
- Positions and intervals are immutable (frozen dataclasses).
- Serialization is deterministic and round-trips exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

SCORE_POSITION_SCHEMA_VERSION = "score_position.v1"
SCORE_INTERVAL_SCHEMA_VERSION = "score_interval.v1"

# The set of supported versions for forward-rejection.
SUPPORTED_POSITION_VERSIONS = {SCORE_POSITION_SCHEMA_VERSION}
SUPPORTED_INTERVAL_VERSIONS = {SCORE_INTERVAL_SCHEMA_VERSION}


def fraction_to_json(value: Fraction) -> dict[str, int]:
    """Serialize a Fraction exactly as {numerator, denominator}.

    Denominator is always positive after Fraction normalization. This form
    preserves exact rational time without floating-point loss.
    """
    if not isinstance(value, Fraction):
        raise TypeError(f"expected Fraction, got {type(value).__name__}")
    # Fraction normalizes sign to numerator; denominator always >0.
    return {"numerator": value.numerator, "denominator": value.denominator}


def fraction_from_json(data: Any) -> Fraction:
    """Deserialize a Fraction from canonical JSON.

    Accepts:
    - {"numerator": int, "denominator": int}
    - "num/den" string (defensive, for legacy payloads)
    Rejects floats.
    """
    if isinstance(data, dict):
        try:
            num = data["numerator"]
            den = data["denominator"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"invalid fraction object {data!r}") from exc
        if not isinstance(num, int) or not isinstance(den, int):
            raise ValueError(f"fraction object requires int num/den, got {data!r}")
        if den == 0:
            raise ValueError("fraction denominator cannot be zero")
        return Fraction(num, den)
    if isinstance(data, str):
        # Defensive support for "num/den" string.
        if "/" not in data:
            raise ValueError(f"invalid fraction string {data!r}")
        num_s, den_s = data.split("/", 1)
        try:
            num = int(num_s.strip())
            den = int(den_s.strip())
        except ValueError as exc:
            raise ValueError(f"invalid fraction string {data!r}") from exc
        if den == 0:
            raise ValueError("fraction denominator cannot be zero")
        return Fraction(num, den)
    if isinstance(data, float):
        raise ValueError(f"lossy float fraction rejected: {data!r}")
    raise ValueError(f"unsupported fraction representation {data!r}")


@dataclass(frozen=True, slots=True)
class ScorePosition:
    """Exact score position with measure context.

    Attributes:
        quarters: Global quarter-note offset from score start (exact).
        measure_index: Stable 0-based measure index.
        measure_number: Printed number when available (e.g., "12" or "12a").
        offset_in_measure: Exact offset within the containing measure.
        voice: Encoded voice label (e.g., "1", "2"), distinct from staff.
        staff: Encoded staff number (1-indexed per MusicXML), distinct from hand.
        hand: Inferred hand label ("left"/"right" or None), distinct from staff.
    """

    quarters: Fraction
    measure_index: int
    measure_number: str | None = None
    offset_in_measure: Fraction = Fraction(0, 1)
    voice: str | None = None
    staff: int | None = None
    hand: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.quarters, Fraction):
            raise TypeError("quarters must be Fraction")
        if not isinstance(self.offset_in_measure, Fraction):
            raise TypeError("offset_in_measure must be Fraction")
        if not isinstance(self.measure_index, int):
            raise TypeError("measure_index must be int")
        if self.measure_index < 0:
            raise ValueError(f"measure_index must be >=0, got {self.measure_index}")
        if self.quarters < 0:
            raise ValueError(f"quarters must be >=0, got {self.quarters}")
        if self.offset_in_measure < 0:
            raise ValueError(f"offset_in_measure must be >=0, got {self.offset_in_measure}")
        if self.measure_number is not None and not isinstance(self.measure_number, str):
            raise TypeError("measure_number must be str or None")
        if self.measure_number == "":
            raise ValueError("measure_number cannot be empty string")
        if self.voice is not None and not isinstance(self.voice, str):
            raise TypeError("voice must be str or None")
        if self.staff is not None and not isinstance(self.staff, int):
            raise TypeError("staff must be int or None")
        if self.staff is not None and self.staff <= 0:
            raise ValueError(f"staff must be >0, got {self.staff}")
        if self.hand is not None and self.hand not in {"left", "right"}:
            raise ValueError(f"hand must be 'left'/'right' or None, got {self.hand!r}")

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-ready dict with schema_version."""
        # Use sorted keys insertion order for determinism; caller uses sort_keys when dumping.
        payload: dict[str, Any] = {
            "schema_version": SCORE_POSITION_SCHEMA_VERSION,
            "quarters": fraction_to_json(self.quarters),
            "measure_index": self.measure_index,
            "offset_in_measure": fraction_to_json(self.offset_in_measure),
        }
        # Include optional fields deterministically when present.
        if self.measure_number is not None:
            payload["measure_number"] = self.measure_number
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.hand is not None:
            payload["hand"] = self.hand
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScorePosition":
        if not isinstance(data, dict):
            raise TypeError(f"ScorePosition requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_POSITION_VERSIONS:
            raise ValueError(
                f"unsupported ScorePosition schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_POSITION_VERSIONS)}"
            )
        try:
            quarters = fraction_from_json(data["quarters"])
            measure_index = data["measure_index"]
            offset_in_measure = fraction_from_json(data["offset_in_measure"])
        except KeyError as exc:
            raise ValueError(f"missing required ScorePosition field {exc.args[0]!r}") from exc
        return cls(
            quarters=quarters,
            measure_index=int(measure_index),
            measure_number=data.get("measure_number"),
            offset_in_measure=offset_in_measure,
            voice=data.get("voice"),
            staff=data.get("staff"),
            hand=data.get("hand"),
        )


@dataclass(frozen=True, slots=True)
class ScoreInterval:
    """Strict non-empty half-open interval [start, end) over score time.

    The interval is defined by two ScorePositions. The half-open convention
    means an event beginning exactly at `end` is outside the interval.
    Invariants:
    - start.quarters < end.quarters (strict)
    - Both positions are valid ScorePositions.
    - Duration is end.quarters - start.quarters (exact Fraction).
    """

    start: ScorePosition
    end: ScorePosition

    def __post_init__(self) -> None:
        if not isinstance(self.start, ScorePosition):
            raise TypeError("start must be ScorePosition")
        if not isinstance(self.end, ScorePosition):
            raise TypeError("end must be ScorePosition")
        if not self.start.quarters < self.end.quarters:
            raise ValueError(
                f"interval must be non-empty half-open [start,end) with start < end; "
                f"got start={self.start.quarters} end={self.end.quarters}"
            )
        # Measure index should be monotonic with quarters, but we allow equal
        # measure_index for same-measure intervals and larger for later measures.
        # We only enforce that start.measure_index <= end.measure_index when
        # start.quarters < end.quarters, which is generally true; we allow
        # start at later measure_index but earlier quarters as invalid.
        if self.start.quarters < self.end.quarters and self.start.measure_index > self.end.measure_index:
            # This can happen if measure_index is inconsistent with quarters;
            # we treat it as a warning-in-code but not hard fail for T01.1,
            # because quarters is canonical. We enforce consistency only when
            # possible: if quarters increases, measure_index must not decrease.
            raise ValueError(
                f"interval measure_index inconsistent with quarters: "
                f"start measure_index {self.start.measure_index} > end {self.end.measure_index} "
                f"but start.quarters {self.start.quarters} < end.quarters {self.end.quarters}"
            )

    @property
    def duration(self) -> Fraction:
        return self.end.quarters - self.start.quarters

    def contains_quarters(self, q: Fraction) -> bool:
        """Return True if global quarter q is in [start, end)."""
        if not isinstance(q, Fraction):
            raise TypeError("quarters must be Fraction")
        return self.start.quarters <= q < self.end.quarters

    def overlaps(self, other: "ScoreInterval") -> bool:
        if not isinstance(other, ScoreInterval):
            raise TypeError("other must be ScoreInterval")
        return self.start.quarters < other.end.quarters and other.start.quarters < self.end.quarters

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCORE_INTERVAL_SCHEMA_VERSION,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScoreInterval":
        if not isinstance(data, dict):
            raise TypeError(f"ScoreInterval requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_INTERVAL_VERSIONS:
            raise ValueError(
                f"unsupported ScoreInterval schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_INTERVAL_VERSIONS)}"
            )
        try:
            start_data = data["start"]
            end_data = data["end"]
        except KeyError as exc:
            raise ValueError(f"missing ScoreInterval field {exc.args[0]!r}") from exc
        start = ScorePosition.from_dict(start_data)
        end = ScorePosition.from_dict(end_data)
        return cls(start=start, end=end)
