"""S7.4 heuristic baseline export.

Exports detector outputs (SemanticBundle) and human labels (AnnotationRecord)
to a compact comparison table for S7.4 verification.

Design refs:
- docs/annotation_schema.md
- semantics/contracts.py, annotation/contracts.py
- S7.3 synthetic fixtures
"""

from __future__ import annotations

from typing import Any

from passage_practice.annotation.contracts import AnnotationRecord
from passage_practice.semantics.contracts import SemanticBundle


def export_baseline_comparison(
    bundle: SemanticBundle,
    annotations: tuple[AnnotationRecord, ...],
) -> list[dict[str, Any]]:
    """Export a compact comparison table.

    Each row corresponds to one annotation record, with detector hypotheses
    for the same passage as context. Columns are stable:

    - ``source_passage_id``: passage under analysis (from bundle)
    - ``annotation_id``: human label ID
    - ``label_family``: e.g., melody
    - ``label_value``: e.g., top_voice
    - ``annotator_role``: e.g., synthetic
    - ``detector_hypothesis_types``: sorted list of hypothesis_type in bundle
    - ``detector_method_versions``: sorted list of method_version strings
    - ``source_refs``: sorted list of source_ref IDs from first detector hypothesis (or empty)
    - ``annotation_confidence``: human label confidence
    - ``detector_top_confidence``: max detector confidence or None

    The table is deterministic (sorted by annotation_id) and does not mutate inputs.
    """
    if not isinstance(bundle, SemanticBundle):
        raise TypeError(f"bundle must be SemanticBundle, got {type(bundle).__name__}")
    if not isinstance(annotations, tuple):
        raise TypeError("annotations must be tuple")
    for a in annotations:
        if not isinstance(a, AnnotationRecord):
            raise TypeError(f"annotations must contain AnnotationRecord, got {type(a).__name__}")

    # Stable detector info
    det_types = tuple(sorted({h.hypothesis_type for h in bundle.hypotheses}))
    det_methods = tuple(sorted({f"{h.method_id}@{h.method_version}" for h in bundle.hypotheses} | set(bundle.method_versions)))
    # Source refs from first hypothesis if any
    first_refs: tuple[str, ...] = ()
    if bundle.hypotheses:
        first_refs = tuple(sorted({r.id for h in bundle.hypotheses for r in h.covered_event_ids}))
    top_conf = max((h.confidence for h in bundle.hypotheses), default=None)

    rows: list[dict[str, Any]] = []
    for ann in sorted(annotations, key=lambda a: a.annotation_id):
        rows.append(
            {
                "source_passage_id": bundle.source_passage_id,
                "annotation_id": ann.annotation_id,
                "label_family": ann.label_family.value,
                "label_value": ann.label_value,
                "annotator_role": ann.annotator_role.value,
                "detector_hypothesis_types": list(det_types),
                "detector_method_versions": list(det_methods),
                "source_refs": list(first_refs),
                "annotation_confidence": ann.confidence,
                "detector_top_confidence": top_conf,
            }
        )
    return rows


__all__ = ["export_baseline_comparison"]
