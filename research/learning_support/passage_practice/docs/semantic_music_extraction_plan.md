# Semantic Music Extraction Implementation Plan

## Purpose

This plan defines a later implementation track for richer semantic extraction
from MusicXML/MXL passages. It is preparatory architecture work, not a request
to interrupt the current difficulty-analysis testing and consolidation work.

The difficulty system answers where a passage may deserve attention. Semantic
music extraction should help answer what may be happening musically inside that
passage and which pedagogical actions could be justified by score evidence,
learner feedback, or both.

The target object is not a single certain analysis. The target object is a
ranked, evidence-backed set of musical and pedagogical hypotheses:

```text
passage
  -> score facts and direct observations
  -> semantic hypotheses with confidence and caveats
  -> learner-adjusted pedagogical hypotheses
  -> strategy and transformation candidates
```

The system must be able to say "likely", "possibly", "not enough evidence", and
"ask the learner" without degrading into vague advice. Uncertainty is a contract
property, not only presentation language.

## Placement in the repository

Semantic extraction belongs in `research/learning_support/passage_practice/`
until it demonstrates a reusable boundary shared by multiple research areas.
The difficulty area may expose generic score facts, temporal regions, and
feature evidence, but it must not import pedagogical concepts or semantic
diagnoses.

The intended dependency relationship is:

```text
research/piano_difficulty/
  MusicXML/MXL loading, ScoreIR, core score descriptors, windows, hotspots,
  difficulty-feature evidence where promoted.

research/learning_support/passage_practice/
  passage views, semantic role hypotheses, pattern hypotheses, diagnoses,
  learner feedback integration, pedagogical strategy selection, transformations.
```

Do not move speculative semantic abstractions to `research/shared/`. A later
move to `research/shared/` requires evidence that both difficulty analysis and
learning support depend on the same stable contract.

## Architectural principle

Every semantic feature or detector must justify its existence by enabling at
least one downstream use:

- a clearer passage explanation;
- a targeted learner question;
- a practice objective;
- a deterministic simplification or exercise transformation;
- a strategy-ranking decision;
- an evaluation comparison; or
- a feedback update to the passage model.

Features that only sound music-theoretically interesting should remain
brainstorm items until they can support one of those uses.

## Layered architecture

This plan extends the passage-practice dependency direction:

```text
score facts
  -> passage selections
  -> derived views
  -> direct observations
  -> semantic hypotheses
  -> pedagogical hypotheses
  -> learner-feedback updates
  -> objectives, strategies, transformations, and presentation
```

### Layer 1: canonical score facts

Owner: `research/piano_difficulty/` for reusable parser and `ScoreIR` behavior.

Responsibilities:

- stable source identity and event IDs;
- exact score time;
- written notes, rests, ties, voices, staves, measures, clefs, keys, meters,
  directions, articulations, and dynamics where supported;
- parse and normalization diagnostics.

Forbidden responsibilities:

- melody labels;
- accompaniment labels;
- pedagogical diagnoses;
- advice;
- learner-dependent claims.

### Layer 2: passage selections

Owner: `passage_practice/passages`.

Responsibilities:

- exact half-open regions;
- source-event inclusion;
- sustaining boundary context;
- inherited notation context;
- parent-child region lineage;
- detection, evidence, pattern, and practice region purposes.

Semantic extraction should run on exact passage selections, not raw whole-score
documents or opaque hotspot IDs.

### Layer 3: derived views

Owner: `passage_practice/views`.

Views are purpose-built projections over a passage. They should be cheap to
rebuild, deterministic, and clear about what they omit.

Initial semantic-view families:

- `attack_stream`: tie-collapsed logical attacks in exact time order;
- `written_stream`: written events retaining voice and notation details;
- `hand_stream`: attacks grouped by inferred hand, with confidence;
- `voice_stream`: encoded voices without assuming musical role;
- `onset_slices`: simultaneous and sounding material at each attack time;
- `pitch_contour`: ordered pitch movement for a candidate line;
- `rhythm_grid`: onset, duration, metric position, and subdivision relations;
- `texture_grid`: simultaneity, density, and layer-change summaries;
- `harmony_view`: pitch-class, bass, duration, and local-key candidates;
- `salience_view`: candidate events scored for melodic, bass, or inner-voice
  salience;
