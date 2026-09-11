"""S5.4 feedback mapping rules.

Maps selected answers to hypothesis adjustments: increase, decrease,
rejection, or request for more evidence. The mapping operates on
controlled choice IDs via the prompt registry, never on raw free text.

Design refs:
- learner_feedback/contracts.py (LearnerFeedbackSignal)
- learner_feedback/prompts.py (PROMPT_REGISTRY, hypothesis_mapping)
- pedagogy/ contracts (PedagogicalHypothesis types)
"""

from __future__ import annotations

from dataclasses import dataclass

from passage_practice.learner_feedback.contracts import AnswerKind, LearnerFeedbackSignal
from passage_practice.learner_feedback.prompts import PROMPT_REGISTRY
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis


@dataclass(frozen=True, slots=True)
class FeedbackAdjustment:
    """Result of mapping one feedback signal onto pedagogical hypotheses.

    - boosted_ids: hypothesis types to increase (multiply confidence)
    - demoted_ids: hypothesis types to decrease
    - rejected_ids: hypothesis types to deprioritize entirely
    - request_more_evidence: whether to ask for more evidence
    - preserved: whether to preserve original score hypotheses unchanged
    - diagnostics: mapping diagnostics
    """

    boosted_ids: tuple[str, ...] = ()
    demoted_ids: tuple[str, ...] = ()
    rejected_ids: tuple[str, ...] = ()
    request_more_evidence: bool = False
    preserved: bool = False
    diagnostics: tuple[Diagnostic, ...] = ()


