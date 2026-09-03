"""Serialization helpers for Difficulty Dynamics artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .core import export_profile_rows
from .models import DifficultyProfile


def export_profile_json(profile: DifficultyProfile, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.write_text(json.dumps(profile.to_payload(), indent=2, sort_keys=True))
    return output_path


def export_profile_csv(profile: DifficultyProfile, path: str | Path) -> Path:
    output_path = Path(path)
    rows = export_profile_rows(profile)
    fieldnames = [
        "score_id",
        "window_index",
        "start_measure",
        "end_measure",
        "position",
        "hand",
        "feature_id",
        "feature_name",
        "provenance",
        "temporal_adaptation",
        "raw_value",
        "normalized_value",
        "smoothed_value",
        "units",
        "source_scope",
        "source_scope_ref",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def export_peaks_json(profile: DifficultyProfile, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.write_text(json.dumps([passage.to_payload() for passage in profile.passages], indent=2, sort_keys=True))
    return output_path


def export_hotspots_csv(profile: DifficultyProfile, path: str | Path) -> Path:
    output_path = Path(path)
    fieldnames = [
        "score_id",
        "score_title",
        "hotspot_rank",
        "hotspot_id",
        "window_index",
        "measure_start",
        "measure_end",
        "measure_label",
        "score_position",
        "support_count",
        "best_feature_id",
        "best_value",
        "contributor_rank",
        "contributor_feature_id",
        "contributor_feature_name",
        "contribution_share",
        "weighted_value",
        "normalized_value",
        "smoothed_value",
        "is_peak_support",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_hotspot_rows(profile))
    return output_path


def export_summary_markdown(profile: DifficultyProfile, path: str | Path, *, top_k: int = 5) -> Path:
    output_path = Path(path)
    output_path.write_text(render_summary_markdown(profile, top_k=top_k), encoding="utf-8")
    return output_path


def render_summary_markdown(profile: DifficultyProfile, *, top_k: int = 5) -> str:
    lines = [
        "# Difficulty Dynamics Summary",
        "",
        f"- Score: {_markdown_value(profile.score_title) or _markdown_value(profile.score_id) or 'unknown'}",
        f"- Composer: {_markdown_value(profile.score_composer) or 'unknown'}",
        f"- Source: {_markdown_value(profile.source_path) or 'unknown'}",
        f"- Regions: {len(profile.regions)}",
        f"- Feature tracks: {len(profile.series)}",
        f"- Hard spots: {len(profile.hard_spots)}",
        "",
        "## Top Hard Spots",
        "",
    ]

    if not profile.hard_spots:
        lines.append("No hard spots detected.")
        lines.append("")
        return "\n".join(lines)

    for index, hotspot in enumerate(profile.hard_spots[: max(top_k, 0)], start=1):
        contributors = ", ".join(_format_contributor_summary(contribution) for contribution in hotspot.feature_contributions[:3])
        lines.extend(
            [
                f"### {index}. {_region_label(hotspot.region)}",
                "",
                f"- Support count: {hotspot.support_count}",
                f"- Peak feature: {hotspot.best_feature_id} ({hotspot.best_value:.3f})",
                f"- Contributors: {contributors or 'none'}",
                "",
            ]
        )
    return "\n".join(lines)


def _hotspot_rows(profile: DifficultyProfile) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for hotspot_rank, hotspot in enumerate(profile.hard_spots, start=1):
        base = {
            "score_id": profile.score_id,
            "score_title": profile.score_title,
            "hotspot_rank": hotspot_rank,
            "hotspot_id": hotspot.hotspot_id,
            "window_index": hotspot.region.window_index,
            "measure_start": hotspot.region.measure_start,
            "measure_end": hotspot.region.measure_end,
            "measure_label": hotspot.region.label,
            "score_position": hotspot.score_position,
            "support_count": hotspot.support_count,
            "best_feature_id": hotspot.best_feature_id,
            "best_value": hotspot.best_value,
        }
        if hotspot.feature_contributions:
            for contribution in hotspot.feature_contributions:
                rows.append(
                    {
                        **base,
                        "contributor_rank": contribution.rank,
                        "contributor_feature_id": contribution.feature_id,
                        "contributor_feature_name": contribution.feature_name,
                        "contribution_share": contribution.contribution_share,
                        "weighted_value": contribution.weighted_value,
                        "normalized_value": contribution.normalized_value,
                        "smoothed_value": contribution.smoothed_value,
                        "is_peak_support": contribution.is_peak_support,
                    }
                )
            continue
        rows.append(
            {
                **base,
                "contributor_rank": None,
                "contributor_feature_id": None,
                "contributor_feature_name": None,
                "contribution_share": None,
                "weighted_value": None,
                "normalized_value": None,
                "smoothed_value": None,
                "is_peak_support": None,
            }
        )
    return rows


def _format_contributor_summary(contribution) -> str:
    share = "" if contribution.contribution_share is None else f" ({contribution.contribution_share:.0%})"
    return f"{contribution.feature_id}{share}"


def _region_label(region) -> str:
    if region.label:
        return region.label
    return f"measures {region.measure_start}-{region.measure_end}"


def _markdown_value(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
