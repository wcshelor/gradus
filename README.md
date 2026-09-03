# Gradus

`gradus` is the working repository for the master's thesis:

> **AI-Assisted Learning of Piano Pieces: A Pedagogically Grounded Approach**

The repository is intentionally broad at this stage. It brings together score
analysis, exploratory learning-support ideas, research questions, prototypes,
and the eventual thesis manuscript without committing the project to a single
AI technique or product design too early.

## Repository map

- `research/piano_difficulty/` contains the existing piano-difficulty project
  as a self-contained research subproject, including its code, tests, datasets,
  documentation, and generated evidence.
- `research/learning_support/` is the staging area for experiments that help a
  pianist learn a particular piece. Its `passage_practice/` program specifies a
  test-driven architecture from difficulty hotspots to diagnoses and generated
  practice exercises.
- `research/shared/` is reserved for concepts or utilities that are genuinely
  shared by more than one research area.
- `brainstorm/` collects possibilities, questions, sketches, and unresolved
  ideas. Material here is exploratory rather than a project commitment.
- `prompts/` contains prompts for research, design discussions, literature
  exploration, and prototype ideation. These are not production prompt
  templates.
- `literature/` contains reading lists, citation records, original notes, and a
  Git-ignored local archive for paper files.
- `docs/` contains repository-wide direction and decisions.
- `thesis/` is reserved for the thesis outline, manuscript, and submission
  material when that work begins.

## Current status

The most developed part of the repository is the difficulty-analysis
subproject. It can identify and describe score-level and passage-level demands.
The documentation-first passage-practice program now defines how agents can
extend that foundation into event attribution, semantic diagnosis, controlled
score transformations, and evaluation while keeping pedagogical claims
inspectable.

To work on or run the existing Python project, begin in
`research/piano_difficulty/` and follow its README.

To implement the passage-practice program, begin with
`research/learning_support/passage_practice/README.md` and its scoped
`AGENTS.md`.

## Setup (fresh clone)

```bash
git clone --recurse-submodules git@github.com:wcshelor/gradus.git
# or, if already cloned without submodules:
git submodule update --init --recursive
conda env create -f research/piano_difficulty/environment.yml
conda activate piano-difficulty
# verify baseline:
conda run -n piano-difficulty python -m pytest -q --ignore=research/piano_difficulty/external
```
