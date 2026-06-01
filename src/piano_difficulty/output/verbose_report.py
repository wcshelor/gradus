"""Verbose plain-text reporting for extracted score payloads."""

from __future__ import annotations


def render_verbose_report(payload: dict[str, object]) -> str:
    """Render a deterministic, verbose text report from a score payload."""

    source = _as_dict(payload.get("source"))
    score = _as_dict(payload.get("score"))
    piece_summary = _as_dict(payload.get("piece_summary"))
    piece_features = _as_dict(piece_summary.get("features"))
    measure_summaries = _as_list(payload.get("measure_summaries"))
    features = sorted(
        (_as_dict(feature) for feature in _as_list(payload.get("features"))),
        key=lambda feature: (
            str(feature.get("feature_id")),
            str(feature.get("scope")),
            str(feature.get("scope_ref")),
        ),
    )
    analysis_profiles = sorted(
        (_as_dict(profile) for profile in _as_list(payload.get("analysis_profiles"))),
        key=lambda profile: str(profile.get("profile_id")),
    )

    lines = [
        "Verbose Extraction Report",
        "=========================",
        "",
        "Source",
        "------",
        f"Path: {source.get('path')}",
        f"Title: {score.get('title') or 'Untitled'}",
        f"Composer: {score.get('composer') or 'Unknown'}",
        f"Measure count: {score.get('measure_count')}",
        f"Written note count: {score.get('written_note_count')}",
        f"Logical note count: {score.get('logical_note_count')}",
        "",
        "Piece Summary",
        "-------------",
        f"Feature count: {piece_summary.get('feature_count')}",
    ]

    if piece_features:
        lines.append("Aggregated feature values:")
        for feature_id in sorted(piece_features):
            value = piece_features[feature_id]
            lines.extend(_render_piece_summary_feature(str(feature_id), value))
    else:
        lines.append("Aggregated feature values: none")
    lines.append("")

    lines.extend(
        [
            "Feature Records",
            "---------------",
            f"Extracted feature records: {len(features)}",
        ]
    )
    for feature in features:
        lines.extend(_render_feature_record(feature))
    lines.append("")

    lines.extend(
        [
            "Measure Summaries",
            "-----------------",
            f"Measure summaries: {len(measure_summaries)}",
        ]
    )
    for summary in measure_summaries:
        lines.extend(_render_measure_summary(_as_dict(summary)))
    lines.append("")

    lines.extend(
        [
            "Analysis Profiles",
            "-----------------",
            f"Profiles: {len(analysis_profiles)}",
        ]
    )
    for profile in analysis_profiles:
        lines.extend(_render_profile(profile))
    lines.append("")

    lines.extend(
        [
            "Top-Level Diagnostics",
            "---------------------",
        ]
    )
    diagnostics = _as_list(payload.get("diagnostics"))
    if diagnostics:
        for diagnostic in diagnostics:
            lines.append(_format_payload_diagnostic(_as_dict(diagnostic)))
    else:
        lines.append("- none")
    lines.append("")

    return "\n".join(lines)


def _render_piece_summary_feature(feature_id: str, value: object) -> list[str]:
    if isinstance(value, dict):
        return [f"- {feature_id}: {_format_piece_summary_entry(value)}"]
    if isinstance(value, list):
        lines = [f"- {feature_id}:"]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"  - {_format_piece_summary_entry(item)}")
            else:
                lines.append(f"  - {item}")
        return lines
    return [f"- {feature_id}: {value}"]


def _render_feature_record(feature: dict[str, object]) -> list[str]:
    lines = [
        f"- {feature.get('feature_id')}",
        f"  value: {feature.get('value')} {feature.get('units')}",
        f"  scope: {feature.get('scope')} ({feature.get('scope_ref')})",
        f"  reliability: {feature.get('reliability')}",
        f"  source span: {_format_source_span(_as_dict(feature.get('source_span')))}",
    ]
    diagnostics = _as_list(feature.get("diagnostics"))
    if diagnostics:
        lines.append("  diagnostics:")
        for diagnostic in diagnostics:
            lines.append(f"    - {diagnostic}")
    return lines


