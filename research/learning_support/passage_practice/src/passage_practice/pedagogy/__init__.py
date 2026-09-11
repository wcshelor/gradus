"""Pedagogical hypothesis bridge — S4.1 input boundary.

Re-exports boundary validator for S4.1 tests. Rule metadata lives in
`pedagogy.rules` (S4.2), concrete hypotheses in后续 S4.3+ modules.
"""

from .bass_leap import BASS_LEAP_RULE, build_bass_leap_hypothesis
from .boundary import validate_pedagogical_inputs
from .compatibility import COMPATIBILITY_TABLE, get_compatible_strategies
from .integration import PedagogicalReport, build_pedagogical_report
from .melody_projection import MELODY_PROJECTION_RULE, build_melody_projection_hypothesis
from .reading_load import READING_LOAD_RULE, build_reading_load_hypothesis
from .rhythmic_coordination import RHYTHMIC_COORDINATION_RULE, build_rhythmic_coordination_hypothesis

__all__ = [
    "BASS_LEAP_RULE",
    "COMPATIBILITY_TABLE",
    "MELODY_PROJECTION_RULE",
    "READING_LOAD_RULE",
    "RHYTHMIC_COORDINATION_RULE",
    "PedagogicalReport",
    "build_bass_leap_hypothesis",
    "build_melody_projection_hypothesis",
    "build_pedagogical_report",
    "build_reading_load_hypothesis",
    "build_rhythmic_coordination_hypothesis",
    "get_compatible_strategies",
    "validate_pedagogical_inputs",
]
