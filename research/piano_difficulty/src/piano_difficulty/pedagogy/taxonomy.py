"""Student-visible musical demand labels for Gradus practice.

Controlled vocabulary that interprets raw feature descriptors as practice
demands. The labels are intentionally musically precise enough for learners to
grow into, but this is not a teacher-only taxonomy. Extensible via
register_factor(); versioned separately from the feature registry.

Maps to brief examples:
  rhythm/polyrhythm -> rhythm_stability
  displacement/leaps -> leaps_position_changes
  chords/span -> chord_spacing
  density/coordination -> hand_coordination
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

TAXONOMY_VERSION = "gradus.taxonomy.v1"


@dataclass(frozen=True, slots=True)
class TaxonomyFactor:
    factor_id: str
    label: str
    description: str
    limitation: str
    direction: str = "higher"

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


_TAXONOMY_FACTORS: tuple[TaxonomyFactor, ...] = (
    TaxonomyFactor(
        factor_id="rhythm_stability",
        label="Rhythm stability",
        description="Uneven, dense, or polyrhythmic timing that can disrupt steady pulse.",
        limitation="Score timing only; individual feel varies.",
    ),
    TaxonomyFactor(
        factor_id="hand_coordination",
        label="Hand coordination",
        description="Independent or misaligned motion between hands.",
        limitation="Different onset patterns need not be difficult for every learner.",
    ),
    TaxonomyFactor(
        factor_id="leaps_position_changes",
        label="Leaps / position changes",
        description="Large intervallic jumps or hand-position shifts.",
        limitation="Pitch-set proxy; not a physical travel estimate.",
    ),
    TaxonomyFactor(
        factor_id="chord_spacing",
        label="Chord spacing",
        description="Wide simultaneous spans and chord density within a hand.",
        limitation="Staff-based hand inference; excludes sustaining notes.",
    ),
    TaxonomyFactor(
        factor_id="reading_notation",
        label="Reading / notation",
        description="Accidentals, clef changes, ledger lines, or cross-staff reading.",
        limitation="Does not model learner reading familiarity.",
    ),
    TaxonomyFactor(
        factor_id="voicing_balance",
        label="Voicing / texture",
        description="Dense or layered texture where voicing and balance matter.",
        limitation="Texture proxy; musical importance is contextual.",
    ),
    TaxonomyFactor(
        factor_id="tempo_control",
        label="Tempo control",
        description="Fast or tempo-change passages requiring controlled tempo.",
        limitation="Does not incorporate performed tempo.",
    ),
    TaxonomyFactor(
        factor_id="endurance",
        label="Endurance",
        description="Sustained or repeated demands that build fatigue.",
        limitation="Duration-based proxy; physical effort varies.",
    ),
)

TAXONOMY: dict[str, TaxonomyFactor] = {f.factor_id: f for f in _TAXONOMY_FACTORS}

# Mapping from raw feature_ids (and dimension ids) to taxonomy factors.
# Used by factor guesser as the default weight table.
FEATURE_TO_FACTORS: dict[str, tuple[str, ...]] = {
    "rhythm.attack_density": ("rhythm_stability", "tempo_control"),
    "rhythm.note_density": ("rhythm_stability", "tempo_control"),
    "rhythm.tuplet_count": ("rhythm_stability",),
    "leaps.max_melodic_leap": ("leaps_position_changes",),
    "leaps.mean_melodic_leap": ("leaps_position_changes",),
    "pitch_geometry.max_simultaneity_span": ("chord_spacing",),
    "pitch_geometry.mean_simultaneity_span": ("chord_spacing",),
    "texture.notes_per_onset": ("voicing_balance", "chord_spacing"),
    "texture.simultaneity_density": ("voicing_balance",),
    "coordination.subdivision_mismatch_proxy": ("hand_coordination", "rhythm_stability"),
    "notation.accidental_density": ("reading_notation",),
    "notation.clef_change_count": ("reading_notation",),
    "notation.ledger_line_burden": ("reading_notation",),
    "expression.articulation_density": ("voicing_balance",),
}


def get_factor(factor_id: str) -> TaxonomyFactor:
    try:
        return TAXONOMY[factor_id]
    except KeyError as exc:
        raise ValueError(f"unknown taxonomy factor {factor_id!r}") from exc


def list_factors() -> tuple[TaxonomyFactor, ...]:
    return tuple(TAXONOMY.values())


def is_known_factor(factor_id: str) -> bool:
    return factor_id in TAXONOMY


def register_factor(factor: TaxonomyFactor) -> None:
    """Register a new factor. Mutates TAXONOMY (extensibility hook)."""
    if not isinstance(factor, TaxonomyFactor):
        raise TypeError("factor must be TaxonomyFactor")
    if factor.factor_id in TAXONOMY:
        raise ValueError(f"factor_id {factor.factor_id!r} already registered")
    TAXONOMY[factor.factor_id] = factor


def taxonomy_payload() -> dict[str, object]:
    return {
        "schema_version": TAXONOMY_VERSION,
        "factors": [f.to_payload() for f in sorted(TAXONOMY.values(), key=lambda x: x.factor_id)],
    }
