"""Focused tests for the CEO demo readiness validator (stdlib-only, no recompute)."""

from __future__ import annotations

import json
import copy
from pathlib import Path
import sys

import pytest

# Ensure validator importable
REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = REPO_ROOT / "research" / "learning_support" / "ceo_demo" / "scripts"
if str(VALIDATOR_PATH) not in sys.path:
    sys.path.insert(0, str(VALIDATOR_PATH))

import validate_demo_readiness as vdr  # type: ignore

EXPECTED = vdr.EXPECTED_PIECE_IDS


def _valid_pieces_entry(piece_id: str) -> dict:
    dataset = "oktav" if piece_id in vdr.OKTAV_IDS else "cipi"
    base = {
        "id": piece_id,
        "title": f"Title {piece_id}",
        "composer": "Composer",
        "dataset": dataset,
        "dataset_id": f"id-{piece_id}",
        "dataset_relative_path": f"pieces/{piece_id}.musicxml",
        "manifest_url": f"../artifacts/{piece_id}/demo_manifest.json",
        "artifact_base": f"../artifacts/{piece_id}/",
        "status": "ready",
    }
    if dataset == "oktav":
        # mapping from validator ok: Oktav needs original dataset label phrasing
        label_map = {
            "oktav_le_onde": "Oktav 43 (original dataset label; not a Gradus grade)",
            "oktav_a_thousand_miles": "Oktav 53 (original dataset label; not a Gradus grade)",
            "oktav_viva_la_vida": "Oktav 55 (original dataset label; not a Gradus grade)",
        }
        base["difficulty_label"] = label_map.get(piece_id, "Oktav 50 (original dataset label; not a Gradus grade)")
    return base


def _valid_pieces_json() -> dict:
    return {
        "generated_at": "2026-09-15T00:00:00Z",
        "schema_version": "ceo_demo_pieces.v1",
        "pieces": [_valid_pieces_entry(pid) for pid in EXPECTED],
    }


def _aspect(aspect_id: str, readiness: str = "ready") -> dict:
    return {
        "aspect_id": aspect_id,
        "id": aspect_id,
        "label": aspect_id.replace("_", " ").title(),
        "readiness": readiness,
        "availability": readiness,
        "description": "test",
        "included_feature_ids": [f"feat.{aspect_id}"],
        "feature_ids": [f"feat.{aspect_id}"],
        "limitations": [],
    }


NINE_ASPECT_IDS = [
    "rhythmic_demand",
    "pitch_movement_demand",
    "hand_shape_span_demand",
    "texture_polyphony_demand",
    "coordination_demand",
    "notation_reading_demand",
    "expression_control_demand",
    "structural_pattern_demand",
    "performance_interpretive_demand",
]


def _valid_aspects_payload() -> dict:
    aspects = [_aspect(aid) for aid in NINE_ASPECT_IDS]
    # blocked/caveated aspects still count; keep ready for simplicity
    aspects[7]["readiness"] = "blocked"
    aspects[8]["readiness"] = "caveated"
    return {
        "schema_version": "difficulty_aspects.v1",
        "profile_version": "test",
        "aspect_count": 9,
        "aspects": aspects,
        "diagnostics": [],
        "warnings": [],
        "interpretation": "test interpretation",
    }


def _valid_chart(num_regions: int = 5) -> dict:
    regions = [
        {"window_index": i, "measure_numbers": [i + 1], "measure_label": f"Measures {i+1}", "start_offset": f"0:{i}", "end_offset": f"0:{i+1}"}
        for i in range(num_regions)
    ]
    series = {}
    for aid in NINE_ASPECT_IDS:
        series[aid] = {
            "aspect_id": aid,
            "feature_id": aid,
            "id": aid,
            "label": aid,
            "feature_name": aid,
            "units": "normalized_score",
            "blocked": aid == "structural_pattern_demand",
            "caveated": aid == "performance_interpretive_demand",
            "readiness": "blocked" if aid == "structural_pattern_demand" else "ready",
            "availability": "blocked" if aid == "structural_pattern_demand" else "ready",
            "raw_values": [0.5] * num_regions,
            "normalized_values": [0.5] * num_regions,
            "smoothed_values": [0.5] * num_regions,
            "missing_region_indices": [],
            "limitations": [],
            "missing_features": [],
        }
    return {
        "hand_mode": "both",
        "window": {"kind": "measure", "size": 2, "step": 1},
        "regions": regions,
        "series": series,
        "composite": {
            "feature_id": "composite.aspect_demand",
            "aspect_id": "composite.aspect_demand",
            "label": "Overall aspect demand",
            "feature_name": "Overall aspect demand",
            "units": "normalized_score",
            "raw_values": [0.5] * num_regions,
            "normalized_values": [0.5] * num_regions,
            "smoothed_values": [0.5] * num_regions,
            "missing_region_indices": [],
        },
        "factor_ids": list(NINE_ASPECT_IDS),
        "aspect_ids": list(NINE_ASPECT_IDS),
        "references": {"analysis_csv": "analysis.csv", "analysis_json": "analysis.json"},
    }


