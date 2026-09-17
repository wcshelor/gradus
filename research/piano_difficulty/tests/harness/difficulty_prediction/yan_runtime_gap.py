"""Diagnostic: compare Yan observed columns vs runtime analogues.

Generates tests/artifacts/difficulty_prediction/yan_runtime_feature_gap.csv
that enumerates old yan2023_observed columns, available runtime analogues,
missing runtime analogues, and runtime-only extra columns.
"""

from __future__ import annotations

import csv
import pathlib

from tests.harness.shared.matrix_features import FEATURE_SET_SPECS, RUNTIME_FAMILY_PREFIXES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_MATRICES = [
    REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "python_analysis" / "full_run" / "oktav_labeled_feature_matrix.csv",
    REPO_ROOT / "tests" / "artifacts" / "cipi_dataset" / "python_analysis" / "full_run" / "cipi_labeled_feature_matrix.csv",
]
YAN_MATRIX_DIR = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "comparisons" / "20260722T183351Z__yan2023-cipi-vs-oktav" / "matrices"
OUTPUT_CSV = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction" / "yan_runtime_feature_gap.csv"

# High-priority Yan features that should be promoted to runtime (per brief).
_HIGH_PRIORITY = {
    "pitch_mean",
    "deviation_of_pitch",  # std
    "mean_of_note_duration",
    "deviation_of_note_duration",
    "pitch_entropy",
    "deviation_of_pitch_from_C4",
    "pitch_variability",
    "note_duration_variability",
    "black_key_rate",
    "polyphony_rate",
    "triad",
    "seventh_chord",
    "ninth_chord",
    "length",
    "tempo",
    "key_signature",
}

# Mapping from Yan base feature -> (runtime analogue prefixes/columns, status, notes, priority)
# status: available / partial / missing / blocked
_YAN_TO_RUNTIME = {
    "pitch_mean": (["metadata_pitch_range (proxy only)"], "missing", "Runtime has range/span but no mean pitch", "high"),
    "deviation_of_pitch": (["metadata_pitch_range"], "missing", "Runtime has range, not std", "high"),
    "pitch_range": (["metadata_pitch_range", "pitch_geometry_register_range_*"], "partial", "Runtime register_range + pitch_range approximates span", "high"),
    "pitch_entropy": ([], "missing", "No entropy column in runtime", "high"),
    "deviation_of_pitch_from_C4": ([], "missing", "No C4-distance in runtime", "high"),
    "black_key_rate": (["notation_accidental_* (proxy)"], "missing", "No black-key rate; accidental counts are proxy", "high"),
    "mean_of_note_duration": ([], "missing", "No duration mean in runtime", "high"),
    "deviation_of_note_duration": ([], "missing", "No duration std in runtime", "high"),
    "playing_speed": (["rhythm_attack_density"], "partial", "Rhythm attack density is attacks/quarter proxy", "medium"),
    "polyphony_rate": (["texture_chord_ratio_*", "texture_notes_per_onset", "texture_simultaneity_density"], "partial", "Texture chord ratios approximate polyphony", "high"),
    "distinct_stroke_rate": ([], "missing", "No distinct-stroke concept in runtime", "medium"),
    "irregular_rhythm": (["rhythm_tuplet_count", "rhythm_polyrhythm_measure_ratio", "rhythm_asymmetric_tuplet_measure_ratio"], "partial", "Rhythm tuplet/polyrhythm approximates irregular rhythm", "medium"),
    "pitch_variability": ([], "missing", "No pitch variability in runtime", "high"),
    "note_duration_variability": ([], "missing", "No duration variability in runtime", "high"),
    "note_density": (["rhythm_note_density"], "available", "Direct analogue: rhythm_note_density", "high"),
    "triad": (["texture_chord_count_*", "texture_chord_ratio_*"], "partial", "Texture chord counts but not triad-typed", "high"),
    "seventh_chord": (["texture_chord_count_*"], "partial", "No seventh-specific typing", "high"),
    "ninth_chord": (["texture_chord_count_*"], "partial", "No ninth-specific typing", "high"),
    "chord_number": (["texture_chord_count_*"], "partial", "Texture chord counts available", "medium"),
    "staccato_rate": (["expression_staccato_note_ratio*"], "available", "Direct analogue via expression_staccato_note_ratio", "medium"),
    "dotted_note_rate": ([], "missing", "No dotted-note rate in runtime", "medium"),
    "length": (["metadata_measure_count", "metadata_note_count", "metadata_page_count"], "partial", "Metadata counts approximate length (quarters)", "high"),
    "tempo": (["metadata_tempo_change_count"], "partial", "Only tempo change count, not BPM", "high"),
    "key_signature": (["metadata_key_change_count"], "partial", "Only key change count, not fifths", "high"),
    "playing_speed_variation": ([], "missing", "No tempo variation ratio in runtime", "medium"),
    "hand_displacement_rate": (["leaps_max_timed_difficult_displacement_*", "leaps_timed_difficult_displacement_ratio_*", "leaps_mean_melodic_leap_*"], "partial", "Leaps family proxies hand displacement", "medium"),
    "hand_stretch": (["pitch_geometry_max_simultaneity_span_*", "pitch_geometry_mean_simultaneity_span"], "partial", "Pitch geometry simultaneity span proxies stretch", "defer"),
    "pressing_velocity_entropy": ([], "blocked", "Needs performance/MIDI", "defer"),
    "pressing_velocity_variability": ([], "blocked", "Needs performance/MIDI", "defer"),
    "melodic_complexity": ([], "blocked", "Needs expectancy model", "defer"),
    "melodic_originality": ([], "blocked", "Needs expectancy model", "defer"),
    "degree_of_melodiousness": ([], "blocked", "Needs expectancy model", "defer"),
}


