"""Tests for T01.1 exact-time value objects."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from passage_practice.models.time import (
    SCORE_INTERVAL_SCHEMA_VERSION,
    SCORE_POSITION_SCHEMA_VERSION,
    ScoreInterval,
    ScorePosition,
    fraction_from_json,
    fraction_to_json,
)


# Fraction round-trip -----------------------------------------------------------------


def test_fraction_round_trip_simple():
    for f in [Fraction(0, 1), Fraction(1, 4), Fraction(3, 4), Fraction(7, 8), Fraction(10, 3)]:
        assert fraction_from_json(fraction_to_json(f)) == f


def test_fraction_round_trip_normalizes():
    # Fraction(2,4) == 1/2 but should serialize normalized and round-trip
    f = Fraction(2, 4)
    j = fraction_to_json(f)
    assert j == {"numerator": 1, "denominator": 2}
    assert fraction_from_json(j) == Fraction(1, 2)


def test_fraction_from_string_defensive():
    assert fraction_from_json("3/4") == Fraction(3, 4)
    assert fraction_from_json("  10 / 8 ") == Fraction(10, 8)


def test_fraction_rejects_float():
    with pytest.raises(ValueError, match="lossy float"):
        fraction_from_json(0.5)
    with pytest.raises(ValueError, match="lossy float"):
        fraction_from_json(1.25)


def test_fraction_rejects_zero_denominator():
    with pytest.raises(ValueError, match="denominator cannot be zero"):
        fraction_from_json({"numerator": 1, "denominator": 0})
    with pytest.raises(ValueError):
        fraction_from_json("1/0")


def test_fraction_rejects_invalid():
    with pytest.raises(ValueError):
        fraction_from_json({"numerator": "a", "denominator": 4})
    with pytest.raises(ValueError):
        fraction_from_json({"num": 1})
    with pytest.raises(ValueError):
        fraction_from_json("notafraction")


# ScorePosition ------------------------------------------------------------------------


def _pos(quarters: Fraction, measure_index: int, offset: Fraction | None = None) -> ScorePosition:
    return ScorePosition(
        quarters=quarters,
        measure_index=measure_index,
        measure_number=str(measure_index + 1),
        offset_in_measure=offset if offset is not None else quarters,
    )


def test_position_basic_valid():
    p = ScorePosition(
        quarters=Fraction(5, 4),
        measure_index=1,
        measure_number="2",
        offset_in_measure=Fraction(1, 4),
        voice="1",
        staff=1,
        hand="right",
    )
    assert p.quarters == Fraction(5, 4)


def test_position_rejects_negative_quarters():
    with pytest.raises(ValueError, match="quarters must be >=0"):
        ScorePosition(quarters=Fraction(-1, 4), measure_index=0, offset_in_measure=Fraction(0, 1))


def test_position_rejects_negative_measure_index():
    with pytest.raises(ValueError):
        ScorePosition(quarters=Fraction(0, 1), measure_index=-1, offset_in_measure=Fraction(0, 1))


def test_position_rejects_negative_offset():
    with pytest.raises(ValueError):
        ScorePosition(quarters=Fraction(0, 1), measure_index=0, offset_in_measure=Fraction(-1, 4))


def test_position_hand_voice_staff_distinct():
    # staff/voice/hand are separate concepts; ensure they are stored distinctly
    p = ScorePosition(quarters=Fraction(0, 1), measure_index=0, offset_in_measure=Fraction(0, 1), voice="2", staff=2, hand="left")
    assert p.voice == "2"
    assert p.staff == 2
    assert p.hand == "left"
    # hand must be left/right, not staff number
    with pytest.raises(ValueError):
        ScorePosition(quarters=Fraction(0, 1), measure_index=0, offset_in_measure=Fraction(0, 1), hand="1")


def test_position_serialization_round_trip():
    p = ScorePosition(
        quarters=Fraction(7, 4),
        measure_index=2,
        measure_number="3",
        offset_in_measure=Fraction(3, 4),
        voice="1",
        staff=1,
        hand="right",
    )
    d = p.to_dict()
    assert d["schema_version"] == SCORE_POSITION_SCHEMA_VERSION
    # deterministic: same dict serializes identically
    j1 = json.dumps(d, sort_keys=True)
    j2 = json.dumps(ScorePosition.from_dict(d).to_dict(), sort_keys=True)
    assert j1 == j2
    assert ScorePosition.from_dict(d) == p


def test_position_minimal_optional_fields():
    p = ScorePosition(quarters=Fraction(0, 1), measure_index=0, offset_in_measure=Fraction(0, 1))
    d = p.to_dict()
    assert "measure_number" not in d
    assert "voice" not in d
    assert "staff" not in d
    assert "hand" not in d
    assert ScorePosition.from_dict(d) == p


def test_position_unsupported_schema_version():
    p = ScorePosition(quarters=Fraction(0, 1), measure_index=0, offset_in_measure=Fraction(0, 1))
    d = p.to_dict()
    d["schema_version"] = "score_position.v999"
    with pytest.raises(ValueError, match="unsupported.*schema_version"):
        ScorePosition.from_dict(d)


def test_position_missing_field():
    with pytest.raises(ValueError, match="missing required"):
        ScorePosition.from_dict({"schema_version": SCORE_POSITION_SCHEMA_VERSION, "quarters": {"numerator": 0, "denominator": 1}})


# ScoreInterval ------------------------------------------------------------------------


def _interval(start_q: Fraction, end_q: Fraction, start_m: int = 0, end_m: int | None = None) -> ScoreInterval:
    if end_m is None:
        end_m = start_m
        # if crossing bar, caller must pass end_m explicitly
        if end_q - start_q >= Fraction(4, 1):
            end_m = start_m + 1
    return ScoreInterval(
        start=ScorePosition(quarters=start_q, measure_index=start_m, offset_in_measure=Fraction(0, 1)),
        end=ScorePosition(quarters=end_q, measure_index=end_m, offset_in_measure=Fraction(0, 1)),
    )


def test_interval_valid():
    iv = _interval(Fraction(0, 1), Fraction(4, 1))
    assert iv.duration == Fraction(4, 1)


def test_interval_rejects_zero_length():
    with pytest.raises(ValueError, match="non-empty"):
        _interval(Fraction(1, 1), Fraction(1, 1))


def test_interval_rejects_negative_length():
    with pytest.raises(ValueError, match="non-empty"):
        ScoreInterval(
            start=ScorePosition(quarters=Fraction(5, 1), measure_index=1, offset_in_measure=Fraction(1, 1)),
            end=ScorePosition(quarters=Fraction(2, 1), measure_index=0, offset_in_measure=Fraction(0, 1)),
        )


def test_interval_boundary_equality_half_open():
    iv = _interval(Fraction(0, 1), Fraction(2, 1))
    # start inclusive
    assert iv.contains_quarters(Fraction(0, 1)) is True
    assert iv.contains_quarters(Fraction(1, 1)) is True
    # end exclusive
    assert iv.contains_quarters(Fraction(2, 1)) is False
    assert iv.contains_quarters(Fraction(2, 1) + Fraction(1, 1000)) is False
    # just before end
    assert iv.contains_quarters(Fraction(2, 1) - Fraction(1, 1000)) is True


def test_interval_overlaps_and_equality():
    a = _interval(Fraction(0, 1), Fraction(2, 1))
    b = _interval(Fraction(2, 1), Fraction(4, 1))
    # half-open: a end == b start -> no overlap
    assert a.overlaps(b) is False
    assert b.overlaps(a) is False
    c = _interval(Fraction(1, 1), Fraction(3, 1))
    assert a.overlaps(c) is True
    assert c.overlaps(a) is True


def test_interval_serialization_round_trip():
    iv = ScoreInterval(
        start=ScorePosition(quarters=Fraction(0, 1), measure_index=0, measure_number="1", offset_in_measure=Fraction(0, 1)),
        end=ScorePosition(quarters=Fraction(3, 2), measure_index=0, offset_in_measure=Fraction(3, 2)),
    )
    d = iv.to_dict()
    assert d["schema_version"] == SCORE_INTERVAL_SCHEMA_VERSION
    j1 = json.dumps(d, sort_keys=True)
    j2 = json.dumps(ScoreInterval.from_dict(d).to_dict(), sort_keys=True)
    assert j1 == j2
    assert ScoreInterval.from_dict(d) == iv


def test_interval_unsupported_schema_version():
    iv = _interval(Fraction(0, 1), Fraction(1, 1))
    d = iv.to_dict()
    d["schema_version"] = "score_interval.v999"
    with pytest.raises(ValueError, match="unsupported"):
        ScoreInterval.from_dict(d)


def test_interval_rejects_measure_index_inconsistent():
    # start later measure but earlier quarters is inconsistent
    with pytest.raises(ValueError, match="measure_index inconsistent"):
        ScoreInterval(
            start=ScorePosition(quarters=Fraction(0, 1), measure_index=5, offset_in_measure=Fraction(0, 1)),
            end=ScorePosition(quarters=Fraction(1, 1), measure_index=0, offset_in_measure=Fraction(0, 1)),
        )


def test_interval_duration_exact_rational():
    iv = _interval(Fraction(1, 3), Fraction(5, 6))
    assert iv.duration == Fraction(1, 2)
    # exact, not float
    assert isinstance(iv.duration, Fraction)
    assert type(iv.duration) is Fraction
    assert iv.duration == Fraction(1, 2)


def test_position_fraction_immutability():
    p = ScorePosition(quarters=Fraction(1, 4), measure_index=0, offset_in_measure=Fraction(1, 4))
    with pytest.raises(AttributeError):
        p.quarters = Fraction(1, 2)  # type: ignore
    iv = _interval(Fraction(0, 1), Fraction(1, 1))
    with pytest.raises(AttributeError):
        iv.start = p  # type: ignore
