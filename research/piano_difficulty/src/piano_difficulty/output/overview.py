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
             '</style></head><body>',
             _markdown_html(render_overview(payload, profile)),
             '<h1>Difficulty timeline</h1><p>Relative within-piece profiles: 0 = local minimum, 1 = local maximum. '
             'The horizontal axis follows score time. Hover over a point for its raw value and score location. '
             'Shaded regions mark candidate sections.</p>']
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
            segment = []
            for i, value in enumerate([*values, None]):
                if value is None:
                    if segment:
                        lines.append('<polyline fill="none" stroke="#287c8e" stroke-width="2" points="' + " ".join(segment) + '"/>')
                        segment = []
                    continue
                segment.append(f"{x(i):.2f},{95 - 75 * value:.2f}")
            for i, value in enumerate(values):
                if value is None:
                    continue
                label = f"{_location(view['regions'][i])}; raw {series['raw_values'][i]} {series['units']}; relative {value:.3f}"
                lines.append(f'<circle cx="{x(i):.2f}" cy="{95-75*value:.2f}" r="4" fill="#287c8e"><title>{html.escape(label)}</title></circle>')
            if view["regions"]:
                first = html.escape(view["regions"][0]["measure_numbers"][0])
                last = html.escape(view["regions"][-1]["measure_numbers"][-1])
                lines.append(f'<text x="20" y="115" font-size="12">Measure {first}</text>'
                             f'<text x="960" y="115" text-anchor="end" font-size="12">Measure {last}</text>')
            lines.append("</svg></article>")
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
