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
    "rhythm": ("rhythm_",),
    "leaps": ("leap_",),
    "texture": ("texture_",),
    "coordination": ("coordination_",),
    "notation": ("notation_",),
}


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
    "og_plus_runtime": FeatureSetSpec(
        exact_columns=OG_PHP_FEATURES,
        prefixes=tuple(prefix for prefixes in RUNTIME_FAMILY_PREFIXES.values() for prefix in prefixes),
        description="Original PHP aggregates plus repo-native runtime families.",
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

