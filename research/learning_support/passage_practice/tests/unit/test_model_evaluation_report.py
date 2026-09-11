"""Tests for S7.7 model evaluation report template."""

from __future__ import annotations

import pytest

from passage_practice.semantics.evaluation_report import ModelEvaluationReport, build_template_report
from passage_practice.models.diagnostics import Diagnostic, Severity


def test_template_contains_required_fields():
    report = build_template_report()
    data = report.to_dict()
    assert data["training_data_id"] == "synthetic.tiny.v1"
    assert data["model_version"] == "fake_model.v1"
    assert "heuristic_baseline_id" in data
    assert "metrics" in data
    assert "baseline_comparison" in data
    assert "limitations" in data
    assert len(data["limitations"]) >= 3
    assert "failure_examples" in data
    # No automatic quality claim: limitations must mention no quality claim
    assert any("no quality claim" in lim for lim in data["limitations"])
    assert any(d["code"] == "synthetic_data" for d in data["diagnostics"])


def test_baseline_comparison_and_training_identity():
    report = build_template_report(
        training_data_id="synthetic.tiny.v1",
        model_version="fake_model.v1",
        heuristic_baseline_id="melody_salience.v1",
        metrics={"agreement": 2},
        baseline_comparison={"agreement": 2, "heuristic_count": 4, "model_count": 4},
    )
    assert report.training_data_id == "synthetic.tiny.v1"
    assert report.baseline_comparison["agreement"] == 2
    # Round-trip
    revived = ModelEvaluationReport.from_dict(report.to_dict())
    assert revived == report


def test_limitations_and_failure_examples():
    report = build_template_report()
    assert len(report.limitations) >= 2
    # Failure examples may be empty for tiny template, but field must exist
    assert isinstance(report.failure_examples, tuple)
    # Limitations must be explicit
    assert all(isinstance(l, str) and l for l in report.limitations)


def test_no_automatic_quality_claim():
    report = build_template_report(metrics={"accuracy": 0.5})
    # The report must not claim high quality automatically; it must carry small_data_warning
    assert any(d.code == "small_data_warning" for d in report.diagnostics)
    # Metrics are illustrative only
    assert "accuracy" in report.metrics or "agreement" in report.metrics
