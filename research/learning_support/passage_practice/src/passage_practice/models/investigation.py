"""Shared passage-investigation contract — LS-03a (D-013).

Minimal envelope over the existing `Passage`: both the analyzer-suggested and
the user-selected entry produce one `PassageInvestigation` with a required
passage, an explicit structured `selection_origin`, an optional requested
hand, and an optional difficulty-context collection (empty is valid).

Design refs:
- docs/contracts.md: Passage investigation request — D-013
- docs/decisions.md: D-013 (accepted design; passage-first)
- docs/entry_points.md: sections 1, 5 (adapter shape for T05.2/T05.3)

Key invariants:
- Reuses `Passage`, `ScoreInterval`, `Diagnostic`; no new region model, no
  parser, no duplicate score representation.
- Origin is a validated field, never inferred from purpose/parent/method.
- Difficulty context is optional; entries validate source identity and
  coverage against the passage. Unrelated evidence is rejected, not
  demoted to local support.
- Scores/contributions require a real hotspot reference; nothing manufactures
  hotspot IDs, scores, ranks, or placeholder references.
- Enrichment (`with_evidence`) returns a new object; origin and passage
  identity never change.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .diagnostics import Diagnostic
from .passage import Passage
from .time import ScoreInterval

PASSAGE_INVESTIGATION_SCHEMA_VERSION = "passage_investigation.v1"
DIFFICULTY_EVIDENCE_SCHEMA_VERSION = "difficulty_evidence.v1"
CONTRIBUTION_SCHEMA_VERSION = "contribution.v1"

SUPPORTED_INVESTIGATION_VERSIONS = {PASSAGE_INVESTIGATION_SCHEMA_VERSION}
SUPPORTED_DIFFICULTY_EVIDENCE_VERSIONS = {DIFFICULTY_EVIDENCE_SCHEMA_VERSION}
SUPPORTED_CONTRIBUTION_VERSIONS = {CONTRIBUTION_SCHEMA_VERSION}

REQUESTED_HANDS = frozenset({"left", "right", "both"})


class SelectionOrigin(str, Enum):
    USER_SELECTED = "user_selected"
    ANALYZER_SUGGESTED = "analyzer_suggested"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_finite(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a finite number, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite, got {value!r}")
    return result


@dataclass(frozen=True, slots=True)
class Contribution:
    """One measured dimension share/rank behind a real analysis result."""

    dimension_id: str
    value: float

    def __post_init__(self) -> None:
        _check_id(self.dimension_id, "dimension_id")
        object.__setattr__(self, "value", _check_finite(self.value, "value"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTRIBUTION_SCHEMA_VERSION,
            "dimension_id": self.dimension_id,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contribution":
        if not isinstance(data, dict):
            raise TypeError(f"Contribution requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_CONTRIBUTION_VERSIONS:
            raise ValueError(
                f"unsupported Contribution schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_CONTRIBUTION_VERSIONS)}"
            )
        try:
            dimension_id = data["dimension_id"]
            value = data["value"]
        except KeyError as exc:
            raise ValueError(f"missing Contribution field {exc.args[0]!r}") from exc
        return cls(dimension_id=dimension_id, value=value)


@dataclass(frozen=True, slots=True)
class DifficultyEvidence:
    """Validated optional difficulty context for one investigation.

    Identifies its source score, covered exact region, producer method, and
    actual feature/evidence references. A hotspot reference with its score
    and contributions occurs only when supplied by a real analysis result:
    `window_score`/`contributions` require `hotspot_id`. Unavailable values
    stay absent, never fabricated zeros.
    """

    source_score_id: str
    method_id: str
    method_version: str
    covered: ScoreInterval
    feature_id: str
    evidence_ref: str
    hotspot_id: str | None = None
    window_score: float | None = None
    contributions: tuple[Contribution, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.source_score_id, "source_score_id")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.covered, ScoreInterval):
            raise TypeError("covered must be ScoreInterval")
        _check_id(self.feature_id, "feature_id")
        _check_id(self.evidence_ref, "evidence_ref")
        if self.hotspot_id is not None:
            _check_id(self.hotspot_id, "hotspot_id")
        if self.window_score is not None:
            object.__setattr__(
                self, "window_score", _check_finite(self.window_score, "window_score")
            )
        if not isinstance(self.contributions, tuple):
            raise TypeError("contributions must be tuple")
        for c in self.contributions:
            if not isinstance(c, Contribution):
                raise TypeError(
                    f"contributions must contain Contribution, got {type(c).__name__}"
                )
        if (self.window_score is not None or self.contributions) and self.hotspot_id is None:
            raise ValueError("window_score/contributions require a real hotspot_id")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": DIFFICULTY_EVIDENCE_SCHEMA_VERSION,
            "source_score_id": self.source_score_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "covered": self.covered.to_dict(),
            "feature_id": self.feature_id,
            "evidence_ref": self.evidence_ref,
        }
        if self.hotspot_id is not None:
            payload["hotspot_id"] = self.hotspot_id
        if self.window_score is not None:
            payload["window_score"] = self.window_score
        if self.contributions:
            payload["contributions"] = [c.to_dict() for c in self.contributions]
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DifficultyEvidence":
        if not isinstance(data, dict):
            raise TypeError(f"DifficultyEvidence requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_DIFFICULTY_EVIDENCE_VERSIONS:
            raise ValueError(
                f"unsupported DifficultyEvidence schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_DIFFICULTY_EVIDENCE_VERSIONS)}"
            )
        try:
            source_score_id = data["source_score_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            covered_data = data["covered"]
            feature_id = data["feature_id"]
            evidence_ref = data["evidence_ref"]
        except KeyError as exc:
            raise ValueError(f"missing DifficultyEvidence field {exc.args[0]!r}") from exc
        covered = ScoreInterval.from_dict(covered_data)
        hotspot_id = data.get("hotspot_id")
        window_score = data.get("window_score")
        raw_contribs = data.get("contributions", [])
        if not isinstance(raw_contribs, list):
            raise ValueError("DifficultyEvidence contributions must be list")
        contributions = tuple(Contribution.from_dict(c) for c in raw_contribs)
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("DifficultyEvidence diagnostics must be list")
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        return cls(
            source_score_id=source_score_id,
            method_id=method_id,
            method_version=method_version,
            covered=covered,
            feature_id=feature_id,
            evidence_ref=evidence_ref,
            hotspot_id=hotspot_id,
            window_score=window_score,
            contributions=contributions,
            diagnostics=diagnostics,
        )


@dataclass(frozen=True, slots=True)
class PassageInvestigation:
    """One investigation over a required passage, either entry origin.

    - passage: the existing musical subject (identity, interval, lineage).
    - selection_origin: why this investigation began (validated field).
    - requested_hand: left/right/both, or None when unspecified/unknown
      (record unknowns with a Diagnostic; unsupported labels are rejected).
    - difficulty: optional validated context; empty is valid.
    - method_id/method_version: how this envelope was produced.
    """

    investigation_id: str
    passage: Passage
    selection_origin: SelectionOrigin
    method_id: str
    method_version: str
    requested_hand: str | None = None
    difficulty: tuple[DifficultyEvidence, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.investigation_id, "investigation_id")
        if not isinstance(self.passage, Passage):
            raise TypeError("passage must be Passage")
        if not isinstance(self.selection_origin, SelectionOrigin):
            raise TypeError(
                f"selection_origin must be SelectionOrigin, got {type(self.selection_origin).__name__}"
            )
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if self.requested_hand is not None and self.requested_hand not in REQUESTED_HANDS:
            raise ValueError(
                f"requested_hand must be one of {sorted(REQUESTED_HANDS)} or None, "
                f"got {self.requested_hand!r}"
            )
        if not isinstance(self.difficulty, tuple):
            raise TypeError("difficulty must be tuple")
        for entry in self.difficulty:
            if not isinstance(entry, DifficultyEvidence):
                raise TypeError(
                    f"difficulty must contain DifficultyEvidence, got {type(entry).__name__}"
                )
            if entry.source_score_id != self.passage.score_id:
                raise ValueError(
                    "difficulty source_score_id "
                    f"{entry.source_score_id!r} does not match passage score_id "
                    f"{self.passage.score_id!r}"
                )
            if not (
                self.passage.start.quarters <= entry.covered.start.quarters
                and entry.covered.end.quarters <= self.passage.end.quarters
            ):
                raise ValueError(
                    "difficulty covered region "
                    f"[{entry.covered.start.quarters}, {entry.covered.end.quarters}) "
                    "is not within passage "
                    f"[{self.passage.start.quarters}, {self.passage.end.quarters})"
                )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def with_evidence(self, entry: DifficultyEvidence) -> "PassageInvestigation":
        """Return a new investigation with one appended context entry.

        Origin, passage identity, and existing context are preserved; the
        appended entry is validated by construction.
        """
        if not isinstance(entry, DifficultyEvidence):
            raise TypeError(
                f"entry must be DifficultyEvidence, got {type(entry).__name__}"
            )
        return PassageInvestigation(
            investigation_id=self.investigation_id,
            passage=self.passage,
            selection_origin=self.selection_origin,
            method_id=self.method_id,
            method_version=self.method_version,
            requested_hand=self.requested_hand,
            difficulty=self.difficulty + (entry,),
            diagnostics=self.diagnostics,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": PASSAGE_INVESTIGATION_SCHEMA_VERSION,
            "investigation_id": self.investigation_id,
            "passage": self.passage.to_dict(),
            "selection_origin": self.selection_origin.value,
            "method_id": self.method_id,
            "method_version": self.method_version,
        }
        if self.requested_hand is not None:
            payload["requested_hand"] = self.requested_hand
        if self.difficulty:
            payload["difficulty"] = [e.to_dict() for e in self.difficulty]
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PassageInvestigation":
        if not isinstance(data, dict):
            raise TypeError(
                f"PassageInvestigation requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_INVESTIGATION_VERSIONS:
            raise ValueError(
                f"unsupported PassageInvestigation schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_INVESTIGATION_VERSIONS)}"
            )
        try:
            investigation_id = data["investigation_id"]
            passage_data = data["passage"]
            origin_raw = data["selection_origin"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(
                f"missing PassageInvestigation field {exc.args[0]!r}"
            ) from exc
        try:
            origin = SelectionOrigin(origin_raw)
        except ValueError as exc:
            raise ValueError(f"unknown selection_origin {origin_raw!r}") from exc
        passage = Passage.from_dict(passage_data)
        requested_hand = data.get("requested_hand")
        raw_difficulty = data.get("difficulty", [])
        if not isinstance(raw_difficulty, list):
            raise ValueError("PassageInvestigation difficulty must be list")
        difficulty = tuple(DifficultyEvidence.from_dict(e) for e in raw_difficulty)
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("PassageInvestigation diagnostics must be list")
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        return cls(
            investigation_id=investigation_id,
            passage=passage,
            selection_origin=origin,
            method_id=method_id,
            method_version=method_version,
            requested_hand=requested_hand,
            difficulty=difficulty,
            diagnostics=diagnostics,
        )
