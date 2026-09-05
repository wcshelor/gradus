# Learning support

This area is reserved for exploratory systems that may help someone learn a
piano piece. Its eventual contents may draw on score analysis, pedagogical
knowledge, learner input, generated material, interaction, feedback, or other
forms of assistance.

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
concrete. Until then, ideas belong in the repository's `brainstorm/` area.

## Active experiments

Use the repository-wide
[three-area plan](../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md)
for sequencing. This area develops pedagogical assistance and flexible interaction,
and currently houses passage-specific semantic experiments. These responsibilities
do not require new top-level packages or moving the existing analyzer.

Supported planning entry points are a whole-piece request, a user-selected
passage, a question, an optional journal entry, or an analyzer-suggested region.
Hotspot detection is not a gate to assistance. Optional learner context may
include goals, preferences, self-described habits, practice attempts, and exactly
what feels difficult in a section. Reports remain distinct from score facts and
unverified system hypotheses; no live-playing feedback or MIDI/audio capture is
part of this phase.

The plan starts learner-context experiments with synthetic data and explicit
save/use/correction/deletion behavior. No learner-context runtime, persistent
memory, or app integration is claimed to exist yet.

- `passage_practice/` defines the documentation-first program for turning
  difficulty hotspots into traceable passage diagnoses and generated practice
  exercises. Its implementation is intentionally phased so score facts,
  musical inference, pedagogical claims, and notation transformations remain
  independently testable.
- `first_slice.md` specifies the bounded LS-01 slice: one-hand broken-chord
  help from user-selected or whole-piece entry, journal-only and returning
  scenarios, disagreement handling, abstention, exclusions, and a reviewable
  success rubric. Planned, not implemented.

The existing passage-practice program is preserved as a bounded experiment, not
the complete learning-support architecture. Its local plans contain hotspot-first
assumptions and some historical status text; reconcile them against actual source,
tests, and the new entry points before extending the program (LS-02 in the
repository-wide plan). Difficulty component hardening can proceed alongside
independent semantic and interaction design; it is not a global prerequisite.
