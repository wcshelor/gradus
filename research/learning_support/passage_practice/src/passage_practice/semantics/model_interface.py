"""S7.5 model interface behind detector contract.

Defines a local deterministic inference interface that returns
SemanticHypothesis records, with version metadata required. The interface
is behind the same detector contract (BaseDetector) so heuristic and learned
outputs are comparable via the same comparison table.

Design refs:
- semantics/registry.py (BaseDetector, DetectorSpec)
- semantics/contracts.py (SemanticHypothesis)
- S7.4 baseline export (same columns/method versions)
"""

from __future__ import annotations

from typing import Any, Callable

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.semantics.contracts import SemanticHypothesis
from passage_practice.semantics.registry import BaseDetector, DetectorSpec


def _check_model_version(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"model_version must be non-empty str, got {value!r}")
    return value


class ModelSemanticAdapter(BaseDetector):
    """Deterministic model adapter behind detector contract.

    - ``spec`` carries detector_id/version and hypothesis_types as usual.
    - ``model_fn`` is a pure function ``(passage, views) -> (hypotheses, diagnostics)``
      that must be deterministic. It is injected for testability (fake model).
    - ``model_version`` and ``training_data_id`` are required provenance and are
      surfaced in hypothesis ``method_version`` and diagnostics.
    - If ``model_version`` is missing or empty, construction fails (version metadata required).
    """

    def __init__(
        self,
        spec: DetectorSpec,
        model_fn: Callable[[Any, dict[str, Any]], tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]],
        *,
        model_version: str,
        training_data_id: str = "synthetic.tiny.v1",
    ) -> None:
        super().__init__(spec)
        if not callable(model_fn):
            raise TypeError("model_fn must be callable")
        _check_model_version(model_version)
        _check_model_version(training_data_id)
        self._model_fn = model_fn
        self.model_version = model_version
        self.training_data_id = training_data_id

    def detect(
        self,
        passage: Any,
        views: dict[str, Any],
        observations: dict[str, Any],
        *,
        investigation: Any | None = None,
        score: Any | None = None,
    ) -> tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]:
        missing = self._missing_required_diagnostics(views)
        if missing is not None:
            return (), missing
        hyps, diags = self._model_fn(passage, views)
        # Enforce version metadata on output hypotheses
        for h in hyps:
            if h.method_version != self.model_version:
                raise ValueError(f"model hypothesis method_version {h.method_version!r} must equal adapter model_version {self.model_version!r}")
        # Append provenance diagnostics
        prov_diags = (
            Diagnostic(code="model_version", severity=Severity.INFO, message=f"model_version={self.model_version}"),
            Diagnostic(code="training_data_id", severity=Severity.INFO, message=f"training_data_id={self.training_data_id}"),
        )
        return hyps, tuple(diags) + prov_diags


def make_fake_model_fn(
    *,
    hypothesis_type: str = "role.melody",
    confidence: float = 0.75,
    method_version: str = "fake_model.v1",
) -> Callable[[Any, dict[str, Any]], tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]]:
    """Create a fake deterministic model function for tests.

    Returns a function that, given (passage, views), produces a single
    SemanticHypothesis covering the passage with the given confidence and
    method_version. Deterministic and version-tagged.
    """

    def _fn(passage: Any, views: dict[str, Any]) -> tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]:
        from fractions import Fraction
        from passage_practice.models.source import SourceKind, SourceRef
        from passage_practice.models.time import ScoreInterval, ScorePosition

        # Need at least one source ref; use passage event_refs if available
        refs = getattr(passage, "event_refs", ())
        if refs:
            covered_refs = (refs[0],)
            try:
                region = ScoreInterval(start=passage.start, end=passage.end)
            except Exception:
                region = ScoreInterval(
                    start=ScorePosition(quarters=Fraction(0), measure_index=0),
                    end=ScorePosition(quarters=Fraction(4), measure_index=0),
                )
            source_passage_id = getattr(passage, "passage_id", "test.passage")
        else:
            # Fallback for tests without passage
            covered_refs = (SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),)
            region = ScoreInterval(
                start=ScorePosition(quarters=Fraction(0), measure_index=0),
                end=ScorePosition(quarters=Fraction(1), measure_index=0),
            )
            source_passage_id = "test.passage"
        hyp = SemanticHypothesis(
            hypothesis_id=f"fake_model:{source_passage_id}:{hypothesis_type.replace('.', '_')}:000",
            hypothesis_type=hypothesis_type,
            source_passage_id=source_passage_id,
            covered_region=region,
            covered_event_ids=covered_refs,
            confidence=confidence,
            confidence_method="learned",
            method_id="fake_model.v1",
            method_version=method_version,
            supporting_observation_ids=(),
            supporting_pattern_ids=(),
            satisfied_criteria=("fake_model",),
            contradictory_criteria=(),
            missing_evidence=(),
            diagnostics=(),
        )
        return (hyp,), ()

    return _fn


__all__ = ["ModelSemanticAdapter", "make_fake_model_fn"]
