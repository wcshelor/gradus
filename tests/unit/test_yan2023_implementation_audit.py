from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tests.harness.yan2023.implementation_audit import (  # noqa: E402
    recommended_base_status_counts,
    recommended_status_counts,
    safe_base_features,
    validate_audit_metadata,
)


class Yan2023ImplementationAuditTests(unittest.TestCase):
    def test_audit_metadata_is_clean(self) -> None:
        self.assertEqual(validate_audit_metadata(), ())

    def test_recommended_counts_are_stable(self) -> None:
        self.assertEqual(
            recommended_status_counts(),
            {
                "implemented": 19,
                "math_drafted": 24,
                "proxyable": 9,
                "blocked": 0,
            },
        )
        self.assertEqual(
            recommended_base_status_counts(),
            {
                "implemented": 7,
                "math_drafted": 10,
                "proxyable": 3,
                "blocked": 0,
            },
        )
        self.assertEqual(
            safe_base_features(),
            (
                "black_key_rate",
                "mean_of_note_duration",
                "note_density",
                "pitch_mean",
                "pitch_range",
                "playing_speed_variation",
                "staccato_rate",
            ),
        )


if __name__ == "__main__":
    unittest.main()
