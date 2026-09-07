"""Walkthrough report writers: context, notes, index, and failures.

Reports only reframe manifest fields and computed analysis evidence; they
add no pedagogical claims.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from . import artifacts as artifact_layout
from .manifest import CeoWalkthroughEntry

REVIEWER_CHECKLIST: tuple[str, ...] = (
    "Score facts: what the symbolic score contains (notes, measures, factors) — read `analysis.md`.",
    "System ranking: relative within-piece candidate sections — inspect `analysis.html`.",
    "Learner self-report: what the learner says is hard — the ranking never overrules it.",
    "System hypothesis: the top section below is a measured candidate, not a diagnosis.",
    "Limitations: read the caveat in each `demo_notes.md`; no calibrated grades, no learning claims.",
)


def overview_profile(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    for profile in payload.get("analysis_profiles", []) or []:
        if isinstance(profile, dict) and profile.get("profile_id") == "difficulty_overview":
            return profile
    return None


def top_section_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the top candidate section, or None when analysis is unavailable."""
    profile = overview_profile(payload)
    if profile is None:
        return None
    sections = profile.get("candidate_sections", []) or []
    if not sections:
        return None
    top = sections[0]
    region = top.get("region", {}) if isinstance(top, dict) else {}
    numbers = region.get("measure_numbers", []) if isinstance(region, dict) else []
    return {
        "rank": top.get("rank") if isinstance(top, dict) else None,
        "score": top.get("score") if isinstance(top, dict) else None,
        "measure_numbers": list(numbers) if isinstance(numbers, list) else [],
        "start_offset": region.get("start_offset") if isinstance(region, dict) else None,
        "end_offset": region.get("end_offset") if isinstance(region, dict) else None,
    }


def _top_section_line(payload: dict[str, Any] | None) -> str:
    top = top_section_summary(payload)
    if top is None:
        return "Top analyzer section: unavailable (no candidate sections in this run)."
    measures = ",".join(top["measure_numbers"]) if top["measure_numbers"] else "unknown measures"
    return (
        f"Top analyzer section: rank {top['rank']}, relative composite {top['score']}, "
        f"measures {measures} (quarters {top['start_offset']}–{top['end_offset']})."
    )