def _valid_hotspot(rank: int = 1) -> dict:
    return {
        "id": f"aspect_section:both:0:{rank}",
        "section_id": f"aspect_section:both:0:{rank}",
        "hotspot_id": f"aspect_section:both:0:{rank}",
        "rank": rank,
        "measure_numbers": [1, 2],
        "measure_range": "1-2",
        "label": "Measures 1-2",
        "start_offset": "0:0",
        "end_offset": "0:2",
        "score_position": 0.0,
        "score_value": 0.5,
        "method": "test",
        "supporting_window_indices": [0],
        "supporting_factor_ids": ["rhythmic_demand"],
        "supporting_aspect_ids": ["rhythmic_demand"],
        "representative_region": {"window_index": 0, "measure_numbers": [1], "start_offset": "0:0", "end_offset": "0:1"},
        "top_contributors": [
            {
                "aspect_id": "rhythmic_demand",
                "feature_id": "rhythmic_demand",
                "label": "Rhythmic demand",
                "rank": 1,
                "contribution_share": 0.5,
                "normalized_value": 0.5,
                "weighted_value": 0.5,
                "readiness": "ready",
            }
        ],
        "aspect_contributors": [
            {
                "aspect_id": "rhythmic_demand",
                "feature_id": "rhythmic_demand",
                "label": "Rhythmic demand",
                "rank": 1,
                "contribution_share": 0.5,
                "normalized_value": 0.5,
                "weighted_value": 0.5,
                "readiness": "ready",
            }
        ],
        "snippet_image": None,
        "snippet_status": "not_rendered",
        "snippet_diagnostic": "Snippet rendering deferred; no image generated.",
    }


def _valid_manifest(piece_id: str) -> dict:
    return {
        "schema_version": "ceo_demo_manifest.v1",
        "demo_id": piece_id,
        "id": piece_id,
        "piece_id": piece_id,
        "generated_at": "2026-09-15T00:00:00Z",
        "piece": {
            "title": f"Title {piece_id}",
            "composer": "Composer",
            "demo_id": piece_id,
            "id": piece_id,
            "piece_id": piece_id,
            "dataset": "oktav" if piece_id in vdr.OKTAV_IDS else "cipi",
            "dataset_id": f"id-{piece_id}",
            "dataset_relative_path": f"pieces/{piece_id}.musicxml",
            "source_score_path": f"research/learning_support/ceo_demo/data/source_scores/{piece_id}.musicxml",
            "canonical_filename": f"{piece_id}.musicxml",
            "measure_count": 10,
            "written_note_count": 100,
            "logical_note_count": 100,
        },
        "artifacts": {"analysis.json": "analysis.json", "demo_manifest.json": "demo_manifest.json"},
        "chart": _valid_chart(),
        "hotspots": [_valid_hotspot(rank=i) for i in range(1, 4)],
        "caveats": [
            "Symbolic-score demo evidence only; no calibrated learner grade.",
            "No measured learning benefit; no pedagogical diagnosis.",
            "No production score-viewer claim; future snippet images are pre-rendered.",
            "Ornamental timing is approximate in symbolic data; rubato and tone are out of scope.",
            "Relative score demands within this piece; no calibrated difficulty grade.",
        ],
        "diagnostics": ["test diagnostic"],
        "warnings": [],
        "methods": {"hand_mode": "both", "window": {"kind": "measure", "size": 2}},
        "snippet_status": "not_rendered",
        "snippet_diagnostic": "Snippet images not yet rendered; demo_manifest.json reserves snippet_image/snippet_status per hotspot.",
        "difficulty_aspects": _valid_aspects_payload(),
        "aspects": _valid_aspects_payload(),
        "aspects_schema_version": "difficulty_aspects.v1",
        "aspects_profile_version": "test",
        "interpretation": "Relative score demands within this piece; no calibrated difficulty grade.",
        "hand_mode": "both",
    }