- `role_stream`: later inferred roles such as melody, bass, inner voice, and
  accompaniment.

Views that include inference must carry `confidence`, `method_id`,
`method_version`, evidence references, and diagnostics.

### Layer 4: direct observations

Owner: `passage_practice/observations` or the existing feature-evidence layer
when promoted.

Direct observations are measured from score facts or views. They do not claim
musical role or learning need.

Observation families:

- pitch and range;
- intervals and leaps;
- simultaneity and chord spans;
- note, attack, and rhythm density;
- metric placement and syncopation;
- hand and staff relationships;
- voice and tie continuity;
- notation readability;
- articulation and dynamics;
- repetition and pattern recurrence;
- local harmonic pitch-class evidence.

Observations must keep source-event references, exact regions, units,
missingness, and diagnostics. Missing data must not silently become zero.

### Layer 5: semantic hypotheses

Owner: `passage_practice/semantics`.

Semantic hypotheses interpret observations as musical roles, structures, or
relationships. They are probabilistic and may conflict.

Hypothesis examples:

- likely melody in right-hand top voice;
- possible left-hand melody;
- possible hidden inner voice;
- bass behaves like a harmonic anchor;
- accompaniment resembles broken chords;
- local texture is melody plus arpeggiated support;
- hands use rhythmically independent layers;
- phrase boundary likely at the end of the passage;
- local harmony likely changes once per measure;
- cadence likely at the end of the pattern region.

Each hypothesis must state:

- `hypothesis_id`;
- `hypothesis_type`;
- source passage ID;
- covered event IDs;
- evidence observation IDs;
- confidence score;
- confidence method;
- supporting criteria;
- contradictory criteria;
- caveats;
- diagnostics;
- method ID and version.

Semantic hypotheses do not prescribe practice material. They make musical
interpretation inspectable.

### Layer 6: pedagogical hypotheses

Owner: `passage_practice/diagnosis`.

Pedagogical hypotheses translate semantic hypotheses and difficulty evidence
into possible learner challenges. They remain qualified unless supported by
learner input.

Examples:

- melody projection may be the main issue;
- left-hand relocation may be a practice focus;
- rhythmic coordination between layers may be unstable;
- reading load may come from accidentals plus dense beaming;
- harmonic understanding may help chunk the passage;
- voicing and balance may matter more than raw note accuracy.

Pedagogical hypotheses should always expose:

- score-derived evidence;
- whether learner evidence exists;
- relevant uncertainty;
- a learner-facing question that could confirm or reject the hypothesis;
- compatible objectives and strategies;
- contraindications or caution notes.

### Layer 7: learner-feedback update

Owner: `passage_practice/learner_feedback` or the existing
`research/learning_support/learner_context/` contracts if generalized.

Learner feedback should update the passage model without rewriting score facts.
The app can ask constrained questions such as:

```text
What feels hardest in this section?
- finding the notes
- keeping the rhythm steady
- moving between positions
- playing both hands together
- making the melody stand out
- understanding the harmony
- keeping the passage relaxed
- something else
```

Feedback records should include:

- source passage ID;
- prompt ID;
- answer type;
- learner text or selected option;
- timestamp or session ordering metadata, if persistence exists;
- privacy and retention status;
- mapping to affected pedagogical hypothesis IDs;
- update method and version.

The update output should not destroy the original analysis. It should produce a
new ranked view:

```text
score-derived hypotheses
  + learner feedback
  -> learner-adjusted teaching focus
```

This separation matters for research: we need to know whether an explanation
came from the score, the learner, or both.

### Layer 8: strategies and transformations

Owner: `passage_practice/strategies` and `passage_practice/transformations`.

Semantic extraction becomes useful when it changes what the system generates.
Every strategy entry should declare which semantic and pedagogical hypotheses
it consumes.

Examples:

- melody hypothesis -> melody-only reduction;
- hidden melody hypothesis -> accent or isolate salient notes;
- accompaniment hypothesis -> simplify accompaniment while preserving melody;
- bass anchor hypothesis -> bass plus harmonic skeleton;
- leap hypothesis -> landing-target drill;
- rhythm-independence hypothesis -> common-attack skeleton;
- harmony-change hypothesis -> blocked harmonic rhythm exercise;
- phrase-boundary hypothesis -> phrase-shape and cadence preparation task.