def write_piece_context(
    piece_dir: str | Path,
    planned: Any,
    *,
    status: str,
    reason: str = "",
    artifact_paths: dict[str, str] | None = None,
    versions: dict[str, str] | None = None,
    timestamp: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Path:
    """Write `piece_context.json` auditing which CIPI row produced each artifact."""
    from datetime import UTC, datetime

    entry: CeoWalkthroughEntry = planned.entry
    match = planned.match
    directory = Path(piece_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    context = {
        "demo_id": entry.demo_id,
        "status": status,
        "reason": reason,
        "manifest": {
            "composer": entry.composer,
            "title": entry.title,
            "henle": entry.henle,
            "dataset_relative_path": entry.dataset_relative_path,
            "recognition_tier": entry.recognition_tier,
            "demo_role": entry.demo_role,
            "analyzer_led_note": entry.analyzer_led_note,
            "user_selected_note": entry.user_selected_note,
            "disagreement_note": entry.disagreement_note,
            "caveat_note": entry.caveat_note,
            "metadata": dict(entry.metadata),
            "source_row_index": entry.source_row_index,
        },
        "cipi": {
            "match_status": match.status,
            "cipi_id": (match.cipi_row or {}).get("cipi_id", ""),
            "piece_uid": (match.cipi_row or {}).get("piece_uid", ""),
            "work_name": (match.cipi_row or {}).get("work_name", ""),
            "movement": (match.cipi_row or {}).get("movement", ""),
        },
        "resolution": {
            "source_path": None if planned.source_path is None else str(planned.source_path),
            "dataset_root": None if planned.dataset_root is None else str(planned.dataset_root),
            "root_source": planned.root_source,
            "root_detail": planned.root_detail,
            "pieces_dir_hint": planned.pieces_dir_hint,
        },
        "artifacts": dict(artifact_paths or {}),
        "runtime_versions": dict(versions or {}),
        "timestamp": timestamp or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    if payload is not None:
        score = payload.get("score", {}) if isinstance(payload, dict) else {}
        context["analysis"] = {
            "score_title": score.get("title", ""),
            "score_composer": score.get("composer", ""),
            "profile_ids": [
                profile.get("profile_id", "")
                for profile in (payload.get("analysis_profiles", []) or [])
                if isinstance(profile, dict)
            ],
            "top_section": top_section_summary(payload),
        }
    out_path = directory / artifact_layout.PIECE_CONTEXT_FILE
    out_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def write_demo_notes(
    piece_dir: str | Path,
    planned: Any,
    *,
    payload: dict[str, Any] | None,
    status: str,
    reason: str = "",
) -> Path:
    """Write the per-piece walkthrough note from manifest framing + evidence."""
    entry: CeoWalkthroughEntry = planned.entry
    directory = Path(piece_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {entry.title}",
        "",
        f"- Composer: {entry.composer}",
        f"- Demo role: {entry.demo_role} (recognition: {entry.recognition_tier})",
        f"- CIPI/Henle label: {entry.henle}",
        "",
        "## Analyzer-led",
        "",
        entry.analyzer_led_note,
        "",
        _top_section_line(payload) if status == "success" else
        f"Analysis unavailable (status: {status}). {reason}".strip(),
        "",
        "## User-selected",
        "",
        entry.user_selected_note,
        "",
        "## If the learner disagrees",
        "",
        entry.disagreement_note,
        "",
        "## Caveats",
        "",
        entry.caveat_note,
        "",
    ]
    out_path = directory / artifact_layout.PIECE_NOTES_FILE
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_index_json(
    out_root: str | Path,
    entries: list[CeoWalkthroughEntry],
    results: list[dict[str, Any]],
    *,
    manifest_csv: str | Path,
) -> dict[str, Any]:
    """Write the machine-readable run summary."""
    root = Path(out_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    by_id = {item["demo_id"]: item for item in results}
    payload = {
        "manifest_csv": str(Path(manifest_csv).expanduser()),
        "output_root": str(root),
        "piece_count": len(entries),
        "success_count": sum(1 for item in results if item["status"] == "success"),
        "failure_count": sum(1 for item in results if item["status"] != "success"),
        "pieces": [
            {
                "demo_id": entry.demo_id,
                "title": entry.title,
                "composer": entry.composer,
                "status": by_id.get(entry.demo_id, {}).get("status", "missing"),
                "reason": by_id.get(entry.demo_id, {}).get("reason", ""),
                "piece_dir": by_id.get(entry.demo_id, {}).get("piece_dir", ""),
                "artifacts": {
                    name: str(path)
                    for name, path in artifact_layout.piece_artifact_paths(
                        root, entry.demo_id
                    ).items()
                },
            }
            for entry in entries
        ],
    }
    (root / artifact_layout.TOP_INDEX_JSON).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def write_index_markdown(
    out_root: str | Path,
    entries: list[CeoWalkthroughEntry],
    results: list[dict[str, Any]],
) -> Path:
    """Write the human-readable CEO walkthrough entry point."""
    root = Path(out_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    by_id = {item["demo_id"]: item for item in results}
    success_count = sum(1 for item in results if item["status"] == "success")
    failure_count = sum(1 for item in results if item["status"] != "success")
    lines = [
        "# CEO CIPI Walkthrough",
        "",
        "Computed demo evidence over familiar CIPI repertoire. Ranks are relative "
        "within each piece; they are not calibrated difficulty grades.",
        "",
        f"- Pieces: {len(entries)}; succeeded: {success_count}; failed: {failure_count}.",
        "",
        "## Pieces",
        "",
    ]
    for entry in entries:
        item = by_id.get(entry.demo_id, {})
        status = item.get("status", "missing")
        lines.append(f"### {entry.demo_id} — {entry.title} ({entry.composer})")
        lines.append("")
        lines.append(f"- Status: {status}")
        if status == "success":
            lines.append(f"- [Timeline]({entry.demo_id}/analysis.html)")
            lines.append(f"- [Score analysis]({entry.demo_id}/analysis.md)")
            lines.append(f"- [Walkthrough notes]({entry.demo_id}/demo_notes.md)")
        elif item.get("reason"):
            lines.append(f"- Reason: {item['reason']}")
        lines.append("")
    lines.extend(["## Reviewer checklist", ""])
    lines.extend([f"- {item}" for item in REVIEWER_CHECKLIST])
    lines.append("")
    out_path = root / artifact_layout.TOP_INDEX_MARKDOWN
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_failures_csv(
    out_root: str | Path,
    planned: list[Any],
    results: list[dict[str, Any]],
) -> Path | None:
    """Write `failures.csv` when any piece failed; otherwise remove it."""
    root = Path(out_root).expanduser()
    failures_path = root / artifact_layout.TOP_FAILURES_CSV
    by_id = {item["demo_id"]: item for item in results}
    planned_by_id = {item.entry.demo_id: item for item in planned}
    rows = []
    for demo_id, item in by_id.items():
        if item["status"] == "success":
            continue
        planned_item = planned_by_id.get(demo_id)
        source = item.get("source_path") or ""
        if not source and planned_item is not None and planned_item.source_path is not None:
            source = str(planned_item.source_path)
        rows.append({
            "demo_id": demo_id,
            "phase": item["status"],
            "reason": item.get("reason", ""),
            "source_path": source,
        })
    if not rows:
        if failures_path.is_file():
            failures_path.unlink()
        return None
    root.mkdir(parents=True, exist_ok=True)
    with failures_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["demo_id", "phase", "reason", "source_path"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return failures_path
