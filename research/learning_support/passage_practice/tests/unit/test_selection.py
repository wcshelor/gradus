"""Tests for WP-02 T02.2-T02.5 exact passage selection and context."""

from __future__ import annotations

import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import PassagePurpose
from passage_practice.models.source import SourceKind
from passage_practice.passages.selection import (
    SELECTED_PASSAGE_SCHEMA_VERSION,
    SelectedPassage,
    UnresolvableRegion,
    locate_measure_by_number,
    refine_selection,
    select_passage,
    whole_piece_range,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


# T02.2 loader smoke + provenance -----------------------------------------------


def test_fixture_manifest_lists_all_fixtures():
    manifest = (FIXTURES / "manifest.md").read_text()
    for name in (
        "selection_two_staff.musicxml",
        "selection_ties.musicxml",
        "selection_two_voices.musicxml",
    ):
        assert name in manifest
        assert (FIXTURES / name).is_file()


def test_loader_smoke_counts_and_tie_collapse():
    two_staff = _load("selection_two_staff.musicxml")
    assert len(two_staff.measures) == 2
    assert len(two_staff.written_notes) == 10
    ties = _load("selection_ties.musicxml")
    tied = [n for n in ties.logical_notes if set(n.source_note_ids) == {"n4", "n5"}]
    assert len(tied) == 1 and tied[0].onset == Fraction(4, 1)
    voices = _load("selection_two_voices.musicxml")
    assert {n.voice for n in voices.written_notes} == {"1", "2"}


# T02.3 boundaries ---------------------------------------------------------------


def test_start_included_end_excluded_two_staves():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1)
    )
    ids = [r.id for r in selected.passage.event_refs]
    assert ids == ["n1", "n5", "n2", "n3", "n4"]  # onset, then document order
    assert all(r.kind == SourceKind.LOGICAL_NOTE for r in selected.passage.event_refs)
    assert selected.passage.start.quarters == Fraction(0, 1)
    assert selected.passage.end.quarters == Fraction(4, 1)
    assert selected.passage.start.measure_number == "1"
    assert selected.passage.end.measure_number == "2"  # half-open end


def test_second_measure_excludes_ended_attack():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(4, 1), end=Fraction(8, 1)
    )
    ids = [r.id for r in selected.passage.event_refs]
    assert ids == ["n6", "n10", "n7", "n8", "n9"]
    # LH C3 (n5) ends exactly at 4: half-open end, no crossing, no context.
    assert "n5" not in ids
    assert selected.boundary_context == ()


def test_note_sustaining_across_end_is_boundary_context():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(3, 1)
    )
    assert [r.id for r in selected.passage.event_refs] == ["n1", "n5", "n2", "n3"]
    # LH C3 (0..4) sustains across 3: context, not a new attack.
    assert [r.id for r in selected.boundary_context] == ["n5"]


def test_tie_chain_counts_once_with_sustain_context():
    score = _load("selection_ties.musicxml")
    first = select_passage(
        score, score_id="ties", start=Fraction(3, 1), end=Fraction(8, 1)
    )
    assert [r.id for r in first.passage.event_refs] == ["n4", "n6"]
    assert [r.id for r in first.boundary_context] == ["n3"]  # E4 (2..4) crosses 3
    assert all(r.kind == SourceKind.WRITTEN_NOTE for r in first.boundary_context)
    second = select_passage(
        score, score_id="ties", start=Fraction(4, 1), end=Fraction(8, 1)
    )
    assert [r.id for r in second.passage.event_refs] == ["n4", "n6"]
    assert "n5" not in [r.id for r in second.passage.event_refs]


def test_empty_selection_is_explicit_valid_result():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(7, 2), end=Fraction(4, 1)
    )
    assert selected.passage.event_refs == ()
    assert any(d.code == "empty_selection" for d in selected.diagnostics)


def test_source_score_is_never_mutated():
    score = _load("selection_two_staff.musicxml")
    before = copy.deepcopy(score)
    select_passage(score, score_id="two-staff", start=Fraction(1, 1), end=Fraction(6, 1))
    assert score == before


def test_selection_round_trip_deterministic():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1)
    )
    data = selected.to_dict()
    assert data["schema_version"] == SELECTED_PASSAGE_SCHEMA_VERSION
    assert _dump(data) == _dump(SelectedPassage.from_dict(data).to_dict())
    assert "rests" in selected.passage.omissions


def test_rejects_malformed_and_unlocatable_bounds():
    score = _load("selection_two_staff.musicxml")
    with pytest.raises(UnresolvableRegion) as exc:
        select_passage(score, score_id="s", start=Fraction(4, 1), end=Fraction(4, 1))
    assert exc.value.reason == "empty_interval"
    with pytest.raises(UnresolvableRegion) as exc:
        select_passage(score, score_id="s", start=Fraction(0, 1), end=Fraction(99, 1))
    assert exc.value.reason == "out_of_range"
    with pytest.raises(UnresolvableRegion) as exc:
        select_passage(score, score_id="s", start=Fraction(-1, 1), end=Fraction(2, 1))
    assert exc.value.reason == "out_of_range"
    with pytest.raises(TypeError):
        select_passage(score, score_id="s", start=0.0, end=Fraction(2, 1))  # type: ignore


