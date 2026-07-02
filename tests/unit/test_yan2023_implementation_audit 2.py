from tests.harness.yan2023.implementation_audit import (
    recommended_base_status_counts,
    recommended_status_counts,
    safe_base_features,
    validate_audit_metadata,
)


def test_yan2023_audit_metadata_is_clean() -> None:
    assert validate_audit_metadata() == ()


def test_yan2023_audit_recommended_counts_are_stable() -> None:
    assert recommended_status_counts() == {
        "implemented": 19,
        "math_drafted": 24,
        "proxyable": 9,
        "blocked": 0,
    }
    assert recommended_base_status_counts() == {
        "implemented": 7,
        "math_drafted": 10,
        "proxyable": 3,
        "blocked": 0,
    }
    assert safe_base_features() == (
        "black_key_rate",
        "mean_of_note_duration",
        "note_density",
        "pitch_mean",
        "pitch_range",
        "playing_speed_variation",
        "staccato_rate",
    )
