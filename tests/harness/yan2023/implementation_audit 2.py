"""Strict implementation audit for currently implemented Yan 2023 slots.

This module does not define new feature math. It audits the slots that are
currently marked ``implemented`` in the working and paper-facing Yan
inventories, records the exact code paths and formulas currently used, and
assigns stricter recommended statuses for downstream work.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tests.harness.yan2023.extractor import extract_first_pass_from_path
from tests.harness.yan2023.paper_inventory import PAPER_73_FEATURE_SLOTS, paper_slot_status_counts
from tests.harness.yan2023.slot_inventory import WORKING_FEATURE_SLOTS, slot_status_counts

AuditConfidence = Literal["high", "medium", "low"]
AuditMathSource = Literal["explicitly paper-derived", "inferred", "repo-native proxy"]
AuditRecommendedStatus = Literal["implemented", "math_drafted", "proxyable", "blocked"]
AuditValidationStatus = Literal["fixture_regression", "trivial_documented", "none"]
InventoryMembership = Literal["working", "paper73", "both"]
ScopeLabel = Literal["global", "treble", "bass", "other (entire_score)"]

ALLOWED_RECOMMENDED_STATUSES: tuple[AuditRecommendedStatus, ...] = (
    "implemented",
    "math_drafted",
    "proxyable",
    "blocked",
)
ALLOWED_MATH_SOURCES: tuple[AuditMathSource, ...] = (
    "explicitly paper-derived",
    "inferred",
    "repo-native proxy",
)
ALLOWED_VALIDATION_STATUSES: tuple[AuditValidationStatus, ...] = (
    "fixture_regression",
    "trivial_documented",
    "none",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
FEATURE_FIXTURE_PATH = _REPO_ROOT / "tests" / "fixtures" / "feature_fixture.musicxml"
FEATURE_FIXTURE_VALIDATION_REF = (
    "tests/fixtures/feature_fixture.musicxml via "
    "tests/scripts/run_yan2023_implementation_audit.py --check"
)
_NUMERIC_TOLERANCE = 1e-9
_SCOPE_LABELS: dict[str, ScopeLabel] = {
    "global": "global",
    "ts": "treble",
    "bs": "bass",
    "es": "other (entire_score)",
}


@dataclass(frozen=True, slots=True)
class _BaseAuditSpec:
    paper_name: str
    implementation_path: str
    math_definition: str
    math_source: AuditMathSource
    recommended_status: AuditRecommendedStatus
    confidence: AuditConfidence
    status_reason: str


@dataclass(frozen=True, slots=True)
class Yan2023ImplementationAuditRow:
    feature_id: str
    paper_name: str | None
    inventory: InventoryMembership
    scope: ScopeLabel
    current_status: str
    implementation_path: str
    math_definition: str
    math_source: AuditMathSource
    toy_validation_exists: bool
    validation_status: AuditValidationStatus
    validation_ref: str | None
    confidence: AuditConfidence
    recommended_status: AuditRecommendedStatus
    status_reason: str


FEATURE_FIXTURE_EXPECTATIONS: dict[str, float | int] = {
    "pitch_mean_es": 61.8,
    "pitch_mean_bs": 48.0,
    "pitch_mean_ts": 65.25,
    "deviation_of_pitch_es": 7.652450587883597,
    "deviation_of_pitch_bs": 0.0,
    "deviation_of_pitch_ts": 3.6996621467371855,
    "pitch_range_es": 22,
    "pitch_range_bs": 0,
    "pitch_range_ts": 10,
    "pitch_entropy_es": 2.321928094887362,
    "pitch_entropy_bs": -0.0,
    "pitch_entropy_ts": 2.0,
    "deviation_of_pitch_from_C4_es": 6.6,
    "deviation_of_pitch_from_C4_bs": 12.0,
    "deviation_of_pitch_from_C4_ts": 5.25,
    "black_key_rate_es": 0.2,
    "black_key_rate_bs": 0.0,
    "black_key_rate_ts": 0.25,
    "mean_of_note_duration_es": 1.7,
    "mean_of_note_duration_bs": 4.0,
    "mean_of_note_duration_ts": 1.125,
    "deviation_of_note_duration_es": 1.2489995996796797,
    "deviation_of_note_duration_bs": 0.0,
    "deviation_of_note_duration_ts": 0.5448623679425842,
    "polyphony_rate_es": 0.3333333333333333,
    "polyphony_rate_bs": 0.0,
    "polyphony_rate_ts": 0.3333333333333333,
    "pitch_variability_es": 0.14938341377300535,
    "pitch_variability_bs": 0.0,
    "pitch_variability_ts": 0.0513710920625905,
    "note_duration_variability_es": 1.0666666666666667,
    "note_duration_variability_bs": 0.0,
    "note_duration_variability_ts": 0.6222222222222222,
    "note_density_es": 0.7142857142857143,
    "note_density_bs": 0.14285714285714285,
    "note_density_ts": 0.5714285714285714,
    "triad_es": 0,
    "triad_bs": 0,
    "triad_ts": 0,
    "seventh_chord_es": 0,
    "seventh_chord_bs": 0,
    "seventh_chord_ts": 0,
    "ninth_chord_es": 0,
    "ninth_chord_bs": 0,
    "ninth_chord_ts": 0,
    "staccato_rate_es": 0.0,
    "staccato_rate_bs": 0.0,
    "staccato_rate_ts": 0.0,
    "length": 7.0,
    "tempo": 100.0,
    "key_signature": 0,
    "playing_speed_variation": 0.5,
}

_BASE_AUDIT_SPECS: dict[str, _BaseAuditSpec] = {
    "pitch_mean": _BaseAuditSpec(
        paper_name="mean of pitch",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _mean",
        math_definition="mean_i(p_i) over scope logical-note MIDI pitches p_i",
        math_source="inferred",
        recommended_status="implemented",
        confidence="high",
        status_reason=(
            "The paper names mean pitch directly and the current MIDI mean is a "
            "low-ambiguity score-statistic contract."
        ),
    ),
    "deviation_of_pitch": _BaseAuditSpec(
        paper_name="deviation of pitch",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_population_stddev"
        ),
        math_definition=(
            "sqrt((1/N) * sum_i((p_i - mean(p))^2)) over scope logical-note MIDI "
            "pitches p_i"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The code is real and regression-checked, but the paper does not "
            "publish whether 'deviation' means population std-dev, sample "
            "std-dev, or another dispersion contract."
        ),
    ),
    "pitch_range": _BaseAuditSpec(
        paper_name="pitch range",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values",
        math_definition="max_i(p_i) - min_i(p_i) over scope logical-note MIDI pitches p_i",
        math_source="inferred",
        recommended_status="implemented",
        confidence="high",
        status_reason=(
            "The current max-minus-min span is a direct, low-ambiguity reading "
            "of the named paper feature."
        ),
    ),
    "pitch_entropy": _BaseAuditSpec(
        paper_name="pitch entropy",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _entropy",
        math_definition=(
            "-sum_x P(x) * log2(P(x)) over the histogram of exact MIDI pitch values x"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The paper names pitch entropy, but it does not publish whether the "
            "distribution is over absolute pitches, pitch classes, intervals, or "
            "another pitch coding."
        ),
    ),
    "deviation_of_pitch_from_C4": _BaseAuditSpec(
        paper_name="deviation of the pitch from middle C (C4)",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _mean",
        math_definition="mean_i(abs(p_i - 60)) over scope logical-note MIDI pitches p_i",
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The current mean absolute distance from MIDI 60 is plausible, but "
            "the paper does not publish the exact aggregator for the C4-distance "
            "feature."
        ),
    ),
    "black_key_rate": _BaseAuditSpec(
        paper_name="black key rate",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _ratio",
        math_definition=(
            "count_i((p_i mod 12) in {1,3,6,8,10}) / N over scope logical-note MIDI pitches p_i"
        ),
        math_source="inferred",
        recommended_status="implemented",
        confidence="high",
        status_reason=(
            "The current pitch-class ratio is a direct and low-ambiguity reading "
            "of the named paper feature."
        ),
    ),
    "mean_of_note_duration": _BaseAuditSpec(
        paper_name="mean of note duration",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _mean",
        math_definition="mean_i(d_i) over scope logical-note durations d_i in quarter notes",
        math_source="inferred",
        recommended_status="implemented",
        confidence="high",
        status_reason=(
            "The current mean duration is a direct, low-ambiguity score-statistic "
            "contract for the named paper feature."
        ),
    ),
    "deviation_of_note_duration": _BaseAuditSpec(
        paper_name="deviation of note duration",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_population_stddev"
        ),
        math_definition=(
            "sqrt((1/N) * sum_i((d_i - mean(d))^2)) over scope logical-note "
            "durations d_i in quarter notes"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The code is concrete, but the paper does not publish the exact "
            "dispersion convention behind 'deviation of note duration'."
        ),
    ),
    "polyphony_rate": _BaseAuditSpec(
        paper_name="polyphony rate",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_scope_onset_groups + _ratio"
        ),
        math_definition=(
            "count_onsets(len(onset_group) > 1) / count_distinct_onsets over scope "
            "logical-note onset groups"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The current numerator and denominator are sensible, but the paper "
            "does not publish the exact attack-grouping contract for this rate."
        ),
    ),
    "pitch_variability": _BaseAuditSpec(
        paper_name="pitch variability (PV)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_ordered_written_notes + _adjacent_normalized_variability"
        ),
        math_definition=(
            "mean_i(abs(p_i - p_(i+1)) / ((abs(p_i) + abs(p_(i+1))) / 2)) over "
            "ordered scope written-note MIDI pitches; zero-denominator terms are skipped"
        ),
        math_source="explicitly paper-derived",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "Table 3 publishes the adjacent-note variability formula, but the "
            "paper does not publish how simultaneous notes and polyphonic score "
            "order should be flattened into one adjacency stream."
        ),
    ),
    "note_duration_variability": _BaseAuditSpec(
        paper_name="note duration variability (NDV)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_ordered_written_notes + _adjacent_normalized_variability"
        ),
        math_definition=(
            "mean_i(abs(d_i - d_(i+1)) / ((abs(d_i) + abs(d_(i+1))) / 2)) over "
            "ordered scope written-note durations d_i in quarter notes; "
            "zero-denominator terms are skipped"
        ),
        math_source="explicitly paper-derived",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "Table 3 publishes the variability formula, but the score-flattening "
            "order for simultaneities is still unpublished."
        ),
    ),
    "note_density": _BaseAuditSpec(
        paper_name="note density (ND)",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _ratio",
        math_definition=(
            "count(scope logical notes) / total score duration in quarter notes"
        ),
        math_source="explicitly paper-derived",
        recommended_status="implemented",
        confidence="medium",
        status_reason=(
            "Table 3 publishes a note-count-over-length density idea and the "
            "current logical-note contract is concrete, documented, and "
            "fixture-validated."
        ),
    ),
    "triad": _BaseAuditSpec(
        paper_name="triad (CN family)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_chord_type_counts"
        ),
        math_definition=(
            "count(chord events whose distinct pitch-class set size == 3)"
        ),
        math_source="repo-native proxy",
        recommended_status="proxyable",
        confidence="low",
        status_reason=(
            "The current code counts pitch-class cardinality, not a published Yan "
            "triad-recognition contract with chord semantics."
        ),
    ),
    "seventh_chord": _BaseAuditSpec(
        paper_name="seventh chord (CN family)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_chord_type_counts"
        ),
        math_definition=(
            "count(chord events whose distinct pitch-class set size == 4)"
        ),
        math_source="repo-native proxy",
        recommended_status="proxyable",
        confidence="low",
        status_reason=(
            "The current code uses pitch-class cardinality as a surrogate rather "
            "than a published Yan seventh-chord recognition contract."
        ),
    ),
    "ninth_chord": _BaseAuditSpec(
        paper_name="ninth chord (CN family)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_scope_values -> "
            "_chord_type_counts"
        ),
        math_definition=(
            "count(chord events whose distinct pitch-class set size >= 5)"
        ),
        math_source="repo-native proxy",
        recommended_status="proxyable",
        confidence="low",
        status_reason=(
            "The current code treats any >=5 pitch-class simultaneity as a ninth "
            "or larger chord, which is a surrogate rather than a published Yan "
            "contract."
        ),
    ),
    "staccato_rate": _BaseAuditSpec(
        paper_name="staccato rate (SR)",
        implementation_path="tests/harness/yan2023/extractor.py:_extract_scope_values -> _ratio",
        math_definition=(
            "count(scope written notes whose articulations include 'staccato') / "
            "count(scope written notes)"
        ),
        math_source="explicitly paper-derived",
        recommended_status="implemented",
        confidence="medium",
        status_reason=(
            "Table 3 publishes a direct note-rate definition and the current code "
            "maps that directly onto written-note articulations."
        ),
    ),
    "length": _BaseAuditSpec(
        paper_name="length",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_global_values -> "
            "_score_duration_quarters"
        ),
        math_definition=(
            "max(measure.end) - min(measure.start), with logical-note end fallback, "
            "reported in quarter notes"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The paper names length but does not publish whether length means "
            "beats, measures, pages, or another unit."
        ),
    ),
    "tempo": _BaseAuditSpec(
        paper_name="tempo",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_global_values -> "
            "_initial_tempo"
        ),
        math_definition=(
            "first parsed tempo direction value, falling back to the first measure "
            "tempo_bpm"
        ),
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The current code uses the initial tempo marking, but the paper does "
            "not publish whether the feature should be initial, average, modal, or "
            "otherwise aggregated."
        ),
    ),
    "key_signature": _BaseAuditSpec(
        paper_name="key signature",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_global_values -> "
            "_initial_key_fifths"
        ),
        math_definition="first available measure.key_fifths integer",
        math_source="inferred",
        recommended_status="math_drafted",
        confidence="medium",
        status_reason=(
            "The current code uses the initial fifths value directly, but the "
            "paper does not publish the categorical or numeric encoding contract."
        ),
    ),
    "playing_speed_variation": _BaseAuditSpec(
        paper_name="variation of playing speed (PSV)",
        implementation_path=(
            "tests/harness/yan2023/extractor.py:_extract_global_values -> "
            "_tempo_variation_ratio"
        ),
        math_definition=(
            "count(consecutive tempo-value changes) / count(known tempo values)"
        ),
        math_source="explicitly paper-derived",
        recommended_status="implemented",
        confidence="medium",
        status_reason=(
            "Table 3 publishes a tempo-variation ratio, and the current code has a "
            "clear, reproducible contract for counted tempo changes."
        ),
    ),
}


def _implemented_working_slots() -> dict[str, object]:
    return {
        slot.slot_id: slot
        for slot in WORKING_FEATURE_SLOTS
        if slot.status == "implemented"
    }


def _implemented_paper_slots() -> dict[str, object]:
    return {
        slot.slot_id: slot
        for slot in PAPER_73_FEATURE_SLOTS
        if slot.status == "implemented"
    }


def build_implementation_audit_rows() -> tuple[Yan2023ImplementationAuditRow, ...]:
    """Return audit rows for every currently implemented Yan slot."""

    working_slots = _implemented_working_slots()
    paper_slots = _implemented_paper_slots()
    ordered_slot_ids = [
        slot.slot_id
        for slot in WORKING_FEATURE_SLOTS
        if slot.status == "implemented"
    ]

    rows: list[Yan2023ImplementationAuditRow] = []
    for slot_id in ordered_slot_ids:
        slot = working_slots[slot_id]
        base_feature = slot.base_feature
        spec = _BASE_AUDIT_SPECS[base_feature]
        in_working = slot_id in working_slots
        in_paper = slot_id in paper_slots
        inventory: InventoryMembership
        if in_working and in_paper:
            inventory = "both"
        elif in_working:
            inventory = "working"
        else:
            inventory = "paper73"

        toy_validation_exists = slot_id in FEATURE_FIXTURE_EXPECTATIONS
        rows.append(
            Yan2023ImplementationAuditRow(
                feature_id=slot_id,
                paper_name=spec.paper_name,
                inventory=inventory,
                scope=_SCOPE_LABELS[slot.scope_code],
                current_status="implemented",
                implementation_path=spec.implementation_path,
                math_definition=spec.math_definition,
                math_source=spec.math_source,
                toy_validation_exists=toy_validation_exists,
                validation_status="fixture_regression" if toy_validation_exists else "none",
                validation_ref=FEATURE_FIXTURE_VALIDATION_REF if toy_validation_exists else None,
                confidence=spec.confidence,
                recommended_status=spec.recommended_status,
                status_reason=spec.status_reason,
            )
        )
    return tuple(rows)


def current_implemented_slot_ids() -> tuple[str, ...]:
    """Return the stable ordered slot ids that are currently marked implemented."""

    return tuple(row.feature_id for row in build_implementation_audit_rows())


def recommended_status_counts(
    rows: tuple[Yan2023ImplementationAuditRow, ...] | None = None,
) -> dict[AuditRecommendedStatus, int]:
    rows = rows or build_implementation_audit_rows()
    counts: dict[AuditRecommendedStatus, int] = {
        "implemented": 0,
        "math_drafted": 0,
        "proxyable": 0,
        "blocked": 0,
    }
    for row in rows:
        counts[row.recommended_status] += 1
    return counts


def recommended_base_status_counts(
    rows: tuple[Yan2023ImplementationAuditRow, ...] | None = None,
) -> dict[AuditRecommendedStatus, int]:
    rows = rows or build_implementation_audit_rows()
    by_base: dict[str, AuditRecommendedStatus] = {}
    for row in rows:
        base_feature = _slot_base_feature(row.feature_id)
        by_base.setdefault(base_feature, row.recommended_status)

    counts: dict[AuditRecommendedStatus, int] = {
        "implemented": 0,
        "math_drafted": 0,
        "proxyable": 0,
        "blocked": 0,
    }
    for status in by_base.values():
        counts[status] += 1
    return counts


def pre_audit_counts() -> dict[str, dict[str, int]]:
    """Return the status counts recorded by the current working and paper inventories."""

    return {
        "working": slot_status_counts(),
        "paper73": paper_slot_status_counts(),
    }


def validate_audit_metadata() -> tuple[str, ...]:
    """Check that the audit registry covers every currently implemented slot."""

    issues: list[str] = []
    rows = build_implementation_audit_rows()
    row_ids = [row.feature_id for row in rows]
    if len(row_ids) != len(set(row_ids)):
        issues.append("Audit rows contain duplicate feature_ids.")

    working_ids = tuple(
        slot.slot_id for slot in WORKING_FEATURE_SLOTS if slot.status == "implemented"
    )
    paper_ids = tuple(
        slot.slot_id for slot in PAPER_73_FEATURE_SLOTS if slot.status == "implemented"
    )
    expected_ids = tuple(dict.fromkeys([*working_ids, *paper_ids]))
    if tuple(row_ids) != expected_ids:
        missing = sorted(set(expected_ids) - set(row_ids))
        extra = sorted(set(row_ids) - set(expected_ids))
        if missing:
            issues.append(
                "Audit rows are missing currently implemented slots: "
                + ", ".join(missing)
            )
        if extra:
            issues.append(
                "Audit rows include unexpected slots: " + ", ".join(extra)
            )

    for row in rows:
        if not row.implementation_path.strip():
            issues.append(f"{row.feature_id}: missing implementation_path")
        if not row.math_definition.strip():
            issues.append(f"{row.feature_id}: missing math_definition")
        if row.recommended_status not in ALLOWED_RECOMMENDED_STATUSES:
            issues.append(
                f"{row.feature_id}: invalid recommended_status {row.recommended_status!r}"
            )
        if row.math_source not in ALLOWED_MATH_SOURCES:
            issues.append(f"{row.feature_id}: invalid math_source {row.math_source!r}")
        if row.validation_status not in ALLOWED_VALIDATION_STATUSES:
            issues.append(
                f"{row.feature_id}: invalid validation_status {row.validation_status!r}"
            )
        if row.recommended_status == "implemented" and not row.toy_validation_exists:
            issues.append(
                f"{row.feature_id}: recommended implemented without toy validation"
            )
        if row.recommended_status == "implemented" and row.math_source == "repo-native proxy":
            issues.append(
                f"{row.feature_id}: recommended implemented even though math_source is repo-native proxy"
            )

    if set(FEATURE_FIXTURE_EXPECTATIONS) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(FEATURE_FIXTURE_EXPECTATIONS))
        extra = sorted(set(FEATURE_FIXTURE_EXPECTATIONS) - set(expected_ids))
        if missing:
            issues.append(
                "FEATURE_FIXTURE_EXPECTATIONS is missing implemented slots: "
                + ", ".join(missing)
            )
        if extra:
            issues.append(
                "FEATURE_FIXTURE_EXPECTATIONS contains non-implemented slots: "
                + ", ".join(extra)
            )

    return tuple(issues)


def validate_feature_fixture_regression() -> tuple[str, ...]:
    """Check that the current extractor still reproduces the committed fixture values."""

    _score, values = extract_first_pass_from_path(FEATURE_FIXTURE_PATH)
    actual = {value.slot_id: value.value for value in values if value.status == "implemented"}
    issues: list[str] = []

    if set(actual) != set(FEATURE_FIXTURE_EXPECTATIONS):
        missing = sorted(set(FEATURE_FIXTURE_EXPECTATIONS) - set(actual))
        extra = sorted(set(actual) - set(FEATURE_FIXTURE_EXPECTATIONS))
        if missing:
            issues.append(
                "Fixture regression is missing implemented outputs: " + ", ".join(missing)
            )
        if extra:
            issues.append(
                "Fixture regression produced unexpected implemented outputs: "
                + ", ".join(extra)
            )

    for slot_id, expected in FEATURE_FIXTURE_EXPECTATIONS.items():
        if slot_id not in actual:
            continue
        observed = actual[slot_id]
        if isinstance(expected, float):
            if observed is None or abs(float(observed) - expected) > _NUMERIC_TOLERANCE:
                issues.append(
                    f"{slot_id}: expected {expected!r}, observed {observed!r}"
                )
        else:
            if observed != expected:
                issues.append(
                    f"{slot_id}: expected {expected!r}, observed {observed!r}"
                )

    return tuple(issues)


def safe_base_features(
    rows: tuple[Yan2023ImplementationAuditRow, ...] | None = None,
) -> tuple[str, ...]:
    rows = rows or build_implementation_audit_rows()
    safe = {
        _slot_base_feature(row.feature_id)
        for row in rows
        if row.recommended_status == "implemented"
    }
    return tuple(sorted(safe))


def downgraded_base_features(
    rows: tuple[Yan2023ImplementationAuditRow, ...] | None = None,
) -> tuple[tuple[str, AuditRecommendedStatus, str], ...]:
    rows = rows or build_implementation_audit_rows()
    grouped: dict[str, Yan2023ImplementationAuditRow] = {}
    for row in rows:
        base_feature = _slot_base_feature(row.feature_id)
        grouped.setdefault(base_feature, row)

    downgraded = [
        (base_feature, row.recommended_status, row.status_reason)
        for base_feature, row in sorted(grouped.items())
        if row.recommended_status != "implemented"
    ]
    return tuple(downgraded)


def build_markdown_report() -> str:
    """Render the strict Yan implementation audit as Markdown."""

    rows = build_implementation_audit_rows()
    slot_counts = recommended_status_counts(rows)
    base_counts = recommended_base_status_counts(rows)
    pre_counts = pre_audit_counts()
    safe_features = safe_base_features(rows)
    downgraded = downgraded_base_features(rows)
    metadata_issues = validate_audit_metadata()
    regression_issues = validate_feature_fixture_regression()

    lines = [
        "# Yan 2023 Implementation Audit",
        "",
        "Strict audit of the slots that are currently marked `implemented` in the "
        "Yan 2023 working and paper-facing inventories.",
        "",
        "## Scope",
        "",
        "- audited current implemented slot union: `52`",
        "- note: the working and paper73 inventories have the same implemented-slot union",
        f"- validation fixture: `{FEATURE_FIXTURE_VALIDATION_REF}`",
        "",
        "## Pre-audit counts",
        "",
        "| Inventory | Implemented | Proxyable | Blocked |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| working | {pre_counts['working']['implemented']} | "
            f"{pre_counts['working']['proxyable']} | {pre_counts['working']['blocked']} |"
        ),
        (
            f"| paper73 | {pre_counts['paper73']['implemented']} | "
            f"{pre_counts['paper73']['proxyable']} | {pre_counts['paper73']['blocked']} |"
        ),
        "",
        "## Post-audit recommended counts",
        "",
        "| Audit level | Implemented | Math drafted | Proxyable | Blocked |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| slot union | {slot_counts['implemented']} | "
            f"{slot_counts['math_drafted']} | {slot_counts['proxyable']} | "
            f"{slot_counts['blocked']} |"
        ),
        (
            f"| base feature | {base_counts['implemented']} | "
            f"{base_counts['math_drafted']} | {base_counts['proxyable']} | "
            f"{base_counts['blocked']} |"
        ),
        "",
        "## Safe To Build On",
        "",
    ]
    lines.extend(f"- `{feature}`" for feature in safe_features)
    lines.extend(
        [
            "",
            "## Downgraded Features",
            "",
            "| Base feature | Recommended status | Why |",
            "| --- | --- | --- |",
        ]
    )
    for base_feature, status, reason in downgraded:
        lines.append(
            f"| `{base_feature}` | `{status}` | { _escape_cell(reason) } |"
        )

    lines.extend(
        [
            "",
            "## Consistency Check",
            "",
            f"- metadata issues: `{len(metadata_issues)}`",
            f"- fixture regression issues: `{len(regression_issues)}`",
        ]
    )
    if metadata_issues:
        lines.extend(f"- metadata: {issue}" for issue in metadata_issues)
    if regression_issues:
        lines.extend(f"- regression: {issue}" for issue in regression_issues)

    lines.extend(
        [
            "",
            "## Detailed Slot Audit",
            "",
            "| feature_id | paper_name | inventory | scope | implementation_path | "
            "math_definition | math_source | toy_validation_exists | "
            "validation_ref | confidence | recommended_status | status_reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.feature_id}`",
                    _escape_cell(row.paper_name or ""),
                    f"`{row.inventory}`",
                    _escape_cell(row.scope),
                    f"`{row.implementation_path}`",
                    _escape_cell(row.math_definition),
                    f"`{row.math_source}`",
                    f"`{row.toy_validation_exists}`",
                    _escape_cell(row.validation_ref or ""),
                    f"`{row.confidence}`",
                    f"`{row.recommended_status}`",
                    _escape_cell(row.status_reason),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def build_json_payload() -> dict[str, object]:
    """Return a machine-readable payload for the implementation audit."""

    rows = build_implementation_audit_rows()
    return {
        "pre_audit_counts": pre_audit_counts(),
        "post_audit_slot_counts": recommended_status_counts(rows),
        "post_audit_base_counts": recommended_base_status_counts(rows),
        "safe_base_features": list(safe_base_features(rows)),
        "downgraded_base_features": [
            {
                "base_feature": base_feature,
                "recommended_status": status,
                "reason": reason,
            }
            for base_feature, status, reason in downgraded_base_features(rows)
        ],
        "metadata_issues": list(validate_audit_metadata()),
        "fixture_regression_issues": list(validate_feature_fixture_regression()),
        "rows": [
            {
                "feature_id": row.feature_id,
                "paper_name": row.paper_name,
                "inventory": row.inventory,
                "scope": row.scope,
                "current_status": row.current_status,
                "implementation_path": row.implementation_path,
                "math_definition": row.math_definition,
                "math_source": row.math_source,
                "toy_validation_exists": row.toy_validation_exists,
                "validation_status": row.validation_status,
                "validation_ref": row.validation_ref,
                "confidence": row.confidence,
                "recommended_status": row.recommended_status,
                "status_reason": row.status_reason,
            }
            for row in rows
        ],
    }


def _slot_base_feature(slot_id: str) -> str:
    for slot in WORKING_FEATURE_SLOTS:
        if slot.slot_id == slot_id:
            return slot.base_feature
    for slot in PAPER_73_FEATURE_SLOTS:
        if slot.slot_id == slot_id:
            return slot.base_feature
    return slot_id.rsplit("_", 1)[0]


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


__all__ = [
    "ALLOWED_MATH_SOURCES",
    "ALLOWED_RECOMMENDED_STATUSES",
    "ALLOWED_VALIDATION_STATUSES",
    "FEATURE_FIXTURE_EXPECTATIONS",
    "FEATURE_FIXTURE_PATH",
    "FEATURE_FIXTURE_VALIDATION_REF",
    "Yan2023ImplementationAuditRow",
    "build_implementation_audit_rows",
    "build_json_payload",
    "build_markdown_report",
    "current_implemented_slot_ids",
    "downgraded_base_features",
    "pre_audit_counts",
    "recommended_base_status_counts",
    "recommended_status_counts",
    "safe_base_features",
    "validate_audit_metadata",
    "validate_feature_fixture_regression",
]