# ---------------------------------------------------------------------------
# pieces.json validation tests
# ---------------------------------------------------------------------------


def test_pieces_json_valid_passes(tmp_path: Path) -> None:
    pj = tmp_path / "pieces.json"
    pj.write_text(json.dumps(_valid_pieces_json()), encoding="utf-8")
    data, issues = vdr.validate_pieces_json(pj)
    errors = [i for i in issues if i.severity != "warning"]
    assert errors == []
    assert data is not None


def test_pieces_json_missing_file(tmp_path: Path) -> None:
    _, issues = vdr.validate_pieces_json(tmp_path / "missing.json")
    assert any("not found" in i.message for i in issues)


def test_pieces_json_wrong_count(tmp_path: Path) -> None:
    payload = _valid_pieces_json()
    payload["pieces"] = payload["pieces"][:5]
    pj = tmp_path / "pieces.json"
    pj.write_text(json.dumps(payload), encoding="utf-8")
    _, issues = vdr.validate_pieces_json(pj)
    assert any("Expected 6 pieces" in i.message for i in issues)


def test_pieces_json_unexpected_piece_id(tmp_path: Path) -> None:
    payload = _valid_pieces_json()
    payload["pieces"][0]["id"] = "extra_piece"
    pj = tmp_path / "pieces.json"
    pj.write_text(json.dumps(payload), encoding="utf-8")
    _, issues = vdr.validate_pieces_json(pj)
    assert any("Unexpected piece id" in i.message for i in issues)
    assert any("missing from pieces.json" in i.message for i in issues)


def test_pieces_json_oktav_label_must_contain_provenance(tmp_path: Path) -> None:
    payload = _valid_pieces_json()
    # break one oktav label to be a fake grade
    for p in payload["pieces"]:
        if p["id"] == "oktav_le_onde":
            p["difficulty_label"] = "Gradus grade 7.5"
    pj = tmp_path / "pieces.json"
    pj.write_text(json.dumps(payload), encoding="utf-8")
    _, issues = vdr.validate_pieces_json(pj)
    assert any("difficulty_label" in i.field and "original dataset label" in i.message for i in issues)


def test_pieces_json_non_oktav_must_not_carry_oktav_label(tmp_path: Path) -> None:
    payload = _valid_pieces_json()
    payload["pieces"][0]["difficulty_label"] = "Oktav 99 (original dataset label; not a Gradus grade)"
    pj = tmp_path / "pieces.json"
    pj.write_text(json.dumps(payload), encoding="utf-8")
    _, issues = vdr.validate_pieces_json(pj)
    assert any("Non-Oktav" in i.message for i in issues)


# ---------------------------------------------------------------------------
# manifest validation tests
# ---------------------------------------------------------------------------


