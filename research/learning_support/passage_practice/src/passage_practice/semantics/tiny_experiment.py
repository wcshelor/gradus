"""S7.6 tiny learned-model experiment plumbing.

Uses small local synthetic data only to test plumbing, not claim quality.
Compares heuristic baseline vs fake model via the same comparison table.

Design refs:
- S7.4 baseline export, S7.5 model interface
- S7.3 synthetic fixtures, S7.2 annotation records
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from passage_practice.annotation.contracts import AnnotationRecord
from passage_practice.annotation.export import export_baseline_comparison
from passage_practice.semantics.contracts import SemanticBundle
from passage_practice.semantics.model_interface import ModelSemanticAdapter, make_fake_model_fn
from passage_practice.semantics.registry import DetectorSpec


def run_tiny_experiment(
    bundles: list[SemanticBundle],
    annotation_sets: list[tuple[AnnotationRecord, ...]],
    *,
    model_version: str = "fake_model.v1",
    training_data_id: str = "synthetic.tiny.v1",
) -> dict[str, Any]:
    """Run tiny experiment plumbing.

    - ``bundles``: heuristic semantic bundles (one per passage)
    - ``annotation_sets``: corresponding annotation tuples
    - Builds a fake model adapter for each bundle's passage and compares
      model outputs vs heuristic via stable columns.

    Returns dict with:
    - ``heuristic_rows``: baseline comparison rows (heuristic)
    - ``model_rows``: model comparison rows (fake model)
    - ``abstention_count``: number of model bundles that abstained (0 hyps)
    - ``comparison``: simple metric dict (heuristic vs model agreement)
    """
    if len(bundles) != len(annotation_sets):
        raise ValueError(f"bundles and annotation_sets length mismatch {len(bundles)} vs {len(annotation_sets)}")

    heuristic_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    abstention_count = 0

    for bundle, anns in zip(bundles, annotation_sets):
        # Heuristic baseline rows
        heuristic_rows.extend(export_baseline_comparison(bundle, anns))

        # Fake model: create a bundle with model hypothesis
        # For plumbing, we create a minimal model bundle that mirrors heuristic passage
        # Use the model's adapter to produce a hypothesis, then wrap in a SemanticBundle
        from fractions import Fraction
        from passage_practice.models.time import ScorePosition, ScoreInterval
        from passage_practice.models.source import SourceKind, SourceRef
        from passage_practice.models.diagnostics import Diagnostic

        # Use same passage ID as heuristic bundle
        passage_id = bundle.source_passage_id
        # Create a fake model hypothesis via adapter (deterministic)
        # We need passage/views; for tiny experiment we reuse bundle's first hypothesis refs
        # Instead, create a synthetic passage mock with one ref
        class FakePassage:
            def __init__(self, pid, refs):
                self.passage_id = pid
                self.event_refs = refs
                self.start = ScorePosition(quarters=Fraction(0), measure_index=0, measure_number="1", offset_in_measure=Fraction(0))
                self.end = ScorePosition(quarters=Fraction(4), measure_index=0, measure_number="1", offset_in_measure=Fraction(4))

        fake_refs = bundle.hypotheses[0].covered_event_ids if bundle.hypotheses else (SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),)
        fake_passage = FakePassage(passage_id, fake_refs)

        spec = DetectorSpec(
            detector_id="fake_model.v1",
            detector_version="v1",
            hypothesis_types=("role.melody",),
            required_views=(),
        )
        fn = make_fake_model_fn(hypothesis_type="role.melody", confidence=0.70, method_version=model_version)
        adapter = ModelSemanticAdapter(spec, fn, model_version=model_version, training_data_id=training_data_id)
        hyps, diags = adapter.detect(fake_passage, {}, {})

        if not hyps:
            abstention_count += 1

        # Wrap in SemanticBundle for export
        from passage_practice.semantics.contracts import SemanticBundle as SB

        model_bundle = SB(
            bundle_id=f"{passage_id}:model_bundle:v1",
            source_passage_id=passage_id,
            hypotheses=hyps,
            ranked_hypothesis_ids=tuple(h.hypothesis_id for h in hyps),
            method_versions=(f"fake_model.v1@{model_version}",),
            diagnostics=tuple(diags),
        )
        model_rows.extend(export_baseline_comparison(model_bundle, anns))

    # Simple comparison: agreement on top hypothesis type
    heuristic_top = {r["annotation_id"]: r["detector_hypothesis_types"][0] if r["detector_hypothesis_types"] else None for r in heuristic_rows}
    model_top = {r["annotation_id"]: r["detector_hypothesis_types"][0] if r["detector_hypothesis_types"] else None for r in model_rows}
    agreement = sum(1 for k in heuristic_top if heuristic_top[k] == model_top.get(k)) if heuristic_top else 0

    return {
        "heuristic_rows": heuristic_rows,
        "model_rows": model_rows,
        "abstention_count": abstention_count,
        "comparison": {
            "heuristic_count": len(heuristic_rows),
            "model_count": len(model_rows),
            "agreement": agreement,
            "training_data_id": training_data_id,
            "model_version": model_version,
        },
    }


__all__ = ["run_tiny_experiment"]
