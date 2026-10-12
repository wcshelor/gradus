# Passage Practice

This research area plans and incrementally implements a system that turns
a selected piano passage — reached either through a windowed
piano-difficulty hotspot or through a directly user-selected exact region —
into inspectable passage diagnoses and source-derived practice exercises.

The target flow is:

```text
MusicXML / MXL
    -> normalized score facts
    -> investigation region (difficulty hotspot OR user-selected exact region)
    -> event-level attribution
    -> musical pattern hypotheses
    -> passage diagnosis
    -> practice objective and strategy
    -> validated score transformation
    -> MusicXML exercise and grounded explanation
```

Hotspot investigation is one bounded entry experiment, not a gate: the
controlled user-selected path isolates pattern, diagnosis, and transformation
quality from hotspot-detection quality and is required for testing (see
`docs/entry_points.md` for the LS-02 reconciliation map).

The system must not collapse these stages into one opaque prediction. A
difficulty hotspot answers **where to investigate**. A diagnosis answers **what
score evidence and musical pattern may explain the signal**. An exercise is a
separate pedagogical intervention that must state its objective and provenance.

## Current status

This directory contains implemented source/time/passage contract models and tests,
plus the LS-05–LS-07 runtime subset used by the current learning-support slice.
It also now contains an active semantic-music-extraction track: semantic
contracts (`SemanticHypothesis`, `SemanticBundle`), a confidence policy, the
initial view family (`attack_stream`, `written_stream`, `rhythm_grid`,
`texture_grid`, `salience_view`), and the fixture family used by the first
deterministic semantic detectors. It is not yet the full
hotspot-to-diagnosis-to-exercise system described below.

Implemented entry runs include user-selected exact regions and whole-piece
ranges; analyzer-suggested regions share the same `PassageInvestigation`
contract but the full T05.2 analyzer translation remains pending. Neither entry
requires the other (see `docs/entry_points.md`). The implemented LS subset
includes exact passage selection, explicit `PassageInvestigation` origin,
optional difficulty context, pitch-transition observations, and one text-only
transition-practice aid. Diagnosis rules, strategy registries, deterministic
transformations, and MusicXML exercise export remain planned work.

Agents must implement the system through the work packages in
[`WORK_PACKAGES.md`](WORK_PACKAGES.md). The semantic track is tracked in
[`docs/semantic_music_extraction_tasks.md`](docs/semantic_music_extraction_tasks.md).
The initial vertical slice is a restricted broken-chord passage that produces
blocked-chord and rhythmic practice variants.

## Document map

Read these in order before implementation:

1. [`AGENTS.md`](AGENTS.md) — local rules, ownership boundaries, and completion
   requirements.
2. [`docs/architecture.md`](docs/architecture.md) — system layers and dependency
   direction.
3. [`docs/contracts.md`](docs/contracts.md) — proposed stable concepts and
   cross-layer payloads.
4. [`docs/prototype_v1.md`](docs/prototype_v1.md) — deliberately restricted
   first end-to-end prototype.
5. [`WORK_PACKAGES.md`](WORK_PACKAGES.md) — dependency-ordered implementation
   backlog and acceptance criteria.
6. [`IMPLEMENTATION_CHECKLIST.md`](IMPLEMENTATION_CHECKLIST.md) — atomic,
   one-agent-at-a-time tasks with dependencies, limits, test increments, and
   milestone gates.
7. [`docs/testing_strategy.md`](docs/testing_strategy.md) — fixture policy,
   test layers, invariants, and required evidence.
8. [`docs/agent_workflow.md`](docs/agent_workflow.md) — how multiple coding
   agents claim, implement, review, and hand off work safely.
9. [`docs/review_checkpoints.md`](docs/review_checkpoints.md) — lead-review gates
   that prevent locally correct changes from drifting architecturally.
10. [`docs/pedagogy_knowledge_base.md`](docs/pedagogy_knowledge_base.md) — later
   literature-to-diagnosis and diagnosis-to-exercise knowledge work.
11. [`docs/practice_chunk_objects.md`](docs/practice_chunk_objects.md) — current
    practice-chunk-centered object model for evidence, semantic observations,
    display/core regions, and learner-facing explanations.
12. [`docs/semantic_music_extraction_tasks.md`](docs/semantic_music_extraction_tasks.md)
    — historical/current task record for implemented semantic support and
    remaining future work.
13. [`docs/semantic_music_extraction_plan.md`](docs/semantic_music_extraction_plan.md)
    — superseded background plan for broader probabilistic semantic extraction;
    do not treat it as the starting point for new chunk-centered work.
14. [`docs/traceability.md`](docs/traceability.md) — requirements mapped to work
    packages, tests, and review gates.
15. [`docs/thesis_alignment.md`](docs/thesis_alignment.md) — research questions,
    claim boundaries, and evidence needed for the thesis.
16. [`docs/risks.md`](docs/risks.md) — technical and research risks with trigger
    conditions and mitigations.
17. [`docs/agent_prompts.md`](docs/agent_prompts.md) — reusable assignment,
    review, and audit prompts.
18. [`docs/decisions.md`](docs/decisions.md) — accepted decisions and unresolved
    questions.
19. [`handoffs/README.md`](handoffs/README.md) — one-file-per-package completion
    records that parallel branches can merge cleanly.

## Repository boundaries

- `research/piano_difficulty/` owns reusable parsing, normalization, direct
  score descriptors, time windows, and hotspot discovery.
- This area owns passage refinement, semantic pattern recognition, diagnostic
  hypotheses, pedagogical strategy selection, exercise transformations, and
  exercise-focused evaluation.
- `research/shared/` remains empty of speculative abstractions. A type or
  utility moves there only after both research areas use it and its boundary is
  documented.
- Literature metadata and original notes remain in `literature/`. This area may
  store stable source IDs and formalized rules but must not duplicate source
  files or unsupported claims.

## Core vocabulary

- **Score fact**: information directly represented in or deterministically
  normalized from the source score.
- **View**: a reduced projection derived from score facts for a particular
  algorithm.
- **Observation**: a measured event-level or group-level property.
- **Hotspot**: a window selected by a difficulty profile for investigation.
- **Attribution**: evidence identifying dimensions and events responsible for
  a hotspot signal.
- **Pattern**: an evidence-backed interpretation such as a broken chord or
  repeated-note figure.
- **Diagnosis**: a qualified hypothesis about a potential learning challenge.
- **Objective**: the capability a practice intervention intends to develop.
- **Strategy**: a pedagogical approach linked to an objective.
- **Transformation**: a deterministic and provenance-preserving score change.
- **Exercise**: a validated artifact presented to a learner or reviewer.

## Non-goals for the first prototype

- Claiming to identify what a particular learner will find hardest.
- Lossless support for the whole MusicXML standard.
- Automatic fingering or biomechanical advice.
- Unconstrained composition of new etudes.
- Universal melody or voice separation.
- Using an LLM as the sole source of musical analysis or pedagogical truth.
- Building a product interface before the research contracts are validated.

## Definition of program success

The first program milestone is complete when a committed fixture can travel
through the entire documented pipeline and produce:

- a reproducible hotspot;
- the exact events that drove its principal difficulty signals;
- a supported broken-chord pattern match;
- a structured diagnosis with confidence and caveats;
- at least two deterministic, source-derived practice variants;
- valid MusicXML that reopens through the repository parser;
- machine-readable provenance from every generated note to its source notes;
- unit, contract, integration, regression, and negative-path tests; and
- a compact explanation generated only from the structured diagnosis.
