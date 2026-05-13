"""JSON export helpers.

JSON should be the canonical output format for early development because it can
preserve detailed structure, diagnostics, and localizable feature metadata.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import ScoreIR


def to_json_payload(score: ScoreIR) -> dict[str, object]:
    """Convert normalized extraction results into a JSON-serializable payload."""

    raise NotImplementedError("JSON export is not implemented yet.")