## Proposed file organization

Create directories only when implementation starts. Do not add empty scaffolding.

```text
research/learning_support/passage_practice/
  docs/
    semantic_music_extraction_plan.md
    semantic_feature_taxonomy.md              # later registry-style design doc
    semantic_confidence_policy.md             # later threshold and wording policy
    semantic_feedback_policy.md               # later learner-feedback update policy

  src/passage_practice/
    views/
      attack_stream.py
      rhythm_grid.py
      texture_grid.py
      salience_view.py
      harmony_view.py

    observations/
      pitch.py
      rhythm.py
      texture.py
      notation.py
      motor_proxy.py
      harmony.py

    semantics/
      contracts.py
      registry.py
      melody.py
      bass.py
      accompaniment.py
      inner_voice.py
      rhythm_roles.py
      phrase.py
      harmony.py
      texture.py

    diagnosis/
      semantic_rules.py
      pedagogical_hypotheses.py

    learner_feedback/
      contracts.py
      update.py
      prompts.py

  tests/
    fixtures/
      semantic_roles/
      rhythm_coordination/
      harmony/
      notation_readability/

    unit/
      test_semantic_contracts.py
      test_melody_hypotheses.py
      test_bass_hypotheses.py
      test_accompaniment_hypotheses.py
      test_rhythm_role_hypotheses.py
      test_feedback_updates.py

    contract/
      test_semantic_payloads.py
      test_semantic_to_diagnosis_boundary.py
      test_feedback_preserves_score_analysis.py

    integration/
      test_passage_to_semantic_hypotheses.py
      test_difficulty_context_to_pedagogical_hypotheses.py

    regression/
      semantic_payloads/
```

### Naming rules

- Use `semantics` for musical interpretation.
- Use `diagnosis` for potential learner challenges.
- Use `strategies` for pedagogical action selection.
- Use `transformations` for score changes.
- Do not name musical-role detectors as difficulty detectors.
- Do not name learner-feedback updates as score-analysis updates.

## Contract additions

The existing `PatternMatch` and `PassageDiagnosis` contracts can support part
of this plan, but richer semantic extraction needs more explicit intermediate
contracts.

### `SemanticHypothesis`

Suggested fields:

```text
schema_version
hypothesis_id
hypothesis_type
source_passage_id
covered_region
covered_event_ids
candidate_role
scope
confidence
confidence_method
method_id
method_version
supporting_observation_ids
supporting_pattern_ids
satisfied_criteria
contradictory_criteria
missing_evidence
diagnostics
```

Example hypothesis types:

- `role.melody`;
- `role.bass`;
- `role.inner_voice`;
- `role.accompaniment`;
- `texture.arpeggiated`;
- `texture.homophonic`;
- `texture.polyphonic`;
- `rhythm.syncopated_layer`;
- `rhythm.independent_hands`;
- `phrase.boundary`;
- `harmony.local_key`;
- `harmony.cadence`;
- `motor_proxy.leap_targeting`.

### `SemanticBundle`

A bundle is the complete semantic analysis for one passage.

Suggested fields:

```text
schema_version
source_passage_id
view_refs
observation_refs
hypotheses
ranked_roles
ranked_difficulty_drivers
diagnostics
method_versions
```

The bundle may contain contradictory hypotheses. Consumers should rank and
filter; producers should not hide uncertainty by returning only one winner.

### `LearnerFeedbackSignal`

Suggested fields:

```text
schema_version
source_passage_id
feedback_id
prompt_id
answer_kind
answer_value
free_text
consent_or_retention_scope
mapped_hypothesis_ids
mapped_objective_ids
method_id
method_version
diagnostics
```

### `LearnerAdjustedFocus`

Suggested fields:

```text
schema_version
source_passage_id
base_semantic_bundle_id
feedback_signal_ids
ranked_pedagogical_hypotheses
primary_focus
secondary_focuses
rejected_or_deprioritized_hypotheses
update_rationale
diagnostics
```

