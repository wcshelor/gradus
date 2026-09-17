#!/usr/bin/env python3
"""Thin backend/demo-readiness validation for the CEO demo catalog.

Validates without recomputing analysis and without touching analysis semantics:

- pieces.json exists and contains exactly the 11 expected ready pieces.
- each piece manifest exists at artifacts/<piece_id>/demo_manifest.json.
- each manifest exposes required frontend fields: piece metadata, chart/series,
  hotspots, 9-aspect taxonomy payload, caveats/diagnostics.
- each manifest exposes exactly 9 aspects via difficulty_aspects/aspects.
- hotspot snippet references are either rendered with an existing image file,
  or explicitly marked not_rendered/render_failed with diagnostic text.
- Oktav difficulty labels, if present, are original dataset labels only.

Deterministic, stdlib-only. Intended for CI and pre-demo checks.

Exit 0 when 11/11 pieces ready; non-zero with actionable failures.

Usage (from repo root):
    python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py
    python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py --json
    python research/learning_support/ceo_demo/scripts/validate_demo_readiness.py --pieces research/learning_support/ceo_demo/artifacts/pieces.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 11 curated catalog entries — CIPI walkthrough pieces plus Oktav demo pieces.
EXPECTED_PIECE_IDS = (
    "beethoven_fur_elise",
    "beethoven_bagatelle_119_10",
    "mozart_k545",
    "chopin_waltz_a_minor_kk_ivb_11",
    "chopin_prelude_e_minor_28_4",
    "chopin_prelude_a_major_28_7",
    "debussy_arabesque_1",
    "satie_gymnopedie_1",
    "oktav_le_onde",
    "oktav_a_thousand_miles",
    "oktav_viva_la_vida",
)

OKTAV_IDS = {"oktav_le_onde", "oktav_a_thousand_miles", "oktav_viva_la_vida"}

ALLOWED_SNIPPET_STATUSES = {"rendered", "not_rendered", "render_failed", "partial"}
HOTSPOT_ALLOWED_STATUSES = {"rendered", "not_rendered", "render_failed"}

# Minimal claim-boundary guards required in caveats
REQUIRED_CAVEAT_FRAGMENTS = [
    "symbolic-score",
    "no calibrated learner grade",
]

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PIECES_JSON = DEFAULT_REPO_ROOT / "research" / "learning_support" / "ceo_demo" / "artifacts" / "pieces.json"


@dataclass
class Issue:
    piece_id: str | None
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class PieceResult:
    piece_id: str
    manifest_path: Path | None
    ok: bool
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)


@dataclass
class ValidationReport:
    pieces_json_path: Path
    pieces_json_ok: bool
    piece_results: list[PieceResult] = field(default_factory=list)
    global_errors: list[Issue] = field(default_factory=list)
    global_warnings: list[Issue] = field(default_factory=list)

    @property
    def ready_count(self) -> int:
        return sum(1 for r in self.piece_results if r.ok)

    @property
    def total_expected(self) -> int:
        return len(EXPECTED_PIECE_IDS)

    @property
    def ok(self) -> bool:
        if self.global_errors:
            return False
        return self.ready_count == self.total_expected and all(r.ok for r in self.piece_results)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to read {path}: {e}") from e


def validate_pieces_json(pieces_path: Path) -> tuple[dict | None, list[Issue]]:
    issues: list[Issue] = []
    try:
        data = _load_json(pieces_path)
    except FileNotFoundError:
        return None, [Issue(None, "pieces.json", f"pieces.json not found: {pieces_path}")]
    except ValueError as e:
        return None, [Issue(None, "pieces.json", str(e))]

    if not isinstance(data, dict):
        return None, [Issue(None, "pieces.json", "Top-level JSON must be an object")]

    pieces = data.get("pieces")
    if not isinstance(pieces, list):
        return data, [Issue(None, "pieces", "Missing or non-list 'pieces' array")]

    # Global count check
    if len(pieces) != len(EXPECTED_PIECE_IDS):
        issues.append(Issue(None, "pieces", f"Expected {len(EXPECTED_PIECE_IDS)} pieces, found {len(pieces)}"))

    ids_found = [p.get("id") for p in pieces if isinstance(p, dict)]
    ids_set = set(ids_found)

    for expected in EXPECTED_PIECE_IDS:
        if expected not in ids_set:
            issues.append(Issue(expected, "pieces", f"Expected piece id '{expected}' missing from pieces.json"))

    for pid in ids_found:
        if pid not in EXPECTED_PIECE_IDS:
            issues.append(Issue(pid, "pieces", f"Unexpected piece id '{pid}' — catalog is scoped to the curated 11-piece demo set"))

    if len(ids_found) != len(ids_set):
        issues.append(Issue(None, "pieces", "Duplicate piece ids in pieces.json"))

    for entry in pieces:
        if not isinstance(entry, dict):
            issues.append(Issue(None, "pieces[]", "Piece entry must be an object"))
            continue
        pid = entry.get("id") or "<unknown>"
        for required in ("id", "title", "composer", "dataset", "manifest_url", "status"):
            if required not in entry or entry[required] in (None, ""):
                issues.append(Issue(pid, f"pieces[].{required}", f"Missing required field '{required}'"))
        status = entry.get("status")
        if status is not None and status != "ready":
            issues.append(Issue(pid, "pieces[].status", f"Expected status 'ready', got '{status}'"))
        # manifest_url convention
        manifest_url = entry.get("manifest_url") or entry.get("manifestUrl") or ""
        if manifest_url and pid in EXPECTED_PIECE_IDS:
            expected_suffix = f"{pid}/demo_manifest.json"
            if expected_suffix not in str(manifest_url):
                issues.append(Issue(pid, "pieces[].manifest_url", f"manifest_url should contain '{expected_suffix}', got '{manifest_url}'"))
        # artifact_base convention if present
        artifact_base = entry.get("artifact_base") or entry.get("artifactBase") or ""
        if artifact_base and pid in EXPECTED_PIECE_IDS:
            if pid not in str(artifact_base):
                issues.append(Issue(pid, "pieces[].artifact_base", f"artifact_base should contain piece id '{pid}'"))

        # Oktav difficulty_label handling
        dataset = entry.get("dataset")
        difficulty_label = entry.get("difficulty_label")
        if dataset == "oktav":
            if difficulty_label is not None:
                lowered = str(difficulty_label).lower()
                if "original dataset label" not in lowered or "not a gradus grade" not in lowered:
                    issues.append(
                        Issue(
                            pid,
                            "pieces[].difficulty_label",
                            "Oktav difficulty_label must be phrased as original dataset label only (must contain 'original dataset label' and 'not a Gradus grade')",
                        )
                    )
                # should not look like a calibrated grade
                if "gradus grade" in lowered and "not a gradus grade" not in lowered:
                    issues.append(Issue(pid, "pieces[].difficulty_label", "Oktav label must not be presented as a Gradus grade"))
            # missing label for oktav is allowed? But curated entries should have it — warn if missing
            if difficulty_label is None and pid in OKTAV_IDS:
                issues.append(Issue(pid, "pieces[].difficulty_label", "Oktav piece expected to carry difficulty_label as original dataset label provenance", severity="warning"))
        else:
            # non-oktav should not carry Oktav-style label
            if difficulty_label is not None:
                lowered = str(difficulty_label).lower()
                if "oktav" in lowered or "original dataset label" in lowered:
                    issues.append(Issue(pid, "pieces[].difficulty_label", "Non-Oktav piece should not carry Oktav difficulty_label"))

    return data, issues


def _get_aspects_payload(manifest: dict) -> dict | None:
    # Prefer difficulty_aspects, fallback to aspects (frontend accepts both, build writes both)
    payload = manifest.get("difficulty_aspects")
    if isinstance(payload, dict) and payload.get("aspects") is not None:
        return payload
    fallback = manifest.get("aspects")
    if isinstance(fallback, dict) and fallback.get("aspects") is not None:
        return fallback
    return None


def validate_manifest(manifest_path: Path, piece_id: str) -> list[Issue]:
    issues: list[Issue] = []
    try:
        manifest = _load_json(manifest_path)
    except FileNotFoundError:
        return [Issue(piece_id, "demo_manifest.json", f"Manifest not found: {manifest_path}")]
    except ValueError as e:
        return [Issue(piece_id, "demo_manifest.json", str(e))]

    if not isinstance(manifest, dict):
        return [Issue(piece_id, "demo_manifest.json", "Manifest top-level must be an object")]

    # Required top-level fields used by frontend
    for field_name in ("piece", "chart", "hotspots", "caveats", "diagnostics"):
        if field_name not in manifest:
            issues.append(Issue(piece_id, field_name, f"Missing required top-level field '{field_name}'"))

    # Aspects payload existence
    aspects_payload = _get_aspects_payload(manifest)
    if aspects_payload is None:
        issues.append(Issue(piece_id, "difficulty_aspects/aspects", "Missing 9-aspect taxonomy payload (difficulty_aspects or aspects)"))
    else:
        issues.extend(_validate_aspects_payload(aspects_payload, piece_id))

    # Exactly 9 aspects requirement — also check chart series provides 9
    chart = manifest.get("chart")
    if isinstance(chart, dict):
        issues.extend(_validate_chart(chart, piece_id))
    elif "chart" in manifest:
        issues.append(Issue(piece_id, "chart", "chart must be an object"))

    # Piece metadata validation
    piece_meta = manifest.get("piece")
    if isinstance(piece_meta, dict):
        issues.extend(_validate_piece_metadata(piece_meta, piece_id))
    elif "piece" in manifest:
        issues.append(Issue(piece_id, "piece", "piece must be an object"))

    # Hotspots validation
    hotspots = manifest.get("hotspots")
    if isinstance(hotspots, list):
        if not hotspots:
            issues.append(Issue(piece_id, "hotspots", "hotspots must be a non-empty list"))
        else:
            issues.extend(_validate_hotspots(hotspots, manifest_path, piece_id))
    elif "hotspots" in manifest:
        issues.append(Issue(piece_id, "hotspots", "hotspots must be a list"))

    # Caveats / diagnostics validation
    caveats = manifest.get("caveats")
    if isinstance(caveats, list):
        if not caveats:
            issues.append(Issue(piece_id, "caveats", "caveats must be non-empty (claim boundaries)"))
        else:
            joined = " ".join(str(c).lower() for c in caveats)
            for frag in REQUIRED_CAVEAT_FRAGMENTS:
                if frag.lower() not in joined:
                    issues.append(Issue(piece_id, "caveats", f"caveats should contain '{frag}' (claim boundary)"))
    elif "caveats" in manifest:
        issues.append(Issue(piece_id, "caveats", "caveats must be a list"))

    diagnostics = manifest.get("diagnostics")
    if diagnostics is not None and not isinstance(diagnostics, list):
        issues.append(Issue(piece_id, "diagnostics", "diagnostics must be a list if present"))

    # snippet_status top-level
    snippet_status = manifest.get("snippet_status")
    if snippet_status is None:
        issues.append(Issue(piece_id, "snippet_status", "Missing top-level snippet_status"))
    elif snippet_status not in ALLOWED_SNIPPET_STATUSES:
        issues.append(Issue(piece_id, "snippet_status", f"snippet_status must be one of {sorted(ALLOWED_SNIPPET_STATUSES)}, got '{snippet_status}'"))

    snippet_diag = manifest.get("snippet_diagnostic")
    if snippet_status in ("not_rendered", "render_failed", "partial"):
        if not isinstance(snippet_diag, str) or not snippet_diag.strip():
            issues.append(Issue(piece_id, "snippet_diagnostic", f"snippet_diagnostic must be non-empty when snippet_status is '{snippet_status}'"))

    # Generate-time sanity
    generated_at = manifest.get("generated_at")
    if generated_at is not None and not isinstance(generated_at, str):
        issues.append(Issue(piece_id, "generated_at", "generated_at should be a string timestamp"))

    # difficulty_aspects / aspects alias check — frontend reads either, but build writes both identically
    da = manifest.get("difficulty_aspects")
    a = manifest.get("aspects")
    if isinstance(da, dict) and isinstance(a, dict):
        if da.get("aspects") != a.get("aspects") and da != a:
            # Not strictly error but worth warning — they should be same payload
            issues.append(Issue(piece_id, "difficulty_aspects/aspects", "difficulty_aspects and aspects payloads differ (expected identical alias)", severity="warning"))

    return issues


def _validate_aspects_payload(payload: dict, piece_id: str) -> list[Issue]:
    issues: list[Issue] = []
    aspects = payload.get("aspects")
    if not isinstance(aspects, list):
        return [Issue(piece_id, "difficulty_aspects.aspects", "aspects must be a list")]
    if len(aspects) != 9:
        issues.append(Issue(piece_id, "difficulty_aspects.aspects", f"Expected exactly 9 aspects, got {len(aspects)}"))
    # aspect_count field if present must be 9
    aspect_count = payload.get("aspect_count")
    if aspect_count is not None and aspect_count != 9:
        issues.append(Issue(piece_id, "difficulty_aspects.aspect_count", f"aspect_count must be 9, got {aspect_count}"))

    seen_ids: set[str] = set()
    for idx, aspect in enumerate(aspects):
        ctx = f"difficulty_aspects.aspects[{idx}]"
        if not isinstance(aspect, dict):
            issues.append(Issue(piece_id, ctx, "aspect entry must be an object"))
            continue
        aid = aspect.get("aspect_id") or aspect.get("id")
        if not aid:
            issues.append(Issue(piece_id, ctx, "Missing aspect_id"))
        else:
            if aid in seen_ids:
                issues.append(Issue(piece_id, ctx, f"Duplicate aspect_id '{aid}'"))
            seen_ids.add(str(aid))
        for key in ("label", "readiness"):
            if key not in aspect or aspect[key] in (None, ""):
                # readiness may be availability etc., but frontend expects readiness
                if key == "readiness" and ("availability" in aspect or "status" in aspect):
                    continue
                issues.append(Issue(piece_id, f"{ctx}.{key}", f"Missing '{key}'"))
    return issues


def _validate_chart(chart: dict, piece_id: str) -> list[Issue]:
    issues: list[Issue] = []
    regions = chart.get("regions")
    if not isinstance(regions, list) or not regions:
        issues.append(Issue(piece_id, "chart.regions", "chart.regions must be a non-empty list"))
    series = chart.get("series")
    if not isinstance(series, dict) or not series:
        issues.append(Issue(piece_id, "chart.series", "chart.series must be a non-empty dict"))
    else:
        if len(series) != 9:
            issues.append(Issue(piece_id, "chart.series", f"chart.series must contain exactly 9 aspect series, got {len(series)}"))
        # Check each series has normalized_values
        for sid, entry in series.items():
            if not isinstance(entry, dict):
                issues.append(Issue(piece_id, f"chart.series[{sid}]", "series entry must be an object"))
                continue
            for req in ("normalized_values", "label"):
                if req not in entry:
                    issues.append(Issue(piece_id, f"chart.series[{sid}].{req}", f"Missing '{req}'"))
            # normalized length consistency with regions when both present
            if isinstance(regions, list) and isinstance(entry.get("normalized_values"), list):
                if len(entry["normalized_values"]) != len(regions):
                    issues.append(
                        Issue(
                            piece_id,
                            f"chart.series[{sid}].normalized_values",
                            f"Length {len(entry['normalized_values'])} != regions length {len(regions)}",
                        )
                    )
    composite = chart.get("composite")
    if composite is not None:
        if not isinstance(composite, dict):
            issues.append(Issue(piece_id, "chart.composite", "chart.composite must be an object if present"))
        else:
            if "normalized_values" not in composite:
                issues.append(Issue(piece_id, "chart.composite.normalized_values", "Missing normalized_values in composite"))

    aspect_ids = chart.get("aspect_ids") or chart.get("factor_ids")
    if aspect_ids is None:
        issues.append(Issue(piece_id, "chart.aspect_ids", "Missing chart.aspect_ids (or factor_ids)"))
    elif not isinstance(aspect_ids, list) or len(aspect_ids) != 9:
        issues.append(Issue(piece_id, "chart.aspect_ids", f"chart.aspect_ids must be a list of 9, got {len(aspect_ids) if isinstance(aspect_ids, list) else type(aspect_ids).__name__}"))
    else:
        if isinstance(series, dict):
            missing = [aid for aid in aspect_ids if aid not in series]
            if missing:
                issues.append(Issue(piece_id, "chart.aspect_ids", f"aspect_ids not in chart.series: {missing}"))

    # Frontend uses these but not strictly required for rendering
    for optional in ("hand_mode", "window"):
        if optional not in chart:
            issues.append(Issue(piece_id, f"chart.{optional}", f"Missing chart.{optional} (frontend metadata)", severity="warning"))

    return issues


def _validate_piece_metadata(piece: dict, expected_id: str) -> list[Issue]:
    issues: list[Issue] = []
    for req in ("title", "composer", "measure_count", "written_note_count"):
        if req not in piece:
            issues.append(Issue(expected_id, f"piece.{req}", f"Missing piece.{req}"))
        elif piece[req] in (None, ""):
            issues.append(Issue(expected_id, f"piece.{req}", f"piece.{req} should not be empty"))
    # id alias consistency
    pid = piece.get("id") or piece.get("piece_id") or piece.get("demo_id")
    if pid is not None and pid != expected_id:
        issues.append(Issue(expected_id, "piece.id", f"piece id '{pid}' does not match catalog id '{expected_id}'"))
    return issues


def _validate_hotspots(hotspots: list, manifest_path: Path, piece_id: str) -> list[Issue]:
    issues: list[Issue] = []
    artifact_dir = manifest_path.parent
    for idx, h in enumerate(hotspots):
        ctx = f"hotspots[{idx}]"
        if not isinstance(h, dict):
            issues.append(Issue(piece_id, ctx, "hotspot entry must be an object"))
            continue
        hid = h.get("id") or h.get("section_id") or h.get("hotspot_id") or f"{ctx}"
        for req in ("id", "rank", "measure_numbers", "measure_range"):
            # allow alias for id
            if req == "id" and ("id" in h or "section_id" in h or "hotspot_id" in h):
                continue
            if req not in h:
                issues.append(Issue(piece_id, f"{ctx}.{req}", f"Missing '{req}' (hotspot {hid})"))
        # contributions
        has_contribs = any(k in h for k in ("top_contributors", "aspect_contributors", "contributions"))
        if not has_contribs:
            issues.append(Issue(piece_id, f"{ctx}.top_contributors", f"Missing aspect contributors (hotspot {hid})"))

        snippet_status = h.get("snippet_status")
        snippet_image = h.get("snippet_image")
        snippet_diag = h.get("snippet_diagnostic")

        if snippet_status is None:
            issues.append(Issue(piece_id, f"{ctx}.snippet_status", f"Missing snippet_status (hotspot {hid})"))
            continue
        if snippet_status not in HOTSPOT_ALLOWED_STATUSES:
            issues.append(Issue(piece_id, f"{ctx}.snippet_status", f"snippet_status must be one of {sorted(HOTSPOT_ALLOWED_STATUSES)}, got '{snippet_status}' (hotspot {hid})"))
            continue

        if snippet_status == "rendered":
            if not isinstance(snippet_image, str) or not snippet_image.strip():
                issues.append(Issue(piece_id, f"{ctx}.snippet_image", f"snippet_image must be non-empty path when status is rendered (hotspot {hid})"))
            else:
                # Resolve relative to artifact dir; allow snippets/ prefix or absolute
                candidate = artifact_dir / snippet_image
                # Also try without snippets prefix if needed? No, manifest uses snippets/...
                if not candidate.is_file():
                    # Try alternative: artifact_dir / "snippets" / basename
                    alt = artifact_dir / "snippets" / Path(snippet_image).name
                    if not alt.is_file():
                        issues.append(
                            Issue(
                                piece_id,
                                f"{ctx}.snippet_image",
                                f"Rendered snippet file not found: {candidate} (hotspot {hid})",
                            )
                        )
                else:
                    # File exists — ensure not empty
                    try:
                        if candidate.stat().st_size < 500:
                            issues.append(Issue(piece_id, f"{ctx}.snippet_image", f"Snippet file too small (<500 bytes): {candidate}"))
                    except Exception:
                        pass
            # diagnostic for rendered should be null/empty — allow but warn if non-empty?
            if isinstance(snippet_diag, str) and snippet_diag.strip():
                issues.append(Issue(piece_id, f"{ctx}.snippet_diagnostic", f"snippet_diagnostic should be null when rendered (hotspot {hid})", severity="warning"))
        else:
            # not_rendered or render_failed
            if snippet_image is not None:
                issues.append(Issue(piece_id, f"{ctx}.snippet_image", f"snippet_image must be null when status is '{snippet_status}' (hotspot {hid})"))
            if not isinstance(snippet_diag, str) or not snippet_diag.strip():
                issues.append(Issue(piece_id, f"{ctx}.snippet_diagnostic", f"snippet_diagnostic must be non-empty when status is '{snippet_status}' (hotspot {hid})"))

    return issues


def validate_all(pieces_path: Path) -> ValidationReport:
    report = ValidationReport(pieces_json_path=pieces_path, pieces_json_ok=False)
    data, piece_issues = validate_pieces_json(pieces_path)
    # Separate errors/warnings
    for iss in piece_issues:
        if iss.severity == "warning":
            report.global_warnings.append(iss)
        else:
            report.global_errors.append(iss)

    if data is None:
        return report

    pieces = data.get("pieces", []) if isinstance(data, dict) else []
    # Build piece-id -> entry map
    entry_map: dict[str, dict] = {}
    for e in pieces:
        if isinstance(e, dict) and e.get("id"):
            entry_map[str(e["id"])] = e

    artifacts_base = pieces_path.parent

    for expected_id in EXPECTED_PIECE_IDS:
        entry = entry_map.get(expected_id)
        # Resolve manifest path
        if entry is not None:
            manifest_url = entry.get("manifest_url") or entry.get("manifestUrl") or f"../artifacts/{expected_id}/demo_manifest.json"
            # pieces.json lives in artifacts/, manifest_url is relative to web/ (..) — resolve robustly
            # Preferred: artifacts/<id>/demo_manifest.json
            candidate = artifacts_base / expected_id / "demo_manifest.json"
            if candidate.is_file():
                manifest_path: Path | None = candidate
            else:
                # Fallback try to resolve manifest_url relative to web/ naive
                # web is artifacts/.. -> resolve as artifacts_base + relative without leading ../
                cleaned = str(manifest_url).replace("../artifacts/", "").replace("../", "")
                alt = artifacts_base / cleaned
                if alt.is_file():
                    manifest_path = alt
                else:
                    # Last fallback: interpret url relative to pieces.json dir
                    rel = Path(str(manifest_url).lstrip("./"))
                    # if contains artifacts, take last parts
                    manifest_path = (pieces_path.parent / rel).resolve()
                    # try also artifacts_base / expected_id
                    if not manifest_path.is_file():
                        manifest_path = candidate
        else:
            candidate = artifacts_base / expected_id / "demo_manifest.json"
            manifest_path = candidate

        manifest_path = Path(manifest_path) if manifest_path is not None else None

        if manifest_path is None or not manifest_path.is_file():
            pr = PieceResult(piece_id=expected_id, manifest_path=manifest_path, ok=False)
            pr.errors.append(Issue(expected_id, "demo_manifest.json", f"Manifest not found at expected path: {manifest_path}"))
            report.piece_results.append(pr)
            continue

        m_issues = validate_manifest(manifest_path, expected_id)
        errors = [i for i in m_issues if i.severity != "warning"]
        warnings = [i for i in m_issues if i.severity == "warning"]
        pr = PieceResult(
            piece_id=expected_id,
            manifest_path=manifest_path,
            ok=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
        report.piece_results.append(pr)

    # Include unexpected pieces as global errors already; don't create PieceResults for them
    report.pieces_json_ok = len([i for i in report.global_errors if i.field.startswith("pieces")]) == 0 or len(report.global_errors) == 0
    # Actually pieces_json_ok means no errors in pieces.json structure (excluding per-piece)
    report.pieces_json_ok = not any(i.severity != "warning" for i in report.global_errors)
    return report


def format_report(report: ValidationReport, use_json: bool = False) -> str:
    if use_json:
        def iss_dict(i: Issue) -> dict:
            return {"piece_id": i.piece_id, "field": i.field, "message": i.message, "severity": i.severity}

        payload = {
            "pieces_json": str(report.pieces_json_path),
            "ok": report.ok,
            "ready": f"{report.ready_count}/{report.total_expected}",
            "global_errors": [iss_dict(i) for i in report.global_errors],
            "global_warnings": [iss_dict(i) for i in report.global_warnings],
            "pieces": [
                {
                    "piece_id": r.piece_id,
                    "manifest": str(r.manifest_path) if r.manifest_path else None,
                    "ok": r.ok,
                    "errors": [iss_dict(i) for i in r.errors],
                    "warnings": [iss_dict(i) for i in r.warnings],
                }
                for r in report.piece_results
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    lines: list[str] = []
    lines.append(f"Pieces catalog: {report.pieces_json_path}")
    if report.global_errors:
        lines.append("Catalog errors:")
        for iss in report.global_errors:
            lines.append(f"  [error] {iss.field}: {iss.message}" + (f" ({iss.piece_id})" if iss.piece_id else ""))
    if report.global_warnings:
        lines.append("Catalog warnings:")
        for iss in report.global_warnings:
            lines.append(f"  [warn] {iss.field}: {iss.message}" + (f" ({iss.piece_id})" if iss.piece_id else ""))
    if not report.global_errors and not report.global_warnings:
        lines.append(f"Catalog: OK ({report.total_expected} entries)")

    for pr in report.piece_results:
        status = "OK" if pr.ok else "FAIL"
        lines.append(f"  {pr.piece_id}: {status} ({pr.manifest_path})")
        for e in pr.errors:
            lines.append(f"    [error] {e.field}: {e.message}")
        for w in pr.warnings:
            lines.append(f"    [warn] {w.field}: {w.message}")

    lines.append(f"{report.ready_count}/{report.total_expected} pieces ready")
    if report.ok:
        lines.append("Demo readiness: READY")
    else:
        lines.append("Demo readiness: NOT READY — see errors above")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate CEO demo readiness (11-piece static walkthrough)")
    p.add_argument("--pieces", type=Path, default=DEFAULT_PIECES_JSON, help="Path to pieces.json (default: artifacts/pieces.json)")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable report")
    p.add_argument("--quiet", action="store_true", help="Suppress stdout except summary (still prints report unless --json)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pieces_path: Path = Path(args.pieces)
    report = validate_all(pieces_path)
    output = format_report(report, use_json=args.json)
    if not args.quiet or args.json:
        sys.stdout.write(output)
    else:
        # quiet mode still prints summary line
        sys.stdout.write(f"{report.ready_count}/{report.total_expected} pieces ready — {'READY' if report.ok else 'NOT READY'}\n")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
