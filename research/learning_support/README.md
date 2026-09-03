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

- `passage_practice/` defines the documentation-first program for turning
  difficulty hotspots into traceable passage diagnoses and generated practice
  exercises. Its implementation is intentionally phased so score facts,
  musical inference, pedagogical claims, and notation transformations remain
  independently testable.
