"""Markdown report rendering from saved JSON payloads."""

from __future__ import annotations


def render_markdown_report(payload: dict[str, object], *, profile_id: str | None = None) -> str:
    """Render a Markdown report from a JSON payload."""

    profiles = payload.get("analysis_profiles", [])
    selected_profile: dict[str, object] | None = None
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if profile_id is None or profile.get("profile_id") == profile_id:
            selected_profile = profile
            break
    if selected_profile is None:
        raise ValueError("No analysis profile is available for Markdown rendering.")
    if selected_profile.get("profile_id") == "difficulty_overview":
        from piano_difficulty.output.overview import render_overview
        return render_overview(payload, selected_profile)

    score = payload.get("score", {})
    source = payload.get("source", {})
    dimensions = {
        dimension["dimension_id"]: dimension
        for dimension in selected_profile.get("dimensions", [])
    }

    lines = [
        "# Difficulty Analysis",
        "",
        "## Overview",
        "",
        f"- Title: {score.get('title') or 'Untitled'}",
        f"- Composer: {score.get('composer') or 'Unknown'}",
        f"- Source: {source.get('path')}",
        f"- Overall score: {selected_profile.get('overall_score')}",
        f"- Overall label: {selected_profile.get('overall_label')}",
        "",
    ]

    for dimension_id, heading in (
        ("speed", "Speed"),
        ("displacement", "Displacement"),
        ("chords", "Chords"),
        ("harmony", "Harmony"),
        ("rhythm", "Rhythm"),
        ("length", "Length"),
        ("tonality", "Tonality"),
    ):
        dimension = dimensions.get(dimension_id, {})
        lines.extend(
            [
                f"## {heading}",
                "",
                f"- Mark: {dimension.get('mark')}",
                f"- Label: {dimension.get('label')}",
                f"- Summary: {dimension.get('summary')}",
                "",
            ]
        )

    notable_measures = selected_profile.get("notable_measures", [])
    lines.extend(
        [
            "## Notable Measures",
            "",
            (
                f"- Measures: {', '.join(str(measure) for measure in notable_measures)}"
                if notable_measures
                else "- Measures: none"
            ),
            "",
            "## Diagnostics",
            "",
        ]
    )
    diagnostics = selected_profile.get("diagnostics", []) or payload.get("diagnostics", [])
    if diagnostics:
        for diagnostic in diagnostics:
            if isinstance(diagnostic, dict):
                lines.append(f"- {diagnostic.get('code')}: {diagnostic.get('message')}")
            else:
                lines.append(f"- {diagnostic}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)
