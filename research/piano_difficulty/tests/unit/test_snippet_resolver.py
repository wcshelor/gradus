from __future__ import annotations

from pathlib import Path

from piano_difficulty.output.snippet_resolver import (
    enrich_payload_with_snippets,
    enrich_hotspot_with_snippet,
    resolve_snippet_for_hotspot,
    snippet_filename,
    snippet_relative_path,
)


def _hotspot(window_index=2, measure_numbers=None, extra=None):
    if measure_numbers is None:
        measure_numbers = [5, 6]
    base = {
        "window_index": window_index,
        "measure_numbers": list(measure_numbers),
        "measure_range": f"{measure_numbers[0]}-{measure_numbers[-1]}" if len(measure_numbers) > 1 else str(measure_numbers[0]),
        "region": {"window_index": window_index, "measure_numbers": [str(x) for x in measure_numbers]},
    }
    if extra:
        base.update(extra)
    return base


def test_snippet_filename_stable_pattern():
    assert snippet_filename(2, ["5", "6"]) == "window_002__measures_5-6.png"
    assert snippet_filename(0, ["3"]) == "window_000__measures_3.png"
    assert snippet_filename(None, ["1", "2"]) == "window_000__measures_1-2.png"
    assert snippet_relative_path(2, ["5", "6"]) == "snippets/window_002__measures_5-6.png"


def test_existing_png_is_available(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    png = snippets / "window_002__measures_5-6.png"
    png.write_bytes(b"x" * 3000)
    hs = _hotspot(window_index=2, measure_numbers=[5, 6])
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=None, renderer=None, allow_render=True)
    assert res.snippet_status == "available"
    assert res.snippet_image == "snippets/window_002__measures_5-6.png"
    assert res.snippet_measure_numbers == ["5", "6"]
    assert res.snippet_measure_index_range == "5-6"
    assert res.absolute_path == png
    assert res.snippet_diagnostic is not None and "Reused" in res.snippet_diagnostic


def test_missing_renders_and_caches(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    src = tmp_path / "piece.musicxml"
    src.write_text("<score/>")

    def fake_renderer(s, d, h):
        Path(d).write_bytes(b"y" * 2500)

    hs = _hotspot(window_index=1, measure_numbers=[1, 2])
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=src, renderer=fake_renderer, allow_render=True)
    assert res.snippet_status == "rendered"
    assert res.snippet_image == "snippets/window_001__measures_1-2.png"
    assert res.snippet_diagnostic is None
    dest = snippets / "window_001__measures_1-2.png"
    assert dest.is_file()

    # second call reuses without calling renderer
    def fail_renderer(s, d, h):
        raise AssertionError("should not be called")

    res2 = resolve_snippet_for_hotspot(hs, snippets, source_score=src, renderer=fail_renderer, allow_render=True)
    assert res2.snippet_status == "available"


def test_missing_source_returns_missing_source(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    hs = _hotspot()
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=None, renderer=lambda s, d, h: None, allow_render=True)
    assert res.snippet_status == "missing_source"
    assert res.snippet_image is None
    assert "Source score" in res.snippet_diagnostic

    missing = tmp_path / "nope.musicxml"
    res2 = resolve_snippet_for_hotspot(hs, snippets, source_score=missing, renderer=lambda s, d, h: None, allow_render=True)
    assert res2.snippet_status == "missing_source"


def test_renderer_failure_returns_render_failed(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    src = tmp_path / "piece.musicxml"
    src.write_text("<score/>")

    def bad_renderer(s, d, h):
        raise RuntimeError("boom pdf")

    hs = _hotspot()
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=src, renderer=bad_renderer, allow_render=True)
    assert res.snippet_status == "render_failed"
    assert res.snippet_image is None
    assert "boom" in res.snippet_diagnostic
    # hotspot still usable — no exception
    hs2 = _hotspot()
    enrich_hotspot_with_snippet(hs2, snippets, src, bad_renderer, allow_render=True)
    assert hs2["snippet_status"] == "render_failed"
    assert hs2["snippet_diagnostic"] is not None
    assert hs2["snippet_measure_numbers"] == ["5", "6"]


def test_missing_renderer_returns_render_failed(tmp_path: Path):
    snippets = tmp_path / "snippets"
    src = tmp_path / "piece.musicxml"
    src.write_text("<score/>")
    hs = _hotspot()
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=src, renderer=None, allow_render=True)
    assert res.snippet_status == "render_failed"
    assert "No renderer" in res.snippet_diagnostic


def test_not_requested_when_disabled(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    hs = _hotspot()
    res = resolve_snippet_for_hotspot(hs, snippets, source_score=None, renderer=None, allow_render=False)
    assert res.snippet_status == "not_requested"
    assert res.snippet_image is None
    assert "not" in res.snippet_diagnostic.lower()

    hs2 = {}
    res2 = resolve_snippet_for_hotspot(hs2, snippets, source_score=None, renderer=None, allow_render=True)
    assert res2.snippet_status == "not_requested"


def test_enrich_payload_with_snippets_available(tmp_path: Path):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    (snippets / "window_000__measures_1-2.png").write_bytes(b"z" * 3000)
    payload = {
        "analysis_profiles": [
            {
                "profile_id": "difficulty_overview",
                "candidate_sections": [
                    {"window_index": 0, "measure_numbers": ["1", "2"], "rank": 1, "region": {"window_index": 0, "measure_numbers": ["1", "2"]}},
                ],
                "hand_views": {},
            },
            {
                "profile_id": "difficulty_aspects",
                "hotspots": [
                    {"window_index": 0, "measure_numbers": ["1", "2"], "rank": 1, "region": {"window_index": 0, "measure_numbers": ["1", "2"]}},
                ],
            },
        ]
    }
    enrich_payload_with_snippets(payload, snippets, source_score=None, renderer=None, allow_render=False)
    assert payload["analysis_profiles"][0]["candidate_sections"][0]["snippet_status"] == "available"
    assert payload["analysis_profiles"][0]["candidate_sections"][0]["snippet_image"] == "snippets/window_000__measures_1-2.png"
    assert payload["analysis_profiles"][0]["candidate_sections"][0]["snippet_measure_numbers"] == ["1", "2"]
    assert payload["analysis_profiles"][0]["candidate_sections"][0]["snippet_measure_index_range"] == "1-2"
    assert payload["analysis_profiles"][1]["hotspots"][0]["snippet_status"] == "available"


def test_enrich_payload_graceful_on_render_failed(tmp_path: Path):
    snippets = tmp_path / "snippets"
    src = tmp_path / "piece.musicxml"
    src.write_text("<score/>")

    def bad(s, d, h):
        raise RuntimeError("no mscore")

    payload = {
        "analysis_profiles": [
            {
                "profile_id": "difficulty_overview",
                "candidate_sections": [
                    {"window_index": 1, "measure_numbers": ["3"], "rank": 1, "region": {"window_index": 1, "measure_numbers": ["3"]}},
                ],
            }
        ]
    }
    enrich_payload_with_snippets(payload, snippets, source_score=src, renderer=bad, allow_render=True)
    sec = payload["analysis_profiles"][0]["candidate_sections"][0]
    assert sec["snippet_status"] == "render_failed"
    assert sec["snippet_image"] is None
    assert sec["snippet_diagnostic"]
