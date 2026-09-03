# Project direction

## Working title

**AI-Assisted Learning of Piano Pieces: A Pedagogically Grounded Approach**

## Broad direction

The project explores how computational and AI-assisted systems might help a
person learn a particular piano piece. Existing work on estimating difficulty,
locating demanding passages, and describing score characteristics forms one
possible source of information for that broader goal.

The project is expected to result in one or more helpful systems or prototypes,
developed in collaboration with a company. The exact form of those systems is
not fixed. Possibilities can be investigated without assuming that every idea
will become part of the final thesis.

## Guiding principles

- Start from a real learning need rather than from the availability of an AI
  technique.
- Make the musical or pedagogical basis of assistance inspectable.
- Distinguish observations about a score from claims about an individual
  learner.
- Treat teachers and learners as sources of knowledge, not only as end users.
- Prefer assistance that is understandable and actionable.
- Evaluate usefulness, correctness, and pedagogical suitability rather than
  judging output only by fluency.
- Keep room for non-AI or hybrid baselines where they clarify what the AI
  component contributes.

## Questions intentionally left open

- Which learner group and learning context should the thesis prioritize?
- Which forms of assistance are most useful and feasible?
- What information will be available beyond the symbolic score?
- Which responsibilities belong to analysis, generation, interaction, or human
  judgment?
- How should pedagogical grounding be represented and evaluated?
- What belongs in the research repository and what belongs in the company's
  product environment?

## Current concrete program

The first documented learning-support program is maintained in
`research/learning_support/passage_practice/`. It investigates an explainable
pipeline from windowed difficulty hotspots through event attribution and
semantic passage diagnosis to deterministic, source-derived practice exercises.
This program is a scoped research direction rather than a commitment that every
planned component will appear in the final thesis or product.
