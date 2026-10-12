# Practice Chunk Objects

Status: current learner-facing chunk-object orientation for passage-practice
contracts. The implemented runtime and current Clair de Lune artifacts live in
`research/piano_difficulty/`; see
`research/piano_difficulty/docs/current_practice_chunking.md`.
This document supersedes `semantic_music_extraction_plan.md` as the main mental
model for new planning. The older plan remains historical background for the
semantic contracts that were already implemented, but future work should start
from the bounded practice chunk object described here.

## Goal

A practice chunk is the learner-facing unit that connects score evidence,
difficulty signals, semantic observations, and explanation. The chunk is not a
raw hotspot and not a whole-piece semantic analysis. It is a bounded musical
region that can be shown, discussed, practiced, evaluated, and traced back to
the score evidence that justified it.

The current working flow is:

```text
score and difficulty evidence
  -> candidate detection windows
  -> grouped practice chunk
  -> chunk evidence brief
  -> chunk semantic observations
  -> learner-facing explanation or next action
```

## Canonical Shape

A practice chunk contains:

- stable chunk identity and schema/method versions;
- source score identity and piece metadata;
- `core_region`: the merged region where evidence actually triggered;
- `display_region` / `practice_region`: the buffered region shown or assigned
  to the learner;
- supporting detection windows, including resolution, measure range, score, and
  available section/window IDs;
- supporting feature, factor, dimension, or graph-dimension IDs when available;
- an evidence brief summarizing local score-derived support and caveats;
- zero or more semantic observations with kind, wording, confidence,
  support level, and evidence IDs;
- learner-facing observations or summary text derived from structured evidence;
- snippet/rendering status when a visual excerpt is produced; and
- diagnostics for missing evidence, unsupported score facts, or rendering gaps.

`core_region` and `display_region` must stay separate. The core answers "what
triggered"; the display/practice region answers "what should the learner see or
work on." A chunk may be created from automatic evidence, manual selection, or a
later learner-adjusted focus, but the origin must remain explicit.

## Boundaries

A practice chunk may carry semantic observations, but it does not require the
system to produce a complete musical analysis. It should prefer a small set of
evidence-backed claims over broad interpretation.

Allowed claims:

- bounded observations supported by local score or difficulty evidence;
- qualified semantic statements such as coordination offset, sustained versus
  moving texture, hand movement plus active layer, or a detected pattern;
- uncertainty, missingness, and "not enough evidence" states; and
- learner-facing wording generated from the chunk's structured evidence.

Disallowed claims:

- unsupported melody, harmony, contour, arpeggio, fingering, or technique
  assertions;
- learner-specific diagnosis without learner evidence;
- raw hotspot IDs as the primary subject of downstream explanation;
- semantic observations that cannot cite the score facts or feature evidence
  that produced them; and
- practice actions that hide their source region or transformation provenance.

## Relationship To Existing Contracts

`PassageInvestigation` remains the passage-first request envelope for both
automatic and user-selected entry paths. Practice chunks are the presentation
and practice-target objects that can be built from one or more passages,
detection windows, or grouped regions.

Existing semantic contracts still matter, but as chunk-attached evidence:

- views and observations provide the facts a chunk may cite;
- `SemanticHypothesis` / `SemanticBundle` can attach richer interpretations to a
  chunk when implemented for a supported family;
- diagnosis, strategy, and transformation contracts should consume chunks or
  chunk-backed passages rather than raw difficulty hotspots; and
- learner feedback should adjust the ranked focus for a chunk without rewriting
  the score-derived evidence.

The David demo manifest currently uses the names `hard_bits`, `practice_regions`,
and `grouped_hard_bits` for this object family. Those names are compatible with
the practice chunk model; future passage-practice code can choose a stable
contract name once the reusable boundary is clearer.

## Verification

Chunk-producing code should verify:

- every chunk has non-empty core and display/practice regions;
- display/practice regions preserve the documented buffer policy and score
  bounds;
- supporting windows are non-empty for analyzer-derived chunks;
- semantic observations cite evidence IDs present in the chunk or its evidence
  brief;
- learner-facing summaries do not introduce claims absent from structured
  evidence; and
- raw hotspots remain inspectable as provenance/debug evidence rather than the
  learner-facing object.