def test_manifest_valid_passes(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    manifest_path = tmp_path / "demo_manifest.json"
    manifest_path.write_text(json.dumps(_valid_manifest(piece_id)), encoding="utf-8")
    issues = vdr.validate_manifest(manifest_path, piece_id)
    errors = [i for i in issues if i.severity != "warning"]
    assert errors == [], errors


def test_manifest_missing_aspects_fails(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    del m["difficulty_aspects"]
    del m["aspects"]
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("9-aspect" in i.message for i in issues)


def test_manifest_wrong_aspect_count_fails(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["difficulty_aspects"]["aspects"] = m["difficulty_aspects"]["aspects"][:8]
    m["difficulty_aspects"]["aspect_count"] = 8
    m["aspects"] = copy.deepcopy(m["difficulty_aspects"])
    m["chart"]["series"] = {k: v for k, v in list(m["chart"]["series"].items())[:8]}
    m["chart"]["aspect_ids"] = m["chart"]["aspect_ids"][:8]
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("exactly 9 aspects" in i.message.lower() for i in issues)


def test_manifest_chart_series_must_be_9(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    # keep aspects 9 but trim chart series to 8
    del m["chart"]["series"][NINE_ASPECT_IDS[0]]
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("chart.series must contain exactly 9" in i.message for i in issues)


def test_manifest_caveats_must_contain_claim_boundaries(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["caveats"] = ["Some generic caveat"]
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("symbolic-score" in i.message.lower() for i in issues)


def test_hotspot_not_rendered_requires_diagnostic(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["hotspots"][0]["snippet_diagnostic"] = ""
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("snippet_diagnostic must be non-empty" in i.message for i in issues)


def test_hotspot_rendered_requires_existing_file(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["hotspots"][0]["snippet_status"] = "rendered"
    m["hotspots"][0]["snippet_image"] = "snippets/hotspot_001.png"
    m["hotspots"][0]["snippet_diagnostic"] = None
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("not found" in i.message for i in issues)

    # Now create the file — should pass
    (tmp_path / "snippets").mkdir()
    (tmp_path / "snippets" / "hotspot_001.png").write_bytes(b"x" * 2000)
    issues2 = vdr.validate_manifest(p, piece_id)
    errors2 = [i for i in issues2 if i.severity != "warning" and "hotspot_001" in i.message]
    assert errors2 == []


def test_hotspot_render_failed_requires_diagnostic_and_null_image(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["hotspots"][0]["snippet_status"] = "render_failed"
    m["hotspots"][0]["snippet_image"] = None
    m["hotspots"][0]["snippet_diagnostic"] = ""
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("snippet_diagnostic must be non-empty" in i.message for i in issues)

    m["hotspots"][0]["snippet_diagnostic"] = "render failed: missing mscore"
    m["hotspots"][0]["snippet_image"] = "snippets/hotspot_001.png"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("must be null when status is 'render_failed'" in i.message for i in issues)


def test_top_level_snippet_status_requires_diagnostic_when_not_rendered(tmp_path: Path) -> None:
    piece_id = EXPECTED[0]
    m = _valid_manifest(piece_id)
    m["snippet_status"] = "not_rendered"
    m["snippet_diagnostic"] = ""
    p = tmp_path / "demo_manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    issues = vdr.validate_manifest(p, piece_id)
    assert any("snippet_diagnostic must be non-empty" in i.message for i in issues)


# ---------------------------------------------------------------------------
# integration: validate_all
# ---------------------------------------------------------------------------


def _write_full_catalog(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    pieces_path = artifacts / "pieces.json"
    pieces_path.write_text(json.dumps(_valid_pieces_json()), encoding="utf-8")
    for pid in EXPECTED:
        d = artifacts / pid
        d.mkdir()
        (d / "demo_manifest.json").write_text(json.dumps(_valid_manifest(pid)), encoding="utf-8")
    return pieces_path


def test_validate_all_ready(tmp_path: Path) -> None:
    pieces_path = _write_full_catalog(tmp_path)
    report = vdr.validate_all(pieces_path)
    assert report.ok
    assert report.ready_count == 6
    assert report.total_expected == 6


def test_validate_all_fails_when_manifest_missing(tmp_path: Path) -> None:
    pieces_path = _write_full_catalog(tmp_path)
    # remove one manifest
    (tmp_path / "artifacts" / EXPECTED[1] / "demo_manifest.json").unlink()
    report = vdr.validate_all(pieces_path)
    assert not report.ok
    assert report.ready_count == 5


def test_format_report_json(tmp_path: Path) -> None:
    pieces_path = _write_full_catalog(tmp_path)
    report = vdr.validate_all(pieces_path)
    out = vdr.format_report(report, use_json=True)
    data = json.loads(out)
    assert data["ok"] is True
    assert data["ready"] == "6/6"
    assert len(data["pieces"]) == 6


def test_real_artifacts_pass() -> None:
    # Validate the actual shipped artifacts (if present)
    real_pieces = REPO_ROOT / "research" / "learning_support" / "ceo_demo" / "artifacts" / "pieces.json"
    if not real_pieces.is_file():
        pytest.skip("real artifacts not present")
    report = vdr.validate_all(real_pieces)
    # Report should be ready with current artifacts (snippets are not_rendered with diagnostic)
    assert report.ok, "\n".join(f"{i.field}: {i.message}" for i in report.global_errors + [e for r in report.piece_results for e in r.errors])
    assert report.ready_count == 6
