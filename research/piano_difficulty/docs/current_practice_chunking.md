# Current Practice Chunking Lane

Status: current orientation for Clair de Lune semantic extraction and practice
chunk analysis work.

This document is the map to use when deciding which repository paths represent
the current practice-chunk work and which paths are older demo or
learning-support history.

## Current Focus

The active runtime lives in:

```text
research/piano_difficulty/src/piano_difficulty/semantic_tokens/
```

The central builder is `build_semantic_bundle()`, which produces a
`SemanticBundle` containing score events, derived tokens, gestures, musical
objects, object components, and practice chunks.

The current conceptual model is documented in:

```text
research/piano_difficulty/docs/practice_chunks.md
```

That model is:

```text
ScoreEvent
  -> DerivedToken / Gesture
  -> MusicalObject
  -> PracticeChunk
  -> PracticeTransform
```

The current goal is not the old hotspot catalog demo. The goal is to create
musically coherent, evidence-backed `PracticeChunk` objects that a pianist could
notice, isolate, subdivide, inspect, and eventually practice.

## Current Clair De Lune Artifacts

The current Clair de Lune review artifacts are:

```text
research/piano_difficulty/tests/artifacts/practice_chunk_review/clair_de_lune_25_26/
research/piano_difficulty/tests/artifacts/practice_chunk_review/clair_de_lune_27_28/
```

Each review directory contains:

- `review.md`: readable summary of the chunks found in the selected span;
- `chunks.json`: serialized chunk payloads;
- `index.html`: visual review page; and
- `snippets/`: rendered MusicXML and PNG snippets for individual chunks.

These are the best files to inspect when asking, "What did the current
practice-chunk pipeline find in Clair de Lune?"

Related semantic inspection reports live in:

```text
research/piano_difficulty/tests/artifacts/semantic_breakdown/clair_de_lune_current/
```

Those reports describe local semantic/instruction-unit evidence for the same
manual Clair de Lune spans. They are useful, but they are not the same artifact
type as the practice-chunk review.

## Code Paths To Read

- `src/piano_difficulty/semantic_tokens/__init__.py`: bundle entry point.
- `src/piano_difficulty/semantic_tokens/models.py`: `PracticeChunk`,
  `SemanticBundle`, chunk kinds, labels, traits, and affordances.
- `src/piano_difficulty/semantic_tokens/practice_chunks.py`: chunk construction,
  fallback chunks, phrase parents, coordination chunks, and marking enrichment.
- `src/piano_difficulty/semantic_tokens/notation_markings.py`: notation marking
  extraction used as chunk evidence.
- `src/piano_difficulty/semantic_tokens/local_inspection.py`: local semantic
  inspection and Markdown rendering.
- `tests/scripts/generate_practice_chunk_review.py`: generates the visual
  practice-chunk review artifacts.
- `tests/scripts/generate_semantic_breakdown_reports.py`: generates the local
  semantic breakdown reports.

## Older Or Historical Paths

The demo workspace under:

```text
research/learning_support/david_demo/
```

is a historical catalog demo lane. It presents difficulty graphs, candidate
hotspots, and old demo manifests. It is useful for provenance and presentation
history, but it is not the current practice-chunk evidence path.

The broader `research/learning_support/` area contains valuable earlier work:
learner context, interaction harnesses, passage-practice contracts, and
handoffs. Treat those as research history or contract-side context unless a
current task explicitly targets them.

The passage-practice document:

```text
research/learning_support/passage_practice/docs/practice_chunk_objects.md
```

describes the intended learner-facing chunk object from the learning-support
side. The implemented runtime, current Clair de Lune artifacts, and visual QA
live in `research/piano_difficulty/`.

## Common Confusion To Avoid

Do not use `research/learning_support/david_demo/artifacts/debussy_clair_de_lune/`
to evaluate the current semantic-token or practice-chunk work. That directory
belongs to the older hotspot demo.

For current Clair de Lune chunk results, start with:

```text
research/piano_difficulty/tests/artifacts/practice_chunk_review/clair_de_lune_25_26/review.md
research/piano_difficulty/tests/artifacts/practice_chunk_review/clair_de_lune_27_28/review.md
```

For current Clair de Lune semantic inspection, start with:

```text
research/piano_difficulty/tests/artifacts/semantic_breakdown/clair_de_lune_current/
```

## Cleanup Candidates

- Decide whether `practice_chunk_review` or `semantic_breakdown` is the primary
  source of truth for future UI review.
- Reduce fallback noise in narrow selected spans when whole-piece hand-stream or
  passage chunks dilute the review.
- Normalize trait vocabulary before UI use, such as singular/plural duplicate
  traits.
- Keep historical demo renames and documentation cleanup in a separate commit
  from practice-chunk behavior changes.
