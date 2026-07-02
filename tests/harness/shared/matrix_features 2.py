from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


OG_PHP_FEATURES: tuple[str, ...] = (
    "speedDifficulty",
    "displacementsDifficulty",
    "chordsDifficulty",
    "harmonyDifficulty",
    "rhythmDifficulty",
    "lengthDifficulty",
    "tonalityDifficulty",
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
    "runtime_all": ("feature__",),
    "rhythm_only": ("feature__rhythm.",),
    "leaps_only": ("feature__leaps.",),
    "texture_only": ("feature__texture.",),
    "coordination_only": ("feature__coordination.",),
    "notation_only": ("feature__notation.",),
}


@dataclass(frozen=True, slots=True)
class FeatureSetSpec:
    exact_columns: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    description: str = ""


FEATURE_SET_SPECS: dict[str, FeatureSetSpec] = {
    "sebastien_clustering": FeatureSetSpec(
        exact_columns=SEBASTIEN_CLUSTERING_FEATURES,
        description="Sebastien clustering-style 9-variable bundle without tonality.",
    ),
    "og_php": FeatureSetSpec(
        exact_columns=OG_PHP_FEATURES,
        description="OG PHP difficulty features.",
    ),
    "runtime_all": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["runtime_all"],
        description="All runtime feature__ columns.",
    ),
    "rhythm_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["rhythm_only"],
        description="Runtime rhythm family only.",
    ),
    "leaps_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["leaps_only"],
        description="Runtime leaps family only.",
    ),
    "texture_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["texture_only"],
        description="Runtime texture family only.",
    ),
    "coordination_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["coordination_only"],
        description="Runtime coordination family only.",
    ),
    "notation_only": FeatureSetSpec(
        prefixes=RUNTIME_FAMILY_PREFIXES["notation_only"],
        description="Runtime notation family only.",
    ),
    "og_plus_runtime": FeatureSetSpec(
        exact_columns=OG_PHP_FEATURES,
        prefixes=RUNTIME_FAMILY_PREFIXES["runtime_all"],
        description="OG PHP features plus any runtime feature__ columns.",
    ),
}

DEFAULT_METADATA_COLUMNS: tuple[str, ...] = (
    "source_row_index",
    "catalog_index",
    "catalog_key",
    "filename",
    "repo_relative_path",
    "dataset_relative_path",
    "file_suffix",
    "oktav_code",
    "arrangement_id",
    "difficulty_raw",
    "difficulty_numeric",
    "difficulty_status",
    "source_path",
    "compressed_source",
    "source_rootfile_path",
    "source_bytes",
    "musicxml_part_count",
    "musicxml_measure_count",
    "musicxml_note_count",
    "musicxml_rest_count",
    "musicxml_duration_total",
    "musicxml_note_duration_total",
    "staged_piece_id",
    "status",
    "error_type",
    "error_message",
    "profile_id",
    "profile_version",
    "overall_score",
    "overall_label",
    "payload_json_path",
    "feature_count",
    "overallDifficulty",
)


@dataclass(slots=True)
class FeatureSelectionReport:
    feature_set: str
    selected_columns: tuple[str, ...]
    missing_exact_columns: tuple[str, ...]
    missing_prefixes: tuple[str, ...]
    blocked_columns: tuple[str, ...]
    blocked_matches: tuple[str, ...]
    available_columns: tuple[str, ...]
    candidate_column_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_set": self.feature_set,
            "selected_columns": list(self.selected_columns),
            "selected_count": len(self.selected_columns),
            "missing_exact_columns": list(self.missing_exact_columns),
            "missing_prefixes": list(self.missing_prefixes),
            "blocked_columns": list(self.blocked_columns),
            "blocked_matches": list(self.blocked_matches),
            "available_columns": list(self.available_columns),
            "available_count": len(self.available_columns),
            "candidate_column_count": self.candidate_column_count,
        }


def select_feature_columns(
    columns: Sequence[str],
    *,
    feature_set: str,
    blocked_columns: Sequence[str] = (),
) -> FeatureSelectionReport:
    normalized_columns = [str(column) for column in columns]
    available = tuple(normalized_columns)
    blocked = tuple(dict.fromkeys(str(column) for column in blocked_columns if str(column)))
    blocked_set = set(blocked)

    key = feature_set.strip().lower()
    if key not in FEATURE_SET_SPECS:
        raise ValueError(
            f"Unsupported feature set '{feature_set}'. Supported sets: {sorted(FEATURE_SET_SPECS)}"
        )
    spec = FEATURE_SET_SPECS[key]

    selected: list[str] = []
    raw_exact_matches = [column for column in spec.exact_columns if column in available]
    missing_exact = [column for column in spec.exact_columns if column not in available]
    for column in spec.exact_columns:
        if column in available and column not in blocked_set and column not in selected:
            selected.append(column)

    raw_prefix_matches: list[str] = []
    missing_prefixes: list[str] = []
    for prefix in spec.prefixes:
        prefix_matches = [column for column in available if column.startswith(prefix)]
        if not prefix_matches:
            missing_prefixes.append(prefix)
            continue
        raw_prefix_matches.extend(prefix_matches)
        for column in prefix_matches:
            if column not in blocked_set and column not in selected:
                selected.append(column)

    blocked_matches = tuple(
        column for column in [*raw_exact_matches, *raw_prefix_matches] if column in blocked_set
    )

    return FeatureSelectionReport(
        feature_set=key,
        selected_columns=tuple(selected),
        missing_exact_columns=tuple(missing_exact),
        missing_prefixes=tuple(missing_prefixes),
        blocked_columns=blocked,
        blocked_matches=blocked_matches,
        available_columns=available,
        candidate_column_count=len([column for column in available if column not in blocked_set]),
    )
