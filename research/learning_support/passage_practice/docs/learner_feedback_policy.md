# Learner Feedback Policy — S5.1 (S-Q005)

Status: accepted 2026-09-10. Blocks S5.2 onward. Decision D-019.

## Allowed feedback fields (synthetic thesis experiments only)

A `LearnerFeedbackSignal` may contain only these structured fields:

| Field | Type | Required | Controlled vocabulary |
|---|---|---|---|
| `feedback_id` | str ID | yes | stable, non-empty, ≤128 chars |
| `source_passage_id` | str ID | yes | `Passage.passage_id` that the feedback addresses |
| `prompt_id` | str ID | yes | one of the S5.3 prompt IDs (e.g., `hardest_aspect`, `melody_hidden`) |
| `answer_kind` | enum | yes | `selected_choice` \| `free_text` \| `skipped` \| `something_else` |
| `selected_value` | str ID | if `selected_choice` | one of the prompt's declared choice IDs |
| `free_text` | str | optional, only if `answer_kind` allows it | verbatim learner text, preserved; never becomes a rule ID |
| `mapped_hypothesis_ids` | tuple[str] | no | hypothesis IDs this feedback could affect, derived by pedagogy mapping |
| `mapped_objective_ids` | tuple[str] | no | objective IDs derived by mapping |
| `retention_scope` | enum | yes | `session` \| `explicit_save` (default `session`) |
| `method_id` / `method_version` | str | yes | provenance of the feedback collector |
| `diagnostics` | tuple[Diagnostic] | no | e.g., `free_text_truncated`, `prompt_unknown` |

Forbidden fields: any `advice_text`, `strategy_id` invented from free text, or
`hypothesis_id` fabricated without semantic grounding. Free text is **data**, not
an instruction that can override pedagogy.

## Retention and privacy (thesis experiments)

- **Retention:** `session` (ephemeral) by default. `explicit_save` only when the
  learner explicitly opts to save; even then it stays thesis-local synthetic
  storage. No automatic persistence across sessions, no background collection.
- **Synthetic-only:** All committed fixtures use synthetic learner text (e.g.,
  `"The jumps feel hard"`). Real learner data collection requires separate owner
  approval, consent infrastructure, and retention/deletion policy outside this
  decision. No real learner data may be committed to the repository.
- **Free text in synthetic tests:** Synthetic `free_text` may be committed when
  it is (a) clearly synthetic, (b) anonymized, and (c) labeled as synthetic in
  the fixture. The text is stored verbatim and never used to override diagnosed
  pedagogy without mapping through `S5.4` rules.
- **Privacy caveats:** Every feedback record carries `diagnostics` noting
  `synthetic_data` vs `real_learner_data` and `retention_scope`. No participant-
  identifiable data, no external transmission, no LLM training on feedback.

## What this decision does not do

- No storage implementation (S5.5/S5.6). No UI, no network, no LLM parsing.
- No real-data handling — that remains blocked until owner review.
- No change to `research/learning_support/learner_context` contracts; this policy
  scopes `passage_practice/learner_feedback` feedback signals only.

## Verification

- Decision entry D-019 in `docs/decisions.md`.
- Tests `tests/unit/test_learner_feedback_signal.py` (S5.2) assert the contract
  accepts synthetic free text and rejects missing passage / unsupported answer
  kind, with `synthetic_data` diagnostic.
