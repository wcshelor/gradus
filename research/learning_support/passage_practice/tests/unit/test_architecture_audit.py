"""Tests for S-X6 periodic architecture audit — layer boundaries and no duplicate parsing."""

from __future__ import annotations

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "passage_practice"


def _grep_imports(subdir: str, pattern: str) -> list[str]:
    files = list((SRC / subdir).rglob("*.py"))
    hits: list[str] = []
    regex = re.compile(pattern)
    for p in files:
        text = p.read_text()
        if regex.search(text):
            hits.append(str(p))
    return hits


def test_semantics_does_not_import_pedagogy_or_learner():
    hits = _grep_imports("semantics", r"from passage_practice\.(pedagogy|learner)")
    assert hits == [], f"semantics must not import pedagogy/learner: {hits}"
    hits2 = _grep_imports("semantics", r"import.*piano_difficulty\.io")
    assert hits2 == [], f"semantics must not directly parse MusicXML: {hits2}"
    hits3 = _grep_imports("semantics", r"ElementTree")
    assert hits3 == [], f"semantics must not use ElementTree: {hits3}"


def test_observations_does_not_import_semantics():
    hits = _grep_imports("observations", r"from passage_practice\.semantics")
    assert hits == [], f"observations must not import semantics: {hits}"


def test_corpus_does_not_duplicate_parsing():
    hits = _grep_imports("corpus", r"load_musicxml_document|ElementTree")
    assert hits == [], f"corpus must not duplicate parsing: {hits}"


def test_no_code_in_shared_prematurely():
    # Only check that helpers are not in research/shared but here
    shared = pathlib.Path(__file__).resolve().parents[5] / "research" / "shared"
    # If shared exists, ensure no passage_practice-specific code was moved
    if shared.exists():
        shared_files = list(shared.rglob("*.py"))
        for p in shared_files:
            text = p.read_text()
            assert "passage_practice" not in text or "shared" in text, f"unexpected passage_practice code in shared: {p}"


def test_audit_doc_exists():
    doc = pathlib.Path(__file__).resolve().parents[2] / "docs" / "architecture_audit_S8.md"
    assert doc.exists(), f"missing architecture audit {doc}"
    text = doc.read_text()
    assert "Layer boundary checks" in text
    assert "PASS" in text
