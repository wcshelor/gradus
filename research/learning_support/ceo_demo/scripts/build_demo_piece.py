#!/usr/bin/env python3
"""Reusable backend package generator for the CEO demo catalog.

Reads a single MusicXML score and writes frontend-ready artifacts under
``research/learning_support/ceo_demo/artifacts/<piece_id>/``:

- analysis.json, analysis.md, analysis.html, analysis.csv via the existing
  ``piano_difficulty`` pipeline (``analyze_score`` + ``write_analysis_outputs``)
- demo_manifest.json — compact manifest for the mini-GUI: the 9-aspect
  difficulty taxonomy (difficulty_aspects.v1) plus supporting feature traces
  for the timeline/hotspots. The manifest is the single frontend contract
  and is presented as one consistent 9-aspect model (timeline signals are
  supporting traces inside that model, not a separate user-facing taxonomy).

Usage (from repo root):
    python research/learning_support/ceo_demo/scripts/build_demo_piece.py \\
        --piece-id debussy_arabesque_1 \\
        --score research/learning_support/ceo_demo/data/source_scores/debussy_arabesque-no-1.musicxml \\
        --title "Arabesque No. 1" \\
        --composer "Claude Debussy" \\
        --dataset cipi \\
        --dataset-id x-336 \\
        --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml \\
        --out-dir research/learning_support/ceo_demo/artifacts/debussy_arabesque_1

Defaults are not assumed for piece identity — callers must pass
``--piece-id``, ``--score`` and ``--out-dir``. ``--title``/``--composer``/
``--dataset`` fall back to score-embedded metadata when omitted so the script
remains usable for ad-hoc runs, but catalog builds should pass them
explicitly.

Technical: profile_ids ("difficulty_aspects","difficulty_overview") —
difficulty_overview is backend provenance for timeline traces only; the
user-facing model is the 9-aspect taxonomy.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "research" / "piano_difficulty" / "src"
if str(_SRC_ROOT) not in sys.path:
    try:
        import piano_difficulty  # noqa: F401
    except ModuleNotFoundError:
        sys.path.insert(0, str(_SRC_ROOT))

from piano_difficulty.output.overview import write_analysis_outputs
from piano_difficulty.pipeline import analyze_score

# Local helper for deterministic explanations (v0). Import guarded so
# validation environments without the helper still produce a manifest via
# frontend fallback.
try:
    from hotspot_explanation import build_hotspot_explanation  # type: ignore
except ModuleNotFoundError:
    try:
        import importlib.util

        _helper_path = Path(__file__).with_name("hotspot_explanation.py")
        _spec = importlib.util.spec_from_file_location("hotspot_explanation", _helper_path)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)  # type: ignore
            build_hotspot_explanation = _mod.build_hotspot_explanation  # type: ignore
        else:
            build_hotspot_explanation = None  # type: ignore
    except Exception:
        build_hotspot_explanation = None  # type: ignore


def _overview_profile(payload: dict) -> dict | None:
    for profile in payload.get("analysis_profiles", []) or []:
        if isinstance(profile, dict) and profile.get("profile_id") == "difficulty_overview":
            return profile
    return None


def _aspects_profile(payload: dict) -> dict | None:
    for profile in payload.get("analysis_profiles", []) or []:
        if isinstance(profile, dict) and profile.get("profile_id") == "difficulty_aspects":
            return profile
    return None


def build_demo_manifest(
    *,
    payload: dict,
    score_path_rel: Path,
    artifact_dir: Path,
    piece_id: str,
    title: str | None = None,
    composer: str | None = None,
    dataset: str | None = None,
    dataset_id: str | None = None,
    dataset_relative_path: str | None = None,
) -> dict:
    """Convert the full analysis payload into a compact frontend manifest."""
    aspects_profile = _aspects_profile(payload)
    overview_profile = _overview_profile(payload)
    if aspects_profile is None:
        raise ValueError("difficulty_aspects profile missing from analysis payload")
    # difficulty_overview is legacy/provenance only; chart/hotspot come from aspects
    profile = aspects_profile
    legacy_profile = overview_profile

    score = payload.get("score", {}) if isinstance(payload, dict) else {}

    # Resolve display title/composer — explicit args take precedence, then score
    # metadata, then generic fallback.
    resolved_title = title or score.get("title") or piece_id
    resolved_composer = composer or score.get("composer") or "Unknown"

    # ------------------------------------------------------------------
    # Piece metadata — dynamic, catalog-compatible.
    # ------------------------------------------------------------------
    piece = {
        "title": resolved_title,
        "composer": resolved_composer,
        "demo_id": piece_id,
        "id": piece_id,
        "piece_id": piece_id,
        "dataset": dataset,
        "dataset_id": dataset_id,
        "dataset_relative_path": dataset_relative_path,
        "source_score_path": score_path_rel.as_posix(),
        "canonical_filename": score_path_rel.name,
        "measure_count": score.get("measure_count"),
        "written_note_count": score.get("written_note_count"),
        "logical_note_count": score.get("logical_note_count"),
    }
    # Back-compat aliases when dataset is cipi (frontend historically read cipi_id)
    if dataset == "cipi":
        piece["cipi_id"] = dataset_id
        piece["cipi_relative_path"] = dataset_relative_path
    elif dataset_id is not None:
        # Keep cipi_* keys only for cipi; for oktav they are not set.
        pass

    # ------------------------------------------------------------------
    # Generated artifact paths (relative to artifact dir, as frontend needs)
    # ------------------------------------------------------------------
    artifacts = {
        "analysis.json": "analysis.json",
        "analysis.md": "analysis.md",
        "analysis.html": "analysis.html",
        "analysis.csv": "analysis.csv",
        "demo_manifest.json": "demo_manifest.json",
    }

    # ------------------------------------------------------------------
    # Factors — legacy overview factors (compatibility) plus aspect-level
    # factors for provenance. Chart now uses aspects, not these 5 factors.
    # ------------------------------------------------------------------
    legacy_factors = []
    if legacy_profile is not None:
        for factor in legacy_profile.get("factors", []) or []:
            legacy_factors.append(
                {
                    "feature_id": factor.get("feature_id"),
                    "label": factor.get("label"),
                    "units": factor.get("units"),
                    "scope": factor.get("scope"),
                    "description": factor.get("description"),
                    "limitation": factor.get("limitation"),
                    "rank": factor.get("rank"),
                    "piece_value": factor.get("piece_value"),
                    "local_min": factor.get("local_min"),
                    "local_max": factor.get("local_max"),
                    "profile_contribution": factor.get("profile_contribution"),
                    "availability": factor.get("availability"),
                    "peak_ids": list(factor.get("peak_ids", []) or []),
                }
            )
        legacy_factors.sort(key=lambda f: (f["rank"] if isinstance(f["rank"], int) else 999, f["feature_id"] or ""))
    # Primary factors for manifest are aspect-level descriptors (for provenance)
    # but chart uses aspect series.
    factors = legacy_factors

    # ------------------------------------------------------------------
    # Chart — per-aspect temporal series (9 aspect IDs), not 5 feature IDs.
    # ------------------------------------------------------------------
    regions = profile.get("regions", []) or []
    series_raw = profile.get("series", {}) or profile.get("aspect_series", {}) or {}
    composite_raw = profile.get("composite") or profile.get("overall_series") or {}

    chart_regions = []
    for region in regions:
        chart_regions.append(
            {
                "window_index": region.get("window_index"),
                "measure_numbers": list(region.get("measure_numbers", []) or []),
                "measure_label": f"Measures {'-'.join(region.get('measure_numbers', []) or [])}" if region.get("measure_numbers") else "unknown",
                "start_offset": region.get("start_offset"),
                "end_offset": region.get("end_offset"),
                "position": region.get("position"),
                "label": region.get("label"),
            }
        )

    chart_series: dict[str, dict] = {}
    for aspect_id in sorted(series_raw.keys()):
        entry = series_raw[aspect_id] or {}
        chart_series[aspect_id] = {
            "aspect_id": aspect_id,
            "feature_id": entry.get("feature_id") or aspect_id,
            "id": aspect_id,
            "label": entry.get("label") or entry.get("feature_name") or aspect_id,
            "feature_name": entry.get("feature_name") or entry.get("label") or aspect_id,
            "units": entry.get("units"),
            "readiness": entry.get("readiness"),
            "availability": entry.get("availability"),
            "blocked": bool(entry.get("blocked")),
            "caveated": bool(entry.get("caveated")),
            "raw_values": list(entry.get("raw_values", []) or []),
            "normalized_values": list(entry.get("normalized_values", []) or []),
            "smoothed_values": list(entry.get("smoothed_values", []) or []),
            "missing_region_indices": list(entry.get("missing_region_indices", []) or []),
            "limitations": list(entry.get("limitations", []) or []),
            "missing_features": list(entry.get("missing_features", []) or []),
        }

    chart_composite: dict[str, object] = {}
    if composite_raw:
        chart_composite = {
            "feature_id": composite_raw.get("feature_id") or "composite.aspect_demand",
            "aspect_id": composite_raw.get("aspect_id") or "composite.aspect_demand",
            "label": composite_raw.get("label") or composite_raw.get("feature_name") or "Overall aspect demand",
            "feature_name": composite_raw.get("feature_name") or "Overall aspect demand",
            "units": composite_raw.get("units"),
            "raw_values": list(composite_raw.get("raw_values", []) or []),
            "normalized_values": list(composite_raw.get("normalized_values", []) or []),
            "smoothed_values": list(composite_raw.get("smoothed_values", []) or []),
            "missing_region_indices": list(composite_raw.get("missing_region_indices", []) or []),
        }

    aspect_ids = sorted(chart_series.keys())
    chart = {
        "hand_mode": profile.get("hand_mode") or profile.get("methods", {}).get("hand_mode") or "both",
        "window": profile.get("methods", {}).get("window") if isinstance(profile.get("methods"), dict) else None,
        "regions": chart_regions,
        "series": chart_series,
        "composite": chart_composite,
        "factor_ids": aspect_ids,
        "aspect_ids": aspect_ids,
        "references": {
            "analysis_csv": "analysis.csv",
            "analysis_json": "analysis.json",
        },
    }

    # ------------------------------------------------------------------
    # Hotspots — aspect-ranked hotspots with nested feature contributors.
    # ------------------------------------------------------------------
    hotspots = []
    candidate_sections = profile.get("candidate_sections", []) or profile.get("hotspots", []) or profile.get("aspect_hotspots", []) or []
    for section in candidate_sections:
        region = section.get("region", {}) if isinstance(section, dict) else {}
        rep = section.get("representative_region", {}) if isinstance(section, dict) else {}
        measure_numbers = list(region.get("measure_numbers", []) or [])
        hotspot_id = section.get("section_id") or section.get("id") or section.get("hotspot_id") or f"section:both:{region.get('start_offset')}:{region.get('end_offset')}"
        # Aspect contributors with nested feature contributors
        aspect_contribs = []
        for contrib in section.get("aspect_contributors", []) or section.get("top_contributors", []) or section.get("contributions", []) or []:
            # Feature contributors nested under aspect
            feat_contribs = []
            for f in contrib.get("feature_contributors", []) or contrib.get("supporting_feature_contributors", []) or contrib.get("feature_summaries", []) or []:
                feat_contribs.append(
                    {
                        "feature_id": f.get("feature_id"),
                        "label": f.get("label") or f.get("feature_name") or f.get("feature_id"),
                        "feature_name": f.get("feature_name") or f.get("label") or f.get("feature_id"),
                        "contribution_share": f.get("contribution_share"),
                        "raw_value": f.get("raw_value"),
                        "normalized_value": f.get("normalized_value"),
                        "weighted_value": f.get("weighted_value"),
                        "rank": f.get("rank"),
                        "units": f.get("units"),
                    }
                )
            feat_contribs.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))
            aspect_contribs.append(
                {
                    "aspect_id": contrib.get("aspect_id") or contrib.get("feature_id") or contrib.get("id"),
                    "feature_id": contrib.get("aspect_id") or contrib.get("feature_id"),
                    "id": contrib.get("aspect_id") or contrib.get("feature_id"),
                    "label": contrib.get("label") or contrib.get("feature_name") or contrib.get("aspect_id"),
                    "feature_name": contrib.get("feature_name") or contrib.get("label"),
                    "readiness": contrib.get("readiness"),
                    "availability": contrib.get("availability"),
                    "contribution_share": contrib.get("contribution_share"),
                    "raw_value": contrib.get("raw_value"),
                    "normalized_value": contrib.get("normalized_value"),
                    "weighted_value": contrib.get("weighted_value"),
                    "rank": contrib.get("rank"),
                    "is_peak_support": bool(contrib.get("is_peak_support")),
                    "feature_contributors": feat_contribs,
                    "supporting_feature_contributors": feat_contribs,
                }
            )
        aspect_contribs.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))

        hotspots.append(
            {
                "id": hotspot_id,
                "section_id": hotspot_id,
                "hotspot_id": hotspot_id,
                "rank": section.get("rank"),
                "measure_numbers": measure_numbers,
                "measure_range": section.get("measure_range") or (f"{measure_numbers[0]}-{measure_numbers[-1]}" if len(measure_numbers) >= 2 else (measure_numbers[0] if measure_numbers else "unknown")),
                "label": region.get("label") or section.get("label") or f"Measures {'-'.join(measure_numbers) if measure_numbers else 'unknown'}",
                "start_offset": region.get("start_offset") or section.get("start_offset"),
                "end_offset": region.get("end_offset") or section.get("end_offset"),
                "score_position": region.get("position") if region.get("position") is not None else section.get("score_position"),
                "score_value": section.get("score_value") if section.get("score_value") is not None else section.get("score"),
                "method": section.get("method"),
                "supporting_window_indices": list(section.get("supporting_window_indices", []) or []),
                "supporting_factor_ids": list(section.get("supporting_factor_ids", []) or section.get("supporting_aspect_ids", []) or []),
                "supporting_aspect_ids": list(section.get("supporting_aspect_ids", []) or [c["aspect_id"] for c in aspect_contribs]),
                "representative_region": {
                    "window_index": rep.get("window_index"),
                    "measure_numbers": list(rep.get("measure_numbers", []) or []),
                    "start_offset": rep.get("start_offset"),
                    "end_offset": rep.get("end_offset"),
                    "label": rep.get("label"),
                    "position": rep.get("position"),
                },
                "top_contributors": aspect_contribs,
                "aspect_contributors": aspect_contribs,
                "contributions": aspect_contribs,
                "snippet_image": None,
                "snippet_status": "not_rendered",
                "snippet_diagnostic": "Snippet rendering deferred; no image generated. Future images will be pre-rendered under artifacts/<piece_id>/snippets/.",
            }
        )
    hotspots.sort(key=lambda h: (h["rank"] if isinstance(h["rank"], int) else 999))

    # ------------------------------------------------------------------
    # Caveats — symbolic-score framing, copied from existing CEO notes +
    # profile interpretation. These are boundaries, not grades.
    # Aspect-based interpretation is primary; overview is legacy.
    # ------------------------------------------------------------------
    ceo_caveat = "Ornamental timing is approximate in symbolic data; rubato and tone are out of scope."
    caveats = [
        "Symbolic-score demo evidence only; no calibrated learner grade.",
        "No measured learning benefit; no pedagogical diagnosis.",
        "No production score-viewer claim; future snippet images are pre-rendered, not a live engraving pipeline.",
        ceo_caveat,
        profile.get("interpretation") or "Relative score demands within this piece; no calibrated difficulty grade.",
        "Aspect ranks describe contributions to this 9-aspect profile, not measured learner difficulty.",
        "Ranks are relative within this piece; they are not comparable across pieces.",
        "Aspect 8 (structural/pattern) is blocked: no temporal trace; aspect 9 (performance/interpretive) is caveated.",
    ]
    seen = set(caveats)
    for diag in profile.get("diagnostics", []) or []:
        if diag not in seen:
            caveats.append(diag)
            seen.add(diag)
    if legacy_profile is not None:
        for diag in legacy_profile.get("diagnostics", []) or []:
            if diag not in seen and "Factor ranks" not in diag:
                # keep legacy diagnostics as provenance but not as primary
                pass

    manifest: dict = {
        "schema_version": "ceo_demo_manifest.v1",
        "demo_id": piece_id,
        "id": piece_id,
        "piece_id": piece_id,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "piece": piece,
        "artifacts": artifacts,
        "factors": factors,
        "legacy_factors": legacy_factors,
        "chart": chart,
        "hotspots": hotspots,
        "caveats": caveats,
        "diagnostics": list(profile.get("diagnostics", []) or []),
        "warnings": list(profile.get("warnings", []) or []),
        "methods": dict(profile.get("methods", {}) or {}),
        "legacy_methods": dict(legacy_profile.get("methods", {}) or {}) if legacy_profile else {},
        "interpretation": profile.get("interpretation"),
        "factor_registry_version": legacy_profile.get("factor_registry_version") if legacy_profile else None,
        "profile_version": profile.get("profile_version"),
        "hand_mode": profile.get("hand_mode") or chart.get("hand_mode"),
        "snippet_status": "not_rendered",
        "snippet_diagnostic": "Snippet images not yet rendered; demo_manifest.json reserves snippet_image/snippet_status per hotspot.",
    }
    manifest["difficulty_aspects"] = aspects_profile
    manifest["aspects"] = aspects_profile
    manifest["aspects_schema_version"] = aspects_profile.get("schema_version")
    manifest["aspects_profile_version"] = aspects_profile.get("profile_version")
    # Legacy overview preserved for provenance
    if legacy_profile is not None:
        manifest["difficulty_overview"] = legacy_profile
        manifest["legacy_overview"] = legacy_profile
    else:
        manifest["difficulty_overview"] = None
        manifest["legacy_overview"] = None

    # Attach deterministic heuristic explanations (v0) after manifest + caveats built.
    if build_hotspot_explanation is not None:
        for h in hotspots:
            if "explanation" in h and h["explanation"]:
                continue
            try:
                exp = build_hotspot_explanation(h, chart, caveats)
                h["explanation"] = exp
            except Exception:
                continue

    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build CEO demo artifacts for one piece (9-aspect taxonomy)"
    )
    parser.add_argument("--piece-id", required=True, help="Catalog piece id, e.g. debussy_arabesque_1")
    parser.add_argument("--score", type=Path, required=True, help="Path to the MusicXML score")
    parser.add_argument("--title", type=str, default=None, help="Piece title for manifest (defaults to score title)")
    parser.add_argument("--composer", type=str, default=None, help="Composer for manifest (defaults to score composer)")
    parser.add_argument("--dataset", type=str, default=None, help="Dataset label, e.g. cipi or oktav")
    parser.add_argument("--dataset-id", type=str, default=None, help="Dataset-local id, e.g. x-336 or OK00027")
    parser.add_argument("--dataset-relative-path", type=str, default=None, help="Dataset-relative path for provenance")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for generated artifacts")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    score_path = Path(args.score).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    piece_id = str(args.piece_id)

    try:
        score_rel = score_path.resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        score_rel = Path(score_path.name)

    if not score_path.is_file():
        print(f"[error] Score file not found: {score_path}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    result = analyze_score(score_path, profile_ids=("difficulty_aspects", "difficulty_overview"))
    payload = result.to_json_payload()

    write_analysis_outputs(payload, out_dir, stem="analysis")

    manifest = build_demo_manifest(
        payload=payload,
        score_path_rel=score_rel if score_rel != Path(".") else Path(score_path.name),
        artifact_dir=out_dir,
        piece_id=piece_id,
        title=args.title,
        composer=args.composer,
        dataset=args.dataset,
        dataset_id=args.dataset_id,
        dataset_relative_path=args.dataset_relative_path,
    )
    manifest_path = out_dir / "demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    print(f"[ok] Wrote analysis artifacts to: {out_dir}")
    for name in ("analysis.json", "analysis.md", "analysis.html", "analysis.csv", "demo_manifest.json"):
        print(f"  - {name}: {out_dir / name}")
    aspects_count = len((manifest.get("difficulty_aspects") or {}).get("aspects", []) or []) if isinstance(manifest.get("difficulty_aspects"), dict) else 0
    print(f"[ok] piece_id={piece_id} factors={len(manifest['factors'])} hotspots={len(manifest['hotspots'])} regions={len(manifest['chart']['regions'])} aspects={aspects_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
