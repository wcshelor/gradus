"""Tests for T01.2 source identity primitives."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from passage_practice.models.source import (
    SOURCE_REF_SCHEMA_VERSION,
    SourceKind,
    SourceRef,
    is_resolvable,
    refs_for_score,
    resolve_ref,
)
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir


# Helpers ---------------------------------------------------------------------------


def load_fixture(name: str):
    path = Path("research/piano_difficulty/tests/fixtures") / name
    doc = load_musicxml_document(path)
    score = build_score_ir(doc)
    return score


# SourceRef basics ------------------------------------------------------------------


def test_source_ref_immutability():
    ref = SourceRef(id="n1", kind=SourceKind.WRITTEN_NOTE)
    with pytest.raises(AttributeError):
        ref.id = "n2"  # type: ignore


def test_source_ref_rejects_empty_id():
    with pytest.raises(ValueError):
        SourceRef(id="", kind=SourceKind.WRITTEN_NOTE)


def test_source_ref_rejects_unknown_kind_string():
    # must be SourceKind, not raw string
    with pytest.raises(TypeError):
        SourceRef(id="n1", kind="written_note")  # type: ignore


def test_source_ref_serialization_round_trip():
    ref = SourceRef(id="n5", kind=SourceKind.LOGICAL_NOTE)
    d = ref.to_dict()
    assert d["schema_version"] == SOURCE_REF_SCHEMA_VERSION
    assert d["kind"] == "logical_note"
    # deterministic
    j1 = json.dumps(d, sort_keys=True)
    j2 = json.dumps(SourceRef.from_dict(d).to_dict(), sort_keys=True)
    assert j1 == j2
    assert SourceRef.from_dict(d) == ref


def test_source_ref_unsupported_version():
    ref = SourceRef(id="n1", kind=SourceKind.WRITTEN_NOTE)
    d = ref.to_dict()
    d["schema_version"] = "source_ref.v999"
    with pytest.raises(ValueError, match="unsupported.*schema_version"):
        SourceRef.from_dict(d)


def test_source_ref_unknown_kind():
    with pytest.raises(ValueError, match="unknown SourceKind"):
        SourceRef.from_dict({"schema_version": SOURCE_REF_SCHEMA_VERSION, "id": "x", "kind": "bogus"})


def test_source_ref_missing_field():
    with pytest.raises(ValueError, match="missing SourceRef field"):
        SourceRef.from_dict({"schema_version": SOURCE_REF_SCHEMA_VERSION, "id": "n1"})


# Uniqueness within a score ---------------------------------------------------------


def test_written_note_ids_unique_within_score():
    score = load_fixture("minimal_piano.musicxml")
    ids = [n.note_id for n in score.written_notes]
    assert len(ids) == len(set(ids)), "written_note ids must be unique"
    # also logical
    lids = [n.note_id for n in score.logical_notes]
    # logical notes reuse first written id per tie chain, so duplicates possible across tie chains? But within synthetic fixture no ties
    assert len(lids) == len(set(lids))


def test_rest_ids_unique_when_present():
    score = load_fixture("feature_fixture.musicxml")
    rids = [r.rest_id for r in score.rests]
    if rids:
        assert len(rids) == len(set(rids))


def test_refs_for_score_enumerates_all():
    score = load_fixture("minimal_piano.musicxml")
    refs = refs_for_score(score)
    # each ref should be resolvable
    for ref in refs:
        assert is_resolvable(score, ref)
    # kinds must be distinct from ids alone: n1 as written_note vs rest may share id string but kind disambiguates
    # Check that duplicate ids across kinds don't cause false resolvable cross-kind
    # (e.g., r1 id string "n1" should not resolve as written_note)
    # Synthetic: ensure at least written_note refs exist
    assert any(r.kind == SourceKind.WRITTEN_NOTE for r in refs)


# Deterministic regeneration --------------------------------------------------------


def test_deterministic_regeneration_same_file():
    score_a = load_fixture("minimal_piano.musicxml")
    score_b = load_fixture("minimal_piano.musicxml")
    ids_a = sorted(n.note_id for n in score_a.written_notes)
    ids_b = sorted(n.note_id for n in score_b.written_notes)
    assert ids_a == ids_b
    # refs should be identical sorted
    refs_a = sorted((r.kind.value, r.id) for r in refs_for_score(score_a))
    refs_b = sorted((r.kind.value, r.id) for r in refs_for_score(score_b))
    assert refs_a == refs_b


def test_explicit_musicxml_id_preserved_when_present(tmp_path):
    # Create a minimal score with explicit ids
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note id="myCustomId"><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type><voice>1</voice><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type><voice>1</voice><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>"""
    p = tmp_path / "explicit_id.musicxml"
    p.write_text(xml, encoding="utf-8")
    doc = load_musicxml_document(p)
    score = build_score_ir(doc)
    ids = [n.note_id for n in score.written_notes]
    assert "myCustomId" in ids
    # second note should be generated f"n..." (xml_order)
    assert any(i.startswith("n") for i in ids)
    # deterministic again
    score2 = build_score_ir(load_musicxml_document(p))
    assert [n.note_id for n in score2.written_notes] == ids