def test_measure_number_lookup_missing_and_ambiguous():
    score = _load("selection_two_staff.musicxml")
    assert locate_measure_by_number(score, "2").measure_index == 2
    with pytest.raises(UnresolvableRegion) as exc:
        locate_measure_by_number(score, "9")
    assert exc.value.reason == "unknown_measure"


# T02.4 relationships + inherited context ------------------------------------------


def test_written_logical_links_preserved_via_resolver():
    from passage_practice.models.source import SourceRef, resolve_ref

    score = _load("selection_ties.musicxml")
    selected = select_passage(
        score, score_id="ties", start=Fraction(4, 1), end=Fraction(8, 1)
    )
    logical = resolve_ref(
        score, SourceRef(id="n4", kind=SourceKind.LOGICAL_NOTE)
    )
    assert logical is not None and set(logical.source_note_ids) == {"n4", "n5"}
    assert all(
        resolve_ref(score, r) is not None for r in selected.passage.event_refs
    )


def test_inherited_context_at_start():
    score = _load("selection_two_voices.musicxml")
    selected = select_passage(
        score, score_id="voices", start=Fraction(0, 1), end=Fraction(3, 1)
    )
    context = selected.context
    assert context is not None
    assert context.measure_number == "1"
    assert context.time_signature == "3/4"
    assert context.key_fifths == 2 and context.key_mode == "major"
    assert [(c.staff, c.sign, c.line) for c in context.clefs] == [(1, "G", 2)]
    assert context.tempo_text == "dolce"
    assert [r.id for r in context.direction_refs] == ["d1"]
    data = context.to_dict()
    assert _dump(data) == _dump(type(context).from_dict(data).to_dict())


def test_voice_and_staff_kept_distinct_from_hand():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1)
    )
    from passage_practice.models.source import SourceRef, resolve_ref

    resolved = [resolve_ref(score, r) for r in selected.passage.event_refs]
    by_id = {n.note_id: n for n in resolved}
    assert by_id["n1"].staff == 1 and by_id["n1"].hand == "right"
    assert by_id["n5"].staff == 2 and by_id["n5"].hand == "left"


# T02.5 purpose, refinement, partial measures ------------------------------------------


def test_refinement_preserves_lineage_and_narrows():
    score = _load("selection_two_staff.musicxml")
    parent = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(8, 1)
    )
    child = refine_selection(
        score, parent, start=Fraction(4, 1), end=Fraction(8, 1),
        purpose=PassagePurpose.EVIDENCE,
    )
    assert child.passage.parent_id == parent.passage.passage_id
    assert child.passage.purpose == PassagePurpose.EVIDENCE
    assert [r.id for r in child.passage.event_refs] == ["n6", "n10", "n7", "n8", "n9"]
    with pytest.raises(UnresolvableRegion) as exc:
        refine_selection(
            score, parent, start=Fraction(6, 1), end=Fraction(10, 1),
            purpose=PassagePurpose.EVIDENCE,
        )
    assert exc.value.reason in ("outside_parent", "out_of_range")


def test_partial_measure_kept_exact_without_padding():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(1, 1), end=Fraction(3, 1)
    )
    assert [r.id for r in selected.passage.event_refs] == ["n2", "n3"]
    assert selected.passage.start.quarters == Fraction(1, 1)
    assert selected.passage.end.quarters == Fraction(3, 1)
    assert selected.context is not None and selected.context.measure_number == "1"


def test_whole_piece_range_covers_measures():
    score = _load("selection_two_staff.musicxml")
    span = whole_piece_range(score)
    assert (span.start.quarters, span.end.quarters) == (Fraction(0, 1), Fraction(8, 1))


def test_selection_report_lists_included_boundary_and_excluded():
    from passage_practice.models.source import resolve_ref

    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1)
    )
    included = [r.id for r in selected.passage.event_refs]
    assert included == ["n1", "n5", "n2", "n3", "n4"]
    assert selected.boundary_context == ()
    all_logical = [n.note_id for n in score.logical_notes]
    excluded = [i for i in all_logical if i not in included]
    assert excluded == ["n6", "n10", "n7", "n8", "n9"]
    # Every listed ID resolves; report round-trips deterministically.
    assert all(resolve_ref(score, r) is not None for r in selected.passage.event_refs)
    data = selected.to_dict()
    assert _dump(data) == _dump(SelectedPassage.from_dict(data).to_dict())