## Confidence policy

Use confidence as a transparent ranking device, not a claim of ground truth.

Minimum requirements:

- confidence is bounded and documented;
- each method declares whether confidence is heuristic, calibrated, or learned;
- contradictory evidence can reduce confidence;
- unavailable evidence is represented separately from negative evidence;
- thresholds are local to a detector version;
- presentation wording maps to confidence bands.

Suggested confidence bands:

| Band | Range | Presentation stance |
|---|---:|---|
| high | `0.75-1.00` | "likely", with evidence |
| medium | `0.50-0.74` | "may", with caveat |
| low | `0.25-0.49` | "possible", usually ask learner or abstain |
| unsupported | `<0.25` | do not present as a finding |

These bands are initial presentation rules, not research claims. They should be
revised after fixture, teacher, or learner-review evidence.

## Feature and heuristic taxonomy

The taxonomy below is intentionally extensive. Implementation should proceed in
small packages, but the architecture should be able to host these families
without reshaping the repository each time.

### Surface and mechanical observations

Pitch and range:

- absolute pitch range by passage, hand, voice, and candidate role;
- local hand span;
- maximum and mean melodic interval;
- leap frequency;
- leap direction changes;
- leap recovery after large intervals;
- registral extremes;
- ledger-line burden;
- repeated-note frequency;
- chromatic pitch density;
- accidental density;
- black-key and white-key pattern changes;
- octave doubling;
- unison doubling between hands.

Rhythm:

- attacks per beat;
- notes per beat;
- shortest duration;
- duration entropy;
- dotted rhythm density;
- tie-over-barline count;
- tuplet presence;
- rests interrupting continuity;
- rhythmic motif recurrence;
- syncopation score;
- off-beat attack density;
- hand attack-alignment ratio;
- conflicting subdivisions between hands;
- duration contrast between candidate melody and accompaniment.

Texture:

- simultaneity count;
- chord size;
- chord density;
- onset-slice pitch span;
- arpeggiation likelihood;
- Alberti-like likelihood;
- tremolo or repeated alternation likelihood;
- scalar passage likelihood;
- broken-chord passage likelihood;
- melody-plus-accompaniment likelihood;
- homophonic block texture likelihood;
- contrapuntal or polyphonic likelihood;
- active voice count;
- voice crossing;
- hand crossing;
- staff crossing;
- sustained notes under moving notes.

Notation and readability:

- accidental clutter;
- clef changes;
- key-signature complexity;
- time-signature rarity;
- beam/group irregularity;
- dense beaming;
- nested tuplets;
- grace notes and ornaments;
- articulation density;
- dynamics and hairpins during dense material;
- ledger-line burden;
- system or page break near passage, when layout is available.

Motor proxies:

- hand relocation distance;
- large jumps to non-adjacent registers;
- lateral travel per beat;
- alternating hand motion;
- contrary and similar motion;
- stretch likelihood;
- blocked-chord span;
- chord inversion changes;
- thumb-under or crossing proxy;
- repeated-note fingering risk;
- same-hand legato difficulty proxy;
- large leap into chord;
- leap landing on weak beat;
- leap in one hand while the other hand remains active.

### Semantic role hypotheses

Melody:

- top-voice salience;
- longest-duration salience;
- accent, slur, and dynamic salience;
- registral prominence;
- motivic contour recurrence;
- phrase-continuity score;
- exclusion from accompaniment pattern;
- melody split between hands;
- melody hidden inside figuration;
- left-hand melody;
- inner-voice melody;
- octave-doubled melody.

Bass:

- lowest-voice stability;
- root-motion likelihood;
- pedal-point likelihood;
- walking-bass likelihood;
- broken-bass pattern;
- bass leap pattern;
- bass as harmonic anchor;
- bass as melodic counterline;
- syncopated bass burden.

Inner voices:

- sustained inner tone;
- moving inner line;
- suspension-like behavior;
- voice-leading continuity;
- alto or tenor line salience;
- voice-crossing ambiguity;
- hidden counter-melody likelihood.

Accompaniment:

