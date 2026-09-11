"""S7.7 model evaluation report template.

Documents metrics, baseline comparison, training-data identity, limitations,
and failure examples. No automatic quality claims — the report is a template
that must be filled with explicit values and reviewed.

Design refs:
- S7.6 tiny experiment, S7.4 baseline export
- S7.5 model interface (version metadata)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.models.diagnostics import Diagnostic


REPORT_SCHEMA_VERSION = "model_evaluation_report.v1"
SUPPORTED_VERSIONS = {REPORT_SCHEMA_VERSION}


@dataclass(frozen=True, slots=True)
class ModelEvaluationReport:
    """Template for model vs heuristic evaluation.

    - report_id: stable ID
    - training_data_id: required provenance (synthetic.tiny.v1)
    - model_version: required provenance
    - heuristic_baseline_id: ID of heuristic method (e.g., melody_salience.v1)
    - metrics: dict of metric name -> value (must be explicit; no hidden claims)
    - baseline_comparison: dict with heuristic/model agreement, counts
    - limitations: tuple of known limitations (must be non-empty)
    - failure_examples: tuple of dicts with annotation_id, expected vs predicted
    - diagnostics: e.g., synthetic_data, small_data_warning
    """

    report_id: str
    training_data_id: str
    model_version: str
    heuristic_baseline_id: str
    metrics: dict[str, Any]
    baseline_comparison: dict[str, Any]
    limitations: tuple[str, ...]
    failure_examples: tuple[dict[str, Any], ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, str) or not self.report_id:
            raise ValueError(f"report_id must be non-empty str, got {self.report_id!r}")
        if not isinstance(self.training_data_id, str) or not self.training_data_id:
            raise ValueError("training_data_id required")
        if not isinstance(self.model_version, str) or not self.model_version:
            raise ValueError("model_version required")
        if not isinstance(self.heuristic_baseline_id, str) or not self.heuristic_baseline_id:
            raise ValueError("heuristic_baseline_id required")
        if not isinstance(self.metrics, dict):
            raise TypeError("metrics must be dict")
        if not isinstance(self.baseline_comparison, dict):
            raise TypeError("baseline_comparison must be dict")
        if not isinstance(self.limitations, tuple) or not self.limitations:
            raise ValueError("limitations must be non-empty tuple")
        for lim in self.limitations:
            if not isinstance(lim, str) or not lim:
                raise ValueError(f"limitation must be non-empty str, got {lim!r}")
        if not isinstance(self.failure_examples, tuple):
            raise TypeError("failure_examples must be tuple")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "training_data_id": self.training_data_id,
            "model_version": self.model_version,
            "heuristic_baseline_id": self.heuristic_baseline_id,
            "metrics": dict(self.metrics),
            "baseline_comparison": dict(self.baseline_comparison),
            "limitations": list(self.limitations),
            "failure_examples": list(self.failure_examples),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelEvaluationReport":
        if not isinstance(data, dict):
            raise TypeError(f"ModelEvaluationReport requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        return cls(
            report_id=data["report_id"],
            training_data_id=data["training_data_id"],
            model_version=data["model_version"],
            heuristic_baseline_id=data["heuristic_baseline_id"],
            metrics=dict(data.get("metrics", {})),
            baseline_comparison=dict(data.get("baseline_comparison", {})),
            limitations=tuple(data.get("limitations", [])),
            failure_examples=tuple(data.get("failure_examples", [])),
            diagnostics=tuple(__import__("passage_practice.models.diagnostics", fromlist=["Diagnostic"]).Diagnostic.from_dict(d) for d in data.get("diagnostics", [])),
        )


def build_template_report(
    *,
    report_id: str = "report.synthetic.tiny.v1",
    training_data_id: str = "synthetic.tiny.v1",
    model_version: str = "fake_model.v1",
    heuristic_baseline_id: str = "melody_salience.v1",
    metrics: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> ModelEvaluationReport:
    """Build a template report with explicit limitations and no quality claims."""
    from passage_practice.models.diagnostics import Diagnostic, Severity

    if metrics is None:
        metrics = {"agreement": 0, "heuristic_count": 0, "model_count": 0}
    if baseline_comparison is None:
        baseline_comparison = {"heuristic": heuristic_baseline_id, "model": model_version, "note": "plumbing only; no quality claim"}

    limitations = (
        "tiny synthetic data only; no quality claim",
        "model not trained on real data; heuristic remains primary",
        "small sample cannot establish general validity",
    )
    failure_examples: tuple[dict[str, Any], ...] = ()
    diagnostics = (
        Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic tiny data; no quality claim"),
        Diagnostic(code="small_data_warning", severity=Severity.WARNING, message="small sample; metrics are illustrative only"),
    )
    return ModelEvaluationReport(
        report_id=report_id,
        training_data_id=training_data_id,
        model_version=model_version,
        heuristic_baseline_id=heuristic_baseline_id,
        metrics=metrics,
        baseline_comparison=baseline_comparison,
        limitations=limitations,
        failure_examples=failure_examples,
        diagnostics=diagnostics,
    )


__all__ = ["ModelEvaluationReport", "REPORT_SCHEMA_VERSION", "build_template_report"]
