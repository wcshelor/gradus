# AI-assisted piano and instrumental learning

This mini review tracks the state of the art in AI-assisted piano and
instrument learning. It focuses on systems that observe performance, generate
feedback or learning material, adapt practice, or support teachers. It should
be read alongside `learning_piano_pieces.md`, which defines the thesis's
pedagogical problem: a learner-passage difficulty is a diagnosis, not only an
accuracy score.

The current state of the art is strongest at **capturing performance and
detecting correctness**. It is weaker at **pedagogical diagnosis**: explaining
why a learner is struggling, matching the problem to an intervention, and
evaluating retention or transfer back into the whole piece.

## Working taxonomy

| System role | Typical input | Typical output | Current maturity | Thesis caution |
| --- | --- | --- | --- | --- |
| Automatic performance assessment | MIDI, audio, score alignment | pitch, rhythm, tempo, onset, dynamics, articulation, overall scores | relatively mature for constrained tasks | scores can look pedagogical while hiding weak diagnosis |
| Practice feedback app | microphone or MIDI plus curriculum | red/green notes, timing labels, scores, loops, tempo changes, hand separation | commercially mature | often optimizes immediate accuracy and engagement |
| Practice scheduling or sequencing | performance history, skill model, exercise library | next task, difficulty adjustment, tempo progression | emerging | needs evidence that sequencing improves retention and transfer |
| Fingering or posture assistance | score, MIDI, video, hand tracking | fingering suggestions, posture/hand-shape prompts | emerging and high-risk | ergonomic claims need specialist validation and safety boundaries |
| Expressive-performance coaching | MIDI/audio features, expert ratings | dynamics, phrasing, affective or expressivity scores | emerging | expressivity is culturally and stylistically situated |
| Generative practice support | score features, learner model, objectives | generated exercises, variants, explanations, plans | underdeveloped for piano technique | generated material needs transfer, fidelity, and teacher review |
| Teacher dashboard or co-pilot | learner traces, score, teacher annotations | summaries, flagged passages, suggested prompts | underdeveloped | should augment teacher judgment rather than replace it |

## Start here: broad reviews

1. **Kim, Ramoneda, Miron, and Serra (2022), “An Overview of Automatic Piano
   Performance Assessment within the Music Education Context.”** Core review
   for automated piano performance assessment. Read for the gap between
   technical assessment methods and feedback that is usable in music education:
   method accuracy, training-data limits, bias, and insufficient alignment with
   real pedagogical workflows.
2. **Carnovalini, Espirito Santo, and Wiggins (2025), “Personalized Music
   Education: A Systematic Review of AI Generation Methods.”** Highest-priority
   review for Gradus. It reports that AI generation for personalized music
   education is still limited, that instrumental technique is weakly served, and
   that the review found no examples of generated piano technical exercises.
   This identifies a clean thesis gap for source-grounded, passage-specific
   practice transformations.
3. **AI-assisted feedback in education systematic reviews.** Use general
   education reviews to frame feedback levels, transparency, learner action, and
   self-regulation. Treat them as background unless their mechanisms are
   transferred explicitly to instrument learning.
4. **AI in music education scoping/systematic reviews.** Use broad music
   education reviews to locate common application areas: performance
   assessment, music theory tutoring, scaffolded self-learning,
   personalization, and risk. Screen carefully for weak review methods and
   broad claims unsupported by instrumental-learning outcomes.

## Automatic piano performance assessment

This is the most developed research lane. Systems commonly compare a learner's
performance against a score or reference and estimate pitch accuracy, timing,
tempo, articulation, dynamics, or a global performance score.

Important lines of work:

- **Aspect-level evaluation.** The 2022 ACM work on automatic evaluation and
  scheduling separates pitch, rhythm, tempo, and articulation/dynamics rather
  than collapsing performance into one grade. This is useful because Gradus also
  needs multiple hypotheses rather than a single difficulty value.
- **MIDI-first assessment.** MIDI remains attractive because note onset, pitch,
  duration, and velocity are explicit. It is less available to learners with
  acoustic instruments and does not directly capture touch, posture, pedalling,
  or acoustic nuance.
- **Audio and polyphonic recognition.** Microphone-based systems are more
  accessible but technically harder, especially for polyphony, noisy rooms,
  pedal resonance, and expressive timing.
- **Score alignment and error localization.** The practical value of an
  assessment depends on mapping performance errors back to musical locations
  and explaining them in a learner-comprehensible way.

Open question: when does automatic assessment become actionable feedback rather
than a correctness report?

## Commercial practice systems

Commercial systems already provide many features that a research prototype
should not merely duplicate:

- **Piano Marvel**: score following, red/green note and rhythm feedback,
  assessment scores, progress tracking, sight-reading assessment, hand
  separation, small-section practice, and tempo progression. It explicitly
  frames core scoring around note and rhythm accuracy and leaves expression
  largely to teacher/video support.
- **Simply Piano**: microphone/MIDI recognition, step-by-step courses, immediate
  visual feedback, personalized short workouts, and newer AR/hand-posture
  features.
