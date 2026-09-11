# Annotation Schema — S7.1 (S-Q006)

Status: accepted 2026-09-10. Decision D-020.

## Purpose

Define fields for human labels used in S7.2+ annotation records and S7.3
synthetic fixtures. The schema covers semantic roles, texture, phrase,
harmony, difficulty reason, learner issue, advice, and reviewer status.
It is synthetic-only for the thesis phase; no real learner data is committed.

## Label families and values (controlled vocabularies)

| Family | Label value examples (controlled) | Supports |
|---|---|---|
| `melody` | `top_voice`, `left_hand`, `inner_voice`, `hidden`, `none` | S2.8/S3.2 salience |
| `bass` | `anchor`, `walking`, `pedal`, `melodic`, `none` | S3.3 |
| `accompaniment` | `broken_chord`, `alberti`, `block`, `arpeggiated`, `ostinato`, `none` | S3.4 |
| `texture` | `monophonic`, `homophonic_block`, `melody_plus_accompaniment`, `arpeggiated`, `polyphonic` | S3.6 |
| `phrase` | `boundary`, `continuation`, `ambiguous` | S6.5 |
| `harmony` | `local_key_C`, `local_key_G`, `cadence`, `no_cadence`, `ambiguous` | S6.1-S6.4 |
| `difficulty_reason` | `leap`, `rhythm`, `reading`, `coordination`, `harmony`, `none` | S4.3-S4.6 pedagogy |
| `learner_issue` | `melody_hidden`, `jumps_hard`, `hands_together`, `reading_hard`, `none` | S4.3-S4.6 |
| `advice` | `simplify_accompaniment`, `blocked_bass`, `hands_separate`, `harder_chunking` | S4.7 compatibility |

## Record fields (S7.2 contract)

| Field | Type | Required | Notes |
|---|---|---|---|
| `annotation_id` | str ID | yes | stable, ≤128 chars |
| `source_passage_id` | str ID | yes | `Passage.passage_id` |
| `label_family` | enum | yes | one of the families above |
| `label_value` | str | yes | must be in family's controlled vocabulary |
| `annotator_role` | enum | yes | `teacher` \| `researcher` \| `synthetic` |
| `confidence` | float | yes | bounded [0,1], heuristic for synthetic |
| `provenance` | str | yes | `synthetic` \| `human` |
| `review_state` | enum | yes | `unreviewed` \| `reviewed` \| `disputed` |
| `privacy_status` | enum | yes | `synthetic` \| `anonymized` (real data blocked) |
| `source_refs` | tuple[SourceRef] | no | optional resolvable refs for melody/bass events |
| `diagnostics` | tuple[Diagnostic] | no | e.g., `synthetic_data`, `unresolved_passage` |
| `schema_version` | str | yes | `annotation.v1` |

## Privacy and synthetic-only policy

- All committed fixtures use `annotator_role=synthetic`, `provenance=synthetic`,
  `privacy_status=synthetic`, and synthetic passage IDs from `semantic_*` fixtures.
- No real learner data, no PII, no external transmission.
- Real human labels require separate owner-approved annotation workflow with
  consent and anonymization; not authorized by this decision.

## What this decision does not do

- No `AnnotationRecord` implementation (S7.2), no fixtures (S7.3), no model
  interface (S7.5).
- No change to `ScoreIR` or semantic detectors.

## Verification

- Decision entry D-020 in `docs/decisions.md`.
- S7.2 tests will assert deterministic serialization, controlled vocabulary
  enforcement, and no private data in synthetic fixtures.