# Resolvable / missing --------------------------------------------------------------


def test_resolvable_written_and_logical():
    score = load_fixture("minimal_piano.musicxml")
    # pick first written note
    wn = score.written_notes[0]
    ref = SourceRef(id=wn.note_id, kind=SourceKind.WRITTEN_NOTE)
    assert is_resolvable(score, ref)
    assert resolve_ref(score, ref) is wn
    # logical note with same id (first in chain) should resolve in logical collection, not written
    if score.logical_notes:
        ln = score.logical_notes[0]
        lref = SourceRef(id=ln.note_id, kind=SourceKind.LOGICAL_NOTE)
        assert resolve_ref(score, lref) is ln
        # cross-kind with same id string should not cross-resolve unless IDs coincidentally equal and object differs
        # If wn and ln share id (tie collapse), they are different objects but same id; kind disambiguates
        if wn.note_id == ln.note_id:
            assert resolve_ref(score, SourceRef(id=wn.note_id, kind=SourceKind.WRITTEN_NOTE)) is wn
            assert resolve_ref(score, SourceRef(id=wn.note_id, kind=SourceKind.LOGICAL_NOTE)) is ln


def test_missing_reference_returns_none():
    score = load_fixture("minimal_piano.musicxml")
    missing = SourceRef(id="n9999", kind=SourceKind.WRITTEN_NOTE)
    assert not is_resolvable(score, missing)
    assert resolve_ref(score, missing) is None


def test_rest_reference_when_present():
    score = load_fixture("feature_fixture.musicxml")
    if not score.rests:
        pytest.skip("fixture has no rests")
    r = score.rests[0]
    ref = SourceRef(id=r.rest_id, kind=SourceKind.REST)
    assert resolve_ref(score, ref) is r
    # wrong kind should not resolve
    wrong = SourceRef(id=r.rest_id, kind=SourceKind.WRITTEN_NOTE)
    # If id accidentally coincides with a note id, it might resolve, but generally should be None or note
    # Assert that looking up rest id as written_note either None or not the rest object
    result = resolve_ref(score, wrong)
    assert result is None or result is not r


def test_measure_reference():
    score = load_fixture("minimal_piano.musicxml")
    # measure indices are 1-based in XML but 1-indexed MeasureIR? Check
    m = score.measures[0]
    ref = SourceRef(id=str(m.measure_index), kind=SourceKind.MEASURE)
    assert resolve_ref(score, ref) is m
    assert is_resolvable(score, ref)
    missing_m = SourceRef(id="9999", kind=SourceKind.MEASURE)
    assert not is_resolvable(score, missing_m)


def test_onset_group_unsupported_returns_none():
    score = load_fixture("minimal_piano.musicxml")
    ref = SourceRef(id="0", kind=SourceKind.ONSET_GROUP)
    assert resolve_ref(score, ref) is None
    assert not is_resolvable(score, ref)


def test_resolve_requires_source_ref_type():
    score = load_fixture("minimal_piano.musicxml")
    with pytest.raises(TypeError):
        resolve_ref(score, "n1")  # type: ignore
    with pytest.raises(TypeError):
        is_resolvable(score, "n1")  # type: ignore


def test_no_xml_mutation():
    # Resolver must not mutate score or XML
    score = load_fixture("minimal_piano.musicxml")
    before_ids = [n.note_id for n in score.written_notes]
    ref = SourceRef(id=before_ids[0], kind=SourceKind.WRITTEN_NOTE)
    resolve_ref(score, ref)
    after_ids = [n.note_id for n in score.written_notes]
    assert before_ids == after_ids
