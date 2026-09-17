"""Factor guesser v0 — map raw feature/dimension evidence to practice demands.

Brief examples:
  rhythm/polyrhythm -> rhythm_stability
  displacement/leaps -> leaps_position_changes
  chords/span -> chord_spacing
  density/coordination -> hand_coordination
"""

from __future__ import annotations

from typing import Any

from piano_difficulty.pedagogy.models import DifficultyFactor
from piano_difficulty.pedagogy.taxonomy import FEATURE_TO_FACTORS, TAXONOMY, TAXONOMY_VERSION


def _normalize_confidence(raw_value: Any, confidence: float | None) -> float | None:
    if confidence is not None:
        return max(0.0, min(1.0, float(confidence)))
    return None


def map_feature_to_factors(
    feature_id: str,
    *,
    confidence: float | None = None,
    evidence_ids: tuple[str, ...] = (),
) -> list[DifficultyFactor]:
    """Map one raw feature_id to zero or more DifficultyFactors."""
    factor_ids = FEATURE_TO_FACTORS.get(feature_id, ())
    factors: list[DifficultyFactor] = []
    for fid in factor_ids:
        factors.append(
            DifficultyFactor(
                factor_id=fid,
                confidence=_normalize_confidence(None, confidence),
                evidence_ids=evidence_ids,
                source_feature_ids=(feature_id,),
            )
        )
    return factors


def guess_factors_for_features(
    feature_ids: list[str],
    *,
    confidence_by_feature: dict[str, float] | None = None,
    evidence_ids_by_feature: dict[str, tuple[str, ...]] | None = None,
) -> list[DifficultyFactor]:
    """Aggregate guesses across multiple features, deduplicating by factor_id.

    Keeps highest confidence per factor; merges evidence/source ids.
    """
    confidence_by_feature = confidence_by_feature or {}
    evidence_ids_by_feature = evidence_ids_by_feature or {}
    acc: dict[str, DifficultyFactor] = {}
    for fid in feature_ids:
        conf = confidence_by_feature.get(fid)
        ev_ids = evidence_ids_by_feature.get(fid, ())
        for factor in map_feature_to_factors(fid, confidence=conf, evidence_ids=ev_ids):
            existing = acc.get(factor.factor_id)
            if existing is None:
                acc[factor.factor_id] = factor
            else:
                # merge: keep max confidence, union evidence/source
                merged_conf: float | None = None
                if existing.confidence is not None and factor.confidence is not None:
                    merged_conf = max(existing.confidence, factor.confidence)
                elif existing.confidence is not None:
                    merged_conf = existing.confidence
                elif factor.confidence is not None:
                    merged_conf = factor.confidence
                merged_ev = tuple(dict.fromkeys((*existing.evidence_ids, *factor.evidence_ids)))
                merged_src = tuple(dict.fromkeys((*existing.source_feature_ids, *factor.source_feature_ids)))
                acc[factor.factor_id] = DifficultyFactor(
                    factor_id=factor.factor_id,
                    confidence=merged_conf,
                    evidence_ids=merged_ev,
                    source_feature_ids=merged_src,
                )
    # sort by confidence desc then factor_id for determinism
    return sorted(
        acc.values(),
        key=lambda f: (-(f.confidence or 0), f.factor_id),
    )


def guess_factors_for_passage(
    measure_start: int,
    measure_end: int,
    *,
    feature_records: list[Any] | None = None,
    notable_dimensions: list[str] | None = None,
    region_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Hard-section form helper: given a user-marked passage, return guesses.

    Returns dict with:
      passage span, top 3 guessed factors, full selectable taxonomy.
    Presence of feature_records or notable_dimensions influences guess;
    without them returns generic fallback.
    """
    feature_ids: list[str] = []
    if feature_records:
        for rec in feature_records:
            # FeatureRecord has feature_id attr or dict
            fid = getattr(rec, "feature_id", None) or (rec.get("feature_id") if isinstance(rec, dict) else None)
            if isinstance(fid, str):
                feature_ids.append(fid)
    if notable_dimensions:
        feature_ids.extend(notable_dimensions)
    # also consider region_evidence feature hints if provided
    if region_evidence and not feature_ids:
        # without explicit features, use high-value feature inference placeholder
        pass

    guessed = guess_factors_for_features(feature_ids)
    # If no evidence, provide a neutral fallback: rhythm + hand coordination low confidence
    if not guessed:
        guessed = [
            DifficultyFactor(factor_id="rhythm_stability", confidence=0.3, evidence_ids=(), source_feature_ids=()),
            DifficultyFactor(factor_id="hand_coordination", confidence=0.3, evidence_ids=(), source_feature_ids=()),
            DifficultyFactor(factor_id="reading_notation", confidence=0.2, evidence_ids=(), source_feature_ids=()),
        ]
    top3 = guessed[:3]
    return {
        "measure_start": measure_start,
        "measure_end": measure_end,
        "guessed_factors": [f.to_payload() for f in top3],
        "selectable_taxonomy": [
            TAXONOMY[fid].to_payload() for fid in sorted(TAXONOMY)
        ],
        "taxonomy_version": TAXONOMY_VERSION,
    }


def factors_for_contributions(
    contributions: list[dict[str, Any]],
    *,
    top_n: int = 3,
) -> list[DifficultyFactor]:
    """Build factors from overview region contributions (overview factors)."""
    # contributions are dicts with feature_id, rank, etc.
    scored: list[tuple[str, float]] = []
    for c in contributions:
        fid = c.get("feature_id")
        if not isinstance(fid, str):
            continue
        # use contribution_share or rank to derive confidence proxy
        share = c.get("contribution_share")
        if isinstance(share, (int, float)) and 0 <= float(share) <= 1:
            conf = float(share)
        else:
            rank = c.get("rank")
            if isinstance(rank, int) and rank >= 1:
                conf = max(0.1, 1.0 - (rank - 1) * 0.2)
            else:
                conf = 0.5
        scored.append((fid, conf))
    # sort by confidence desc
    scored.sort(key=lambda x: -x[1])
    feature_ids = [fid for fid, _ in scored[:top_n]]
    conf_map = {fid: conf for fid, conf in scored}
    return guess_factors_for_features(feature_ids, confidence_by_feature=conf_map)
