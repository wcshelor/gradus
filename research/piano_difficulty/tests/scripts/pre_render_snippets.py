"""Pre-render snippet PNGs for David walkthrough demo pieces.

Preferred flow:
  1. Pre-render page/snippet PNGs for known demo pieces into
     artifacts/<demo_id>/snippets/window_<index>__measures_<range>.png.
  2. During analysis/report generation, attach matching snippet paths.
  3. If missing, attempt on-demand render from MusicXML/MXL source and cache.
  4. If rendering fails, keep hotspot usable with snippet_status/diagnostic.

This script can be run standalone or via the walkthrough harness.

Usage:
  conda run -n piano-difficulty python -m tests.scripts.pre_render_snippets --out-dir tests/artifacts/david_walkthrough/cipi_familiar_v1 --limit 1
  conda run -n piano-difficulty python -m tests.scripts.pre_render_snippets --demo-id chopin_prelude_e_minor_28_4 --overwrite
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.david_walkthrough.cipi_selection import (
    DEFAULT_CANONICAL_MANIFEST_CSV,
    DEFAULT_CURATION_MANIFEST_CSV,
    plan_batch,
)
from tests.harness.david_walkthrough.manifest import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "david_walkthrough" / "cipi_familiar_v1"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pre_render_snippets",
        description="Pre-render snippet PNGs for David walkthrough demo pieces (offline, explainable).",
    )
    p.add_argument("--manifest-csv", type=Path, default=DEFAULT_CURATION_MANIFEST_CSV)
    p.add_argument("--canonical-manifest-csv", type=Path, default=DEFAULT_CANONICAL_MANIFEST_CSV)
    p.add_argument("--dataset-root", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--demo-id", type=str, default=None, help="Only render this demo_id")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--overwrite", action="store_true", help="Re-render even if PNG exists")
    p.add_argument("--no-render", action="store_true", help="Only check existing PNGs (no mscore attempt)")
    p.add_argument("--dry-run", action="store_true", help="Do not write files; report what would happen")
    return p


def _load_analysis_payload(piece_dir: Path) -> dict[str, Any] | None:
    p = piece_dir / "analysis.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    entries = load_manifest(args.manifest_csv)
    if args.demo_id:
        entries = [e for e in entries if e.demo_id == args.demo_id]
        if not entries:
            print(f"No entry for demo_id {args.demo_id!r}")
            return 2
    if args.limit is not None:
        entries = entries[: max(0, int(args.limit))]

    planned = plan_batch(entries, dataset_root=args.dataset_root, canonical_manifest_csv=args.canonical_manifest_csv)

    # import resolver lazily
    try:
        from piano_difficulty.output.snippet_resolver import (
            enrich_payload_with_snippets,
            try_default_mscore_renderer,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Snippet resolver not available: {exc}")
        return 2

    out_root = Path(args.out_dir).expanduser()
    renderer = None if args.no_render else try_default_mscore_renderer

    total_ok = 0
    total_fail = 0
    per_piece: list[dict[str, Any]] = []

    for item in planned:
        piece_dir = out_root / item.entry.demo_id
        analysis_path = piece_dir / "analysis.json"
        html_path = piece_dir / "analysis.html"
        snippets_dir = piece_dir / "snippets"

        # ensure analysis exists; if not, skip (dry-run reports)
        payload = _load_analysis_payload(piece_dir)
        if payload is None:
            reason = "no analysis.json" if not analysis_path.is_file() else "unreadable analysis.json"
            if item.source_path is None or not Path(item.source_path).is_file():
                reason += f"; source {item.source_path} missing"
            per_piece.append({"demo_id": item.entry.demo_id, "status": "skipped", "reason": reason})
            continue

        # If dry-run, just report what would be checked
        if args.dry_run:
            # count existing snippets
            existing = list(snippets_dir.glob("window_*.png")) if snippets_dir.is_dir() else []
            per_piece.append({"demo_id": item.entry.demo_id, "status": "dry_run", "existing_snippets": len(existing)})
            continue

        # enrich payload (re-check existing, attempt render)
        snippets_dir.mkdir(parents=True, exist_ok=True)
        try:
            enrich_payload_with_snippets(
                payload,
                snippets_dir,
                item.source_path,
                renderer,
                allow_render=not args.no_render,
                overwrite=args.overwrite,
            )
        except Exception as exc:  # noqa: BLE001
            per_piece.append({"demo_id": item.entry.demo_id, "status": "enrich_failed", "reason": str(exc)[:200]})
            total_fail += 1
            continue

        # write back analysis.json atomically and re-render HTML
        try:
            tmp = analysis_path.with_suffix(".tmp.json")
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            json.loads(tmp.read_text(encoding="utf-8"))
            tmp.replace(analysis_path)
        except Exception as exc:  # noqa: BLE001
            per_piece.append({"demo_id": item.entry.demo_id, "status": "write_failed", "reason": str(exc)[:200]})
            total_fail += 1
            continue

        # re-write HTML without recomputing analysis
        try:
            from piano_difficulty.output.overview import render_html

            # need profile for html
            analysis_profiles = payload.get("analysis_profiles", [])
            overview = next((p for p in analysis_profiles if p.get("profile_id") == "difficulty_overview"), None)
            if overview is not None:
                html = render_html(payload, overview)
                tmp_html = html_path.with_suffix(".tmp.html")
                tmp_html.write_text(html, encoding="utf-8")
                tmp_html.replace(html_path)
        except Exception:
            pass

        # summarize snippet statuses
        statuses: list[str] = []
        for prof in payload.get("analysis_profiles", []) or []:
            if isinstance(prof, dict):
                for key in ("candidate_sections", "hotspots"):
                    secs = prof.get(key)
                    if isinstance(secs, list):
                        for s in secs:
                            if isinstance(s, dict) and s.get("snippet_status"):
                                statuses.append(str(s["snippet_status"]))
        available = sum(1 for s in statuses if s in ("available", "rendered"))
        failed = sum(1 for s in statuses if s in ("render_failed", "missing_source"))
        # also consider not_requested
        per_piece.append(
            {
                "demo_id": item.entry.demo_id,
                "status": "ok",
                "snippets_dir": str(snippets_dir),
                "snippet_statuses": statuses,
                "available_or_rendered": available,
                "failed": failed,
                "total_hotspots": len(statuses),
                "source": str(item.source_path) if item.source_path else None,
            }
        )
        if failed == 0:
            total_ok += 1
        else:
            # partial still counts as ok if at least one available
            if available > 0:
                total_ok += 1
            else:
                total_fail += 1

    summary = {
        "out_dir": str(out_root),
        "piece_count": len(planned),
        "ok": total_ok,
        "failed": total_fail,
        "per_piece": per_piece,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
