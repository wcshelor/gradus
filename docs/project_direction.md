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
- Let the learner enter, leave, and return at any stage of learning a piece;
  do not require a prescribed sequence or continuous observation.
- Treat optional learner reports as contextual evidence, not measured playing
  ability. Keep score facts, self-reports, and system hypotheses distinct.

## Three complementary areas

1. **Semantic understanding of the piece:** source facts, structure, patterns,
   relationships, and descriptive demands. Difficulty analysis is one capability
   here, not the organizing center or a prerequisite for every request.
2. **Development of pedagogical assistance:** turn supported musical evidence
   and a learner's stated need into explanations, practice approaches, and other
   inspectable aids. Generated exercises are one possibility, not the only output.
3. **Support of flexible interaction:** accept passage selections, questions,
   optional practice journaling, and information about goals, preferences,
   self-described habits, and passage-specific difficulties. Help the learner
   resume without pretending to know what happened between visits.

These are research responsibilities, not a commitment to three new packages,
services, or a chatbot architecture. A feature set within the company's app or
an assistant-like interface may expose them; that product boundary remains open.

## Current scope and learner control

No live-playing feedback, microphone analysis, MIDI keyboard requirement, or
automatic performance tracking is planned in this phase. Assistance starts from
symbolic score evidence and information the learner chooses to provide.

Journaling is optional. A request must remain useful without a profile, practice
history, or onboarding questionnaire. Learners may record what they attempted,
what helped, and what feels difficult at piece, section, or specific-event scope.
They control whether this context is saved or used later, and can inspect,
correct, exclude, or delete it. Repeated reports may support a tentative pattern
for confirmation, never a silently assigned ability/personality label. Absence
of a journal entry does not imply absence of practice or lack of progress.

Research prototypes use synthetic learner histories first. Real learner data,
company integration, external model processing, and retention require explicit
data-handling decisions before implementation with those data.

## Questions intentionally left open

- Which learner group and learning context should the thesis prioritize?
- Which forms of assistance are most useful and feasible?
- Which optional learner inputs are useful enough to justify their collection?
- Which responsibilities belong to analysis, generation, interaction, or human
  judgment?
- How should pedagogical grounding be represented and evaluated?
- What belongs in the research repository and what belongs in the company's
  product environment?

## Current concrete program

The repository-wide execution direction is recorded in
[the three-area learning-support plan](Task_list_2026-09-05_flexible_piano_learning_support.md).
It supersedes the earlier assumption that all learning-support work must wait
for difficulty consolidation or begin at a difficulty hotspot. LS-01 through
LS-11 are now implemented and pending lead/human review.

Consolidating the analyzer remains a bounded component milestone: one supported
score should yield an inspectable factor overview, factor peaks, and candidate
high-demand sections through one public workflow. Its acceptance is not acceptance
of the whole learning assistant. Semantic experiments may use a user-selected
region and existing score contracts without requiring a difficulty ranking.

The first completed learning-support slice is maintained under
`research/learning_support/`. It demonstrates exact user-selected passage
selection, optional learner context, one pitch-transition observation family,
one grounded text-only aid, a deterministic interaction harness, a multi-visit
synthetic history, and technical evaluation. It is intentionally narrow:
pedagogical effectiveness is unproven, no real learner data has been collected,
and no product integration is claimed.

The next selected increment is a thin local CEO walkthrough prototype that makes
the slice visible alongside the existing difficulty overview and graph outputs.
That demo should remain a presentation harness over tested components, not the
new architectural center. The broader `passage_practice/` program still contains
plans for event attribution, semantic diagnosis, deterministic transformations,
and generated exercises; not every planned component must appear in the final
thesis or product.
