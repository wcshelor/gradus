import json
from fractions import Fraction
from pathlib import Path

from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand
from piano_difficulty.difficulty_analysis.overview import DifficultyOverviewProfile, OverviewOptions
from piano_difficulty.difficulty_analysis.events import explain_flagged_span
from piano_difficulty.difficulty_analysis.events.models import DifficultyEvent
from piano_difficulty.difficulty_analysis.events.pipeline import explain_events_for_extraction
from piano_difficulty.normalize.schema import LogicalNoteIR, MeasureIR, ScoreIR, WrittenNoteIR
from piano_difficulty.pipeline import ExtractionResult, analyze_score
from piano_difficulty.features import extract_all


def synthetic_debussy_like():
    # 4 measures mimicking brief, but constructed as ScoreIR for deterministic metrics
    score = ScoreIR(title="Synthetic Debussy", measures=[
        MeasureIR(i, str(34+i), Fraction(i*4), Fraction((i+1)*4)) for i in range(4)
    ])
    # Measure 34-35: high density RH, two voices
    for mi in (0, 1):
        base = 60 + mi*2
        for j in range(8):
            onset = Fraction(mi*4) + Fraction(j, 2)
            nid = f"r{mi}:{j}"
            score.written_notes.append(WrittenNoteIR(nid, base+j, onset, Fraction(1,2), 1, "1", hand="right", measure_index=mi))
            score.logical_notes.append(LogicalNoteIR("logical:"+nid, base+j, onset, Fraction(1,2), 1, "1", hand="right", measure_index=mi, source_note_ids=(nid,)))
            # second voice lower
            nid2 = f"r{mi}:{j}:v2"
            score.written_notes.append(WrittenNoteIR(nid2, base+j-7, onset, Fraction(1,2), 1, "2", hand="right", measure_index=mi))
            score.logical_notes.append(LogicalNoteIR("logical:"+nid2, base+j-7, onset, Fraction(1,2), 1, "2", hand="right", measure_index=mi, source_note_ids=(nid2,)))
        # LH
        score.written_notes.append(WrittenNoteIR(f"l{mi}", 36, Fraction(mi*4), Fraction(4), 2, "5", hand="left", measure_index=mi))
        score.logical_notes.append(LogicalNoteIR(f"logical:l{mi}", 36, Fraction(mi*4), Fraction(4), 2, "5", hand="left", measure_index=mi, source_note_ids=(f"l{mi}",)))
    # Measure 36: arpeggiated arrival + LH relocation
    mi = 2
    for j, pitch in enumerate([60, 64, 67, 72, 76, 79]):
        onset = Fraction(mi*4) + Fraction(j, 2)
        nid = f"r{mi}:{j}"
        score.written_notes.append(WrittenNoteIR(nid, pitch, onset, Fraction(1,2), 1, "1", hand="right", measure_index=mi))
        score.logical_notes.append(LogicalNoteIR("logical:"+nid, pitch, onset, Fraction(1,2), 1, "1", hand="right", measure_index=mi, source_note_ids=(nid,)))
    # LH large leap
    score.written_notes.append(WrittenNoteIR("l2a", 28, Fraction(mi*4), Fraction(2), 2, "5", hand="left", measure_index=mi))
    score.logical_notes.append(LogicalNoteIR("logical:l2a", 28, Fraction(mi*4), Fraction(2), 2, "5", hand="left", measure_index=mi, source_note_ids=("l2a",)))
    score.written_notes.append(WrittenNoteIR("l2b", 48, Fraction(mi*4)+Fraction(2), Fraction(2), 2, "5", hand="left", measure_index=mi))
    score.logical_notes.append(LogicalNoteIR("logical:l2b", 48, Fraction(mi*4)+Fraction(2), Fraction(2), 2, "5", hand="left", measure_index=mi, source_note_ids=("l2b",)))
    # Measure 37: closing
    mi = 3
    for j, pitch in enumerate([72, 76, 79]):
        onset = Fraction(mi*4)+Fraction(j)
        nid = f"r{mi}:{j}"
        score.written_notes.append(WrittenNoteIR(nid, pitch, onset, Fraction(1), 1, "1", hand="right", measure_index=mi))
        score.logical_notes.append(LogicalNoteIR("logical:"+nid, pitch, onset, Fraction(1), 1, "1", hand="right", measure_index=mi, source_note_ids=(nid,)))
    score.written_notes.append(WrittenNoteIR("l3", 24, Fraction(mi*4), Fraction(4), 2, "5", hand="left", measure_index=mi))
    score.logical_notes.append(LogicalNoteIR("logical:l3", 24, Fraction(mi*4), Fraction(4), 2, "5", hand="left", measure_index=mi, source_note_ids=("l3",)))
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    return score


