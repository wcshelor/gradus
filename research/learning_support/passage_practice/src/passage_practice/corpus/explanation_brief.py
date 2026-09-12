"""S8.4 evidence-grounded explanation brief.

Produces a structured prompt/input payload for explanation adapters from
semantic and pedagogical hypotheses. No unsupported claims, uncertainty
wording fields present.

Design refs:
- S8.1 corpus schema (separate score/system/human/learner)
- S1.5 confidence bands, semantics contracts
- S8.3 synthetic corpus examples
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.corpus.schema import PedagogicalCorpusRecord
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.semantics.confidence import band_for
from passage_practice.semantics.contracts import SemanticBundle

EXPLANATION_BRIEF_SCHEMA_VERSION = "explanation_brief.v1"
SUPPORTED_VERSIONS = {EXPLANATION_BRIEF_SCHEMA_VERSION}

# Allowed claim families that an explanation may mention when grounded.
# Anything outside this set is considered an unsupported claim for audit.
ALLOWED_CLAIM_FAMILIES = {
    "role.melody",
    "role.bass",
    "role.accompaniment",
    "texture.",
    "rhythm.",
    "phrase.",
    "harmony.",
    "motor_proxy.",
    "difficulty_reason.",
    "learner_issue.",
}

# Wording map per band (from semantic_confidence_policy: high likely, medium may, low possible)
WORDING_BY_BAND = {
    "high": "likely",
    "medium": "may",
    "low": "possible",
    "unsupported": "unsupported",
}


def _is_allowed_claim(claim_type: str) -> bool:
    return any(claim_type == f.rstrip(".") or claim_type.startswith(f) for f in ALLOWED_CLAIM_FAMILIES)


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ExplanationBrief:
    """Structured payload for explanation adapters.

    - ``brief_id``: stable ID
    - ``source_passage_id``: passage under explanation
    - ``semantic_bundle_id``: bundle that grounds the claims
    - ``corpus_record_id``: optional corpus record reference
    - ``supported_claims``: list of claim types grounded in semantic hypotheses
    - ``uncertainty_wording``: dict claim_type -> wording ("likely"/"may"/"possible")
    - ``confidence_bands``: dict claim_type -> band ("high"/"medium"/"low")
    - ``caveats``: learner-dependent or provenance caveats
    - ``provenance``: synthetic/human, with diagnostics
    """

    brief_id: str
    source_passage_id: str
    semantic_bundle_id: str
    supported_claims: tuple[str, ...] = ()
    uncertainty_wording: tuple[dict[str, str], ...] = ()
    confidence_bands: tuple[dict[str, str], ...] = ()
    caveats: tuple[str, ...] = ()
    corpus_record_id: str | None = None
    provenance: str = "synthetic"
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = EXPLANATION_BRIEF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_id(self.brief_id, "brief_id")
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.semantic_bundle_id, "semantic_bundle_id")
        if self.corpus_record_id is not None:
            _check_id(self.corpus_record_id, "corpus_record_id")
        if not isinstance(self.supported_claims, tuple):
            raise TypeError("supported_claims must be tuple")
        for c in self.supported_claims:
            if not isinstance(c, str) or not c:
                raise ValueError(f"supported_claims must contain non-empty str, got {c!r}")
            if not _is_allowed_claim(c):
                raise ValueError(f"unsupported claim {c!r}; allowed families: {sorted(ALLOWED_CLAIM_FAMILIES)}")
        if not isinstance(self.uncertainty_wording, tuple):
            raise TypeError("uncertainty_wording must be tuple")
        if not isinstance(self.confidence_bands, tuple):
            raise TypeError("confidence_bands must be tuple")
        if not isinstance(self.caveats, tuple):
            raise TypeError("caveats must be tuple")
        if self.provenance not in ("synthetic", "human"):
            raise ValueError(f"provenance must be synthetic/human, got {self.provenance!r}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        if self.schema_version != EXPLANATION_BRIEF_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {EXPLANATION_BRIEF_SCHEMA_VERSION!r}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "brief_id": self.brief_id,
            "source_passage_id": self.source_passage_id,
            "semantic_bundle_id": self.semantic_bundle_id,
            "supported_claims": list(self.supported_claims),
            "uncertainty_wording": list(self.uncertainty_wording),
            "confidence_bands": list(self.confidence_bands),
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }
        if self.corpus_record_id is not None:
            payload["corpus_record_id"] = self.corpus_record_id
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExplanationBrief":
        if not isinstance(data, dict):
            raise TypeError(f"ExplanationBrief requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        try:
            brief_id = data["brief_id"]
            source_passage_id = data["source_passage_id"]
            semantic_bundle_id = data["semantic_bundle_id"]
            supported_claims = data["supported_claims"]
            uncertainty_wording = data["uncertainty_wording"]
            confidence_bands = data["confidence_bands"]
            caveats = data["caveats"]
            provenance = data["provenance"]
        except KeyError as exc:
            raise ValueError(f"missing ExplanationBrief field {exc.args[0]!r}") from exc
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("diagnostics must be list")
        return cls(
            brief_id=str(brief_id),
            source_passage_id=str(source_passage_id),
            semantic_bundle_id=str(semantic_bundle_id),
            supported_claims=tuple(str(c) for c in supported_claims),
            uncertainty_wording=tuple(dict(d) for d in uncertainty_wording),
            confidence_bands=tuple(dict(d) for d in confidence_bands),
            caveats=tuple(str(c) for c in caveats),
            corpus_record_id=str(data["corpus_record_id"]) if "corpus_record_id" in data else None,
            provenance=str(provenance),
            diagnostics=tuple(__import__("passage_practice.models.diagnostics", fromlist=["Diagnostic"]).Diagnostic.from_dict(d) for d in raw_diags),
        )


def build_explanation_brief(
    bundle: SemanticBundle,
    corpus_record: PedagogicalCorpusRecord | None = None,
    *,
    brief_id: str | None = None,
) -> ExplanationBrief:
    """Build an evidence-grounded brief from a semantic bundle and optional corpus record.

    - Only claim types present in ``bundle.hypotheses`` become ``supported_claims``
    - Each claim's confidence band and wording derived via ``band_for``
    - Caveats include provenance and learner-dependent notes
    - No unsupported claims (e.g., harmony or learner trait not in bundle) are invented
    """
    if not isinstance(bundle, SemanticBundle):
        raise TypeError(f"bundle must be SemanticBundle, got {type(bundle).__name__}")
    # Supported claims are exactly the hypothesis types present
    supported = tuple(sorted({h.hypothesis_type for h in bundle.hypotheses}))
    # Enforce allowed families (filter unsupported - should not happen for heuristic bundles, but guard)
    filtered_supported = tuple(c for c in supported if _is_allowed_claim(c))
    # Build per-claim wording and bands only for filtered supported claims
    # If multiple hypotheses share a type, keep the highest confidence for wording/band
    filtered_set = set(filtered_supported)
    best_by_type: dict[str, Any] = {}
    for h in bundle.hypotheses:
        if h.hypothesis_type not in filtered_set:
            continue
        existing = best_by_type.get(h.hypothesis_type)
        if existing is None or h.confidence > existing.confidence:
            best_by_type[h.hypothesis_type] = h
    wording_list: list[dict[str, str]] = []
    band_list: list[dict[str, str]] = []
    for claim_type in sorted(best_by_type):
        h = best_by_type[claim_type]
        band = band_for(h.confidence).value
        wording = WORDING_BY_BAND[band]
        wording_list.append({"claim_type": claim_type, "wording": wording})
        band_list.append({"claim_type": claim_type, "band": band})
    wording_tuple = tuple(wording_list)
    band_tuple = tuple(band_list)

    caveats: list[str] = []
    if corpus_record is not None:
        if corpus_record.human_explanation:
            caveats.append("human_explanation_present: teacher note preserved separately from system claims")
        if corpus_record.learner_feedback_ids:
            caveats.append("learner_feedback_present: learner perspective is separate evidence")
        caveats.append(f"provenance:{corpus_record.provenance}")
    else:
        caveats.append("no_corpus_context: score-only evidence")
    # Always add uncertainty caveat
    caveats.append("uncertainty: confidence is uncalibrated heuristic ranking, not probability")

    resolved_brief_id = brief_id if brief_id is not None else f"{bundle.source_passage_id}:brief:v1"
    diagnostics = (
        Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic brief for testing"),
    )
    return ExplanationBrief(
        brief_id=resolved_brief_id,
        source_passage_id=bundle.source_passage_id,
        semantic_bundle_id=bundle.bundle_id,
        supported_claims=filtered_supported,
        uncertainty_wording=wording_tuple,
        confidence_bands=band_tuple,
        caveats=tuple(caveats),
        corpus_record_id=corpus_record.record_id if corpus_record else None,
        provenance="synthetic",
        diagnostics=diagnostics,
    )


__all__ = ["ExplanationBrief", "EXPLANATION_BRIEF_SCHEMA_VERSION", "build_explanation_brief", "ALLOWED_CLAIM_FAMILIES"]