- ostinato;
- Alberti bass;
- waltz-like bass-chord-chord pattern;
- block chords;
- broken chords;
- arpeggiated support;
- repeated rhythmic comping;
- tremolo;
- drone or pedal;
- call-and-response;
- accompaniment changes under stable melody;
- stable accompaniment under changing melody.

Phrase and grouping:

- boundary likelihood from rests, long notes, slurs, and cadential patterns;
- motivic repetition;
- sequence likelihood;
- antecedent/consequent likelihood;
- local climax likelihood;
- cadential arrival;
- phrase overlap;
- pickup or anacrusis;
- elision;
- grouping ambiguity.

Meter:

- downbeat stability;
- metric accent agreement;
- weak-beat attacks;
- syncopated melody against stable accompaniment;
- hemiola likelihood;
- cross-rhythm likelihood;
- phrase beginning away from downbeat;
- cadential delay.

Harmony:

- key confidence;
- local key-shift confidence;
- harmonic rhythm;
- cadence likelihood;
- coarse tonic, dominant, and predominant function;
- chromatic-harmony density;
- secondary-dominant likelihood;
- diminished or augmented sonority;
- non-chord-tone density;
- suspension or appoggiatura likelihood;
- pedal point;
- harmonic surprise;
- bass inversion ambiguity;
- circle-of-fifths motion;
- harmonic sequence pattern.

Melodic semantics:

- stepwise continuation;
- large leap;
- leap compensation;
- contour reversal;
- registral return;
- sequence;
- fragmentation;
- repetition;
- climax tone;
- tendency tone or leading-tone behavior;
- unresolved dissonance;
- closure versus continuation.

### Cognitive and learning-demand hypotheses

Reading load:

- many notational dimensions change at once;
- accidentals and rhythm complexity coincide;
- unfamiliar or unstable key center;
- dense notation with weak visual grouping cues;
- low pattern redundancy;
- high visual-search burden;
- unpredictable next event;
- limited lookahead affordance.

Memory load:

- long repeated pattern with small variations;
- sequence requiring transposition tracking;
- accompaniment pattern changes subtly;
- phrase repeats with altered ending;
- learner must maintain hand position while reading ahead;
- recurring motif returns in another register or key.

Coordination load:

- hands have different rhythms;
- melody attacks between accompaniment attacks;
- leap in one hand while the other continues;
- hand alignment changes frequently;
- one hand sustains while the other articulates;
- dynamic or articulation independence between hands;
- phrase shaping conflicts with motor pattern.

Attention splitting:

- melody hidden in busy texture;
- inner voice requires attention;
- bass line is musically important but physically discontinuous;
- articulation differs by voice;
- dynamics apply to one layer more than another;
- pedaling could obscure if uncontrolled.

Expressive load:

- voicing demand;
- phrase shaping through a technical pattern;
- articulation contrast;
- dynamic shaping over leaps or chords;
- rubato-sensitive cadence;
- hand balance;
- legato illusion where physical legato is hard.

## Detector design

Each detector should be small, typed, and independently testable.

Suggested interface responsibilities:

```text
Detector metadata:
  detector_id
  detector_version
  hypothesis_types produced
  required views
  optional views
  supported subset
  known limitations

Detector input:
  passage
  requested scope
  derived views
  observations
  optional difficulty context
  optional learner feedback context

Detector output:
  zero or more SemanticHypothesis records
  diagnostics
```

The registry should support:

- listing detectors by hypothesis family;
- selecting detectors by available views;
- selecting detectors by difficulty-triggered dimensions;
- running all deterministic detectors for a controlled user-selected passage;
- comparing detector versions in regression tests.

Do not build one large analyzer that produces every semantic claim. That would
make confidence, diagnostics, and replacement by learned models hard to test.

## Heuristic methods versus learned models

The first implementation should prefer readable heuristics with strong fixture
tests. Learned models can enter later behind the same contracts.

### Heuristic methods

Appropriate for:

- onset grouping;
- rhythmic density and alignment;
- basic texture classification;
- candidate melody salience;
- bass anchoring;
- broken-chord and pattern recurrence;
- phrase-boundary candidates;
- coarse harmony and harmonic rhythm;
- notation-readability proxies.

Advantages:

- deterministic;
- inspectable;
- easy to attach source evidence;
- easy to test against positive, negative, and ambiguous fixtures.

