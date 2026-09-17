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
    if selected_profile.get("profile_id") == "difficulty_aspects":
        return _render_aspects_profile(payload, selected_profile)

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
        f"- Legacy ScoreAnalyzer label: {selected_profile.get('scoreanalyzer_legacy_grade')}",
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
                f"- Legacy ScoreAnalyzer label: {dimension.get('legacy_label')}",
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


def _render_aspects_profile(payload: dict[str, object], profile: dict[str, object]) -> str:
    score = payload.get("score", {})
    source = payload.get("source", {})
    aspects = profile.get("aspects", [])

    lines = [
        "# Difficulty Analysis",
        "",
        "## Overview",
        "",
        f"- Title: {score.get('title') or 'Untitled'}",
        f"- Composer: {score.get('composer') or 'Unknown'}",
        f"- Source: {source.get('path')}",
        f"- Profile: {profile.get('profile_id')} ({profile.get('schema_version')})",
        "",
        "## Difficulty Aspects",
        "",
    ]

    if isinstance(aspects, list) and aspects:
        for aspect in aspects:
            if not isinstance(aspect, dict):
                continue
            feature_ids = aspect.get("included_feature_ids") or aspect.get("feature_ids") or []
            feature_count = len(feature_ids) if isinstance(feature_ids, list) else 0
            lines.extend(
                [
                    f"### {aspect.get('label') or aspect.get('aspect_id')}",
                    "",
                    f"- Status: {aspect.get('readiness')}",
                    f"- Features: {feature_count}",
                    f"- Description: {aspect.get('description')}",
                    "",
                ]
            )
    else:
        lines.extend(["- none", ""])

    # Front-facing graph taxonomy (learner-visible) if present
    graph_payload = profile.get("front_graph_taxonomy") or profile.get("graph_taxonomy")
    if isinstance(graph_payload, dict) and graph_payload.get("dimensions"):
        lines.extend(["## Learner-Facing Graph Dimensions (front_graph_taxonomy)", "", f"- Version: {graph_payload.get('version') or graph_payload.get('taxonomy_version') or 'unknown'}", "- Graph dimensions are presentation-layer composite signals over normalized raw feature traces; smoothing is visual only.", ""])
        for dim in graph_payload.get("dimensions", []):
            if not isinstance(dim, dict):
                continue
            lines.extend([f"### {dim.get('label') or dim.get('id')}", "", f"- ID: {dim.get('id')}", f"- Description: {dim.get('description')}", f"- Caveats: {dim.get('caveats')}", ""])
        # contributor note
        lines.extend(["- Note: Graph hotspots list dimension contributors with raw feature IDs; refined section metadata (local_causes, distinct_local_causes, setup/continuation windows, hand_tempering/is_single_hand_window, has_mosso_tempo/tempo_texts/tempo_influence) can support hover/tooltip explanations where available.", ""])

    diagnostics = profile.get("diagnostics", []) or payload.get("diagnostics", [])
    lines.extend(["## Diagnostics", ""])
    if diagnostics:
        for diagnostic in diagnostics:
            lines.append(f"- {diagnostic}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)
