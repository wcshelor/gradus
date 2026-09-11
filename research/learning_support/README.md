# Learning support

This area contains exploratory systems that may help someone learn a piano
piece. The current implementation is a bounded, deterministic research slice:
score-derived passage selection, optional learner context, one semantic
observation family, one grounded text aid, a local interaction harness, and
evaluation documentation.

No particular AI mechanism or application architecture is assumed here. Early
work should begin with a clear learning problem, the information available to
the system, the intended user, and a way to judge whether the result is useful
and pedagogically responsible.

Possible questions include:

- What does a learner need help with at a particular moment?
- Which aspects of a score can be inferred reliably, and which require input
  from the learner or a teacher?
- How might a system turn musical observations into something actionable?
- How should assistance change with experience, goals, time, or progress?
- What should remain under the control of the learner or teacher?
- What evidence would show that an intervention helps rather than merely sounds
  convincing?

Experiments should create their own documented subfolder when they become
concrete. Broader ideas still belong in the repository's `brainstorm/` area
until they are promoted into a scoped plan.

## Active experiments

Use the repository-wide
[three-area plan](../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md)
for historical sequencing and status. LS-01 through LS-11 are implemented and
pending lead/human review. This area develops pedagogical assistance and
flexible interaction, and houses passage-specific semantic experiments. These
responsibilities do not require new top-level packages or moving the existing
analyzer.

Supported planning entry points are a whole-piece request, a user-selected
passage, a question, an optional journal entry, or an analyzer-suggested region.
Hotspot detection is not a gate to assistance. Optional learner context may
include goals, preferences, self-described habits, practice attempts, and exactly
what feels difficult in a section. Reports remain distinct from score facts and
unverified system hypotheses; no live-playing feedback or MIDI/audio capture is
part of this phase.

The implemented slice uses synthetic data and explicit
save/use/correction/deletion behavior. It includes in-memory learner-context
runtime and a deterministic local interaction harness, but no app integration,
real learner data, external model processing, or product persistence.

- `passage_practice/` defines the documentation-first program for turning
  difficulty hotspots into traceable passage diagnoses and generated practice
  exercises. It also now contains the LS passage-selection, investigation,
  observation, and text-aid modules used by the current learning-support slice.
  Its implementation remains phased so score facts, musical inference,
  pedagogical claims, and notation transformations stay independently testable.
- `learner_context/` contains minimal request, journal, permission, summary,
  assistance-result, and context-store contracts.
- `interaction/` contains `InteractionSession`, the local deterministic harness
  that composes context, passage selection, observations, and the text aid.
- `first_slice.md` specifies the bounded LS-01 slice: one-hand broken-chord
  help from user-selected or whole-piece entry, journal-only and returning
  scenarios, disagreement handling, abstention, exclusions, and a reviewable
  success rubric.
- `evaluation_ls10.md` is the reproducible technical evaluation of the first
  slice. It explicitly states that pedagogical effectiveness is unproven and
  no real learner data has been used.
- `ceo_demo_milestone_2026-09-06.md` selects the next increment: a thin local
  CEO walkthrough prototype. Planning is complete; demo implementation has not
  started.

The existing passage-practice program is preserved as a bounded experiment, not
the complete learning-support architecture. Difficulty component hardening can
proceed alongside independent semantic and interaction design; it is not a
global prerequisite.

Current verified baseline after LS-11: full suite `594 passed, 10 skipped`
with optional local-corpus skips unchanged.