### Small learned models

Appropriate later for:

- melody salience ranking;
- role labeling;
- texture classification;
- phrase-boundary ranking;
- difficulty-reason ranking;
- strategy ranking from annotated passage records.

Required safeguards:

- same output contract as heuristic detectors;
- model version and training-data identity in payloads;
- deterministic inference settings;
- abstention or low-confidence behavior;
- baseline heuristic comparison;
- test fixtures that prevent regressions in obvious cases;
- no model-only source evidence.

Learned outputs may rank or combine evidence, but the system should still retain
score-derived observations used to explain why a hypothesis was proposed.

## Pedagogical mapping

The semantic layer should feed a reviewed mapping from hypothesis to action.

Example mappings:

| Semantic/pedagogical hypothesis | Possible action |
|---|---|
| melody likely hidden in figuration | melody-only reduction; accent melody notes; simplify accompaniment |
| left-hand bass leap pattern | landing-target drill; guide-tone bass skeleton |
| broken-chord accompaniment | blocked-chord reduction; arpeggio-to-block comparison |
| hands rhythmically independent | common-attack skeleton; one-hand simplification |
| dense accidentals and weak grouping | chunk by harmonic or melodic pattern; visual grouping prompt |
| cadence likely near end | phrase-ending focus; harmonic skeleton into cadence |
| inner voice salient | isolate inner voice; two-layer voicing drill |
| harmonic rhythm changes quickly | block harmonies; bass-and-chord-label skeleton |

This mapping belongs in strategy or diagnosis registries, not in detectors.
Detectors say what may be present. Strategies say what to do with that.

## Literature integration

Literature should inspire feature families and support pedagogical mappings, but
the repository must preserve the distinction between source claims, formalized
heuristics, and executable strategies.

Initial literature-inspired domains:

- piano sight-reading complexity: note density, rhythm, chromaticism, lookahead,
  visual grouping, pitch/rhythm error separation;
- eye-hand span and cognitive load: planning burden and local predictability;
- symbolic MIR melody and voice separation: salience, contour, stream
  continuity, role ambiguity;
- music cognition grouping theories: phrase boundaries, grouping preference,
  metrical stability;
- melodic expectancy: continuation, reversal, closure, leap recovery;
- computational fingering and ergonomics: movement smoothness, span, jumps,
  hand-position continuity;
- harmony and tonal syntax: harmonic rhythm, cadences, local key, chromaticism;
- pedagogy and etudes: practice reductions, blocked versions, rhythm variants,
  voicing drills, reintegration.

Implementation should not wait for exhaustive literature review. Instead, each
detector or strategy should declare its provenance status:

- `prototype_unvalidated`;
- `literature_inspired`;
- `expert_reviewed`;
- `teacher_piloted`;
- `learner_study_supported`.

## Testing strategy

Semantic extraction must be tested through musical invariants, not just object
shape.

### Unit tests

Cover:

- view construction;
- observation calculations;
- detector criteria;
- confidence calculations;
- contradictory evidence;
- missing evidence;
- feedback update arithmetic;
- registry selection.

### Contract tests

Cover:

- schema version preservation;
- exact fraction serialization;
- source-event reference resolution;
- deterministic JSON output;
- confidence and diagnostic requirements;
- semantic-to-diagnosis boundary;
- learner feedback not mutating score-derived analysis.

### Integration tests

Cover:

- exact passage -> views -> observations -> semantic bundle;
- semantic bundle -> pedagogical hypotheses;
- difficulty context + semantic bundle -> ranked diagnoses;
- learner feedback + semantic bundle -> learner-adjusted focus;
- semantic hypothesis -> strategy candidate compatibility.

### Regression tests

Freeze compact payloads for representative cases:

- melody in top voice;
- left-hand melody;
- hidden melody in chords or figuration;
- clear broken-chord accompaniment;
- homophonic block texture;
- two independent voices;
- syncopated melody over stable accompaniment;
- simple cadence;
- ambiguous passage where the system abstains or returns low confidence.

### Metamorphic tests

Use transformations to verify detector claims:

- transposition should preserve contour-based melody and texture hypotheses;
- rhythmic scaling should preserve role labels but change density values;
- adding a neighboring measure should not change an exact passage result;
- swapping staves with hand annotations should swap hand-scoped hypotheses;
- removing accents should reduce, not erase, a melody hypothesis if pitch and
  duration evidence remain;
- simplifying accompaniment should increase melody-projection confidence where
  appropriate;
- serialize and reopen should preserve event references within the supported
  subset.

### Negative and ambiguous fixtures

Every positive feature family needs nearby negatives:

- top voice that is not melody;
- accompaniment above melody;
- bass line that is melodic rather than harmonic anchor;
- repeated notes that resemble tremolo but are not accompaniment;
- broken chord that is too short to infer a pattern;
- phrase boundary candidate contradicted by tie or continuation;
- cadence-like pitch set without metric or phrase support;
- harmony view with low key confidence;
- two encoded voices that do not imply two musical roles.

Ambiguity should be a supported output with stable diagnostics.

## Evaluation plan

The initial evaluation should not claim pedagogical effectiveness. It should
measure whether the semantic layer is consistent, inspectable, and useful enough
to guide later exercise generation.

Suggested evaluation questions:

- Do detectors identify expected semantic roles on synthetic fixtures?
- Do detectors abstain or lower confidence on close negatives?
- Are confidence changes sensible under metamorphic tests?
- Can a reviewer trace each hypothesis to source events?
- Do strategy candidates change when semantic hypotheses change?
- Does learner feedback update the teaching focus without altering score facts?
- Do teachers agree that the ranked hypotheses are plausible for selected
  CIPI passages?
- Do generated explanations avoid unsupported certainty?

Later evaluation can compare:

- heuristic-only versus small-model role ranking;
- score-derived focus versus learner-adjusted focus;
- generic advice versus semantically grounded advice;
- teacher-rated usefulness of generated exercise candidates.

## Phased implementation roadmap

This roadmap is intentionally separate from the current work-package board. It
should be converted into explicit `WP-*` packages only after the difficulty
testing pass identifies which existing contracts are stable enough to consume.

### Phase S0: inventory existing capabilities

Goal: document what already exists.

Tasks:

- inspect current MXL/ScoreIR facts available from difficulty analysis;
- list existing features that can become observations;
- identify which passage-practice contracts are implemented versus planned;
- map current CIPI walkthrough outputs to potential semantic inputs;
- document gaps in a short inventory file.

Exit criteria:

- a table of available score facts, features, event references, and missing
  requirements;
- no new runtime semantics yet.

### Phase S1: semantic contracts and confidence policy

Goal: define stable payloads before detectors grow.

Tasks:

- add `SemanticHypothesis`, `SemanticBundle`, and confidence-band contracts;
- document method/version requirements;
- add representative frozen JSON payloads;
- define diagnostics for unsupported and ambiguous cases.

Exit criteria:

- deterministic serialization tests;
- at least one empty/no-supported-hypothesis payload;
- documentation links from contracts and architecture.

### Phase S2: core semantic views

Goal: create reusable projections needed by many detectors.

Tasks:

- implement or promote attack stream, onset slices, rhythm grid, texture grid,
  and simple salience view;
- keep encoded voice, staff, inferred hand, and inferred role separate;
- expose missingness and ambiguity diagnostics.

Exit criteria:

- unit tests for exact ordering, grouping, and provenance;
- fixtures covering two staves, two voices, ties, chords, and partial regions.

### Phase S3: first deterministic role detectors

Goal: produce useful semantic hypotheses without changing transformations.

Tasks:

- melody salience detector;
- bass-anchor detector;
- accompaniment-pattern detector;
- rhythm-independence detector;
- texture classifier for monophonic, homophonic, melody-plus-accompaniment,
  arpeggiated, and polyphonic candidates.

Exit criteria:

- each detector has positive, close-negative, and ambiguous fixtures;
- semantic bundle output is stable and inspectable;
- no detector emits advice directly.

### Phase S4: pedagogical hypothesis bridge

Goal: connect semantics to diagnosis without generating notation yet.

Tasks:

- create rules that map semantic bundles plus optional difficulty context to
  ranked pedagogical hypotheses;
