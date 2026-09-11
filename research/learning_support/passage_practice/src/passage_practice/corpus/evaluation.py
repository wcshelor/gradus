"""S8.6 corpus evaluation checklist — programmatic representation.

Provides the teacher-review questions for S8.6 and a helper to validate
that a checklist covers the required dimensions. No real participant data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CHECKLIST_VERSION = "corpus_evaluation_checklist.v1"

# Required dimensions and their question IDs
REQUIRED_DIMENSIONS: dict[str, list[str]] = {
    "plausibility": ["P1", "P2"],
    "usefulness": ["U1", "U2"],
    "traceability": ["T1", "T2"],
    "overclaiming": ["O1", "O2"],
    "exercise_fit": ["E1", "E2"],
}

QUESTIONS: dict[str, str] = {
    "P1": "Does the top semantic hypothesis match what a musician hears?",
    "P2": "Are plausible alternatives also present (no false certainty)?",
    "U1": "Does the explanation suggest an actionable next step fitting the passage?",
    "U2": "Is the exercise candidate appropriate for the hypothesized difficulty?",
    "T1": "Can every explanation sentence be traced to a supporting claim in the brief?",
    "T2": "Do source IDs resolve and point to the correct passage?",
    "O1": "Does the explanation avoid unsupported melody/harmony/learner/difficulty claims?",
    "O2": "Is uncertainty wording present and appropriate (likely/may/possible)?",
    "E1": "Does the exercise preserve pitch/voice relationships where required?",
    "E2": "Is the exercise within the supported subset?",
}


@dataclass(frozen=True, slots=True)
class Checklist:
    version: str
    questions: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.version != CHECKLIST_VERSION:
            raise ValueError(f"version must be {CHECKLIST_VERSION!r}, got {self.version!r}")
        if set(self.questions) != set(QUESTIONS):
            missing = set(QUESTIONS) - set(self.questions)
            extra = set(self.questions) - set(QUESTIONS)
            raise ValueError(f"checklist must contain exactly {sorted(QUESTIONS)}; missing {missing}, extra {extra}")

    def covers_all_dimensions(self) -> bool:
        for dim, qids in REQUIRED_DIMENSIONS.items():
            if not all(q in self.questions for q in qids):
                return False
        return True


def load_checklist() -> Checklist:
    """Load the canonical S8.6 checklist."""
    return Checklist(version=CHECKLIST_VERSION, questions=tuple(sorted(QUESTIONS)))


def evaluate_checklist(checklist: Checklist) -> dict[str, Any]:
    """Validate that a checklist covers all required dimensions."""
    if not isinstance(checklist, Checklist):
        raise TypeError(f"checklist must be Checklist, got {type(checklist).__name__}")
    return {
        "version": checklist.version,
        "covers_all_dimensions": checklist.covers_all_dimensions(),
        "dimensions": {dim: all(q in checklist.questions for q in qids) for dim, qids in REQUIRED_DIMENSIONS.items()},
        "question_count": len(checklist.questions),
    }


__all__ = ["Checklist", "CHECKLIST_VERSION", "QUESTIONS", "REQUIRED_DIMENSIONS", "load_checklist", "evaluate_checklist"]