def _render_measure_summary(summary: dict[str, object]) -> list[str]:
    measure_index = summary.get("measure_index")
    features = sorted(
        (_as_dict(feature) for feature in _as_list(summary.get("features"))),
        key=lambda feature: (
            str(feature.get("feature_id")),
            str(feature.get("scope")),
            str(feature.get("scope_ref")),
        ),
    )
    lines = [f"- Measure {measure_index}: {len(features)} feature records"]
    for feature in features:
        lines.append(
            "  - "
            f"{feature.get('feature_id')} = {feature.get('value')} {feature.get('units')} "
            f"[scope={feature.get('scope')}:{feature.get('scope_ref')}, "
            f"reliability={feature.get('reliability')}]"
        )
    return lines


def _render_profile(profile: dict[str, object]) -> list[str]:
    lines = [
        f"- Profile: {profile.get('profile_id')} (version {profile.get('profile_version')})",
        f"  overall score: {profile.get('overall_score')}",
        f"  overall label: {profile.get('overall_label')}",
        f"  notable measures: {_format_measure_list(profile.get('notable_measures'))}",
    ]

    dimensions = sorted(
        (_as_dict(dimension) for dimension in _as_list(profile.get("dimensions"))),
        key=lambda dimension: str(dimension.get("dimension_id")),
    )
    if dimensions:
        lines.append("  dimensions:")
        for dimension in dimensions:
            lines.extend(_render_dimension(dimension))

    diagnostics = _as_list(profile.get("diagnostics"))
    if diagnostics:
        lines.append("  diagnostics:")
        for diagnostic in diagnostics:
            lines.append(f"    - {diagnostic}")
    return lines


def _render_dimension(dimension: dict[str, object]) -> list[str]:
    lines = [
        f"    - {dimension.get('dimension_id')}",
        f"      mark: {dimension.get('mark')}",
        f"      label: {dimension.get('label')}",
        f"      raw value: {dimension.get('raw_value')} {dimension.get('raw_units')}",
        f"      source span: {_format_source_span(_as_dict(dimension.get('source_span')))}",
        f"      notable measures: {_format_measure_list(dimension.get('notable_measures'))}",
        f"      summary: {dimension.get('summary')}",
    ]
    diagnostics = _as_list(dimension.get("diagnostics"))
    if diagnostics:
        lines.append("      diagnostics:")
        for diagnostic in diagnostics:
            lines.append(f"        - {diagnostic}")
    return lines


def _format_piece_summary_entry(entry: dict[str, object]) -> str:
    scope = entry.get("scope")
    scope_ref = entry.get("scope_ref")
    value = entry.get("value")
    units = entry.get("units")
    reliability = entry.get("reliability")
    if scope is None and scope_ref is None:
        return f"{value} {units} (reliability={reliability})"
    return (
        f"{value} {units} "
        f"[scope={scope}:{scope_ref}, reliability={reliability}]"
    )


def _format_source_span(source_span: dict[str, object]) -> str:
    measure_start = source_span.get("measure_start")
    measure_end = source_span.get("measure_end")
    if measure_start is None and measure_end is None:
        return "unbounded"
    if measure_start == measure_end:
        return f"measure {measure_start}"
    return f"measures {measure_start}..{measure_end}"


def _format_payload_diagnostic(diagnostic: dict[str, object]) -> str:
    code = diagnostic.get("code")
    severity = diagnostic.get("severity")
    message = diagnostic.get("message")
    span = _format_source_span(diagnostic)
    return f"- [{severity}] {code}: {message} ({span})"


def _format_measure_list(value: object) -> str:
    measures = _as_list(value)
    if not measures:
        return "none"
    return ", ".join(str(measure) for measure in measures)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
