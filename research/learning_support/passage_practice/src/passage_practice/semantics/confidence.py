"""Confidence value objects and helpers — S1.5 (D-016, S-Q003 policy).

Enforces `docs/semantic_confidence_policy.md`: deterministic uncalibrated
ranking scores in [0, 1], exact band boundaries, the `confidence_method`
vocabulary, and a shared contradiction-penalty helper. No detector
thresholds live here — penalties are detector-local inputs, bands are
presentation rules, and calibration itself stays reserved (Q-006).

Design refs:
- docs/semantic_confidence_policy.md: bands, vocabulary, abstention split
- docs/decisions.md: D-016 (S-Q003 policy), Q-006 (uncalibrated v1)
"""

from __future__ import annotations

import math
from enum import Enum

# Exact presentation-floor and band boundaries from the S1.4 policy.
# Lower-bound inclusive; upper-bound exclusive except high, which includes
# 1.0. Boundary values are exactly representable floats, so derivation is
# exact, not approximate.
HIGH_FLOOR = 0.75
MEDIUM_FLOOR = 0.50
LOW_FLOOR = 0.25
PRESENTATION_FLOOR = LOW_FLOOR


class ConfidenceBand(str, Enum):
    """Presentation band for a bounded confidence score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSUPPORTED = "unsupported"


class ConfidenceMethod(str, Enum):
    """Calibration status declared by a confidence producer."""

    HEURISTIC = "heuristic"
    CALIBRATED = "calibrated"
    LEARNED = "learned"


def check_confidence(value: float) -> float:
    """Validate a bounded confidence score and return it as float.

    Rejects bools, non-numbers, NaN/inf, and anything outside [0, 1].
    Shared by the S1.2 contract and every helper in this module so the
    bound has a single source of truth.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"confidence must be a finite number, got {value!r}")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(
            f"confidence must be bounded in [0, 1], got {value!r}"
        )
    return result


def band_for(value: float) -> ConfidenceBand:
    """Derive the S1.4 presentation band for a confidence score.

    Pure and deterministic: the same input always yields the same band.
    Mapping is presentation only — it never alters the stored score.
    """
    score = check_confidence(value)
    if score >= HIGH_FLOOR:
        return ConfidenceBand.HIGH
    if score >= MEDIUM_FLOOR:
        return ConfidenceBand.MEDIUM
    if score >= LOW_FLOOR:
        return ConfidenceBand.LOW
    return ConfidenceBand.UNSUPPORTED


def parse_method_status(value: str) -> ConfidenceMethod:
    """Validate a `confidence_method` string against the S1.4 vocabulary.

    Exact match only — no case folding or silent normalization. Unknown
    statuses fail explicitly (supported-subset rule); `calibrated` and
    `learned` parse here but remain unusable until their policy
    prerequisites (Q-006, S7) are met, which detectors must check.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"confidence_method must be str, got {type(value).__name__}"
        )
    try:
        return ConfidenceMethod(value)
    except ValueError as exc:
        raise ValueError(
            "unknown confidence_method "
            f"{value!r}; supported: {sorted(m.value for m in ConfidenceMethod)}"
        ) from exc


def apply_contradiction_penalty(confidence: float, penalty: float) -> float:
    """Apply a detector-local contradiction penalty to a confidence score.

    The penalty must be a finite number >= 0, so the result can never
    exceed the input (contradictions must not increase confidence, per
    policy §4). Results floor at 0.0. A zero penalty returns the input
    unchanged — the correct input when evidence is merely missing rather
    than contradictory (missing is not negative evidence, per policy §4).
    """
    score = check_confidence(confidence)
    if isinstance(penalty, bool) or not isinstance(penalty, (int, float)):
        raise TypeError(
            f"contradiction_penalty must be a finite number, got {penalty!r}"
        )
    amount = float(penalty)
    if not math.isfinite(amount) or amount < 0.0:
        raise ValueError(
            "contradiction_penalty must be finite and >= 0 "
            f"(penalties never increase confidence), got {penalty!r}"
        )
    return max(0.0, score - amount)