def _load_header(path: pathlib.Path) -> list[str]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def _resolve_runtime_columns() -> list[str]:
    for p in DEFAULT_RUNTIME_MATRICES:
        if p.is_file():
            cols = _load_header(p)
            # Filter to runtime-relevant columns (exclude metadata id columns, but keep feature columns)
            from tests.harness.shared.matrix_features import DEFAULT_METADATA_COLUMNS
            excluded = set(DEFAULT_METADATA_COLUMNS)
            # Also exclude dataset-specific identifiers
            extra_exclude = {
                "dataset_name",
                "arrangement_key",
                "arrangement_raw",
                "oktav_id",
                "cipi_id",
                "movement",
                "uri",
                "book",
                "work_name",
                "file_exists",
                "path_resolution",
                "resolved_dataset_relative_path",
                "upstream_path",
                "legacy_dataset_relative_path",
                "legacy_piece_uid",
                "normalized_filename",
                "source_path",
                "piece_json_path",
                "error_type",
                "message",
            }
            runtime_cols = [c for c in cols if c not in excluded and c not in extra_exclude and not c.startswith("dataset_relative_path") and not c.startswith("repo_relative_path")]
            # Keep only those that look like runtime features (have _)
            runtime_cols = [c for c in runtime_cols if "_" in c]
            return runtime_cols
    return []


def _resolve_yan_columns() -> list[str]:
    yan_spec = FEATURE_SET_SPECS["yan2023_observed"]
    # Expand prefixes to example columns: e.g., pitch_mean_es
    examples: list[str] = []
    for prefix in yan_spec.prefixes:
        examples.append(f"{prefix}es")
    examples.extend(list(yan_spec.exact_columns))
    return examples


def build_gap_rows() -> list[dict[str, str]]:
    yan_spec = FEATURE_SET_SPECS["yan2023_observed"]
    # Derive base features from prefixes: strip trailing _
    yan_bases: list[str] = []
    for prefix in yan_spec.prefixes:
        base = prefix.rstrip("_")
        # Handle prefixes that end with _ but include scope: e.g., pitch_mean_ -> pitch_mean
        # For hand_displacement_rate_ -> hand_displacement_rate etc.
        # Keep as is without scope
        yan_bases.append(base)
    yan_bases.extend(list(yan_spec.exact_columns))

    runtime_cols = _resolve_runtime_columns()
    runtime_prefixes_set = set(RUNTIME_FAMILY_PREFIXES.keys())
    # Build runtime-only extras: columns whose family is not in Yan mapping
    # Runtime-only families we consider extra are: rhythm_duration_value_ratio_*, notation_*, expression_* (except staccato), coordination extra etc.
    # For simplicity, runtime-only = any runtime column whose stem not in YAN_TO_RUNTIME analogues.

    rows: list[dict[str, str]] = []
    for base in sorted(set(yan_bases)):
        analogues, status, notes, priority = _YAN_TO_RUNTIME.get(base, ([], "missing", "No mapping defined", "medium"))
        # Find example yan column
        example = next((ex for ex in _resolve_yan_columns() if ex.startswith(base)), base)
        rows.append(
            {
                "category": "yan_observed",
                "yan_base_feature": base,
                "yan_example_column": example,
                "runtime_analogue_columns": "; ".join(analogues) if analogues else "",
                "gap_status": status,
                "priority": priority,
                "is_blocked": "yes" if status == "blocked" else "no",
                "notes": notes,
            }
        )

    # Runtime-only extra columns (those not covered as analogues)
    # List runtime families not cleanly mapped: rhythm_duration_value_ratio_*, notation_accidental_*, expression_* (except staccato), etc.
    # We'll produce summary rows for runtime-only families.
    runtime_only_families = [
        ("rhythm_duration_value_ratio_*", "high-cardinality sparse duration ratios (100+ columns on CIPI)", "runtime_only_extra", "sparse"),
        ("notation_accidental_* + ledger_line_burden + clef_change", "notation burden", "runtime_only_extra", "extra"),
        ("expression_accent/tenuto/wedge/dynamic* (except staccato)", "expression family beyond staccato", "runtime_only_extra", "extra"),
        ("coordination_subdivision_mismatch_proxy", "coordination extra", "runtime_only_extra", "extra"),
        ("pitch_geometry_* beyond range", "pitch geometry span details", "runtime_only_extra", "extra"),
    ]
    for prefix, desc, cat, priority in runtime_only_families:
        rows.append(
            {
                "category": cat,
                "yan_base_feature": prefix,
                "yan_example_column": "",
                "runtime_analogue_columns": prefix,
                "gap_status": "runtime_only",
                "priority": priority,
                "is_blocked": "no",
                "notes": desc,
            }
        )

    # Add summary row for available runtime analogues that exist
    # Count available/partial/missing
    return rows


def write_gap_csv(output_path: pathlib.Path | None = None) -> pathlib.Path:
    out = output_path or OUTPUT_CSV
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_gap_rows()
    fieldnames = ["category", "yan_base_feature", "yan_example_column", "runtime_analogue_columns", "gap_status", "priority", "is_blocked", "notes"]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out


if __name__ == "__main__":
    out_path = write_gap_csv()
    print(f"Wrote {out_path} with {len(build_gap_rows())} rows")
