"""S5.3 standard feedback prompt registry.

Controlled prompts for hardest aspect, melody projection, rhythm, jumps,
reading, harmony, and relaxation. Each prompt has stable ID, controlled
choice IDs, and a mapping to pedagogical hypothesis types it can inform.

Design refs:
- docs/learner_feedback_policy.md (D-019)
- learner_feedback/contracts.py (LearnerFeedbackSignal)
- pedagogy/ contracts: pedagogy.melody_projection etc.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedbackPrompt:
    prompt_id: str
    question_text: str
    choice_ids: tuple[str, ...]
    hypothesis_mapping: dict[str, str]  # choice_id -> hypothesis_type or "" for no mapping

    def __post_init__(self) -> None:
        if not isinstance(self.prompt_id, str) or not self.prompt_id:
            raise ValueError(f"prompt_id must be non-empty str, got {self.prompt_id!r}")
        if not isinstance(self.question_text, str) or not self.question_text:
            raise ValueError("question_text must be non-empty str")
        if not isinstance(self.choice_ids, tuple):
            raise TypeError("choice_ids must be tuple")
        for c in self.choice_ids:
            if not isinstance(c, str) or not c:
                raise ValueError(f"choice_id must be non-empty str, got {c!r}")
        if len(set(self.choice_ids)) != len(self.choice_ids):
            raise ValueError(f"duplicate choice_ids in {self.prompt_id!r}: {self.choice_ids!r}")
        if not isinstance(self.hypothesis_mapping, dict):
            raise TypeError("hypothesis_mapping must be dict")
        for choice, hyp in self.hypothesis_mapping.items():
            if choice not in self.choice_ids:
                raise ValueError(f"mapping choice {choice!r} not in choice_ids for {self.prompt_id!r}")
            if not isinstance(hyp, str):
                raise ValueError(f"hypothesis_mapping value must be str, got {hyp!r}")


PROMPT_REGISTRY: dict[str, FeedbackPrompt] = {}


def _register(prompt: FeedbackPrompt) -> FeedbackPrompt:
    if prompt.prompt_id in PROMPT_REGISTRY:
        raise ValueError(f"duplicate prompt_id {prompt.prompt_id!r}")
    PROMPT_REGISTRY[prompt.prompt_id] = prompt
    return prompt


# Standard prompts (S5.3 scope: hardest aspect + 6 families)
_hardest_aspect = _register(
    FeedbackPrompt(
        prompt_id="hardest_aspect",
        question_text="What feels hardest in this section?",
        choice_ids=(
            "finding_notes",
            "keeping_rhythm",
            "moving_positions",
            "both_hands_together",
            "melody_stand_out",
            "understanding_harmony",
            "keeping_relaxed",
            "something_else",
        ),
        hypothesis_mapping={
            "finding_notes": "pedagogy.reading_load",
            "keeping_rhythm": "pedagogy.rhythmic_coordination",
            "moving_positions": "pedagogy.bass_leap",
            "both_hands_together": "pedagogy.rhythmic_coordination",
            "melody_stand_out": "pedagogy.melody_projection",
            "understanding_harmony": "",
            "keeping_relaxed": "",
            "something_else": "",
        },
    )
)

_melody_projection = _register(
    FeedbackPrompt(
        prompt_id="melody_projection",
        question_text="Is the melody clear or hidden in the texture?",
        choice_ids=("melody_hidden", "melody_clear", "not_sure"),
        hypothesis_mapping={
            "melody_hidden": "pedagogy.melody_projection",
            "melody_clear": "",
            "not_sure": "",
        },
    )
)

_rhythm = _register(
    FeedbackPrompt(
        prompt_id="rhythm",
        question_text="How does the rhythm feel between the hands?",
        choice_ids=("hands_together_hard", "hands_together_ok", "not_sure"),
        hypothesis_mapping={
            "hands_together_hard": "pedagogy.rhythmic_coordination",
            "hands_together_ok": "",
            "not_sure": "",
        },
    )
)

_jumps = _register(
    FeedbackPrompt(
        prompt_id="jumps",
        question_text="How do the large jumps or position changes feel?",
        choice_ids=("jumps_hard", "jumps_ok", "not_sure"),
        hypothesis_mapping={
            "jumps_hard": "pedagogy.bass_leap",
            "jumps_ok": "",
            "not_sure": "",
        },
    )
)

_reading = _register(
    FeedbackPrompt(
        prompt_id="reading",
        question_text="How is reading the notation?",
        choice_ids=("reading_hard", "reading_ok", "not_sure"),
        hypothesis_mapping={
            "reading_hard": "pedagogy.reading_load",
            "reading_ok": "",
            "not_sure": "",
        },
    )
)

_harmony = _register(
    FeedbackPrompt(
        prompt_id="harmony",
        question_text="How clear is the harmony or chord progression?",
        choice_ids=("harmony_unclear", "harmony_clear", "not_sure"),
        hypothesis_mapping={
            "harmony_unclear": "",
            "harmony_clear": "",
            "not_sure": "",
        },
    )
)

_relaxation = _register(
    FeedbackPrompt(
        prompt_id="relaxation",
        question_text="How relaxed does playing feel?",
        choice_ids=("tense", "relaxed", "not_sure"),
        hypothesis_mapping={
            "tense": "",
            "relaxed": "",
            "not_sure": "",
        },
    )
)


def get_prompt(prompt_id: str) -> FeedbackPrompt:
    try:
        return PROMPT_REGISTRY[prompt_id]
    except KeyError as exc:
        raise KeyError(f"unknown prompt_id {prompt_id!r}") from exc


def list_prompts() -> list[FeedbackPrompt]:
    return [PROMPT_REGISTRY[k] for k in sorted(PROMPT_REGISTRY)]


__all__ = ["FeedbackPrompt", "PROMPT_REGISTRY", "get_prompt", "list_prompts"]