- define learner questions for each hypothesis family;
- define compatible objective and strategy IDs;
- retain score-derived and learner-dependent caveats separately.

Exit criteria:

- integration tests from passage to ranked pedagogical hypotheses;
- no hotspot required for controlled user-selected passages;
- explanations remain grounded in structured evidence.

### Phase S5: learner-feedback loop

Goal: allow the user to confirm, reject, or refine the teaching focus.

Tasks:

- add feedback signal contract;
- map common learner answers to hypothesis updates;
- preserve the original score-derived semantic bundle;
- produce learner-adjusted focus records.

Exit criteria:

- tests show feedback can increase, reduce, or reject hypotheses;
- free-text feedback can be stored as evidence without requiring an LLM;
- privacy and retention policy is explicit.

### Phase S6: harmony and phrase expansion

Goal: add higher-level semantics where they improve pedagogy.

Tasks:

- coarse local key confidence;
- harmonic rhythm;
- bass plus pitch-class sonority summaries;
- cadence candidates;
- phrase-boundary candidates;
- sequence and repetition candidates.

Exit criteria:

- harmony detectors can abstain when evidence is weak;
- phrase/harmony hypotheses are consumed by at least one strategy or learner
  question;
- tests include ambiguous and cadence-like negatives.

### Phase S7: learned-model experiments

Goal: evaluate whether small models improve ranking while preserving contracts.

Tasks:

- define annotation records for passages and bars;
- create small labels for melody, bass, accompaniment, texture, and difficulty
  reason;
- train or evaluate simple models behind detector interfaces;
- compare against heuristic baselines.

Exit criteria:

- model outputs use the same `SemanticHypothesis` contract;
- training data identity and model version are recorded;
- heuristic baseline remains runnable;
- no production path depends on nondeterministic external service calls.

### Phase S8: pedagogical corpus and text generation

Goal: prepare for grounded explanation or fine-tuning work.

Tasks:

- collect passage-level records containing score excerpt identity, semantic
  bundle, difficulty context, learner feedback, human explanation, suggested
  simplification, generated exercise, and expected learner mistake;
- link pedagogical text to structured evidence;
- preserve source/teacher/learner provenance;
- evaluate retrieval or fine-tuning only after enough reviewed examples exist.

Exit criteria:

- corpus schema separates score facts, system hypotheses, human comments,
  learner comments, and generated text;
- no copyrighted score or participant-identifiable data is committed;
- text generation can be evaluated against structured evidence.

## CIPI testing relationship

Tomorrow's CIPI/difficulty testing should inform this plan, but should not be
blocked by it.

During testing, useful notes to collect are:

- what region the difficulty system selects;
- which existing features drove the selection;
- whether event-level evidence is available;
- what a human notices musically in the selected bars;
- which semantic hypothesis families would explain the passage;
- which learner question would be natural;
- what exercise transformation would follow if the hypothesis were true.

This can become an inventory table before any semantic detector is implemented.

Suggested note format:

```text
Piece:
Selected region:
Difficulty evidence available:
Human-observed semantics:
Likely semantic detectors needed:
Possible learner question:
Possible exercise/advice action:
Missing score facts or references:
```

## Open architectural decisions

- Should semantic observations live in a new `observations/` package or extend
  the existing feature-evidence layer?
- How much of `ScoreIR` must be promoted before semantic views can avoid
  duplicate parsing?
- Should `SemanticHypothesis` be separate from `PatternMatch`, or should
  `PatternMatch` become one subtype of semantic hypothesis?
- What confidence scale should learned models use if heuristic confidence is
  not calibrated?
- Which learner-feedback signals are safe to persist during the thesis phase?
- How should teacher annotations be stored without mixing them with score facts?
- When does a semantic detector become generic enough to move toward
  `research/shared/`?

## Non-goals

- Do not implement semantic extraction before the current difficulty-analysis
  review has identified stable inputs.
- Do not build a product interface around these semantics yet.
- Do not claim individual learner difficulty from score evidence alone.
- Do not use an LLM as the only melody, harmony, or diagnosis engine.
- Do not require harmony analysis before simpler semantic roles are useful.
- Do not add speculative empty packages.
- Do not commit copyrighted score excerpts or identifiable learner records.
