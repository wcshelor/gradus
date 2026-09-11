"""S4.8 integration report: passage -> semantic -> pedagogical hypotheses.

Produces a compact report that shows difficulty context is optional, semantic
evidence is required, and learner caveats are retained. The report is the
testable handoff for S4.8 and does not invoke transformations.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1)
- pedagogy/contracts.py, pedagogy/rules.py
- pedagogy/melody_projection.py, bass_leap.py, rhythmic_coordination.py, reading_load.py
- pedagogy/compatibility.py (S4.7)
- semantics/bundle_builder.py (semantic bundle source)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.bass_leap import build_bass_leap_hypothesis
from passage_practice.pedagogy.compatibility import get_compatible_strategies
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.pedagogy.melody_projection import build_melody_projection_hypothesis
from passage_practice.pedagogy.reading_load import build_reading_load_hypothesis
from passage_practice.pedagogy.rhythmic_coordination import build_rhythmic_coordination_hypothesis
from passage_practice.semantics.contracts import SemanticBundle

REPORT_SCHEMA_VERSION = "pedagogical_report.v1"
METHOD_ID = "pedagogical_integration.v1"
METHOD_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class PedagogicalReport:
    """Compact integration report for one passage.

    - source_passage_id: required passage under analysis
    - semantic_bundle: the semantic analysis (required evidence)
    - pedagogical_hypotheses: ranked pedagogical hypotheses derived from semantics
      plus optional observations; may be empty with diagnostic (no supported
      pedagogical finding is a valid abstention, not an error).
    - difficulty_context_refs: optional IDs of DifficultyEvidence considered
      (may be empty → still valid, per S4.8 "difficulty context optional").
    - learner_caveats: union of learner caveats from hypotheses (retained verbatim).
    - method_versions: provenance of semantic + pedagogical methods run.
    - diagnostics: integration-level diagnostics (e.g., no pedagogical hypothesis
      produced, but semantic evidence present).
    """

    source_passage_id: str
    semantic_bundle: SemanticBundle
    pedagogical_hypotheses: tuple[PedagogicalHypothesis, ...] = ()
    difficulty_context_refs: tuple[str, ...] = ()
    learner_caveats: tuple[str, ...] = ()
    method_versions: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.source_passage_id, str) or not self.source_passage_id:
            raise ValueError(f"source_passage_id must be non-empty str, got {self.source_passage_id!r}")
        if not isinstance(self.semantic_bundle, SemanticBundle):
            raise TypeError(f"semantic_bundle must be SemanticBundle, got {type(self.semantic_bundle).__name__}")
        if self.semantic_bundle.source_passage_id != self.source_passage_id:
            raise ValueError(
                f"semantic bundle passage {self.semantic_bundle.source_passage_id!r} "
                f"does not match report passage {self.source_passage_id!r}"
            )
        if not isinstance(self.pedagogical_hypotheses, tuple):
            raise TypeError("pedagogical_hypotheses must be tuple")
        for h in self.pedagogical_hypotheses:
            if not isinstance(h, PedagogicalHypothesis):
                raise TypeError(f"pedagogical_hypotheses must contain PedagogicalHypothesis, got {type(h).__name__}")
            if h.source_passage_id != self.source_passage_id:
                raise ValueError(f"hypothesis {h.hypothesis_id!r} passage mismatch")
        if not isinstance(self.difficulty_context_refs, tuple):
            raise TypeError("difficulty_context_refs must be tuple")
        if not isinstance(self.method_versions, tuple):
            raise TypeError("method_versions must be tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_passage_id": self.source_passage_id,
            "semantic_bundle": self.semantic_bundle.to_dict(),
            "pedagogical_hypotheses": [h.to_dict() for h in self.pedagogical_hypotheses],
            "difficulty_context_refs": list(self.difficulty_context_refs),
            "learner_caveats": list(self.learner_caveats),
            "method_versions": list(self.method_versions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "method_id": METHOD_ID,
            "method_version": METHOD_VERSION,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PedagogicalReport":
        if not isinstance(data, dict):
            raise TypeError(f"PedagogicalReport requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version != REPORT_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version {version!r}")
        bundle = SemanticBundle.from_dict(data["semantic_bundle"])
        hyps = tuple(PedagogicalHypothesis.from_dict(h) for h in data.get("pedagogical_hypotheses", []))
        return cls(
            source_passage_id=data["source_passage_id"],
            semantic_bundle=bundle,
            pedagogical_hypotheses=hyps,
            difficulty_context_refs=tuple(data.get("difficulty_context_refs", [])),
            learner_caveats=tuple(data.get("learner_caveats", [])),
            method_versions=tuple(data.get("method_versions", [])),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in data.get("diagnostics", [])),
        )


def build_pedagogical_report(
    bundle: SemanticBundle,
    *,
    passage: Any | None = None,
    difficulty_context_refs: tuple[str, ...] = (),
    accidental_count: int | None = None,
    syncopation_proxy_count: int | None = None,
    shortest_duration_ticks: int | None = None,
    has_low_redundancy: bool = False,
    layout_available: bool = False,
    leap_count: int | None = None,
    hand_alignment_ratio: int | None = None,
    learner_feedback_present: bool = False,
) -> PedagogicalReport:
    """Build a pedagogical report from a semantic bundle and optional observations.

    - ``bundle`` is required semantic evidence (S4.8 "semantic evidence required").
      If bundle has no hypotheses, the report still succeeds with empty
      pedagogical hypotheses and a diagnostic.
    - ``difficulty_context_refs`` is optional (S4.8 "difficulty context optional"):
      an empty tuple is valid and does not block report generation. Callers that
      pass analyzer-suggested DifficultyEvidence should supply resolvable IDs here
      for provenance; user-selected passages supply ``()`` and succeed.
    - Observation params are optional and forwarded to the respective builders.
    - Learner caveats from all produced hypotheses are unioned into the report's
      ``learner_caveats`` (retained, not hidden).
    """
    if not isinstance(bundle, SemanticBundle):
        raise TypeError(f"bundle must be SemanticBundle, got {type(bundle).__name__}")

    source_passage_id = bundle.source_passage_id
    if passage is not None:
        pid = getattr(passage, "passage_id", None)
        if pid is not None and pid != source_passage_id:
            raise ValueError(f"passage {pid!r} does not match bundle {source_passage_id!r}")

    hyps: list[PedagogicalHypothesis] = []
    diagnostics: list[Diagnostic] = []

    # Build each family; each builder handles its own applicability and learner caveats
    for builder, kwargs in [
        (build_melody_projection_hypothesis, {"learner_feedback_present": learner_feedback_present}),
        (build_bass_leap_hypothesis, {"leap_count": leap_count, "learner_feedback_present": learner_feedback_present}),
        (build_rhythmic_coordination_hypothesis, {"hand_alignment_ratio": hand_alignment_ratio, "learner_feedback_present": learner_feedback_present}),
        (
            build_reading_load_hypothesis,
            {
                "accidental_count": accidental_count,
                "syncopation_proxy_count": syncopation_proxy_count,
                "shortest_duration_ticks": shortest_duration_ticks,
                "has_low_redundancy": has_low_redundancy,
                "layout_available": layout_available,
                "learner_feedback_present": learner_feedback_present,
            },
        ),
    ]:
        hyp = builder(bundle, **kwargs)  # type: ignore[arg-type]
        if hyp is not None:
            hyps.append(hyp)

    # Rank by confidence descending, then hypothesis_type for determinism
    hyps_sorted = tuple(sorted(hyps, key=lambda h: (-h.confidence, h.hypothesis_type)))

    # Union learner caveats
    caveats_set: set[str] = set()
    for h in hyps_sorted:
        caveats_set.update(h.learner_caveats)
    learner_caveats = tuple(sorted(caveats_set))

    # Method versions provenance: semantic bundle methods + pedagogical methods
    method_versions = tuple(sorted(set(bundle.method_versions) | {f"{METHOD_ID}@{METHOD_VERSION}"}))

    if not hyps_sorted:
        diagnostics.append(
            Diagnostic(
                code="no_supported_pedagogical_hypothesis",
                severity=Severity.INFO,
                message="no pedagogical hypothesis met thresholds; semantic evidence present but no qualified learner focus",
            )
        )
    if not difficulty_context_refs:
        diagnostics.append(
            Diagnostic(
                code="difficulty_context_optional_empty",
                severity=Severity.INFO,
                message="no difficulty context supplied; report valid for user-selected passage without hotspot",
            )
        )
    else:
        diagnostics.append(
            Diagnostic(
                code="difficulty_context_present",
                severity=Severity.INFO,
                message=f"difficulty context refs {difficulty_context_refs!r} retained as optional context",
            )
        )

    # Surface compatibility: ensure each hypothesis has at least one compatible strategy
    for h in hyps_sorted:
        strategies = get_compatible_strategies(h.hypothesis_type)
        if not strategies:
            diagnostics.append(
                Diagnostic(
                    code="no_compatible_strategy",
                    severity=Severity.WARNING,
                    message=f"hypothesis {h.hypothesis_id!r} has no compatible strategies",
                )
            )

    return PedagogicalReport(
        source_passage_id=source_passage_id,
        semantic_bundle=bundle,
        pedagogical_hypotheses=hyps_sorted,
        difficulty_context_refs=difficulty_context_refs,
        learner_caveats=learner_caveats,
        method_versions=method_versions,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["PedagogicalReport", "REPORT_SCHEMA_VERSION", "build_pedagogical_report"]
