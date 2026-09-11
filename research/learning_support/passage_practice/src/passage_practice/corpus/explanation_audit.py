"""S8.5 explanation-audit checks.

Verifies that generated or template explanations cannot introduce melody,
harmony, learner, or difficulty claims missing from the structured evidence.

Design refs:
- S8.4 explanation brief (supported_claims, uncertainty wording)
- S8.1 corpus schema (separate evidence types)
"""

from __future__ import annotations

import re
from typing import Any

from passage_practice.corpus.explanation_brief import ExplanationBrief

# Claim families that require evidence; if a text mentions these without
# evidence, it's a violation. Mapping from keyword regex to required claim family prefix.
CLAIM_KEYWORDS: dict[str, str] = {
    r"\bmelody\b": "role.melody",
    r"\bbass\b": "role.bass",
    r"\baccompaniment\b": "role.accompaniment",
    r"\bharmony\b": "harmony.",
    r"\bharmonic\b": "harmony.",
    r"\bcadence\b": "harmony.",
    r"\blearner\b": "learner_issue.",
    r"\bdifficulty\b": "difficulty_reason.",
    r"\bcoordination\b": "rhythm.",
    r"\bphrase\b": "phrase.",
    r"\btexture\b": "texture.",
}


def _normalize(text: str) -> str:
    return text.lower()


def audit_explanation(text: str, brief: ExplanationBrief) -> list[dict[str, Any]]:
    """Audit explanation text against a brief's supported claims.

    Returns list of violations, each with ``keyword``, ``required_claim``,
    and ``message``. Empty list means no unsupported claims detected.

    The audit is intentionally conservative (keyword-based) for the synthetic
    phase; it does not parse semantics, but it catches obvious overclaims.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")
    if not isinstance(brief, ExplanationBrief):
        raise TypeError(f"brief must be ExplanationBrief, got {type(brief).__name__}")
    violations: list[dict[str, Any]] = []
    supported = set(brief.supported_claims)
    # Also allow families: if brief has role.melody.ambiguous, it supports role.melody family
    # Check prefix match for families like harmony.
    def is_supported(required: str) -> bool:
        # Exact or prefix match: required "harmony." matches any supported starting with "harmony."
        if required.endswith("."):
            return any(s.startswith(required) for s in supported)
        return required in supported

    lower = _normalize(text)
    for pattern, required_claim in CLAIM_KEYWORDS.items():
        if re.search(pattern, lower):
            if not is_supported(required_claim):
                violations.append(
                    {
                        "keyword": pattern,
                        "required_claim": required_claim,
                        "message": f"text mentions {pattern!r} but brief lacks {required_claim!r}; supported: {sorted(supported)}",
                    }
                )
    return violations


def template_explanation(brief: ExplanationBrief) -> str:
    """Deterministic template explanation from a brief.

    Uses only supported claims and uncertainty wording from the brief.
    Never invents claims outside supported_claims.
    """
    if not brief.supported_claims:
        return "No supported semantic hypothesis for this passage. Consider asking the learner what feels difficult."
    parts: list[str] = []
    # Map wording for each supported claim
    wording_map = {d["claim_type"]: d["wording"] for d in brief.uncertainty_wording}
    for claim in sorted(brief.supported_claims):
        wording = wording_map.get(claim, "may")
        # Minimal grounded sentence per claim
        parts.append(f"{claim} {wording} present.")
    # Add caveat
    if brief.caveats:
        parts.append(f"Caveats: {'; '.join(brief.caveats[:2])}")
    return " ".join(parts)


def mock_llm_explanation(brief: ExplanationBrief, *, inject_unsupported: bool = False) -> str:
    """Mock LLM path for audit tests.

    When ``inject_unsupported`` is False, delegates to the grounded template.
    When True, injects an unsupported harmony claim to test audit detection.
    """
    base = template_explanation(brief)
    if inject_unsupported:
        # Inject a harmony claim even if brief has no harmony evidence
        return base + " Harmony suggests a cadence at the end."
    return base


__all__ = ["audit_explanation", "template_explanation", "mock_llm_explanation", "CLAIM_KEYWORDS"]
