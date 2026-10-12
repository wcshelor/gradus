"""Render the canonical overview payload without recomputing analysis."""

import csv
import html
import json
import re
from fractions import Fraction
from pathlib import Path


def _text(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def _number(value):
    return "unavailable" if value is None else f"{value:.3g}"


def _location(region):
    numbers = region["measure_numbers"]
    measures = "–".join(dict.fromkeys((numbers[0], numbers[-1]))) if numbers else "unknown"
    return f"Measures {measures} (quarters {region['start_offset']}–{region['end_offset']})"


def render_overview(payload, profile):
    score = payload.get("score", {})
    lines = ["# Piano difficulty overview", "",
             f"{_text(score.get('title') or 'Untitled')} — {_text(score.get('composer') or 'Unknown composer')}", "",
             profile["interpretation"], "",
             "## Dominant factors", "",
             "Ranks describe average contribution to this relative profile. Raw values retain their original units.", "",
             "| Factor | Piece value | Local range | Profile contribution |",
             "| --- | --- | --- | --- |"]
    for factor in profile["factors"]:
        lines.append(f"| {_text(factor['label'])} | {_number(factor['piece_value'])} {_text(factor['units'])} | "
                     f"{_number(factor['local_min'])}–{_number(factor['local_max'])} | {_number(factor['profile_contribution'])} |")
    views = [(profile["hand_mode"], profile), *profile.get("hand_views", {}).items()]
    for hand, view in views:
        lines.extend(["", f"## Candidate high-demand sections — {hand}", ""])
        if not view["candidate_sections"]:
            lines.append("No distinct local peaks. Review raw factor values for sustained demands.")
        for section in view["candidate_sections"]:
            labels = {f["feature_id"]: f["label"] for f in view["factors"]}
            terms = [f"{labels.get(c['feature_id'], c['feature_id'])} ({c['contribution_share']:.0%})"
                     for c in section["contributions"] if c["contribution_share"]]
            lines.extend([
                f"{section['rank']}. **{_location(section['region'])}** — relative composite {_number(section['score'])}.",
                f"   Contributions at {_location(section['representative_region'])}: {', '.join(terms) or 'none'}.",
            ])
        lines.extend(["", f"## Factor peaks — {hand}", "",
                      "| Factor | Peak regions |", "| --- | --- |"])
        for factor in view["factors"]:
            peaks = [p for p in view["factor_peaks"] if p["contributing_feature_id"] == factor["feature_id"]]
            locations = "; ".join(f"{_location(p['region'])}: {_number(p['value'])}" for p in peaks)
            lines.append(f"| {_text(factor['label'])} | {locations or 'No distinct peak'} |")
    lines.extend(["", "## Diagnostics and limitations", ""])
    for message in [*profile["diagnostics"], *(f["limitation"] for f in profile["factors"])]:
        lines.append(f"- {_text(message)}")
    for diagnostic in payload.get("diagnostics", []):
        lines.append(f"- {_text(diagnostic)}")
    return "\n".join(lines) + "\n"


def _snippet_html_for_section(section: dict) -> str:
    """Render hotspot snippet image or diagnostic without requiring live render."""
    status = section.get("snippet_status") or section.get("snippetStatus") or "not_requested"
    image = section.get("snippet_image")
    diagnostic = section.get("snippet_diagnostic")
    measure_numbers = section.get("snippet_measure_numbers") or section.get("measure_numbers") or []
    # normalize to display string
    if isinstance(measure_numbers, list) and measure_numbers:
        meas = ",".join(str(x) for x in measure_numbers)
    else:
        meas = section.get("measure_range") or section.get("snippet_measure_index_range") or "unknown"
    rank = section.get("rank") or "?"
    window_idx = section.get("window_index") or section.get("snippet_window_index")
    alt = f"Snippet window {window_idx} measures {meas}"
    diag = html.escape(str(diagnostic)) if diagnostic else ""
    # available/rendered with image path -> show img (relative path)
    if image and status in ("available", "rendered"):
        safe_src = html.escape(str(image))
        return (
            f'<figure style="margin:12px 0;padding:8px;border:1px solid #d8e1e6;background:#fbfdff">'
            f'<figcaption style="font-size:13px;color:#405060">Rank {html.escape(str(rank))} — {html.escape(str(meas))} '
            f'({html.escape(str(status))})</figcaption>'
            f'<img src="{safe_src}" alt="{html.escape(alt)}" loading="lazy" style="max-width:100%;height:auto;display:block;margin:8px 0;border:1px solid #e1ecef">'
            f'{f"<small style=color:#5a6d7a>{diag}</small>" if diag else ""}'
            f'</figure>'
        )
    # otherwise show status + diagnostic
    status_label = html.escape(str(status))
    # map legacy not_rendered to not_requested for display
    if status == "not_rendered":
        status_label = "not_requested"
    return (
        f'<div class="note" style="margin:10px 0"><strong>Snippet {status_label}</strong> — '
        f'rank {html.escape(str(rank))} measures {html.escape(str(meas))}. '
        f'{diag or "No image pre-rendered."}</div>'
    )


def _smooth_path_d(points, tension=0.25):
    """Convert polyline points to smooth cubic Bezier path (Catmull-Rom style).

    Points is list of (x,y). Returns SVG path 'd' string. Raw series values remain
    the source of truth; this interpolation is visual only to reduce spiky appearance.
    """
    if not points:
        return ""
    if len(points) == 1:
        x, y = points[0]
        return f"M {x:.2f} {y:.2f}"
    if len(points) == 2:
        x0, y0 = points[0]
        x1, y1 = points[1]
        return f"M {x0:.2f} {y0:.2f} L {x1:.2f} {y1:.2f}"
    d = f"M {points[0][0]:.2f} {points[0][1]:.2f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[0]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else points[-1]
        # control points
        cp1x = p1[0] + (p2[0] - p0[0]) * tension / 6
        cp1y = p1[1] + (p2[1] - p0[1]) * tension / 6
        cp2x = p2[0] - (p3[0] - p1[0]) * tension / 6
        cp2y = p2[1] - (p3[1] - p1[1]) * tension / 6
        d += f" C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}"
    return d


def render_html(payload, profile):
    """Self-contained report with aligned SVG profile tracks; no external assets."""
    lines = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>Piano difficulty overview</title>',
             '<style>body{font:16px system-ui;margin:40px auto;padding:0 24px;max-width:1100px;color:#20303d}'
             'svg{width:100%;height:auto;background:#f5f8fa}'
             'article{margin:24px 0}h2{font-size:20px;margin-top:32px}'
             'table{border-collapse:collapse;width:100%;margin:20px 0;font-size:14px}'
             'td,th{border-bottom:1px solid #d8e1e6;text-align:left;padding:10px}'
             'p{line-height:1.6}.note{padding:8px 16px;border-left:3px solid #acd0d7}'
             'figure img{max-width:100%}'
             '.graph-line{opacity:0.92;transition:opacity 0.15s, stroke-width 0.15s}'
             '.graph-line.dimmed{opacity:0.35}'
             '.graph-line.hovered{opacity:1}'
             '.graph-line path,.graph-line polyline{stroke-linejoin:round;stroke-linecap:round}'
             '.overall-line{opacity:0.98}'
             '#graph-tooltip{position:fixed;display:none;pointer-events:none;background:#20303d;color:#fff;'
             'font-size:12px;padding:4px 8px;border-radius:4px;white-space:nowrap;z-index:999;box-shadow:0 2px 8px rgba(0,0,0,0.18)}'
             '</style></head><body>',
             _markdown_html(render_overview(payload, profile)),
             '<h1>Difficulty timeline</h1><p>Relative within-piece profiles: 0 = local minimum, 1 = local maximum. '
             'The horizontal axis follows score time. Hover over a point for its raw value and score location. '
             'Shaded regions mark candidate sections. Graph lines use smooth curve interpolation with rounded joins/caps for visual clarity — '
             'underlying data remains the raw normalized series; smoothing is visual only.</p>']
    for hand, view in [(profile["hand_mode"], profile), *profile.get("hand_views", {}).items()]:
        lines.append(f"<h2>{html.escape(hand.title())}</h2>")
        for factor in view["factors"]:
            series = view["series"][factor["feature_id"]]
            values = series["normalized_values"]
            start = float(Fraction(view["regions"][0]["start_offset"])) if view["regions"] else 0
            end = float(Fraction(view["regions"][-1]["end_offset"])) if view["regions"] else 1
            def position_x(position):
                return 20 + 940 * (position - start) / max(end - start, 1e-9)
            def x(index):
                return position_x(view["regions"][index]["position"])
            lines.append(f"<article><strong>{html.escape(factor['label'])}</strong>"
                         '<svg viewBox="0 0 980 120" role="img" aria-label="Relative difficulty profile">')
            for section in view["candidate_sections"]:
                left = position_x(float(Fraction(section["region"]["start_offset"])))
                right = position_x(float(Fraction(section["region"]["end_offset"])))
                lines.append(f'<rect x="{left:.2f}" y="10" width="{right-left:.2f}" height="90" fill="#e1ecef"/>')
            # Split at missing observations instead of drawing invented continuity.
            # Use polished graph lines: smooth path, rounded caps/joins, hover highlight with tooltip.
            # Keep polyline semantics but render as smooth path for less spiky visuals.
            dim_label = html.escape(factor['label'])
            lines.append(f'<g class="graph-line" data-label="{dim_label}" data-factor="{html.escape(factor["feature_id"])}">')
            segment_points: list[tuple[float, float]] = []
            for i, value in enumerate([*values, None]):
                if value is None:
                    if segment_points:
                        d = _smooth_path_d(segment_points)
                        lines.append(f'<path d="{d}" fill="none" stroke="#287c8e" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />')
                        segment_points = []
                    continue
                segment_points.append((x(i), 95 - 75 * value))
            lines.append('</g>')
            for i, value in enumerate(values):
                if value is None:
                    continue
                label = f"{_location(view['regions'][i])}; raw {series['raw_values'][i]} {series['units']}; relative {value:.3f}"
                lines.append(f'<circle cx="{x(i):.2f}" cy="{95-75*value:.2f}" r="3.5" fill="#287c8e"><title>{html.escape(label)}</title></circle>')
            if view["regions"]:
                first = html.escape(view["regions"][0]["measure_numbers"][0])
                last = html.escape(view["regions"][-1]["measure_numbers"][-1])
                lines.append(f'<text x="20" y="115" font-size="12">Measure {first}</text>'
                             f'<text x="960" y="115" text-anchor="end" font-size="12">Measure {last}</text>')
            lines.append("</svg></article>")
        # Render overall composite line where available (more pronounced than dimension lines)
        _composite = view.get("composite") or view.get("overall_series")
        if isinstance(_composite, dict) and _composite.get("normalized_values"):
            comp_values = _composite["normalized_values"]
            comp_raw = _composite.get("raw_values", comp_values)
            start = float(Fraction(view["regions"][0]["start_offset"])) if view["regions"] else 0
            end = float(Fraction(view["regions"][-1]["end_offset"])) if view["regions"] else 1
            def _pos_x(position):
                return 20 + 940 * (position - start) / max(end - start, 1e-9)
            def _cx(idx):
                return _pos_x(view["regions"][idx]["position"])
            lines.append('<article><strong>Overall difficulty</strong>'
                         '<svg viewBox="0 0 980 120" role="img" aria-label="Overall difficulty profile">')
            for section in view["candidate_sections"]:
                left = _pos_x(float(Fraction(section["region"]["start_offset"])))
                right = _pos_x(float(Fraction(section["region"]["end_offset"])))
                lines.append(f'<rect x="{left:.2f}" y="10" width="{right-left:.2f}" height="90" fill="#e1ecef"/>')
            lines.append('<g class="graph-line overall-line" data-label="Overall difficulty">')
            pts: list[tuple[float, float]] = []
            for i, v in enumerate([*comp_values, None]):
                if v is None:
                    if pts:
                        d = _smooth_path_d(pts)
                        lines.append(f'<path d="{d}" fill="none" stroke="#1a4d5c" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round" />')
                        pts = []
                    continue
                pts.append((_cx(i), 95 - 75 * float(v)))
            lines.append('</g>')
            for i, v in enumerate(comp_values):
                if v is None:
                    continue
                label = f"{_location(view['regions'][i])}; overall {comp_raw[i] if i < len(comp_raw) else v:.3f} (relative {float(v):.3f})"
                lines.append(f'<circle cx="{_cx(i):.2f}" cy="{95-75*float(v):.2f}" r="3.5" fill="#1a4d5c"><title>{html.escape(label)}</title></circle>')
            if view["regions"]:
                first = html.escape(view["regions"][0]["measure_numbers"][0])
                last = html.escape(view["regions"][-1]["measure_numbers"][-1])
                lines.append(f'<text x="20" y="115" font-size="12">Measure {first}</text>'
                             f'<text x="960" y="115" text-anchor="end" font-size="12">Measure {last}</text>')
            lines.append("</svg></article>")
        # --- Learner-facing graph taxonomy (six learner-facing dimensions) when available ---
        try:
            _aspects_for_graph = next((p for p in payload.get("analysis_profiles", []) if p.get("profile_id") == "difficulty_aspects"), None)
            _graph_payload = None
            if isinstance(_aspects_for_graph, dict):
                _graph_payload = _aspects_for_graph.get("front_graph_taxonomy") or _aspects_for_graph.get("graph_taxonomy")
            if isinstance(_graph_payload, dict) and _graph_payload.get("series"):
                graph_series_all = _graph_payload.get("series") or _graph_payload.get("graph_series") or {}
                graph_composite_all = _graph_payload.get("composite") or _graph_payload.get("graph_composite")
                # Only render graph dimensions that have data for this hand's regions (both)
                if isinstance(graph_series_all, dict) and graph_series_all:
                    palette = ["#287c8e", "#b35c1e", "#6a4c93", "#2a9d8f", "#c1666b", "#6b7a3f"]
                    dim_ids_in_order = _graph_payload.get("dimension_ids") or list(graph_series_all.keys())
                    # Use view regions for x mapping
                    start_g = float(Fraction(view["regions"][0]["start_offset"])) if view["regions"] else 0
                    end_g = float(Fraction(view["regions"][-1]["end_offset"])) if view["regions"] else 1
                    def _pos_x_g(position):
                        return 20 + 940 * (position - start_g) / max(end_g - start_g, 1e-9)
                    def _cx_g(idx):
                        try:
                            return _pos_x_g(view["regions"][idx]["position"])
                        except Exception:
                            return 20 + 940 * idx / max(len(view["regions"]) - 1, 1)
                    # Render a combined timeline with all six dimensions + overall (if present)
                    lines.append('<article><strong>Learner-facing graph dimensions</strong>'
                                 '<p style="font-size:13px;color:#405060">Six learner-facing graph dimensions as a presentation layer over raw feature traces; hover a line to highlight it. Underlying data is the normalized series; curve smoothing is visual only.</p>'
                                 '<svg viewBox="0 0 980 150" role="img" aria-label="Learner-facing graph dimensions">')
                    for section in view["candidate_sections"]:
                        left = _pos_x_g(float(Fraction(section["region"]["start_offset"])))
                        right = _pos_x_g(float(Fraction(section["region"]["end_offset"])))
                        lines.append(f'<rect x="{left:.2f}" y="10" width="{right-left:.2f}" height="118" fill="#e1ecef"/>')
                    for idx, dim_id in enumerate(dim_ids_in_order):
                        series_g = graph_series_all.get(dim_id)
                        if not isinstance(series_g, dict):
                            continue
                        vals_g = series_g.get("normalized_values") or []
                        color = palette[idx % len(palette)]
                        dim_label = html.escape(series_g.get("label") or dim_id)
                        # polished smooth line per dimension
                        lines.append(f'<g class="graph-line" data-label="{dim_label}" data-dimension="{html.escape(dim_id)}">')
                        pts_g: list[tuple[float, float]] = []
                        for i, v in enumerate([*vals_g, None]):
                            if v is None:
                                if pts_g:
                                    d_g = _smooth_path_d(pts_g)
                                    lines.append(f'<path d="{d_g}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />')
                                    pts_g = []
                                continue
                            # map y: higher difficulty higher on graph (10 top, 128 bottom)
                            pts_g.append((_cx_g(i), 95 - 75 * float(v)))
                        lines.append('</g>')
                        # dots for hover detail (small)
                        for i, v in enumerate(vals_g):
                            if v is None:
                                continue
                            label_g = f"{_location(view['regions'][i])}; {series_g.get('label') or dim_id}: raw {series_g.get('raw_values',[])[i] if i < len(series_g.get('raw_values',[])) else v} relative {float(v):.3f}"
                            lines.append(f'<circle cx="{_cx_g(i):.2f}" cy="{95-75*float(v):.2f}" r="2.8" fill="{color}" opacity="0.85"><title>{html.escape(label_g)}</title></circle>')
                    # overall graph composite more pronounced
                    if isinstance(graph_composite_all, dict) and graph_composite_all.get("normalized_values"):
                        comp_vals_g = graph_composite_all.get("normalized_values") or []
                        lines.append('<g class="graph-line overall-line" data-label="Overall difficulty">')
                        pts_c: list[tuple[float, float]] = []
                        for i, v in enumerate([*comp_vals_g, None]):
                            if v is None:
                                if pts_c:
                                    d_c = _smooth_path_d(pts_c)
                                    lines.append(f'<path d="{d_c}" fill="none" stroke="#1a2e35" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round" />')
                                    pts_c = []
                                continue
                            pts_c.append((_cx_g(i), 95 - 75 * float(v)))
                        lines.append('</g>')
                    if view["regions"]:
                        first_g = html.escape(view["regions"][0]["measure_numbers"][0])
                        last_g = html.escape(view["regions"][-1]["measure_numbers"][-1])
                        lines.append(f'<text x="20" y="142" font-size="12">Measure {first_g}</text>'
                                     f'<text x="960" y="142" text-anchor="end" font-size="12">Measure {last_g}</text>')
                    lines.append('</svg>')
                    # legend
                    legend_parts = []
                    for idx, dim_id in enumerate(dim_ids_in_order):
                        series_g = graph_series_all.get(dim_id)
                        if not series_g:
                            continue
                        color = palette[idx % len(palette)]
                        label = html.escape(series_g.get("label") or dim_id)
                        legend_parts.append(f'<span style="display:inline-block;margin:4px 10px 0 0;font-size:12px"><span style="display:inline-block;width:14px;height:3px;background:{color};vertical-align:middle;margin-right:4px"></span>{label}</span>')
                    if graph_composite_all:
                        legend_parts.append('<span style="display:inline-block;margin:4px 10px 0 0;font-size:12px"><span style="display:inline-block;width:14px;height:4px;background:#1a2e35;vertical-align:middle;margin-right:4px"></span>Overall difficulty</span>')
                    lines.append('<div style="margin:6px 0 12px 0">' + "".join(legend_parts) + '</div>')
                    lines.append('</article>')
        except Exception:
            pass
        # Hotspot snippet gallery (no live render required; uses pre-rendered PNG when available)
        has_sections = any(
            view.get("candidate_sections")
            for _hand, view in [(profile["hand_mode"], profile), *profile.get("hand_views", {}).items()]
        )
        if has_sections:
            lines.append('<h1>Hotspot snippets</h1><p>Score bars for top candidate sections. Images are pre-rendered PNGs '
                         'under <code>snippets/window_&lt;index&gt;__measures_&lt;range&gt;.png</code> when available; otherwise a diagnostic explains why.</p>')
            for hand, view in [(profile["hand_mode"], profile), *profile.get("hand_views", {}).items()]:
                sections = view.get("candidate_sections") or []
                if not sections:
                    continue
                lines.append(f"<h2>{html.escape(hand.title())} — snippets</h2>")
                for section in sections:
                    lines.append(_snippet_html_for_section(section))
        # also render difficulty_aspects hotspots if present (same payload, different profile)
        aspects_profile = next((p for p in payload.get("analysis_profiles", []) if p.get("profile_id") == "difficulty_aspects"), None)
        if isinstance(aspects_profile, dict) and aspects_profile.get("hotspots"):
            lines.append('<h1>Aspect hotspots — snippets</h1>')
            for hs in aspects_profile["hotspots"][:5]:
                if isinstance(hs, dict):
                    lines.append(_snippet_html_for_section(hs))
        # render graph hotspots if available (learner-facing)
        _graph_aspects = next((p for p in payload.get("analysis_profiles", []) if p.get("profile_id") == "difficulty_aspects"), None)
        if isinstance(_graph_aspects, dict):
            _g_hotspots = (_graph_aspects.get("front_graph_taxonomy") or {}).get("hotspots") or _graph_aspects.get("graph_hotspots")
            if isinstance(_g_hotspots, list) and _g_hotspots:
                lines.append('<h1>Graph hotspots — learner-facing dimensions</h1><p>Top windows by overall graph demand; each lists dimension contributors with raw feature IDs. Refined section metadata (local_causes, distinct_local_causes, setup/continuation windows, hand_tempering, mosso tempo) supports hover/tooltip explanations where available.</p>')
                for hs in _g_hotspots[:5]:
                    if isinstance(hs, dict):
                        # Render using same snippet helper but add explanatory note about refined metadata
                        lines.append(_snippet_html_for_section(hs))
                        # compact contributor note
                        dim_parts = []
                        for dc in hs.get("dimension_contributors", [])[:3]:
                            feat_names = ", ".join(fc["feature_id"] for fc in dc.get("feature_contributors", [])[:2])
                            dim_parts.append(f"{dc.get('label')} ({feat_names})" if feat_names else dc.get("label"))
                        if dim_parts:
                            lines.append(f'<p style="font-size:12px;color:#405060">Top dimensions: {html.escape("; ".join(dim_parts))}</p>')
                        # refined metadata compact line when present
                        meta_bits = []
                        if hs.get("distinct_local_causes"):
                            meta_bits.append(f"distinct causes: {', '.join(hs.get('distinct_local_causes',[])[:3])}")
                        if hs.get("is_single_hand_window"):
                            meta_bits.append("single-hand window (rhythm tempered)" if hs.get("hand_tempering") else "single-hand window")
                        if hs.get("has_mosso_tempo"):
                            meta_bits.append(f"mosso: {', '.join(hs.get('tempo_texts',[])[:2])}")
                        if meta_bits:
                            lines.append(f'<p style="font-size:11px;color:#5a6d7a">Refined: {html.escape(" | ".join(meta_bits))}</p>')
    lines.append('<div id="graph-tooltip"></div>')
    lines.append('<script>')
    lines.append('(function(){var tooltip=document.getElementById("graph-tooltip");var lines=document.querySelectorAll(".graph-line");'
                 'function show(e,el){var label=el.getAttribute("data-label")||el.getAttribute("data-dimension")||el.getAttribute("data-factor")||"graph line";'
                 'tooltip.textContent=label;tooltip.style.display="block";'
                 'tooltip.style.left=(e.clientX+12)+"px";tooltip.style.top=(e.clientY-28)+"px";'
                 'lines.forEach(function(l){if(l===el){l.classList.add("hovered");l.classList.remove("dimmed");'
                 'var p=l.querySelector("path");if(p){p.setAttribute("stroke-width", l.classList.contains("overall-line")?"5":"3.2");}}else{l.classList.add("dimmed");l.classList.remove("hovered");}});}'
                 'function hide(el){tooltip.style.display="none";lines.forEach(function(l){l.classList.remove("dimmed");l.classList.remove("hovered");'
                 'var p=l.querySelector("path");if(p){if(l.classList.contains("overall-line"))p.setAttribute("stroke-width","3.5");else p.setAttribute("stroke-width","2.2");}});}'
                 'lines.forEach(function(el){el.addEventListener("mouseenter",function(e){show(e,el);});'
                 'el.addEventListener("mousemove",function(e){tooltip.style.left=(e.clientX+12)+"px";tooltip.style.top=(e.clientY-28)+"px";});'
                 'el.addEventListener("mouseleave",function(){hide(el);});'
                 'el.style.cursor="pointer";});})();')
    lines.append('</script>')
    lines.append("</body></html>")
    return "\n".join(lines)


