from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


OG_PHP_FEATURES: tuple[str, ...] = (
    "length",
    "rhythm",
    "speed",
    "tonality",
    "harmony",
    "chords",
    "displacements",
)

SEBASTIEN_CLUSTERING_FEATURES: tuple[str, ...] = (
    "length",
    "rhythm",
    "speed",
    "harmonyRH",
    "harmonyLH",
    "chordsRH",
    "chordsLH",
    "displacementsRH",
    "displacementsLH",
)

RUNTIME_FAMILY_PREFIXES: dict[str, tuple[str, ...]] = {
    "metadata": ("metadata_",),
    "rhythm": ("rhythm_",),
    "pitch_geometry": ("pitch_geometry_",),
    "leaps": ("leap_", "leaps_"),
    "texture": ("texture_",),
    "coordination": ("coordination_",),
    "notation": ("notation_",),
    "expression": ("expression_",),
    "statistics": ("statistics_",),
}

# Rhythm duration-ratio columns are high-cardinality sparse features that dominate
# variance and calibration.  Core sets exclude them by using a curated non-sparse
# rhythm allowlist rather than the broad ``rhythm_`` prefix.
_RHYTHM_CORE_PREFIXES: tuple[str, ...] = (
    "rhythm_asymmetric_tuplet",
    "rhythm_attack_density",
    "rhythm_note_density",
    "rhythm_polyrhythm",
    "rhythm_shortest",
    "rhythm_significant",
    "rhythm_tuplet",
)

# Prefix that identifies sparse high-cardinality duration-ratio columns.
RUNTIME_SPARSE_DURATION_RATIO_PREFIX: str = "rhythm_duration_value_ratio_"


@dataclass(frozen=True, slots=True)
class FeatureSetSpec:
    exact_columns: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    description: str = ""


FEATURE_SET_SPECS: dict[str, FeatureSetSpec] = {
    "og_php": FeatureSetSpec(
        exact_columns=OG_PHP_FEATURES,
        description="Original PHP / Sebastien-style aggregate difficulty features.",
    ),
    "sebastien_clustering": FeatureSetSpec(
        exact_columns=SEBASTIEN_CLUSTERING_FEATURES,
        description="Nine-feature Sebastien clustering bundle without tonality.",
    ),
    "runtime_all": FeatureSetSpec(
        prefixes=tuple(prefix for prefixes in RUNTIME_FAMILY_PREFIXES.values() for prefix in prefixes),
        description="All repo-native runtime feature families.",
    ),
    "runtime_no_expression": FeatureSetSpec(
        prefixes=tuple(
            prefix
            for family, prefixes in RUNTIME_FAMILY_PREFIXES.items()
            if family != "expression"
            for prefix in prefixes
        ),
        description="All repo-native runtime feature families except expression.",
    ),
    "rhythm_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["rhythm"],
        description="Repo-native rhythm family only.",
    ),
    "leaps_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["leaps"],
        description="Repo-native leap family only.",
    ),
    "texture_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["texture"],
        description="Repo-native texture family only.",
    ),
    "coordination_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["coordination"],
        description="Repo-native coordination family only.",
    ),
    "notation_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["notation"],
        description="Repo-native notation family only.",
    ),
    "expression_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["expression"],
        description="Repo-native articulation and written-dynamics family only.",
    ),
    "og_plus_runtime": FeatureSetSpec(
        exact_columns=OG_PHP_FEATURES,
        prefixes=tuple(prefix for prefixes in RUNTIME_FAMILY_PREFIXES.values() for prefix in prefixes),
        description="Original PHP aggregates plus repo-native runtime families.",
    ),
    "yan2023_observed": FeatureSetSpec(
        prefixes=(
            "pitch_mean_",
            "deviation_of_pitch_",
            "deviation_of_pitch_from_C4_",
            "pitch_range_",
            "pitch_entropy_",
            "hand_displacement_rate_",
            "hand_stretch_",
            "black_key_rate_",
            "mean_of_note_duration_",
            "deviation_of_note_duration_",
            "playing_speed_",
            "polyphony_rate_",
            "distinct_stroke_rate_",
            "irregular_rhythm_",
            "pitch_variability_",
            "note_duration_variability_",
            "note_density_",
            "triad_",
            "seventh_chord_",
            "ninth_chord_",
            "staccato_rate_",
            "dotted_note_rate_",
        ),
        exact_columns=(
            "length",
            "tempo",
            "key_signature",
            "playing_speed_variation",
        ),
        description="Observed Yan 2023 first-pass features with the currently empty slots excluded.",
    ),
    "yan2023_observed_no_blocked": FeatureSetSpec(
        prefixes=(
            "pitch_mean_",
            "deviation_of_pitch_",
            "deviation_of_pitch_from_C4_",
            "pitch_range_",
            "pitch_entropy_",
            "hand_displacement_rate_",
            "hand_stretch_",
            "black_key_rate_",
            "mean_of_note_duration_",
            "deviation_of_note_duration_",
            "playing_speed_",
            "polyphony_rate_",
            "distinct_stroke_rate_",
            "irregular_rhythm_",
            "pitch_variability_",
            "note_duration_variability_",
            "note_density_",
            "triad_",
            "seventh_chord_",
            "ninth_chord_",
            "staccato_rate_",
            "dotted_note_rate_",
        ),
        exact_columns=(
            "length",
            "tempo",
            "key_signature",
            "playing_speed_variation",
        ),
        description="Alias of yan2023_observed explicitly documented as the predictive baseline (implemented + proxyable, no blocked slots).",
    ),
    # Curated runtime sets for controlled experiments — config-level selection only.
    "runtime_core_no_expression": FeatureSetSpec(
        prefixes=(
            "metadata_",
            *_RHYTHM_CORE_PREFIXES,
            "pitch_geometry_",
            "leap_",
            "leaps_",
            "texture_",
            "coordination_",
            "notation_",
        ),
        description="Runtime families minus expression and sparse duration-ratio columns (core motor/structural set).",
    ),
    "runtime_core_no_sparse": FeatureSetSpec(
        prefixes=(
            "metadata_",
            *_RHYTHM_CORE_PREFIXES,
            "pitch_geometry_",
            "leap_",
            "leaps_",
            "texture_",
            "coordination_",
            "notation_",
            "expression_",
        ),
        description="Runtime all minus known sparse/high-cardinality rhythm_duration_value_ratio_* columns.",
    ),
    "runtime_motor_texture": FeatureSetSpec(
        prefixes=(
            "leap_",
            "leaps_",
            "pitch_geometry_",
            "texture_",
            "coordination_",
        ),
        description="Leaps + pitch geometry + texture + coordination (motor/texture coordination bundle).",
    ),
    "runtime_statistical": FeatureSetSpec(
        prefixes=("statistics_",),
        exact_columns=(
            "metadata_length_quarters",
            "metadata_primary_tempo",
            "metadata_key_signature",
        ),
        description="Promoted compact Yan-style score-native statistical descriptors plus compact metadata predictors (pitch/duration aggregates, entropy, C4 deviation, variability, black-key/polyphony rates, typed chord counts, length/tempo/key).",
    ),
    "runtime_yan_overlap": FeatureSetSpec(
        prefixes=(
            "metadata_",
            "statistics_",
            "rhythm_note_density",
            "rhythm_attack_density",
            "rhythm_tuplet",
            "rhythm_asymmetric",
            "rhythm_polyrhythm",
            "pitch_geometry_",
            "leap_",
            "leaps_",
            "texture_",
            "coordination_",
            "expression_staccato_",
        ),
        description="Only runtime columns that correspond cleanly to Yan concepts where available (pitch range, note density, playing speed, hand stretch/displacement, polyphony, chord types, staccato), now runtime-native via statistics_* and compact metadata predictors.",
    ),
}

