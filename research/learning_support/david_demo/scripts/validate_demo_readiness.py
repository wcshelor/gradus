#!/usr/bin/env python3
"""Thin backend/demo-readiness validation for the David demo catalog.

Validates without recomputing analysis and without touching analysis semantics:

- pieces.json exists and contains exactly the 12 expected ready pieces.
- each piece manifest exists at artifacts/<piece_id>/demo_manifest.json.
- each manifest exposes required frontend fields: piece metadata, chart/series,
  hotspots, 9-aspect backend taxonomy payload, caveats/diagnostics.
- chart.series exposes exactly 6 learner-facing graph dimensions (graph_dimension_ids).
- each manifest exposes exactly 9 backend aspects via difficulty_aspects/aspects.
- hotspot snippet references are either rendered with an existing image file,
  or explicitly marked not_rendered/render_failed with diagnostic text.
- Oktav difficulty labels, if present, are original dataset labels only.

Deterministic, stdlib-only. Intended for CI and pre-demo checks.

Exit 0 when 12/12 pieces ready; non-zero with actionable failures.

Usage (from repo root):
    python research/learning_support/david_demo/scripts/validate_demo_readiness.py
    python research/learning_support/david_demo/scripts/validate_demo_readiness.py --json
    python research/learning_support/david_demo/scripts/validate_demo_readiness.py --pieces research/learning_support/david_demo/artifacts/pieces.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 12 curated catalog entries — CIPI walkthrough pieces plus Oktav demo pieces.
EXPECTED_PIECE_IDS = (
    "beethoven_fur_elise",
    "beethoven_bagatelle_119_10",
    "mozart_k545",
    "chopin_waltz_a_minor_kk_ivb_11",
    "chopin_prelude_e_minor_28_4",
    "chopin_prelude_a_major_28_7",
    "debussy_arabesque_1",
    "debussy_clair_de_lune",
    "satie_gymnopedie_1",
    "oktav_le_onde",
    "oktav_a_thousand_miles",
    "oktav_viva_la_vida",
)

OKTAV_IDS = {"oktav_le_onde", "oktav_a_thousand_miles", "oktav_viva_la_vida"}

ALLOWED_SNIPPET_STATUSES = {"rendered", "not_rendered", "render_failed", "partial"}
HOTSPOT_ALLOWED_STATUSES = {"rendered", "not_rendered", "render_failed"}

GRAPH_DIMENSION_IDS = (
    "finger_dexterity",
    "hand_movement_position",
    "layers_coordination",
    "rhythm_timing",
    "expression_sound_control",
    "notation_reading",
)

# Minimal claim-boundary guards required in caveats
REQUIRED_CAVEAT_FRAGMENTS = [
    "symbolic-score",
    "no calibrated learner grade",
]

# Graph hotspot driver guard: visible hotspots must be graph-composite based
REQUIRED_GRAPH_CAVEAT_FRAGMENTS = [
    "6 learner-facing dimensions",
    "graph composite",
]

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PIECES_JSON = DEFAULT_REPO_ROOT / "research" / "learning_support" / "david_demo" / "artifacts" / "pieces.json"


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
            issues.append(Issue(pid, "pieces", f"Unexpected piece id '{pid}' — catalog is scoped to the curated 12-piece demo set"))

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

    # Hotspots validation (raw windows remain provenance, but learner-facing is hard_bits)
    hotspots = manifest.get("hotspots")
    if isinstance(hotspots, list):
        if not hotspots:
            issues.append(Issue(piece_id, "hotspots", "hotspots must be a non-empty list"))
        else:
            issues.extend(_validate_hotspots(hotspots, manifest_path, piece_id))
    elif "hotspots" in manifest:
        issues.append(Issue(piece_id, "hotspots", "hotspots must be a list"))
    # Phase 3: hard bits / practice regions are learner-facing grouped targets
    hard_bits = manifest.get("hard_bits") or manifest.get("practice_regions") or manifest.get("grouped_hard_bits")
    if hard_bits is None:
        issues.append(Issue(piece_id, "hard_bits", "Missing hard_bits / practice_regions (grouped hard bits with buffered display region required for Phase 3)", severity="warning"))
    elif isinstance(hard_bits, list):
        if not hard_bits:
            issues.append(Issue(piece_id, "hard_bits", "hard_bits must be non-empty (grouped practice regions)"))
        else:
            issues.extend(_validate_hard_bits(hard_bits, manifest, manifest_path, piece_id))
            # Cross-check: hard_bits should not be raw 2-measure windows only; grouped count <= hotspots count is expected when merging
            # Not strictly error if equal, but warn if hard_bits == hotspots with same raw windows and no grouping occurred on pieces with close windows
            # We keep this as warning only when hard_bits length equals hotspots length and hotspots have overlapping windows
            try:
                if len(hard_bits) == len(hotspots or []):
                    # Check if any hotspots actually overlap/are within 2 measures (would have been grouped)
                    # If so, warn that grouping may not have applied
                    raw_starts = []
                    for h in hotspots or []:
                        ms = h.get("measure_start")
                        if ms is None:
                            nums = h.get("measure_numbers") or []
                            if nums:
                                try:
                                    ms = int(str(nums[0]))
                                except ValueError:
                                    ms = None
                        if isinstance(ms, int):
                            raw_starts.append(ms)
                    raw_starts.sort()
                    has_close = any(raw_starts[i+1] - raw_starts[i] <= 3 for i in range(len(raw_starts)-1)) if len(raw_starts) >= 2 else False
                    if has_close:
                        issues.append(Issue(piece_id, "hard_bits", "hard_bits count equals hotspots count but raw windows contain close detections (gap ≤2) — grouping may not have merged as required", severity="warning"))
            except Exception:
                pass
    elif "hard_bits" in manifest:
        issues.append(Issue(piece_id, "hard_bits", "hard_bits must be a list"))

    # Caveats / diagnostics validation — must state graph/hotspot driver = 6 taxonomy and 9-way = backend
    caveats = manifest.get("caveats")
    if isinstance(caveats, list):
        if not caveats:
            issues.append(Issue(piece_id, "caveats", "caveats must be non-empty (claim boundaries)"))
        else:
            joined = " ".join(str(c).lower() for c in caveats)
            for frag in REQUIRED_CAVEAT_FRAGMENTS:
                if frag.lower() not in joined:
                    issues.append(Issue(piece_id, "caveats", f"caveats should contain '{frag}' (claim boundary)"))
            for frag in REQUIRED_GRAPH_CAVEAT_FRAGMENTS:
                if frag.lower() not in joined:
                    issues.append(Issue(piece_id, "caveats", f"caveats should contain '{frag}' (graph/hotspot driver = 6 taxonomy; 9-way = backend provenance)"))
    elif "caveats" in manifest:
        issues.append(Issue(piece_id, "caveats", "caveats must be a list"))
    # Provenance checks — 9-aspect must be present but not primary UI; graph must be primary
    if "backend_aspect_hotspots" not in manifest and "aspect_hotspots" not in manifest:
        # backend_aspect_hotspots is the explicit provenance key; difficulty_aspects already has aspects,
        # but we require the manifest-level provenance alias for clarity
        if isinstance(manifest.get("difficulty_aspects"), dict) and manifest["difficulty_aspects"].get("aspects"):
            # still warn if top-level backend key missing (help ensure demotion is explicit)
            issues.append(Issue(piece_id, "backend_aspect_hotspots", "Missing manifest.backend_aspect_hotspots (9-aspect hotspots preserved as provenance only; visible hotspots must be graph-ranked)", severity="warning"))
    # Graph taxonomy provenance
    graph_tax = manifest.get("graph_taxonomy") or manifest.get("front_graph_taxonomy")
    if not isinstance(graph_tax, dict) or not graph_tax:
        issues.append(Issue(piece_id, "graph_taxonomy", "Missing graph_taxonomy / front_graph_taxonomy (6-dimension taxonomy provenance) — ensure front_graph_taxonomy.py mapping is embedded"))

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
        if len(series) != 6:
            issues.append(Issue(piece_id, "chart.series", f"chart.series must contain exactly 6 graph dimension series, got {len(series)}"))
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

    # Visible chart must expose 6 graph dimension ids
    graph_ids = chart.get("graph_dimension_ids") or chart.get("dimension_ids")
    if graph_ids is None:
        issues.append(Issue(piece_id, "chart.graph_dimension_ids", "Missing chart.graph_dimension_ids (or dimension_ids) — visible chart must have 6 learner-facing dimensions"))
    elif not isinstance(graph_ids, list) or len(graph_ids) != 6:
        issues.append(Issue(piece_id, "chart.graph_dimension_ids", f"chart.graph_dimension_ids must be a list of 6, got {len(graph_ids) if isinstance(graph_ids, list) else type(graph_ids).__name__}"))
    else:
        if isinstance(series, dict):
            missing = [gid for gid in graph_ids if gid not in series]
            if missing:
                issues.append(Issue(piece_id, "chart.graph_dimension_ids", f"graph_dimension_ids not in chart.series: {missing}"))
        # taxonomy version should be present
        taxonomy_version = chart.get("taxonomy_version") or chart.get("graph_taxonomy_version") or chart.get("front_graph_taxonomy_version")
        if taxonomy_version is None:
            issues.append(Issue(piece_id, "chart.taxonomy_version", "Missing chart.taxonomy_version / graph_taxonomy_version (expected gradus.front_graph_taxonomy.v2)", severity="warning"))
        elif "front_graph_taxonomy" not in str(taxonomy_version):
            issues.append(Issue(piece_id, "chart.taxonomy_version", f"Unexpected taxonomy_version '{taxonomy_version}' — expected gradus.front_graph_taxonomy.v2", severity="warning"))

    # Backend 9-aspect taxonomy is not the visible graph but should still be present in difficulty_aspects; chart.aspect_ids is now provenance alias only — warn if it looks like 9-aspect graph
    aspect_ids = chart.get("aspect_ids")
    if isinstance(aspect_ids, list) and len(aspect_ids) == 9 and (graph_ids is None or len(graph_ids) != 6):
        issues.append(Issue(piece_id, "chart.aspect_ids", "chart.aspect_ids has 9 entries but visible graph should be 6 graph_dimension_ids — regenerate with front_graph_taxonomy.v2"))

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


def _validate_hard_bits(hard_bits: list, manifest: dict, manifest_path: Path, piece_id: str) -> list[Issue]:
    issues: list[Issue] = []
    piece = manifest.get("piece") or {}
    measure_count = piece.get("measure_count") if isinstance(piece, dict) else None
    for idx, hb in enumerate(hard_bits):
        ctx = f"hard_bits[{idx}]"
        if not isinstance(hb, dict):
            issues.append(Issue(piece_id, ctx, "hard_bit entry must be an object"))
            continue
        hid = hb.get("id") or hb.get("hard_bit_id") or hb.get("section_id") or f"{ctx}"
        # Required learner-facing keys
        for req in ("id", "rank", "measure_numbers", "measure_range", "label"):
            if req == "id" and ("id" in hb or "hard_bit_id" in hb or "section_id" in hb):
                continue
            if req not in hb:
                issues.append(Issue(piece_id, f"{ctx}.{req}", f"Missing '{req}' (hard_bit {hid})"))
        # Core / display regions must exist
        core = hb.get("core_region")
        disp = hb.get("display_region") or hb.get("practice_region")
        if not isinstance(core, dict):
            issues.append(Issue(piece_id, f"{ctx}.core_region", f"Missing core_region (hard_bit {hid}) — merged core before buffer"))
        else:
            for k in ("measure_numbers", "measure_start", "measure_end", "measure_range"):
                if k not in core:
                    issues.append(Issue(piece_id, f"{ctx}.core_region.{k}", f"Missing '{k}' in core_region (hard_bit {hid})"))
        if not isinstance(disp, dict):
            issues.append(Issue(piece_id, f"{ctx}.display_region", f"Missing display_region / practice_region (hard_bit {hid}) — buffered span shown to learner"))
        else:
            for k in ("measure_numbers", "measure_start", "measure_end", "measure_range"):
                if k not in disp:
                    issues.append(Issue(piece_id, f"{ctx}.display_region.{k}", f"Missing '{k}' in display_region (hard_bit {hid})"))
            # Buffer check: display should be core ±1 bounded
            if isinstance(core, dict) and isinstance(disp, dict):
                try:
                    c_s = int(core.get("measure_start"))
                    c_e = int(core.get("measure_end"))
                    d_s = int(disp.get("measure_start"))
                    d_e = int(disp.get("measure_end"))
                    # Expected buffered start/end
                    exp_s = max(1, c_s - 1) if isinstance(measure_count, int) else c_s - 1
                    exp_e = min(int(measure_count), c_e + 1) if isinstance(measure_count, int) else c_e + 1
                    if d_s != exp_s:
                        issues.append(Issue(piece_id, f"{ctx}.display_region", f"display_region start {d_s} != expected buffered start {exp_s} (core {c_s}±1, bounded) (hard_bit {hid})", severity="warning"))
                    if d_e != exp_e:
                        issues.append(Issue(piece_id, f"{ctx}.display_region", f"display_region end {d_e} != expected buffered end {exp_e} (core {c_e}±1, bounded) (hard_bit {hid})", severity="warning"))
                    # Also measure_numbers should match range
                    exp_count = exp_e - exp_s + 1
                    if len(disp.get("measure_numbers", [])) != exp_count:
                        issues.append(Issue(piece_id, f"{ctx}.display_region.measure_numbers", f"display measure_numbers length {len(disp.get('measure_numbers', []))} != expected {exp_count} for buffered span {exp_s}-{exp_e} (hard_bit {hid})", severity="warning"))
                except Exception:
                    pass
        # Supporting provenance must be present and non-empty
        sw = hb.get("supporting_windows")
        if not isinstance(sw, list) or not sw:
            issues.append(Issue(piece_id, f"{ctx}.supporting_windows", f"Missing supporting_windows provenance (hard_bit {hid}) — raw 1m/2m windows must remain inspectable"))
        sres = hb.get("supporting_resolutions")
        if not isinstance(sres, list) or not sres:
            issues.append(Issue(piece_id, f"{ctx}.supporting_resolutions", f"Missing supporting_resolutions (hard_bit {hid}) — must list 1m/2m resolutions"))
        elif "2_measures" not in sres and "1_measures" not in sres:
            issues.append(Issue(piece_id, f"{ctx}.supporting_resolutions", f"supporting_resolutions must include at least 1_measures or 2_measures (hard_bit {hid})", severity="warning"))
        # Check that hard_bit has evidence attached (semantic observations etc. target grouped region)
        # Existence of evidence/heuristic is expected but not strictly required for validation to pass if build postponed
        # We warn if missing
        if "evidence" not in hb or "heuristic_explanation" not in hb:
            issues.append(Issue(piece_id, f"{ctx}.evidence", f"Missing evidence / heuristic_explanation (hard_bit {hid}) — semantic explanation must be attached to grouped hard bit", severity="warning"))
        # Contributions check similar to hotspots
        has_contribs = any(k in hb for k in ("top_contributors", "dimension_contributors", "graph_dimension_contributors"))
        if not has_contribs:
            issues.append(Issue(piece_id, f"{ctx}.top_contributors", f"Missing dimension contributors (hard_bit {hid}) — grouped hard bit must carry aggregated dimension contributors", severity="warning"))
        # Snippet status should be not_rendered with diagnostic (consistent with hotspots)
        sn_status = hb.get("snippet_status")
        if sn_status is None:
            issues.append(Issue(piece_id, f"{ctx}.snippet_status", f"Missing snippet_status (hard_bit {hid})", severity="warning"))
        elif sn_status not in HOTSPOT_ALLOWED_STATUSES:
            issues.append(Issue(piece_id, f"{ctx}.snippet_status", f"snippet_status must be one of {HOTSPOT_ALLOWED_STATUSES}, got '{sn_status}' (hard_bit {hid})"))
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
        # contributions — visible hotspots must be graph-dimension ranked (6-way) with nested micro-component feature_contributors
        has_contribs = any(k in h for k in ("top_contributors", "dimension_contributors", "graph_dimension_contributors", "contributions", "aspect_contributors", "feature_contributions"))
        if not has_contribs:
            issues.append(Issue(piece_id, f"{ctx}.top_contributors", f"Missing graph dimension contributors (hotspot {hid}) — expected top_contributors/dimension_contributors with graph_dimension_id/dimension_id"))
        else:
            contribs = (
                h.get("top_contributors")
                or h.get("dimension_contributors")
                or h.get("graph_dimension_contributors")
                or h.get("contributions")
                or h.get("aspect_contributors")
                or h.get("feature_contributions")
                or []
            )
            if isinstance(contribs, list) and contribs:
                for c_idx, c in enumerate(contribs[:3]):
                    if not isinstance(c, dict):
                        issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}]", f"contributor must be object (hotspot {hid})"))
                        continue
                    dim_id = c.get("dimension_id") or c.get("graph_dimension_id") or c.get("feature_id") or c.get("id") or c.get("aspect_id")
                    if not dim_id:
                        issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}].dimension_id", f"Missing dimension_id/graph_dimension_id (hotspot {hid})"))
                    elif dim_id not in GRAPH_DIMENSION_IDS:
                        # Allow but warn if it's a legacy 9-aspect id used as primary
                        if dim_id in ("rhythmic_demand", "pitch_movement_demand", "hand_shape_span_demand", "texture_polyphony_demand", "coordination_demand", "notation_reading_demand", "expression_control_demand", "structural_pattern_demand", "performance_interpretive_demand"):
                            issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}].graph_dimension_id", f"Primary contributor uses legacy 9-aspect id '{dim_id}' instead of graph dimension — visible hotspots must be 6-dimension graph ranked (hotspot {hid})"))
                        else:
                            issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}].graph_dimension_id", f"Unknown graph dimension '{dim_id}' (hotspot {hid}) — expected one of {sorted(GRAPH_DIMENSION_IDS)}"))
                    # Nested micro-component feature_contributors
                    feats = c.get("feature_contributors") or c.get("supporting_feature_contributors") or c.get("graph_contributors") or []
                    if not isinstance(feats, list) or not feats:
                        issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}].feature_contributors", f"Missing nested feature_contributors (micro-components) for dimension '{dim_id}' (hotspot {hid}) — expected FEATURE_TO_DIMENSION_WEIGHTS feature IDs"))
                    else:
                        for f_idx, f in enumerate(feats[:2]):
                            if not isinstance(f, dict):
                                continue
                            fid = f.get("feature_id")
                            if not fid or "." not in str(fid):
                                issues.append(Issue(piece_id, f"{ctx}.top_contributors[{c_idx}].feature_contributors[{f_idx}].feature_id", f"feature_contributor missing valid micro-component feature_id (expected 'family.feature', got '{fid}') (hotspot {hid})"))
                    # Check contribution_share exists
                    if c.get("contribution_share") is None and c.get("share") is None:
                        # warn not error — but ensure at least one indicator
                        pass
                # Enforce that hotspot method is graph composite
                method = h.get("method") or ""
                if "graph_composite" not in str(method) and "graph" not in str(method).lower():
                    # If method indicates aspect_composite, flag as error because visible hotspots must be graph-based
                    if "aspect_composite" in str(method):
                        issues.append(Issue(piece_id, f"{ctx}.method", f"Visible hotspot method '{method}' is aspect-based — must be graph composite (graph_composite_top_n.v1) (hotspot {hid})"))
            # Check supporting_dimension_ids vs legacy aspect ids
            supp_dims = h.get("supporting_dimension_ids") or h.get("supporting_graph_dimension_ids") or []
            if isinstance(supp_dims, list) and supp_dims:
                for sid in supp_dims:
                    if sid not in GRAPH_DIMENSION_IDS:
                        if sid in ("rhythmic_demand", "pitch_movement_demand"):
                            issues.append(Issue(piece_id, f"{ctx}.supporting_dimension_ids", f"supporting ids contain legacy 9-aspect '{sid}' instead of graph dimensions (hotspot {hid})", severity="warning"))

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
    p = argparse.ArgumentParser(description="Validate David demo readiness (12-piece static walkthrough)")
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
