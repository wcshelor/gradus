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
  pianist learn a particular piece. It now contains the completed LS-01–LS-11
  first research slice: optional learner context, exact passage selection,
  bounded semantic observations, one grounded text aid, a deterministic
  interaction harness, evaluation evidence, and the next CEO-demo milestone
  plan. Its `passage_practice/` program remains one route to assistance, not
  the mandatory workflow.
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

The project is organized around three complementary areas: semantic understanding
of a piece, development of pedagogical assistance, and flexible interaction.
Optional practice notes and learner-reported difficulties can provide context;
neither continuous tracking nor a fixed learning sequence is required. Live-playing
feedback and MIDI/audio performance capture are outside the current scope.

See [project direction](docs/project_direction.md) and
[the three-area implementation plan](docs/Task_list_2026-09-05_flexible_piano_learning_support.md).
These describe the broader program; difficulty analysis is one reusable capability.

As of 2026-09-06, LS-01 through LS-11 are implemented and pending lead/human
review. The current learning-support slice can:

- select exact user passages or whole-piece ranges from symbolic score data;
- save, inspect, correct, exclude, delete, and optionally ignore learner notes;
- produce one bounded semantic observation family over pitch transitions;
- generate one traceable text-only practice aid when the evidence supports it;
- replay multi-visit synthetic histories without inferring progress, traits, or
  playing ability; and
- evaluate the slice through a reproducible technical report.

The next selected increment is a thin local
[CEO walkthrough prototype](research/learning_support/ceo_demo_milestone_2026-09-06.md),
planned but not yet built. It should make the existing capabilities visible,
including the difficulty graph, learner notes, manual measure ranges, and
score-only versus score-plus-report comparisons.

The current CEO demo workspace is
[`research/learning_support/ceo_demo/`](research/learning_support/ceo_demo/README.md).
For the walkthrough, it deliberately uses a compact set of score-native,
learner-legible feature families: note/attack density, rhythmic variety,
leaps/displacement, hand span/chord size, polyphony/chord density, hand
coordination, accidentals/reading load, descriptive articulation/dynamics, and
a hotspot timeline over those signals. Ambiguous Yan et al. features such as
distinct stroke rate, playing-speed variation, pressing velocity, melodic
originality/melodiousness, and deeper structural-pattern modeling are deferred
to the research track. They should be revisited after the demo through
candidate feature banks and prediction tests against difficulty labels as one
validity measure.

Difficulty-analysis consolidation remains a component milestone. Its public
workflow now produces factor summaries, local peaks, candidate high-demand sections,
hand views, and JSON/Markdown/CSV/HTML reports:

```bash
conda run -n piano-difficulty piano-difficulty analyze piece.mxl --out-dir analysis
```

See [the analyzer README](research/piano_difficulty/README.md) and
[the consolidation record](research/piano_difficulty/docs/consolidation.md).
The learning-support slice uses difficulty analysis as a modular evidence source:
auto-detected high-demand sections can suggest where to look, but user-selected
regions and learner notes do not depend on hotspot detection.

To work on or run the existing Python project, begin in
`research/piano_difficulty/` and follow its README.

To continue learning-support work, begin with
`research/learning_support/README.md`, the CEO milestone document, and any scoped
`AGENTS.md` files for the area being edited.

## Setup (fresh clone)

```bash
git clone --recurse-submodules git@github.com:wcshelor/gradus.git
# or, if already cloned without submodules:
git submodule update --init --recursive
conda env create -f research/piano_difficulty/environment.yml
conda run -n piano-difficulty python -m pip install -e 'research/piano_difficulty[dev]'
conda activate piano-difficulty
# verify baseline:
conda run -n piano-difficulty python -m pytest -q --ignore=research/piano_difficulty/external
```