DEFAULT_METADATA_COLUMNS: tuple[str, ...] = (
    "source_row_index",
    "piece_id",
    "piece_uid",
    "title",
    "composer",
    "filename",
    "dataset_relative_path",
    "repo_relative_path",
    "status",
    "difficulty_numeric",
    "overallDifficulty",
    "henle",
)


@dataclass(frozen=True, slots=True)
class FeatureSelectionReport:
    feature_set: str
    selected_columns: tuple[str, ...]
    missing_exact_columns: tuple[str, ...]
    missing_prefixes: tuple[str, ...]
    excluded_columns: tuple[str, ...]
    candidate_column_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_set": self.feature_set,
            "selected_columns": list(self.selected_columns),
            "missing_exact_columns": list(self.missing_exact_columns),
            "missing_prefixes": list(self.missing_prefixes),
            "excluded_columns": list(self.excluded_columns),
            "candidate_column_count": self.candidate_column_count,
        }


def select_feature_columns(
    available_columns: Sequence[str],
    feature_set: str,
    excluded_columns: Sequence[str] | None = None,
) -> FeatureSelectionReport:
    normalized_feature_set = feature_set.strip().lower()
    if normalized_feature_set not in FEATURE_SET_SPECS:
        available = ", ".join(sorted(FEATURE_SET_SPECS))
        raise ValueError(
            f"Unknown feature_set {feature_set!r}. Available feature sets: {available}."
        )

    spec = FEATURE_SET_SPECS[normalized_feature_set]
    seen = dict.fromkeys(str(column) for column in available_columns)
    available = tuple(seen.keys())
    excluded = set(str(column) for column in (excluded_columns or ()))

    selected: list[str] = []
    missing_exact_columns: list[str] = []
    for column in spec.exact_columns:
        if column in available and column not in excluded:
            selected.append(column)
        elif column not in available:
            missing_exact_columns.append(column)

    missing_prefixes: list[str] = []
    for prefix in spec.prefixes:
        matched = [column for column in available if column.startswith(prefix) and column not in excluded]
        if matched:
            selected.extend(matched)
        else:
            missing_prefixes.append(prefix)

    deduped_selected = tuple(dict.fromkeys(selected))
    return FeatureSelectionReport(
        feature_set=normalized_feature_set,
        selected_columns=deduped_selected,
        missing_exact_columns=tuple(missing_exact_columns),
        missing_prefixes=tuple(missing_prefixes),
        excluded_columns=tuple(sorted(excluded)),
        candidate_column_count=len(deduped_selected),
    )
