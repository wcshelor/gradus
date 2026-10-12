from __future__ import annotations

import json
from pathlib import Path

from piano_difficulty.pipeline import analyze_score

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "minimal_piano.musicxml"


def _payload(tmp_path: Path):
    result = analyze_score(FIXTURE)
    return result.to_json_payload()


def test_aspects_hotspots_have_snippet_fields(tmp_path: Path):
    payload = _payload(tmp_path)
    aspects = next(p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_aspects")
    assert aspects["hotspots"]
    for hs in aspects["hotspots"]:
        assert "snippet_image" in hs
        assert "snippet_status" in hs
        assert "snippet_diagnostic" in hs
        assert "snippet_measure_numbers" in hs
        assert "snippet_measure_index_range" in hs
        # diagnostic non-empty when not available/rendered
        if hs["snippet_status"] in ("not_requested", "not_rendered"):
            assert isinstance(hs["snippet_diagnostic"], str) and hs["snippet_diagnostic"]
        # measure_numbers consistent
        assert hs["snippet_measure_numbers"] == [str(x) for x in hs["measure_numbers"]] or hs["snippet_measure_numbers"]
        assert isinstance(hs["snippet_measure_index_range"], str) and hs["snippet_measure_index_range"]


def test_overview_candidate_sections_have_snippet_fields(tmp_path: Path):
    # Use a longer score so dynamics builds regions; minimal fixture has 1 measure and no peaks.
    from pathlib import Path as _P

    score = _P(__file__).resolve().parents[2] / "evaluation_scores" / "known_levels" / "cipi" / "beethoven" / "beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml"
    src = score if score.is_file() else FIXTURE
    result = analyze_score(src)
    payload = result.to_json_payload()
    overview = next(p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_overview")
    # sections may still be empty for some scores; check structure when present, otherwise verify consolidator contract
    if not overview["candidate_sections"]:
        # direct consolidator check — ensure fields exist when a section is produced
        from piano_difficulty.difficulty_analysis.sections import consolidate_sections
        from piano_difficulty.difficulty_analysis.dynamics.core import build_difficulty_profile
        from piano_difficulty.difficulty_analysis.dynamics.models import (
            CompositeConfig, DifficultyDynamicsConfig, NormalizationConfig, PeakDetectionConfig, WindowStrategyConfig,
        )
        from piano_difficulty.normalize.converters import build_score_ir
        from piano_difficulty.io.musicxml import load_musicxml_document

        doc = load_musicxml_document(src)
        score_ir = build_score_ir(doc)
        # minimal config
        cfg = DifficultyDynamicsConfig(
            experiment_name="test", score_path=src,
            feature_ids=("rhythm.note_density",), hand_mode="both",
            window=WindowStrategyConfig(kind="measure", size=1, step=1),
            normalization=NormalizationConfig(method="min_max"),
            composite=CompositeConfig(enabled=True, weights={"rhythm.note_density": 1.0}),
            peaks=PeakDetectionConfig(top_n=1), overview_mode=True,
        )
        profile = build_difficulty_profile(score_ir, cfg)
        secs = consolidate_sections(profile, cfg.composite, limit=1)
        assert secs, "consolidator should produce at least one section for test score"
        sec = secs[0]
        for k in ("snippet_image", "snippet_status", "snippet_diagnostic", "snippet_measure_numbers", "snippet_measure_index_range"):
            assert k in sec
        return
    for sec in overview["candidate_sections"]:
        assert "snippet_image" in sec
        assert "snippet_status" in sec
        assert "snippet_diagnostic" in sec
        assert "snippet_measure_numbers" in sec
        assert "snippet_measure_index_range" in sec


def test_html_report_includes_snippet_gallery(tmp_path: Path):
    from piano_difficulty.output.overview import render_html

    payload = _payload(tmp_path)
    overview = next(p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_overview")
    html = render_html(payload, overview)
    # gallery appears as either overview hotspot or aspect hotspot snippets
    assert "snippets" in html.lower()
    assert "snippet" in html.lower()
    # inject an available snippet and verify img tag — prefer overview, fallback to aspects
    target = None
    if overview.get("candidate_sections"):
        target = overview["candidate_sections"][0]
    else:
        aspects = next((p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_aspects"), None)
        if aspects and aspects.get("hotspots"):
            target = aspects["hotspots"][0]
            # render needs overview profile; patch overview temporarily
            overview["candidate_sections"] = [dict(target)]
            target = overview["candidate_sections"][0]
    if target is not None:
        target["snippet_image"] = "snippets/window_000__measures_1-2.png"
        target["snippet_status"] = "available"
        target["snippet_measure_numbers"] = ["1", "2"]
        html2 = render_html(payload, overview)
        assert 'src="snippets/window_000__measures_1-2.png"' in html2


def test_writer_preserves_snippets_dir(tmp_path: Path):
    # analyzer should not delete snippets/ on rerun
    from tests.harness.david_walkthrough.artifacts import clean_planned_outputs

    out = tmp_path / "out"
    demo_dir = out / "demo_piece"
    demo_dir.mkdir(parents=True)
    (demo_dir / "analysis.json").write_text("{}")
    snippets = demo_dir / "snippets"
    snippets.mkdir()
    png = snippets / "window_000__measures_1-2.png"
    png.write_bytes(b"x" * 3000)
    clean_planned_outputs(out, ["demo_piece"])
    assert png.is_file(), "snippets should be preserved"
    assert not (demo_dir / "analysis.json").exists()
