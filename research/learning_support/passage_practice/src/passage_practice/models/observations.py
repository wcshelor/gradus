"""Minimal passage-observation contract — LS-06.

One observation family now: consecutive-attack pitch intervals. Direct score
facts (pitches, onsets) carry `basis=FACT`; anything relying on inferred
grouping (hand-scoped filtering) carries `basis=INFERENCE` with a diagnostic.
Ordinary observations need no attribution record (D-013); none is modeled here.

Design refs:
- docs/contracts.md: Feature evidence (Observation), D-013 passage references
- research/learning_support/first_slice.md N1; prototype_v1.md triggers
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .diagnostics import Diagnostic
from .source import SourceRef
from .time import ScoreInterval

OBSERVATION_SCHEMA_VERSION = "observation.v1"
OBSERVATION_RESULT_SCHEMA_VERSION = "observation_result.v1"

SUPPORTED_OBSERVATION_VERSIONS = {OBSERVATION_SCHEMA_VERSION}
SUPPORTED_OBSERVATION_RESULT_VERSIONS = {OBSERVATION_RESULT_SCHEMA_VERSION}


class ObservationBasis(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class Observation:
    """One measured event/transition/group property over a passage.

    - passage_id: required source passage (resolvable in context).
    - value/units: exact measured value; signed semitones for transitions.
    - source_refs: ordered source events behind the value (non-empty).
    - region: exact covered interval, or None for simultaneous pairs with
      zero temporal extent (diagnosed, never padded).
    - basis: FACT for direct score facts, INFERENCE when inferred grouping
      (e.g., hand filtering) was required.
    """

    observation_id: str
    observation_type: str
    passage_id: str
    value: int
    units: str
    source_refs: tuple[SourceRef, ...]
    method_id: str
    method_version: str
    region: ScoreInterval | None = None
    hand: str | None = None
    staff: int | None = None
    voice: str | None = None
    basis: ObservationBasis = ObservationBasis.FACT
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.observation_id, "observation_id")
        _check_id(self.observation_type, "observation_type")
        _check_id(self.passage_id, "passage_id")
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise TypeError(f"value must be int, got {self.value!r}")
        _check_id(self.units, "units")
        if not isinstance(self.source_refs, tuple) or not self.source_refs:
            raise ValueError("source_refs must be a non-empty tuple")
        for r in self.source_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(
                    f"source_refs must contain SourceRef, got {type(r).__name__}"
                )
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if self.region is not None and not isinstance(self.region, ScoreInterval):
            raise TypeError("region must be ScoreInterval or None")
        if not isinstance(self.basis, ObservationBasis):
            raise TypeError(
                f"basis must be ObservationBasis, got {type(self.basis).__name__}"
            )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": OBSERVATION_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "observation_type": self.observation_type,
            "passage_id": self.passage_id,
            "value": self.value,
            "units": self.units,
            "source_refs": [r.to_dict() for r in self.source_refs],
            "method_id": self.method_id,
            "method_version": self.method_version,
            "basis": self.basis.value,
        }
        if self.region is not None:
            payload["region"] = self.region.to_dict()
        if self.hand is not None:
            payload["hand"] = self.hand
        if self.staff is not None:
            payload["staff"] = self.staff
        if self.voice is not None:
            payload["voice"] = self.voice
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        if not isinstance(data, dict):
            raise TypeError(f"Observation requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_OBSERVATION_VERSIONS:
            raise ValueError(
                f"unsupported Observation schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_OBSERVATION_VERSIONS)}"
            )
        try:
            observation_id = data["observation_id"]
            observation_type = data["observation_type"]
            passage_id = data["passage_id"]
            value = data["value"]
            units = data["units"]
            refs_raw = data["source_refs"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            basis_raw = data.get("basis", ObservationBasis.FACT.value)
        except KeyError as exc:
            raise ValueError(f"missing Observation field {exc.args[0]!r}") from exc
        if not isinstance(refs_raw, list):
            raise ValueError("Observation source_refs must be list")
        try:
            basis = ObservationBasis(basis_raw)
        except ValueError as exc:
            raise ValueError(f"unknown basis {basis_raw!r}") from exc
        region_data = data.get("region")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("Observation diagnostics must be list")
        return cls(
            observation_id=observation_id,
            observation_type=observation_type,
            passage_id=passage_id,
            value=value,
            units=units,
            source_refs=tuple(SourceRef.from_dict(r) for r in refs_raw),
            method_id=method_id,
            method_version=method_version,
            region=ScoreInterval.from_dict(region_data) if region_data is not None else None,
            hand=data.get("hand"),
            staff=data.get("staff"),
            voice=data.get("voice"),
            basis=basis,
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


@dataclass(frozen=True, slots=True)
class ObservationResult:
    """Observations from one method run plus abstention diagnostics."""

    observations: tuple[Observation, ...] = ()
    method_id: str = ""
    method_version: str = ""
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be tuple")
        for o in self.observations:
            if not isinstance(o, Observation):
                raise TypeError(
                    f"observations must contain Observation, got {type(o).__name__}"
                )
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": OBSERVATION_RESULT_SCHEMA_VERSION,
            "method_id": self.method_id,
            "method_version": self.method_version,
        }
        if self.observations:
            payload["observations"] = [o.to_dict() for o in self.observations]
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservationResult":
        if not isinstance(data, dict):
            raise TypeError(
                f"ObservationResult requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_OBSERVATION_RESULT_VERSIONS:
            raise ValueError(
                f"unsupported ObservationResult schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_OBSERVATION_RESULT_VERSIONS)}"
            )
        try:
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(
                f"missing ObservationResult field {exc.args[0]!r}"
            ) from exc
        raw_obs = data.get("observations", [])
        if not isinstance(raw_obs, list):
            raise ValueError("ObservationResult observations must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("ObservationResult diagnostics must be list")
        return cls(
            observations=tuple(Observation.from_dict(o) for o in raw_obs),
            method_id=method_id,
            method_version=method_version,
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )
