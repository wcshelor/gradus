"""Tests for S5.3 standard feedback prompt registry."""

from __future__ import annotations

import pytest

from passage_practice.learner_feedback.prompts import PROMPT_REGISTRY, get_prompt, list_prompts


def test_stable_ids():
    ids = sorted(PROMPT_REGISTRY.keys())
    assert ids == ["hardest_aspect", "harmony", "jumps", "melody_projection", "reading", "relaxation", "rhythm"]


def test_no_duplicate_choices():
    for prompt in list_prompts():
        assert len(prompt.choice_ids) == len(set(prompt.choice_ids)), f"duplicate in {prompt.prompt_id}"


def test_prompt_to_hypothesis_mappings():
    hardest = get_prompt("hardest_aspect")
    assert hardest.hypothesis_mapping["melody_stand_out"] == "pedagogy.melody_projection"
    assert hardest.hypothesis_mapping["both_hands_together"] == "pedagogy.rhythmic_coordination"
    assert hardest.hypothesis_mapping["moving_positions"] == "pedagogy.bass_leap"
    assert hardest.hypothesis_mapping["finding_notes"] == "pedagogy.reading_load"
    assert get_prompt("melody_projection").hypothesis_mapping["melody_hidden"] == "pedagogy.melody_projection"
    assert get_prompt("rhythm").hypothesis_mapping["hands_together_hard"] == "pedagogy.rhythmic_coordination"
    assert get_prompt("jumps").hypothesis_mapping["jumps_hard"] == "pedagogy.bass_leap"
    assert get_prompt("reading").hypothesis_mapping["reading_hard"] == "pedagogy.reading_load"


def test_unknown_prompt_raises():
    with pytest.raises(KeyError):
        get_prompt("unknown_prompt")
