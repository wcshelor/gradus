"""Learner feedback loop — S5.

S5.2 contracts, S5.3 prompts, S5.4 mappings, S5.5 adjusted focus live here.
"""

from .adjusted_focus import LearnerAdjustedFocus, build_learner_adjusted_focus
from .contracts import AnswerKind, LearnerFeedbackSignal, RetentionScope
from .mapping import FeedbackAdjustment, map_feedback
from .prompts import FeedbackPrompt, PROMPT_REGISTRY, get_prompt, list_prompts

__all__ = [
    "AnswerKind",
    "FeedbackAdjustment",
    "FeedbackPrompt",
    "LearnerAdjustedFocus",
    "LearnerFeedbackSignal",
    "PROMPT_REGISTRY",
    "RetentionScope",
    "build_learner_adjusted_focus",
    "get_prompt",
    "list_prompts",
    "map_feedback",
]
