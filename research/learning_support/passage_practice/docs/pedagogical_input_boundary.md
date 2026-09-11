# Pedagogical hypothesis input boundary — S4.1

Status: accepted 2026-09-10. Blocks S4.2 onward.

## Allowed inputs to pedagogical hypothesis construction

Only these structured evidence types may feed a `PedagogicalHypothesis` or
`DiagnosisRule` evaluation. All are versioned contracts with stable IDs and
provenance; free-text advice is never an input.

| Input family | Contract | Required fields consumed | Optional fields consumed | Forbidden |
|---|---|---|---|---|
| Semantic bundle | `SemanticBundle` (`semantics/contracts.py`, `semantic_bundle.v1`) + `SemanticHypothesis` | `source_passage_id`, `hypothesis_id`, `hypothesis_type`, `covered_event_ids`, `covered_region`, `confidence`, `confidence_method` | `supporting_observation_ids`, `satisfied_criteria`, `contradictory_criteria`, `missing_evidence`, `diagnostics` | Raw MusicXML parsing, hotspot IDs as primary subject |
| Difficulty context | `DifficultyEvidence` (`models/investigation.py`, `difficulty_evidence.v1`) | `source_score_id`, `covered_region`, `method_id`, `method_version` | `hotspot_id`, `window_score`, `contributions` only when produced by real analysis result | Fabricated contribution values, unvalidated score refs, calibrated grade claims |
| Learner feedback | `LearnerFeedbackSignal` (planned `learner_feedback/contracts.py`, not yet implemented) or existing `learner_context` verbatim `JournalEntry` via `report_refs` | `entry_id`, `source_passage_id`/`passage_ref`, `text` verbatim preserved, `scope`, `recorded_at` | `context_permission`, `tags` | Raw free-text advice like `"play more musically"` as a rule input; inferred traits; external model outputs |
| Score facts | `Passage` + `ScoreIR` via `SourceRef` | `passage_id`, `score_id`, `region`, `event_refs` (logical/written) | `hand` scoping (INFERENCE basis) | `SourceRef` that does not resolve in the provided `ScoreIR`; floating-point time |

## Rejection rules (contract-level, tested in S4.1)

1. **Raw free-text advice is rejected.** A pedagogical hypothesis factory must not
   accept an `advice_text: str` or `free_text_diagnosis: str` parameter. Text
   that reaches `AssistanceResult` or future `PedagogicalHypothesis` must be a
   template-derived label from `satisfied_criteria` plus confidence band wording,
   never the learner's or author's raw sentence. Tests assert `ValueError` or
   `TypeError` when `advice_text` is supplied.

2. **Unsupported score refs are rejected.** A ref of kind `logical_note` or
   `written_note` that does not resolve via `resolve_ref(score, ref)` is
   rejected at construction or at evaluation time with diagnostic
   `unresolvable_score_ref` / `unsupported_passage_ref`. Empty `covered_event_ids`
   is rejected (no provenance). Tests assert creation fails or evaluation
   returns an error diagnostic, not a silent hypothesis.

3. **Hotspot ID is never the primary subject.** The passage ID is required;
   hotspot IDs travel only inside `DifficultyEvidence` as optional `hotspot_id`.
   A pedagogical hypothesis whose `source_passage_id` is a hotspot/section ID
   rather than a `Passage.passage_id` is rejected.

4. **Layer direction preserved.** `passage_practice/pedagogy` may depend on
   `models`, `semantics`, and `observations`; it must not import `piano_difficulty`
   runtime beyond `ScoreIR`+`SourceRef`, and no upstream layer may import
   pedagogical types. Score facts remain FACT/INFERENCE-tagged; learner caveats
   remain explicit.

5. **Unproven effectiveness.** All pedagogical hypotheses carry
   `method_version` provenance and `learner_caveats`; presentation must not
   claim calibrated learner difficulty.

## What S4.1 does not do

- No `PedagogicalHypothesis` richness beyond the boundary validator (S4.2 defines
  rule metadata, S4.3+ define concrete hypotheses).
- No learner-feedback storage or retention policy (S5.1).
- No difficulty grade or trait inference.

## Verification

`tests/unit/test_pedagogical_input_boundary.py` asserts rejection of
`advice_text` / `free_text_diagnosis` and of an unresolvable `SourceRef`, plus
acceptance of a valid semantic+score-ref input. See also S4.2 for rule-level
validation.
