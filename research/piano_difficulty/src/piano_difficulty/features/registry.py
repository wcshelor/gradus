"""Reviewed factor definitions used by the public overview.

The extractor registry in features.__init__ owns all raw descriptors. This
registry selects a small, non-duplicating subset for descriptive ranking.
"""

from dataclasses import asdict, dataclass

REGISTRY_VERSION = "difficulty_factors.v1"


@dataclass(frozen=True, slots=True)
class FactorDefinition:
    feature_id: str
    label: str
    units: str
    scope: str
    description: str
    limitation: str
    direction: str = "higher"
    weight: float = 1.0

    def to_payload(self):
        return asdict(self)


FACTORS = {
    item.feature_id: item for item in (
        FactorDefinition("rhythm.attack_density", "Attack density", "attacks_per_quarter",
                         "selected_hand_or_score", "Distinct logical onset times per quarter note.",
                         "Does not incorporate performance tempo."),
        FactorDefinition("leaps.max_melodic_leap", "Largest pitch transition", "semitones",
                         "hand", "Largest closest-pitch distance between successive onset groups.",
                         "A pitch-set proxy, not an estimate of physical hand travel."),
        FactorDefinition("pitch_geometry.max_simultaneity_span", "Largest simultaneous span", "semitones",
                         "hand", "Largest pitch span within a hand onset group.",
                         "Staff-based hand inference; excludes already-sustaining notes."),
        FactorDefinition("coordination.subdivision_mismatch_proxy", "Hand timing mismatch", "ratio",
                         "coordination", "Unaligned onset proportion in measures with activity in both hands.",
                         "Different onset patterns need not be difficult for a given learner."),
        FactorDefinition("notation.accidental_density", "Accidental density", "ratio",
                         "selected_hand_or_score", "Explicit accidentals relative to written notes.",
                         "Does not model the learner's reading familiarity."),
    )
}
DEFAULT_FACTOR_IDS = tuple(FACTORS)


def resolve_factors(feature_ids=DEFAULT_FACTOR_IDS):
    unknown = set(feature_ids) - FACTORS.keys()
    if unknown:
        raise ValueError(f"Unreviewed overview factors: {', '.join(sorted(unknown))}")
    return tuple(FACTORS[feature_id] for feature_id in feature_ids)