def _markdown_html(markdown):
    """Render the report's small generated Markdown vocabulary, escaping input."""
    result = []
    in_table = False
    for line in markdown.splitlines():
        if line.startswith("|"):
            if set(line.replace("|", "").replace(" ", "")) <= {"-"}:
                continue
            if not in_table:
                result.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            cells = re.split(r"(?<!\\)\|", line)[1:-1]
            result.append("<tr>" + "".join(f"<{tag}>{html.escape(cell.strip())}</{tag}>" for cell in cells) + "</tr>")
            continue
        if in_table:
            result.append("</table>")
            in_table = False
        if not line.strip():
            continue
        safe = html.escape(line)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        heading = len(line) - len(line.lstrip("#"))
        if heading and line[heading:heading+1] == " ":
            result.append(f"<h{heading}>{safe[heading+1:]}</h{heading}>")
        elif line.startswith("- "):
            result.append(f'<p class="note">{safe[2:]}</p>')
        else:
            result.append("<p>" + safe + "</p>")
    if in_table:
        result.append("</table>")
    return "\n".join(result)


def write_analysis_outputs(payload, out_dir, *, stem="analysis", write_csv=True):
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {}
    def save(suffix, text):
        path = output / f"{stem}.{suffix}"
        path.write_text(text, encoding="utf-8")
        paths[suffix] = str(path)
    save("json", json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    from piano_difficulty.difficulty_analysis.markdown import render_markdown_report
    save("md", render_markdown_report(payload))
    profile = next((p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_overview"), None)
    if profile:
        save("html", render_html(payload, profile))
        if write_csv:
            rows = []
            for hand, view in [(profile["hand_mode"], profile), *profile["hand_views"].items()]:
                for feature_id, series in view["series"].items():
                    for i, region in enumerate(view["regions"]):
                        rows.append({"hand": hand, "feature_id": feature_id,
                                     "window_index": region["window_index"],
                                     "measure_numbers": ",".join(region["measure_numbers"]),
                                     "start_offset": region["start_offset"], "end_offset": region["end_offset"],
                                     "raw_value": series["raw_values"][i],
                                     "normalized_value": series["normalized_values"][i],
                                     "smoothed_value": series["smoothed_values"][i], "units": series["units"]})
            path = output / f"{stem}.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["hand", "feature_id", "window_index", "raw_value"])
                writer.writeheader()
                writer.writerows(rows)
            paths["csv"] = str(path)
    return paths
