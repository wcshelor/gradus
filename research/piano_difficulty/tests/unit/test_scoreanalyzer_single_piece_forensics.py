from __future__ import annotations

from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity import run_replica_metrics
from piano_difficulty.comparison.scoreanalyzer_single_piece_forensics import (
    build_forensic_index,
    locate_metric_suspects,
)
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir


ALLA_TURCA_PATH = Path("external/ScoreAnalyzer/pieces/AllaTurca_Mozart/Alla_Turca.xml")
PARITY_PROBE_PATH = Path("tests/fixtures/parity_feature_probe.musicxml")


def _mutated_og_for_metric(metric: str, replica_metrics: dict[str, object]) -> dict[str, object]:
    og_metrics = dict(replica_metrics)
    value = og_metrics.get(metric)
    if isinstance(value, (int, float)):
        og_metrics[metric] = value + 1
    elif isinstance(value, str):
        og_metrics[metric] = value + "_og"
    else:
        og_metrics[metric] = 0
    return og_metrics


def test_metric_family_locators_emit_expected_reason_codes() -> None:
    score = build_score_ir(load_musicxml_document(ALLA_TURCA_PATH))
    forensic_index = build_forensic_index(score)
    replica_metrics = run_replica_metrics(ALLA_TURCA_PATH)

    locators = {
        "displacementsRH": "DIFFICULT_DISPLACEMENT",
        "chordsRH": "CHORD_BASE_EVENT",
        "harmonyRH": "ACCIDENTAL_EVENT",
        "baseDuration": "BASE_DURATION_NOTE",
    }
    for metric, reason_code in locators.items():
        rows = locate_metric_suspects(
            piece_relpath="AllaTurca_Mozart/Alla_Turca.xml",
            metric=metric,
            og_metrics=_mutated_og_for_metric(metric, replica_metrics),
            replica_metrics=replica_metrics,
            mismatched_metrics={metric},
            forensic_index=forensic_index,
            max_suspects_per_metric=20,
        )
        assert rows
        assert rows[0].reason_code == reason_code


def test_rhythm_locator_emits_measure_and_note_on_probe_fixture() -> None:
    score = build_score_ir(load_musicxml_document(PARITY_PROBE_PATH))
    forensic_index = build_forensic_index(score)
    replica_metrics = run_replica_metrics(PARITY_PROBE_PATH)
    og_metrics = _mutated_og_for_metric("rhythm", replica_metrics)

    rows = locate_metric_suspects(
        piece_relpath="parity_feature_probe.musicxml",
        metric="rhythm",
        og_metrics=og_metrics,
        replica_metrics=replica_metrics,
        mismatched_metrics={"rhythm"},
        forensic_index=forensic_index,
        max_suspects_per_metric=20,
    )
    assert rows
    assert rows[0].reason_code == "POLYRHYTHM_MEASURE"
    assert rows[0].measure_index is not None
    assert rows[0].measure_number != ""


def test_measure_identifiers_include_index_and_number() -> None:
    score = build_score_ir(load_musicxml_document(ALLA_TURCA_PATH))
    forensic_index = build_forensic_index(score)
    replica_metrics = run_replica_metrics(ALLA_TURCA_PATH)
    og_metrics = _mutated_og_for_metric("maxIntervalRH", replica_metrics)

    rows = locate_metric_suspects(
        piece_relpath="AllaTurca_Mozart/Alla_Turca.xml",
        metric="maxIntervalRH",
        og_metrics=og_metrics,
        replica_metrics=replica_metrics,
        mismatched_metrics={"maxIntervalRH"},
        forensic_index=forensic_index,
        max_suspects_per_metric=20,
    )
    assert rows
    assert rows[0].measure_index is not None
    assert rows[0].measure_number != ""


def test_suspect_cap_is_enforced() -> None:
    score = build_score_ir(load_musicxml_document(ALLA_TURCA_PATH))
    forensic_index = build_forensic_index(score)
    replica_metrics = run_replica_metrics(ALLA_TURCA_PATH)
    og_metrics = _mutated_og_for_metric("noteCounterRH", replica_metrics)

    rows = locate_metric_suspects(
        piece_relpath="AllaTurca_Mozart/Alla_Turca.xml",
        metric="noteCounterRH",
        og_metrics=og_metrics,
        replica_metrics=replica_metrics,
        mismatched_metrics={"noteCounterRH"},
        forensic_index=forensic_index,
        max_suspects_per_metric=3,
    )
    assert len(rows) <= 3
