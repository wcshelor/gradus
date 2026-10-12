"""Detector interface and registry — S3.1 (depends S1.5/S2.13).

Defines the minimal detector contract and a deterministic registry.

Design refs:
- docs/practice_chunk_objects.md: semantic detectors produce evidence-backed
  claims that can attach to bounded chunks
- detector_id, detector_version, hypothesis_types produced, required_views,
  optional_views, supported subset, known limitations; detector input (passage,
  requested scope, derived views, observations, optional difficulty/learner
  context) and output (zero or more SemanticHypothesis + diagnostics)
- S1.5/S-Q003: confidence vocabulary via semantics.confidence, S1.2 contracts

Registry expectations (S3.1 verification):
- unsupported view diagnostic
- deterministic ordering
- detector selection by family
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.semantics.contracts import SemanticHypothesis


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_id_tuple(values: tuple[str, ...], field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple, got {type(values).__name__}")
    for v in values:
        if not isinstance(v, str) or not v:
            raise ValueError(f"{field} must contain non-empty str, got {v!r}")
        if len(v) > 128:
            raise ValueError(f"{field} too long (>128): {v!r}")
    if not allow_empty and not values:
        raise ValueError(f"{field} must be non-empty tuple")
    # Deterministic: require sorted unique for view lists? No, preserve author order
    # but forbid duplicates for clarity.
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates, got {values!r}")
    return values


@dataclass(frozen=True, slots=True)
class DetectorSpec:
    """Immutable metadata for one deterministic semantic detector.

    - detector_id: stable identifier, e.g. ``melody_salience.v1``
    - detector_version: version string, e.g. ``v1``
    - hypothesis_types: hypothesis families produced, e.g. ``("role.melody",)``
    - required_views: view identifiers that must be present (e.g. ``rhythm_grid``)
    - optional_views: view identifiers that improve the detector if present
    - supported_subset: human-readable description of what the detector supports
    - known_limitations: human-readable limitation strings (never hidden)
    """

    detector_id: str
    detector_version: str
    hypothesis_types: tuple[str, ...]
    required_views: tuple[str, ...] = ()
    optional_views: tuple[str, ...] = ()
    supported_subset: str = ""
    known_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.detector_id, "detector_id")
        _check_id(self.detector_version, "detector_version")
        _check_id_tuple(self.hypothesis_types, "hypothesis_types", allow_empty=False)
        _check_id_tuple(self.required_views, "required_views", allow_empty=True)
        _check_id_tuple(self.optional_views, "optional_views", allow_empty=True)
        if not isinstance(self.supported_subset, str):
            raise TypeError("supported_subset must be str")
        _check_id_tuple(self.known_limitations, "known_limitations", allow_empty=True)
        # required and optional must not overlap
        overlap = set(self.required_views) & set(self.optional_views)
        if overlap:
            raise ValueError(f"required_views and optional_views overlap: {overlap!r}")
        # hypothesis_types should look like ``family.suffix``; keep open but ensure a dot
        for ht in self.hypothesis_types:
            if "." not in ht:
                raise ValueError(f"hypothesis_type must contain '.', got {ht!r}")


class SemanticDetector(Protocol):
    """Protocol for a deterministic semantic detector.

    Concrete detectors expose ``spec`` and implement ``detect``.
    ``detect`` must be pure, deterministic, and never raise on missing
    optional views; missing *required* views must produce a
    ``missing_required_view`` diagnostic and no hypotheses (not an exception).
    """

    spec: DetectorSpec

    def detect(
        self,
        passage: Any,
        views: dict[str, Any],
        observations: dict[str, Any],
        *,
        investigation: Any | None = None,
        score: Any | None = None,
    ) -> tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]:
        ...


class BaseDetector(ABC):
    """Abstract base for concrete detectors to inherit from."""

    spec: DetectorSpec

    def __init__(self, spec: DetectorSpec) -> None:
        object.__setattr__(self, "spec", spec)

    @abstractmethod
    def detect(
        self,
        passage: Any,
        views: dict[str, Any],
        observations: dict[str, Any],
        *,
        investigation: Any | None = None,
        score: Any | None = None,
    ) -> tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]:
        ...

    def _missing_required_diagnostics(
        self, views: dict[str, Any]
    ) -> tuple[Diagnostic, ...] | None:
        missing = [v for v in self.spec.required_views if v not in views]
        if not missing:
            return None
        # One diagnostic per missing view, plus a summary, all deterministic sorted
        missing_sorted = tuple(sorted(missing))
        diags: list[Diagnostic] = []
        for vid in missing_sorted:
            diags.append(
                Diagnostic(
                    code="missing_required_view",
                    severity=Severity.WARNING,
                    message=f"detector {self.spec.detector_id!r} requires view {vid!r} which is not present",
                )
            )
        diags.append(
            Diagnostic(
                code="unsupported_view",
                severity=Severity.INFO,
                message=f"detector {self.spec.detector_id!r} cannot run; missing required views {missing_sorted!r}",
            )
        )
        return tuple(diags)


class DetectorRegistry:
    """Deterministic registry of semantic detectors."""

    def __init__(self) -> None:
        self._by_id: dict[str, BaseDetector] = {}

    def register(self, detector: BaseDetector) -> None:
        if not isinstance(detector, BaseDetector):
            # Allow Protocol duck-typed but require spec attribute
            spec = getattr(detector, "spec", None)
            if not isinstance(spec, DetectorSpec):
                raise TypeError("detector must expose DetectorSpec at .spec")
        else:
            spec = detector.spec
        did = spec.detector_id
        if did in self._by_id:
            raise ValueError(f"duplicate detector_id {did!r}")
        # type: ignore[arg-type]
        self._by_id[did] = detector  # type: ignore[assignment]

    def get(self, detector_id: str) -> BaseDetector:
        _check_id(detector_id, "detector_id")
        try:
            return self._by_id[detector_id]
        except KeyError as exc:
            raise KeyError(f"unknown detector_id {detector_id!r}") from exc

    def list_all(self) -> list[BaseDetector]:
        """All detectors in deterministic order (sorted by detector_id)."""
        return [self._by_id[k] for k in sorted(self._by_id)]

    def by_family(self, prefix: str) -> list[BaseDetector]:
        """Detectors that produce at least one hypothesis_type starting with ``prefix``.

        ``prefix`` is a family prefix like ``"role."`` or ``"role.melody"``.
        Matching is ``ht == prefix`` or ``ht.startswith(prefix)`` where prefix
        ends with ``.``; otherwise exact type prefix. Keeps registry deterministic.
        """
        if not isinstance(prefix, str) or not prefix:
            raise ValueError("prefix must be non-empty str")
        matched: list[BaseDetector] = []
        for det in self.list_all():
            for ht in det.spec.hypothesis_types:
                if ht == prefix or ht.startswith(prefix):
                    matched.append(det)
                    break
        return matched

    def selectable_for(self, available_views: set[str] | tuple[str, ...] | list[str]) -> list[BaseDetector]:
        """Detectors whose required_views are subset of ``available_views``."""
        if not isinstance(available_views, (set, tuple, list)):
            raise TypeError("available_views must be set/tuple/list of str")
        av_set = set(available_views)  # type: ignore[arg-type]
        for v in av_set:
            if not isinstance(v, str) or not v:
                raise ValueError(f"available_views must contain non-empty str, got {v!r}")
        result: list[BaseDetector] = []
        for det in self.list_all():
            if set(det.spec.required_views) <= av_set:
                result.append(det)
        return result

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, detector_id: str) -> bool:
        return detector_id in self._by_id


__all__ = ["BaseDetector", "DetectorRegistry", "DetectorSpec", "SemanticDetector"]
