"""Structural guardrails for the Yan 2023 paper-first feature lane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LaneFeatureStatus = Literal["implemented", "proxyable", "blocked"]

LANE_ID = "yan2023_experimental"
LANE_NAME = "Yan 2023 paper-first feature reconstruction lane"

LANE_BOUNDARY_RULES: tuple[str, ...] = (
    "Do not modify or shadow scoreanalyzer parity modules.",
    "Do not register this lane in the runtime difficulty-profile registry.",
    "Do not store artifacts under tests/artifacts/scoreanalyzer_parity.",
    "Do not describe this lane as OG parity or exact Sebastien replication.",
    "Use the Yan paper as the feature-definition source.",
    "Do not depend on unlabeled external Yan results or external Yan code to "
    "name or align features.",
    "Prefer repo-native MusicXML experiments over paper-faithful MIDI claims.",
)

EXPERIMENTAL_FEATURE_STATUSES: dict[str, LaneFeatureStatus] = {
    "length": "implemented",
    "note_density": "implemented",
    "chord_number": "implemented",
    "triad": "implemented",
    "seventh_chord": "implemented",
    "ninth_chord": "implemented",
    "pitch_mean": "implemented",
    "pitch_std": "implemented",
    "pitch_range": "implemented",
    "pitch_entropy": "implemented",
    "deviation_of_pitch_from_C4": "implemented",
    "duration_mean": "implemented",
    "duration_std": "implemented",
    "tempo": "implemented",
    "key_signature": "implemented",
    "black_key_rate": "implemented",
    "polyphony_rate": "implemented",
    "pitch_variability": "implemented",
    "note_duration_variability": "implemented",
    "playing_speed_variation": "implemented",
    "staccato_rate": "implemented",
    "playing_speed": "proxyable",
    "dotted_note_rate": "proxyable",
    "hand_displacement_rate": "proxyable",
    "hand_stretch": "proxyable",
    "distinct_stroke_rate": "proxyable",
    "irregular_rhythm": "proxyable",
    "pressing_velocity_entropy": "blocked",
    "pressing_velocity_variability": "blocked",
    "melodic_complexity": "blocked",
    "melodic_originality": "blocked",
    "degree_of_melodiousness": "blocked",
}


@dataclass(frozen=True, slots=True)
class BoundaryReport:
    lane_id: str
    lane_name: str
    allowed_artifact_root: str
    disallowed_runtime_profile_id: str
    boundary_rules: tuple[str, ...]
    feature_statuses: dict[str, LaneFeatureStatus]

    def to_markdown(self) -> str:
        lines = [
            f"# {self.lane_name}",
            "",
            f"- lane_id: `{self.lane_id}`",
            f"- allowed_artifact_root: `{self.allowed_artifact_root}`",
            f"- disallowed_runtime_profile_id: `{self.disallowed_runtime_profile_id}`",
            "",
            "## Boundary rules",
        ]
        lines.extend(f"- {rule}" for rule in self.boundary_rules)
        lines.extend(["", "## Feature status inventory"])
        for feature_name in sorted(self.feature_statuses):
            status = self.feature_statuses[feature_name]
            lines.append(f"- `{feature_name}`: `{status}`")
        return "\n".join(lines)


def build_boundary_report() -> BoundaryReport:
    return BoundaryReport(
        lane_id=LANE_ID,
        lane_name=LANE_NAME,
        allowed_artifact_root="tests/artifacts/yan2023",
        disallowed_runtime_profile_id="scoreanalyzer_reference",
        boundary_rules=LANE_BOUNDARY_RULES,
        feature_statuses=dict(EXPERIMENTAL_FEATURE_STATUSES),
    )
