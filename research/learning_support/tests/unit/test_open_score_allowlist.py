"""Focused tests for Open in MuseScore allowlist (local-demo only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVER_PATH = REPO_ROOT / "research" / "learning_support" / "david_demo" / "scripts"
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

import run_live_demo_server as srv  # type: ignore


def test_curated_piece_resolves_to_demo_source_dir():
    # Every curated id in CURATED_FILE_MAP should resolve to a file under data/source_scores
    for pid, fname in srv.CURATED_FILE_MAP.items():
        p = srv._resolve_curated_path(pid)
        assert p is not None, f"Expected curated {pid} to resolve"
        assert p.is_file(), f"Curated {pid} resolved to missing {p}"
        assert srv._is_allowed_path(p) is True, f"Curated {pid} not allowed"


def test_is_allowed_path_rejects_arbitrary():
    # Arbitrary system path must be blocked
    assert srv._is_allowed_path(Path("/etc/passwd")) is False
    assert srv._is_allowed_path(Path("/tmp/evil.musicxml")) is False
    # Traversal outside demo dir
    assert srv._is_allowed_path(REPO_ROOT / ".." / "etc" / "passwd") is False


def test_is_allowed_path_rejects_untrusted_relative():
    # Untrusted manifest with arbitrary absolute path not in allowed locations
    assert srv._is_allowed_path(Path(REPO_ROOT / "README.md")) is False


def test_resolve_curated_unknown_returns_none():
    assert srv._resolve_curated_path("unknown_piece_xyz") is None


def test_resolve_curated_live_manifest_on_disk(tmp_path: Path, monkeypatch):
    # Simulate a live manifest under artifacts/live/
    live_id = "live_cipi_test_piece"
    live_dir = tmp_path / "live" / live_id
    live_dir.mkdir(parents=True)
    # create a dummy source file outside demo dir
    src = tmp_path / "external_source.musicxml"
    src.write_text("<score>test</score>", encoding="utf-8")
    manifest = {
        "piece": {
            "id": live_id,
            "source_score_path": str(src),
        }
    }
    (live_dir / "demo_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    # monkeypatch LIVE_BASE and ARTIFACTS_BASE
    monkeypatch.setattr(srv, "LIVE_BASE", tmp_path / "live")
    monkeypatch.setattr(srv, "ARTIFACTS_BASE", tmp_path)
    # resolving live_id should find the external source via manifest
    resolved = srv._resolve_curated_path(live_id)
    assert resolved is not None
    assert resolved.resolve() == src.resolve()
    # allowlist should permit it via LIVE_BASE manifest scanning
    assert srv._is_allowed_path(src) is True


def test_resolve_source_score_path_raw_rejects_url():
    assert srv._resolve_source_score_path_raw("https://example.com/score.xml") is None
    assert srv._resolve_source_score_path_raw("file://evil") is None
    # control chars
    assert srv._resolve_source_score_path_raw("bad\npath") is None


def test_resolve_source_score_path_raw_allows_curated_relative():
    rel = "research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml"
    p = srv._resolve_source_score_path_raw(rel)
    assert p is not None and p.is_file()
    assert srv._is_allowed_path(p) is True