def map_feedback(
    signal: LearnerFeedbackSignal,
    hypotheses: tuple[PedagogicalHypothesis, ...] = (),
) -> FeedbackAdjustment:
    """Map ``signal`` to adjustments over ``hypotheses``.

    Rules:
    - ``something_else`` (either answer_kind SOMETHING_ELSE or selected_value
      ``something_else``) → preserved=True, no boost/demote, keep score
      hypotheses.
    - ``selected_choice`` with a mapped hypothesis_type → boosted_ids contains
      that hypothesis_type; if the mapped type matches one of the supplied
      hypotheses, that focus is boosted.
    - ``melody_hidden`` choice → boost melody_projection; ``hands_together_hard``
      → boost rhythmic_coordination, etc. via registry mapping.
    - ``not_sure`` / ``skipped`` → request_more_evidence=True.
    - Free text alone (no selected_value mapping) → preserved + request_more_evidence.
    - Demotion example: if learner says melody_clear, demote melody_projection.
    """
    if not isinstance(signal, LearnerFeedbackSignal):
        raise TypeError(f"signal must be LearnerFeedbackSignal, got {type(signal).__name__}")

    diagnostics: list[Diagnostic] = []

    # Something else preserves score hypotheses
    if signal.answer_kind == AnswerKind.SOMETHING_ELSE or signal.selected_value == "something_else":
        diagnostics.append(
            Diagnostic(
                code="feedback_preserved",
                severity=Severity.INFO,
                message=f"feedback {signal.feedback_id!r} is something_else; preserving score hypotheses",
            )
        )
        return FeedbackAdjustment(preserved=True, diagnostics=tuple(diagnostics))

    if signal.answer_kind in (AnswerKind.SKIPPED, AnswerKind.FREE_TEXT) and signal.selected_value is None:
        # No controlled choice → preserve + request evidence if free text
        if signal.answer_kind == AnswerKind.SKIPPED:
            diagnostics.append(Diagnostic(code="feedback_skipped", severity=Severity.INFO, message="skipped; preserving"))
            return FeedbackAdjustment(preserved=True, diagnostics=tuple(diagnostics))
        diagnostics.append(Diagnostic(code="free_text_preserved", severity=Severity.INFO, message="free text preserved; requesting more evidence"))
        return FeedbackAdjustment(preserved=True, request_more_evidence=True, diagnostics=tuple(diagnostics))

    # For selected_choice, look up prompt mapping
    prompt = PROMPT_REGISTRY.get(signal.prompt_id)
    if prompt is None:
        diagnostics.append(Diagnostic(code="unknown_prompt", severity=Severity.WARNING, message=f"unknown prompt {signal.prompt_id!r}"))
        return FeedbackAdjustment(preserved=True, request_more_evidence=True, diagnostics=tuple(diagnostics))

    selected = signal.selected_value
    if selected is None:
        diagnostics.append(Diagnostic(code="no_selected_value", severity=Severity.INFO, message="no selected_value; preserving"))
        return FeedbackAdjustment(preserved=True, diagnostics=tuple(diagnostics))

    mapped_type = prompt.hypothesis_mapping.get(selected, "")
    if mapped_type == "":
        # Demotion signals have empty mapping but still indicate demotion (e.g., *_ok, melody_clear)
        demotion_for_ok = {
            "hands_together_ok": "pedagogy.rhythmic_coordination",
            "jumps_ok": "pedagogy.bass_leap",
            "reading_ok": "pedagogy.reading_load",
            "melody_clear": "pedagogy.melody_projection",
        }
        if selected in demotion_for_ok:
            demoted_hyp = demotion_for_ok[selected]
            diagnostics.append(Diagnostic(code="feedback_demoted", severity=Severity.INFO, message=f"demoting {demoted_hyp!r} due to {selected!r}"))
            return FeedbackAdjustment(demoted_ids=(demoted_hyp,), diagnostics=tuple(diagnostics))
        # Choices like not_sure, understanding_harmony with no pedagogical mapping
        if selected in ("not_sure",):
            diagnostics.append(Diagnostic(code="request_more_evidence", severity=Severity.INFO, message=f"selected {selected!r} requests more evidence"))
            return FeedbackAdjustment(request_more_evidence=True, diagnostics=tuple(diagnostics))
        diagnostics.append(Diagnostic(code="no_mapping", severity=Severity.INFO, message=f"choice {selected!r} has no hypothesis mapping; preserving"))
        return FeedbackAdjustment(preserved=True, diagnostics=tuple(diagnostics))

    # Mapped type: boost it
    boosted: tuple[str, ...] = (mapped_type,)
    diagnostics.append(Diagnostic(code="feedback_boosted", severity=Severity.INFO, message=f"boosting {mapped_type!r} from {selected!r}"))

    # Example demotion: if learner says melody_clear, we would demote melody_projection
    # Encode as: choices ending _clear or _ok imply demotion of the mapped type's alternative
    demoted: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()
    if selected in ("melody_clear",):
        # Melody clear demotes hidden projection
        demoted = (mapped_type,) if mapped_type == "" else ()
        # Actually melody_clear has no mapping, so we handle via explicit choice
        # For demo, treat melody_clear as demotion signal for melody_projection
        # Since mapping is empty for melody_clear, we synthesize demotion
        if selected == "melody_clear":
            demoted = ("pedagogy.melody_projection",)
            boosted = ()
            diagnostics.append(Diagnostic(code="feedback_demoted", severity=Severity.INFO, message="demoting melody_projection due to melody_clear"))
    if selected in ("hands_together_ok", "jumps_ok", "reading_ok"):
        # These imply coordination/jumps/reading less hard → demote corresponding
        mapping_for_ok = {
            "hands_together_ok": "pedagogy.rhythmic_coordination",
            "jumps_ok": "pedagogy.bass_leap",
            "reading_ok": "pedagogy.reading_load",
        }
        demoted_hyp = mapping_for_ok.get(selected, "")
        if demoted_hyp:
            demoted = (demoted_hyp,)
            boosted = ()
            diagnostics.append(Diagnostic(code="feedback_demoted", severity=Severity.INFO, message=f"demoting {demoted_hyp!r} due to {selected!r}"))

    return FeedbackAdjustment(
        boosted_ids=boosted,
        demoted_ids=demoted,
        rejected_ids=rejected,
        preserved=not boosted and not demoted and not rejected,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["FeedbackAdjustment", "map_feedback"]