- **Yousician**: multi-instrument real-time feedback, accuracy/timing scoring,
  practice and play modes, tempo adjustment, auto-adjusted speed, and
  curriculum progression.
- **flowkey**: repertoire-centered piano learning with wait mode, hand
  separation, slow motion, looping, video, and sheet music.

Commercial state of the art suggests that the baseline user expectation is
instant feedback, looping, tempo control, hand separation, and progress
tracking. Gradus should therefore contribute diagnosis, explanation,
source-grounded practice design, or teacher collaboration rather than another
red/green correctness interface.

## Personalization and generation

Personalization in music-learning systems is usually implemented as:

- selecting the next exercise or repertoire item;
- changing tempo, length, or repetition requirements;
- adapting visual feedback or interface complexity;
- recommending practice segments from performance history; or
- generating theoretical or musical material.

The major gap is **personalized generation for piano technique and passage
practice**. Current generation work is more visible in music theory, creative
composition, accompaniment, or general educational content than in the
generation of bounded technical exercises that preserve the relation the
learner must ultimately perform.

For Gradus, generated exercises should record:

- source passage and target relation;
- difficulty hypothesis being addressed;
- transformation applied;
- what was preserved and what was simplified;
- intended mechanism;
- reconnection step to the original score;
- contraindications and uncertainty;
- teacher or learner evaluation criterion.

## Multimodal, fingering, and embodied feedback

Recent work increasingly combines MIDI, audio, video, hand tracking, pose
estimation, or haptic feedback. This enables new claims about fingering,
ergonomics, hand posture, technical comfort, and expressive control.

This is promising but high-risk for the thesis. Movement advice can easily
become overconfident or unsafe, especially from score-only evidence. Treat
fingering, posture, pain, injury, hand span, and biomechanical efficiency as
learner- and teacher-dependent unless supported by specialist validation.

Near-term safe use for Gradus:

- flag that a passage may involve fingering or movement planning;
- ask for learner/teacher fingering information;
- present multiple hypotheses rather than one prescription;
- avoid injury, pain, or medical claims;
- recommend teacher review for embodied technique questions.

## Expressive performance and musicality

AI systems can measure or model some expressive features: timing deviations,
dynamics, articulation, tempo curves, pedalling proxies, phrase-level changes,
or similarity to expert performances. Some recent studies claim gains in
expressive piano performance from AI-supported coaching.

Use this literature carefully. Expressive playing is not merely high variance in
dynamics or timing; it depends on style, phrase structure, sound ideal,
teacher-student goals, and interpretive agency. Automated expressivity scores
may be useful as prompts for listening, but should not become a universal
standard of musicality.

Thesis opportunity: use expression-related feedback as **attention guidance**
rather than judgment. For example: "try listening for whether the top voice
remains audible through this left-hand pattern," then ask the learner or teacher
to evaluate the result.

## Evaluation standards

Many systems are evaluated on algorithmic accuracy, immediate performance
scores, user satisfaction, or engagement. For a pedagogical thesis, stronger
evidence would include:

- delayed retention;
- transfer back into the original passage;
- comparison against unguided practice or generic feedback;
- teacher ratings of diagnosis and intervention fit;
- learner self-regulation changes;
- robustness across levels, instruments, rooms, and repertoire;
- transparent reporting of datasets, labels, and model limits.

The thesis should avoid claiming that better detection automatically means
better learning. The core evaluation question is whether assistance changes how
the learner practises and whether the improvement persists.

## Fit with Gradus

The defensible contribution is not a full autonomous piano tutor. A stronger
position is:

> Gradus is a learner-passage diagnostic support system that uses score
> evidence, learner feedback, and pedagogical source claims to propose bounded
> practice hypotheses and teacher-reviewable interventions.

This occupies a gap between existing systems:

- more pedagogically structured than correctness-scoring apps;
- safer than automatic posture or injury advice;
- more source-grounded than generic language-model coaching;
- more generative than static curricula;
- more evaluable than a broad "AI teacher" claim.

## Sources to add or verify in the catalog

- Kim, Ramoneda, Miron, and Serra (2022), automatic piano performance assessment
  overview.
- Tamir-Ostrover et al. / Friedman group (2022), automatic evaluation of
  performance aspects and scheduling in piano.
- Carnovalini, Espirito Santo, and Wiggins (2025), systematic review of AI
  generation methods for personalized music education.
- Recent broad AI-in-music-education scoping reviews, screened for quality and
  method transparency.
- Selected commercial-system documentation for Piano Marvel, Simply Piano,
  Yousician, and flowkey as industry/practitioner context, not empirical proof.
- Recent multimodal fingering, posture, and expressive-coaching papers, marked
  as high-risk until close-read.

## Search gaps

- AI systems that diagnose causes of piano passage failure, not only errors.
- Teacher-facing dashboards or co-pilots for instrumental lessons.
- Generated exercises for piano technique with transfer evaluation.
- Studies comparing automatic feedback against teacher feedback or teacher plus
  system feedback.
- Longitudinal studies measuring retention, transfer, motivation, and
  self-regulated practice.
- Safety and validity studies for posture, hand tracking, and fingering advice.