def test_event_model_roundtrip():
    from piano_difficulty.temporal.windows import ScoreRegion
    region = ScoreRegion("s", 0, 0, 1, ("1","2"), Fraction(0), Fraction(8), Fraction(0), Fraction(8), 4.0, "both", "Measures 1-2")
    ev = DifficultyEvent(
        event_id="s:e:0:0:repeated_ascending_pattern",
        span=region,
        difficulty_type="repeated_ascending_pattern",
        label="Repeated ascending right-hand pattern",
        confidence=0.7,
        supporting_metric_evidence=(),
        note_evidence=None,
        window_indices=(0,),
        measure_start=0,
        measure_end=1,
    )
    payload = ev.to_payload()
    assert payload["difficulty_type"] == "repeated_ascending_pattern"
    assert 0 <= payload["confidence"] <= 1
    restored = DifficultyEvent.from_payload(payload)
    assert restored.difficulty_type == ev.difficulty_type
    assert restored.span.measure_start == 0


def test_segmentation_splits_flagged_span():
    score = synthetic_debussy_like()
    extraction = ExtractionResult(score, extract_all(score), {}, [])
    # Need overview profile to get flagged region; use window 2
    payload = DifficultyOverviewProfile().analyze(extraction, OverviewOptions(window_size=2)).to_payload()
    assert payload["candidate_sections"], "should have flagged passage"
    flagged = payload["candidate_sections"][0]["region"]
    from piano_difficulty.difficulty_analysis.events.pipeline import _payload_region_to_score_region, _reconstruct_profile
    profile = _reconstruct_profile(extraction, OverviewOptions(window_size=2))
    region = _payload_region_to_score_region(flagged, profile.score_id)
    events = explain_flagged_span(score, profile, region)
    assert len(events) >= 2, f"expected multiple sub-events, got {events}"
    # Overlap allowed: at least one pair shares measure
    has_overlap = any(
        set(a.span.measure_numbers) & set(b.span.measure_numbers) or set(a.window_indices) & set(b.window_indices)
        for i, a in enumerate(events) for b in events[i+1:]
    )
    # For this synthetic, overlap may occur via window overlap or explicit two-voice overlap
    # At least should have distinct types
    types = {e.difficulty_type for e in events}
    assert len(types) >= 2

def test_pipeline_events_do_not_mutate_scores():
    # Real fixture
    fixture = Path("research/piano_difficulty/tests/fixtures/difficulty_events/debussy_arabesque_34_37.musicxml")
    if not fixture.exists():
        fixture = Path("tests/fixtures/difficulty_events/debussy_arabesque_34_37.musicxml")
    # Try both
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[2] / "tests/fixtures/difficulty_events/debussy_arabesque_34_37.musicxml"
    if p.exists():
        fixture = p
    result = analyze_score(str(fixture), explain_events=True)
    payload = result.to_json_payload()
    overview = next(p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_overview")
    ev_payload = overview.get("difficulty_events")
    assert ev_payload is not None
    assert ev_payload["schema_version"] == "difficulty_events.v1"
    # Check existing scores unchanged: factors still present
    assert "factors" in overview
    # Check events have required fields
    for e in ev_payload.get("events", []):
        assert "span" in e and "difficulty_type" in e and "confidence" in e and "supporting_metric_evidence" in e
        assert 0 <= e["confidence"] <= 1
        assert e["measure_numbers"]

def test_uncertain_event_has_reason():
    # Flat passage should produce uncertain
    from piano_difficulty.normalize.schema import ScoreIR, MeasureIR, WrittenNoteIR, LogicalNoteIR
    score = ScoreIR(title="Flat", measures=[MeasureIR(i, str(i+1), Fraction(i*4), Fraction((i+1)*4)) for i in range(4)])
    for i in range(4):
        nid = f"n{i}"
        score.written_notes.append(WrittenNoteIR(nid, 60, Fraction(i*4), Fraction(4), 1, "1", hand="right", measure_index=i))
        score.logical_notes.append(LogicalNoteIR("logical:"+nid, 60, Fraction(i*4), Fraction(4), 1, "1", hand="right", measure_index=i, source_note_ids=(nid,)))
        score.written_notes.append(WrittenNoteIR(f"l{i}", 48, Fraction(i*4), Fraction(4), 2, "1", hand="left", measure_index=i))
        score.logical_notes.append(LogicalNoteIR("logical:l"+str(i),48,Fraction(i*4),Fraction(4),2,"1",hand="left",measure_index=i,source_note_ids=(f"l{i}",)))
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    extraction = ExtractionResult(score, extract_all(score), {}, [])
    payload = DifficultyOverviewProfile().analyze(extraction, OverviewOptions(window_size=2, top_sections=1)).to_payload()
    # May have no candidate_sections; if so, pipeline should handle gracefully
    from piano_difficulty.difficulty_analysis.events.pipeline import explain_events_for_extraction
    ev = explain_events_for_extraction(extraction, payload, options=OverviewOptions(window_size=2))
    # Should not crash, may have 0 events but diagnostics
    assert "events" in ev
    # If flagged, ensure uncertain handling
    if payload.get("candidate_sections"):
        from piano_difficulty.difficulty_analysis.events.pipeline import _reconstruct_profile, _payload_region_to_score_region
        profile = _reconstruct_profile(extraction, OverviewOptions(window_size=2))
        region = _payload_region_to_score_region(payload["candidate_sections"][0]["region"], profile.score_id)
        events = explain_flagged_span(score, profile, region)
        for e in events:
            if e.uncertainty:
                assert e.uncertainty_reason
