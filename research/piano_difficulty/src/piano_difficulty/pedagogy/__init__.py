"""Gradus pedagogical practice layer — UI-neutral backend/domain contracts.

Entry points:
  from piano_difficulty.pedagogy import build_gradus_payload
  from piano_difficulty.pedagogy.hotspots import generate_hotspots
  from piano_difficulty.pedagogy.factors import guess_factors_for_features
  from piano_difficulty.pedagogy.feedback import ingest_feedback
  from piano_difficulty.pedagogy.cards import create_card, apply_log
  from piano_difficulty.pedagogy.recommendations import rank_recommendations
  from piano_difficulty.pedagogy.drills import spec_for

New payloads are additive; existing extraction/analysis payloads remain
backward-compatible unless gradus output is explicitly requested.
"""

from piano_difficulty.pedagogy.models import (
    GRADUS_SCHEMA,
    GRADUS_SCHEMA_VERSION,
    DifficultyFactor,
    DrillSpec,
    DrillType,
    EvidenceRef,
    FeedbackEvent,
    FeedbackKind,
    GradusRecommendationContext,
    HotspotOrigin,
    HotspotStatus,
    LearnerProfileSnapshot,
    LogMode,
    PracticeCard,
    PracticeHotspot,
    PracticeLog,
    UncertaintyMeta,
)
from piano_difficulty.pedagogy.payload import build_gradus_payload, build_gradus_payload_from_dict
from piano_difficulty.pedagogy.taxonomy import TAXONOMY, TAXONOMY_VERSION

__all__ = [
    "GRADUS_SCHEMA",
    "GRADUS_SCHEMA_VERSION",
    "TAXONOMY",
    "TAXONOMY_VERSION",
    "DifficultyFactor",
    "DrillSpec",
    "DrillType",
    "EvidenceRef",
    "FeedbackEvent",
    "FeedbackKind",
    "GradusRecommendationContext",
    "HotspotOrigin",
    "HotspotStatus",
    "LearnerProfileSnapshot",
    "LogMode",
    "PracticeCard",
    "PracticeHotspot",
    "PracticeLog",
    "UncertaintyMeta",
    "build_gradus_payload",
    "build_gradus_payload_from_dict",
]
