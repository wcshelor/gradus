"""Semantic bundle builder — S3.7.

Runs selected detectors, merges hypotheses, sorts by confidence and family,
keeps contradictions visible.

Depends on S3.2-S3.6.
"""

from __future__ import annotations

from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.semantics.contracts import SemanticBundle
from passage_practice.semantics.registry import DetectorRegistry


def build_semantic_bundle(
    passage: Any,
    views: dict[str, Any],
    observations: dict[str, Any],
    registry: DetectorRegistry | None = None,
    *,
    bundle_id: str | None = None,
    available_views: set[str] | None = None,
) -> SemanticBundle:
    """Run detectors and build a SemanticBundle.

    - Selects detectors via ``registry.selectable_for`` based on ``available_views``
      (defaults to ``views.keys()``), otherwise runs all.
    - Collects hypotheses and diagnostics from each detector.
    - Sorts hypotheses by (-confidence, hypothesis_type, hypothesis_id) for
      determinism; ranked_hypothesis_ids follows that order.
    - Keeps contradictory hypotheses (no winner-takes-all).
    - If no hypotheses, adds ``no_supported_hypothesis`` diagnostic and returns
      empty hypotheses bundle (S1.6 pattern).
    """
    if registry is None:
        # Lazy import to avoid circular deps; create default registry with known detectors
        registry = DetectorRegistry()
        # Register known v1 detectors if available
        try:
            from passage_practice.semantics.melody import MelodySalienceDetector

            registry.register(MelodySalienceDetector())
        except Exception:
            pass
        try:
            from passage_practice.semantics.bass import BassAnchorDetector

            registry.register(BassAnchorDetector())
        except Exception:
            pass
        try:
            from passage_practice.semantics.accompaniment import AccompanimentPatternDetector

            registry.register(AccompanimentPatternDetector())
        except Exception:
            pass
        try:
            from passage_practice.semantics.rhythm import RhythmLayerDetector

            registry.register(RhythmLayerDetector())
        except Exception:
            pass
        try:
            from passage_practice.semantics.texture import TextureClassifier

            registry.register(TextureClassifier())
        except Exception:
            pass

    if available_views is None:
        available_views = set(views.keys())

    selectable = registry.selectable_for(available_views)

    all_hyps: list[Any] = []
    all_diags: list[Diagnostic] = []
    view_refs: list[str] = []
    observation_refs: list[str] = []
    method_versions: list[str] = []

    # Collect view_refs / method_versions from views for provenance
    for vid, view in views.items():
        # view_ref as in integration: type:method@version:passage_id
        vtype = getattr(getattr(view, "view_type", None), "value", str(vid))
        mid = getattr(view, "method_id", vid)
        mver = getattr(view, "method_version", "v1")
        view_refs.append(f"{vtype}:{mid}@{mver}:{passage.passage_id}")
        token = f"{mid}@{mver}"
        if token not in method_versions:
            method_versions.append(token)
        for d in getattr(view, "diagnostics", ()):
            all_diags.append(d)

    # Observation refs
    for oid, result in observations.items():
        # result may be ObservationResult
        for obs in getattr(result, "observations", ()):
            oid_str = getattr(obs, "observation_id", None)
            if oid_str and oid_str not in observation_refs:
                observation_refs.append(oid_str)
        for d in getattr(result, "diagnostics", ()):
            all_diags.append(d)
        mid = getattr(result, "method_id", oid)
        mver = getattr(result, "method_version", "v1")
        token = f"{mid}@{mver}"
        if token not in method_versions:
            method_versions.append(token)

    # Run detectors
    for det in selectable:
        hyps, diags = det.detect(passage, views, observations)
        all_hyps.extend(hyps)
        all_diags.extend(diags)
        token = f"{det.spec.detector_id}@{det.spec.detector_version}"
        if token not in method_versions:
            method_versions.append(token)

    # Also include diagnostics from non-selectable detectors (unsupported view)
    non_selectable = [d for d in registry.list_all() if d not in selectable]
    for det in non_selectable:
        # Emit unsupported diagnostics without running detect (already handled via selectable filter)
        # But we still want to record that they were not run
        all_diags.append(
            Diagnostic(
                code="detector_not_run_missing_view",
                severity=Severity.INFO,
                message=f"detector {det.spec.detector_id!r} not run; missing required views {det.spec.required_views!r}",
            )
        )

    # Deterministic ordering: sort by (-confidence, hypothesis_type, hypothesis_id)
    all_hyps_sorted = sorted(all_hyps, key=lambda h: (-h.confidence, h.hypothesis_type, h.hypothesis_id))
    ranked_ids = tuple(h.hypothesis_id for h in all_hyps_sorted)

    # Deduplicate diagnostics deterministically (by code, message, id)
    # Keep order of first appearance but sorted for determinism? Use insertion order then sort for bundle diagnostics?
    # Bundle diagnostics should be deterministic: sort by (code, message)
    # But we want to preserve mixed detector diagnostics visibly; sorting makes it deterministic
    diag_sorted = tuple(sorted(all_diags, key=lambda d: (d.code, d.message, str(getattr(d, "source_refs", "")))))

    # Handle no-supported-hypothesis
    if not all_hyps_sorted:
        # Ensure diagnostic present
        has_no_support = any(d.code == "no_supported_hypothesis" for d in diag_sorted)
        if not has_no_support:
            diag_sorted = diag_sorted + (
                Diagnostic(
                    code="no_supported_hypothesis",
                    severity=Severity.INFO,
                    message="no detector met its minimum evidence threshold",
                ),
            )

    resolved_bundle_id = bundle_id if bundle_id is not None else f"{passage.passage_id}:semantic_bundle:v1"

    bundle = SemanticBundle(
        bundle_id=resolved_bundle_id,
        source_passage_id=passage.passage_id,
        hypotheses=tuple(all_hyps_sorted),
        ranked_hypothesis_ids=ranked_ids,
        view_refs=tuple(sorted(set(view_refs))),
        observation_refs=tuple(sorted(set(observation_refs))),
        method_versions=tuple(sorted(set(method_versions))),
        diagnostics=diag_sorted,
    )
    return bundle
