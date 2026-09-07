"""Tests for LS-05 user-selected regions independent of difficulty."""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.investigation import (
    DifficultyEvidence,
    PassageInvestigation,
    SelectionOrigin,
)
from passage_practice.models.time import ScoreInterval
from passage_practice.passages.investigate import (
    manual_investigation,
    whole_piece_investigation,
)
from passage_practice.passages.selection import UnresolvableRegion, select_passage

from test_selection import _load


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def test_user_selected_low_demand_passage_without_any_profile():
    before = {
        mod for mod in sys.modules if mod.startswith("piano_difficulty.difficulty_analysis")
    }
    score = _load("selection_two_voices.musicxml")  # sparse: low demand, never ranked
    inv = manual_investigation(
        score, score_id="voices", start=Fraction(0, 1), end=Fraction(3, 1),
        investigation_id="inv.ls05.1",
    )
    assert inv.selection_origin == SelectionOrigin.USER_SELECTED
    assert inv.difficulty == ()
    assert len(inv.passage.event_refs) == 4
    after = {
        mod for mod in sys.modules if mod.startswith("piano_difficulty.difficulty_analysis")
    }
    assert after == before, "adapter must not import the difficulty pipeline"


def test_selection_concern_and_difficulty_stay_distinct():
    score = _load("selection_two_staff.musicxml")
    selected = select_passage(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1)
    )
    span = ScoreInterval(start=selected.passage.start, end=selected.passage.end)
    evidence = DifficultyEvidence(
        source_score_id="two-staff",
        method_id="difficulty_overview",
        method_version="v1",
        covered=span,
        feature_id="attack_density",
        evidence_ref="ev.ad.w0",
    )
    inv = manual_investigation(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1),
        investigation_id="inv.ls05.2",
        report_refs=("entry.7",),
        difficulty=(evidence,),
    )
    score_ids = {r.id for r in inv.passage.event_refs}
    concern = next(d for d in inv.diagnostics if d.code == "reported_concern")
    assert concern.context == {"report_refs": ["entry.7"]}
    assert "entry.7" not in score_ids  # concern is not score evidence
    assert inv.difficulty[0].evidence_ref == "ev.ad.w0"  # measured, separate
    assert _dump(inv.to_dict()) == _dump(PassageInvestigation.from_dict(inv.to_dict()).to_dict())


def test_whole_piece_request_has_explicit_outcome():
    score = _load("selection_two_staff.musicxml")
    inv = whole_piece_investigation(
        score, score_id="two-staff", investigation_id="inv.ls05.3"
    )
    assert inv.selection_origin == SelectionOrigin.USER_SELECTED
    assert (inv.passage.start.quarters, inv.passage.end.quarters) == (
        Fraction(0, 1), Fraction(8, 1),
    )
    assert len(inv.passage.event_refs) == 10
    assert any(d.code == "whole_piece" for d in inv.diagnostics)


def test_unresolved_selections_are_explicit_without_fabrication():
    score = _load("selection_two_staff.musicxml")
    with pytest.raises(UnresolvableRegion) as exc:
        manual_investigation(
            score, score_id="two-staff", start=Fraction(0, 1),
            end=Fraction(99, 1), investigation_id="inv.bad",
        )
    assert exc.value.reason == "out_of_range"
    assert exc.value.diagnostics[0].code == "region_out_of_range"
    with pytest.raises(UnresolvableRegion) as exc:
        manual_investigation(
            score, score_id="two-staff", start=Fraction(2, 1),
            end=Fraction(2, 1), investigation_id="inv.bad",
        )
    assert exc.value.reason == "empty_interval"


def test_analyzer_route_has_no_nonzero_score_gate():
    score = _load("selection_ties.musicxml")

    selected = select_passage(
        score, score_id="ties", start=Fraction(4, 1), end=Fraction(8, 1)
    )
    # Suggested but unscored: empty difficulty is valid analyzer context.
    unscored = PassageInvestigation(
        investigation_id="inv.ls05.4",
        passage=selected.passage,
        selection_origin=SelectionOrigin.ANALYZER_SUGGESTED,
        method_id="hotspot_adapter",
        method_version="v1",
    )
    assert unscored.difficulty == ()
    # Zero score is a measurement, not a gate.
    zero = unscored.with_evidence(
        DifficultyEvidence(
            source_score_id="ties",
            method_id="difficulty_overview",
            method_version="v1",
            covered=ScoreInterval(
                start=selected.passage.start, end=selected.passage.end
            ),
            feature_id="attack_density",
            evidence_ref="ev.ad.w0",
            hotspot_id="hs.w0",
            window_score=0.0,
        )
    )
    assert zero.difficulty[0].window_score == 0.0
    assert zero.selection_origin == SelectionOrigin.ANALYZER_SUGGESTED


def test_manual_enrichment_preserves_origin_and_identity():
    score = _load("selection_two_staff.musicxml")
    inv = manual_investigation(
        score, score_id="two-staff", start=Fraction(0, 1), end=Fraction(4, 1),
        investigation_id="inv.ls05.5",
    )
    enriched = inv.with_evidence(
        DifficultyEvidence(
            source_score_id="two-staff",
            method_id="difficulty_overview",
            method_version="v1",
            covered=ScoreInterval(start=inv.passage.start, end=inv.passage.end),
            feature_id="attack_density",
            evidence_ref="ev.ad.w0",
        )
    )
    assert enriched.selection_origin == SelectionOrigin.USER_SELECTED
    assert enriched.passage.passage_id == inv.passage.passage_id


def test_rejects_bad_concern_hand_and_difficulty_shapes():
    score = _load("selection_two_staff.musicxml")
    with pytest.raises(ValueError):
        manual_investigation(
            score, score_id="two-staff", start=Fraction(0, 1),
            end=Fraction(4, 1), investigation_id="inv.bad",
            requested_hand="middle",
        )
    with pytest.raises(TypeError):
        manual_investigation(
            score, score_id="two-staff", start=Fraction(0, 1),
            end=Fraction(4, 1), investigation_id="inv.bad",
            report_refs=["entry.1"],  # type: ignore
        )
    with pytest.raises(TypeError):
        manual_investigation(
            score, score_id="two-staff", start=Fraction(0, 1),
            end=Fraction(4, 1), investigation_id="inv.bad",
            difficulty="ev.ad.w0",  # type: ignore
        )
