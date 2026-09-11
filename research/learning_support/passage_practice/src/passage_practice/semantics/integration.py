"""Semantic-view integration payload — S2.13.

Builds a compact, ref-oriented ``SemanticBundle`` that shows the passage
under analysis together with the views that were read (S2.4–S2.8) and the
observations that were produced (S2.9–S2.12) — without embedding full view
or observation payloads.

Design refs:
- docs/semantic_music_extraction_tasks.md S2.13: one compact payload
  showing passage, view refs, observation refs, diagnostics; deterministic
  JSON and resolvable refs
- semantics/contracts.py: SemanticBundle is immutable, versioned,
  deterministic, ref-oriented; view_refs/observation_refs are opaque ID
  strings, hypotheses may be empty (no detectors yet)
- views/__init__.py: 5 view builders (attack, written, rhythm, texture,
  salience) — all cheap, deterministic, and declared omissions
- observations/__init__.py: 4 observation families (pitch, rhythm,
  texture, notation-readability) — S2.9–S2.12

Salience is the only S2 view that may be treated as optional for this
integration test (to exercise missing-optional-view handling); all other
views are required. Observations are always produced; empty results
abstain with a diagnostic and contribute no observation_ref but do
contribute their method_version and diagnostics.
"""

from __future__ import annotations

from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.investigation import PassageInvestigation

from .contracts import SemanticBundle

# Deterministic version for the integration bundle itself.
INTEGRATION_METHOD_ID = "semantic_view_integration"
INTEGRATION_METHOD_VERSION = "v1"


def _view_ref(view: Any, passage_id: str) -> str:
    """Compact opaque view ref: ``view_type:method_id@version:passage_id``."""
    view_type = getattr(view, "view_type", None)
    # view_type is an Enum (ViewType); use its value
    type_str = getattr(view_type, "value", str(view_type))
    method_id = getattr(view, "method_id", "unknown")
    method_version = getattr(view, "method_version", "v1")
    return f"{type_str}:{method_id}@{method_version}:{passage_id}"


def _method_version_token(method_id: str, method_version: str) -> str:
    return f"{method_id}@{method_version}"


def build_semantic_integration(
    investigation: PassageInvestigation,
    score: Any,
    *,
    bundle_id: str | None = None,
    include_salience: bool = True,
) -> SemanticBundle:
    """Build a deterministic integration bundle referencing views and observations.

    - Reads all S2.4–S2.8 views (attack, written, rhythm, texture, salience).
      When ``include_salience`` is False, salience is omitted and a
      ``missing_optional_view`` diagnostic is recorded.
    - Runs all S2.9–S2.12 observation families (pitch: 4 fns, rhythm: 6 fns,
      texture: 5 fns, notation: 5 fns incl. clef which abstains). Collects
      every emitted ``observation_id`` as ``observation_refs`` and every
      ``method_id@version`` as ``method_versions``.
    - Returns a ``SemanticBundle`` with ``hypotheses=()`` (no S3 detectors yet),
      populated ``view_refs``/``observation_refs``/``method_versions`` and
      aggregated diagnostics. Caller may embed or resolve the referenced IDs
      externally; this bundle stores only refs.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")

    passage = investigation.passage
    passage_id = passage.passage_id
    resolved_bundle_id = bundle_id if bundle_id is not None else f"{passage_id}:integration:v1"

    # Local imports to keep module import light and avoid cycles.
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.written_stream import build_written_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.salience_view import build_salience_view

    from passage_practice import observations as obs

    view_refs: list[str] = []
    method_versions: list[str] = []
    observation_refs: list[str] = []
    diagnostics: list[Diagnostic] = []

    # --- Views (S2.4–S2.8) ---
    view_builders = [
        ("attack", build_attack_stream),
        ("written", build_written_stream),
        ("rhythm", build_rhythm_grid),
        ("texture", build_texture_grid),
    ]
    if include_salience:
        view_builders.append(("salience", build_salience_view))

    for _name, builder in view_builders:
        view = builder(passage, score)  # type: ignore[arg-type]
        view_refs.append(_view_ref(view, passage_id))
        method_versions.append(_method_version_token(view.method_id, view.method_version))
        diagnostics.extend(list(view.diagnostics))

    if not include_salience:
        diagnostics.append(
            Diagnostic(
                code="missing_optional_view",
                severity=Severity.INFO,
                message="salience_view omitted by caller (optional); integration valid without it",
            )
        )

    # --- Observations (S2.9 pitch) ---
    pitch_fns = [
        obs.observe_pitch_range,
        obs.observe_pitch_transitions,
        obs.observe_leap_frequency,
        obs.observe_repeated_notes,
        obs.observe_registral_extremes,
    ]
    # --- S2.10 rhythm ---
    rhythm_fns = [
        obs.observe_attack_density,
        obs.observe_shortest_duration,
        obs.observe_off_beat_density,
        obs.observe_syncopation_proxy,
        obs.observe_hand_alignment_ratio,
        obs.observe_subdivision_mismatch,
    ]
    # --- S2.11 texture ---
    texture_fns = [
        obs.observe_max_simultaneity,
        obs.observe_chord_density,
        obs.observe_sustained_under_moving,
        obs.observe_voice_count,
        obs.observe_staff_crossing,
    ]
    # --- S2.12 notation-readability ---
    notation_fns = [
        obs.observe_accidental_density,
        obs.observe_ledger_line_proxy,
        obs.observe_clef_change_presence,
        obs.observe_articulation_density,
        obs.observe_ornament_grace_notes,
    ]

    all_fns: list[Any] = [*pitch_fns, *rhythm_fns, *texture_fns, *notation_fns]
    seen_method_versions: set[str] = set(method_versions)
    for fn in all_fns:
        result = fn(investigation, score)
        token = _method_version_token(result.method_id, result.method_version)
        if token not in seen_method_versions:
            method_versions.append(token)
            seen_method_versions.add(token)
        # Observation refs: every emitted observation_id (clef abstains → none)
        for o in result.observations:
            observation_refs.append(o.observation_id)
        diagnostics.extend(list(result.diagnostics))

    # Include the integration method itself in provenance
    integration_token = _method_version_token(INTEGRATION_METHOD_ID, INTEGRATION_METHOD_VERSION)
    if integration_token not in seen_method_versions:
        method_versions.append(integration_token)

    # Deterministic ordering: views already in fixed order, observations in
    # fn order which is fixed, method_versions in insertion order which is
    # fixed. No sorting needed; insertion order is the spec.
    bundle = SemanticBundle(
        bundle_id=resolved_bundle_id,
        source_passage_id=passage_id,
        hypotheses=(),
        ranked_hypothesis_ids=(),
        view_refs=tuple(view_refs),
        observation_refs=tuple(observation_refs),
        method_versions=tuple(method_versions),
        diagnostics=tuple(diagnostics),
    )
    return bundle


__all__ = ["INTEGRATION_METHOD_ID", "INTEGRATION_METHOD_VERSION", "build_semantic_integration"]
