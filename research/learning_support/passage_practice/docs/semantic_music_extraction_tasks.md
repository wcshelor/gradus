# Semantic Music Extraction Atomic Tasks

This checklist decomposes `semantic_music_extraction_plan.md` into agent-sized
tasks. It is now an active execution aid: S1–S6.7 plus S7.1–S7.7 annotation
and model experiments have been implemented and tested (834 tests). Remaining
S8.1+ tasks remain future work until explicitly claimed. Status is reconciled
with the code on this branch as of 2026-09-10.

## Use rules

An agent should normally take one unchecked task at a time. Before changing
runtime code, read only:

1. `AGENTS.md`;
2. `research/learning_support/passage_practice/AGENTS.md`;
3. the selected task block;
4. the exact source files and tests named by the selected task.

Do not perform open-ended repository exploration. Read broad context documents
such as `README.md`, `docs/architecture.md`, `docs/contracts.md`,
`docs/testing_strategy.md`, or `docs/semantic_music_extraction_plan.md` only
when the selected task explicitly names them or the listed context is
insufficient. If the listed context is insufficient, stop and ask for the
specific missing file or output.

Each task should leave:

- focused tests for the behavior it adds;
- stable diagnostics for unsupported or ambiguous cases;
- no unrequested empty package scaffolding;
- no MusicXML fixture without provenance notes;
- no downstream pedagogical claims inside upstream score or observation code.

## Decision stops

Resolve these before downstream implementation depends on them:

| ID | Decision | Blocks |
|---|---|---|
| S-Q001 | Whether `SemanticHypothesis` is independent from `PatternMatch` or whether pattern matches become one subtype. | Accepted (D-015). S1.2 onward |
| S-Q002 | Whether semantic direct observations live in `observations/` or extend feature evidence. | Accepted (D-017). S2.1 onward |
| S-Q003 | Initial confidence scale and wording bands. | Accepted (D-016). S1.4, S3.1 onward |
| S-Q004 | Minimum source facts needed from `ScoreIR` before semantic views can avoid duplicate parsing. | Accepted (D-018). S2.2 onward |
| S-Q005 | Learner-feedback retention and privacy policy for thesis experiments. | S5.1 onward |
| S-Q006 | Annotation schema for teacher or human semantic labels. | S7.1 onward |

## Phase S0 — Inventory Existing Inputs

- [x] **S0.1 Inventory current score facts exposed to passage practice.**
  Scope: inspect implemented passage-practice models, selection code, and tests.
  Output: a table of currently available event IDs, timing, staff, voice, hand,
  tie, articulation, dynamic, measure, key, meter, and clef facts. Limit: no
  runtime changes.

- [x] **S0.2 Inventory current piano-difficulty feature evidence.** Scope:
  inspect promoted difficulty features and exported payloads that can describe
  a selected CIPI passage. Output: a table of feature IDs, units, region scope,
  event-level trace availability, and missing event references. Limit: do not
  alter feature formulas.

- [x] **S0.3 Map CIPI walkthrough outputs to semantic inputs.** Scope:
  identify what a CIPI test run can provide to a passage semantic analyzer:
  score path, selected region, difficulty score, contributing dimensions,
  available features, and exported evidence. Output: one documented handoff
  note. Limit: do not require CIPI data in committed tests.

- [x] **S0.4 Identify duplicate parsing risks.** Scope: list any semantic facts
  that would be tempting to parse directly from MusicXML but should instead
  come from `ScoreIR` or passage views. Output: risk list with owner package.
  Limit: no parser changes.

- [x] **S0.5 Create the semantic input readiness matrix.** Depends on: S0.1-S0.4.
  Scope: combine the inventories into a matrix with columns for source,
  available now, needed for phase, owner, test fixture, and blocking decision.
  Output: committed documentation only.

## Phase S1 — Contracts and Confidence Policy

- [x] **S1.1 Record S-Q001 decision.** Scope: decide whether semantic hypotheses
  are separate from pattern matches. Output: dated decision entry. Limit: no
  runtime model changes in the decision task.

- [x] **S1.2 Add the minimal `SemanticHypothesis` contract.** Depends on:
  S1.1. Scope: implement immutable payload fields for hypothesis identity,
  type, passage reference, covered region, covered events, confidence, method,
  evidence references, criteria, contradictions, missing evidence, and
  diagnostics. Tests: invalid confidence, missing passage reference, bad
  version, deterministic serialization.

- [x] **S1.3 Add the minimal `SemanticBundle` contract.** Depends on: S1.2.
  Scope: group semantic hypotheses for one passage with view refs, observation
  refs, method versions, ranked hypothesis refs, and diagnostics. Tests:
  bundle rejects mixed passage IDs, preserves contradictory hypotheses, and
  serializes deterministically.

- [x] **S1.4 Record S-Q003 confidence policy.** Scope: define initial bands,
  calibration status labels, abstention behavior, and presentation wording.
  Output: doc section or separate policy file plus decision entry. Limit: no
  detector thresholds yet.

- [x] **S1.5 Add confidence helper value objects.** Depends on: S1.4. Scope:
  bounded score, band derivation, method status, and contradiction penalty
  helper where needed. Tests: boundary values, unsupported score, deterministic
  band mapping.

- [x] **S1.6 Add empty/no-supported-hypothesis payload fixture.** Depends on:
  S1.3-S1.5. Scope: frozen JSON for a passage where no semantic finding should
  be presented. Tests: round-trip and diagnostic assertions.

- [x] **S1.7 Document contract examples.** Depends on: S1.6. Scope: add concise
  examples for high-confidence, low-confidence, contradictory, and no-supported
  semantic outputs. Limit: documentation only.

## Phase S2 — Core Views and Observations

- [x] **S2.1 Resolve S-Q002 observation ownership.** Scope: decide package
  location and import direction for semantic observations versus feature
  evidence. Output: dated decision. Limit: no implementation.

- [x] **S2.2 Resolve S-Q004 minimum source facts.** Scope: identify which facts
  must be promoted or exposed before semantic views are reliable. Output: dated
  decision and any required upstream task list. Limit: do not implement upstream
  changes here.

- [x] **S2.3 Add semantic fixture manifest entries.** Depends on: S2.1-S2.2.
  Scope: define fixture provenance and expected semantic role for top-voice
  melody, left-hand melody, accompaniment pattern, two voices, syncopation, and
  ambiguity. Tests: fixture loader smoke checks.

- [x] **S2.4 Implement or adapt `attack_stream` view.** Depends on: S2.3.
  Scope: deterministic tie-collapsed attacks with exact timing and source refs.
  Tests: ties, rests, chords, ordering, source immutability.

- [x] **S2.5 Implement or adapt `written_stream` view.** Depends on: S2.4.
  Scope: written events preserving staff, encoded voice, notation details, and
  links to logical attacks. Tests: two voices, two staves, ties, omissions.

- [x] **S2.6 Implement `rhythm_grid` view.** Depends on: S2.4. Scope: attack
  positions, durations, beat location, subdivision relation, and hand alignment.
  Tests: off-beat attacks, ties across beats, mixed subdivisions, exact
  fractions.

- [x] **S2.7 Implement `texture_grid` view.** Depends on: S2.4-S2.5. Scope:
  onset simultaneity, chord size, active voices, sustained-under-moving flags,
  and density summaries. Tests: homophonic chords, arpeggiation, sustained
  notes, two encoded voices.

- [x] **S2.8 Implement initial `salience_view`.** Depends on: S2.6-S2.7.
  Scope: event-level candidate salience factors for register, duration, metric
  accent, explicit accent/dynamic evidence where available, plus explicit
  diagnostics for unavailable slur evidence and unavailable pattern-exclusion
  markers. Tests: top note salience, long-note salience, missing dynamic
  evidence, unavailable slur/pattern evidence, contradictory cues.

- [x] **S2.9 Add direct pitch and interval observations.** Depends on: S2.4.
  Scope: range, contour intervals, leap frequency, repeated notes, registral
  extremes. Tests: transposition metamorphism, repeated-note negative, source
  refs.
  Implementation context:
  - Must read:
    `src/passage_practice/observations/__init__.py`,
    `src/passage_practice/models/observations.py`,
    `tests/unit/test_observations.py`.
  - Existing pattern to copy: `observe_pitch_transitions()` already resolves
    passage refs, emits `ObservationResult`, carries exact regions/source refs,
    and records stable diagnostics.
  - Likely edits: extend `observations/__init__.py` if the additions remain
    small; split a new observation module only if this file becomes unwieldy.
  - Verification: run
    `python -m pytest research/learning_support/passage_practice/tests/unit/test_observations.py -q`.
  - Do not inspect views, detectors, or difficulty-analysis code unless
    blocked by missing source facts.
  Status 2026-09-10: implemented in `src/passage_practice/observations/__init__.py`
  (`observe_pitch_range`, `observe_leap_frequency`, `observe_repeated_notes`,
  `observe_registral_extremes`) with 8 new tests in `tests/unit/test_observations.py`;
  all verify FACT/INFERENCE basis, resolvable refs, and abstention diagnostics. Suite 49 passed.

- [x] **S2.10 Add direct rhythm observations.** Depends on: S2.6. Scope:
  attack density, shortest duration, off-beat density, syncopation proxy, hand
  alignment ratio, subdivision mismatch. Tests: aligned hands, staggered hands,
  tuplets unsupported/diagnostic if not supported.
  Implementation context:
  - Must read:
    `src/passage_practice/views/rhythm_grid.py`,
    `tests/unit/test_rhythm_grid.py`,
    `src/passage_practice/models/observations.py`.
  - Existing pattern to copy: view builders project `Passage` + `ScoreIR` into
    deterministic facts; observation builders should consume those facts and
    return `ObservationResult`, not parse MusicXML.
  - Likely edits: observation code plus `tests/unit/test_observations.py` or a
    focused new rhythm-observation test file if the existing file becomes too
    mixed.
  - Verification: run the rhythm observation test file and
    `tests/unit/test_rhythm_grid.py`.
  - Do not recompute raw score parsing, add detector logic, or inspect broader
    semantic plans unless blocked.
  Status 2026-09-10: implemented in `src/passage_practice/observations/__init__.py`
  (`observe_attack_density`, `observe_shortest_duration`, `observe_off_beat_density`,
  `observe_syncopation_proxy`, `observe_hand_alignment_ratio`,
  `observe_subdivision_mismatch`) with `tests/unit/test_rhythm_observations.py`; rhythm_grid facts consumed only, tuplets flagged unsupported.

- [x] **S2.11 Add direct texture observations.** Depends on: S2.7. Scope:
  simultaneity count, chord density, sustained-under-moving count, voice count,
  staff crossing where available. Tests: chord versus sequential notes, two
  voices, ambiguous voice behavior.
  Implementation context:
  - Must read:
    `src/passage_practice/views/texture_grid.py`,
    `tests/unit/test_texture_grid.py`,
    `src/passage_practice/models/observations.py`.
  - Existing pattern to copy: `texture_grid` owns simultaneity and sustained
    context facts; observations should measure from those view facts and keep
    source refs/diagnostics.
  - Edge case to preserve: cross-boundary sustained material may matter for
    sustained-under-moving observations; do not silently ignore it if the view
    exposes it.
  - Likely edits: observation code plus a focused texture-observation test.
    Extract a helper for active/sounding material only if real duplication
    appears with existing salience/texture logic.
  - Verification: run the texture observation test file and
    `tests/unit/test_texture_grid.py`.
  - Do not inspect notation/readability or detector files unless blocked.
  Status 2026-09-10: implemented in `src/passage_practice/observations/__init__.py`
  (`observe_max_simultaneity`, `observe_chord_density`, `observe_sustained_under_moving`,
  `observe_voice_count`, `observe_staff_crossing`) with `tests/unit/test_texture_observations.py`; cross-boundary sustained out-of-scope per view semantics preserved.

- [x] **S2.12 Add direct notation-readability observations.** Depends on:
  S2.5. Scope: accidental density, ledger-line proxy, clef-change presence,
  articulation density, ornament/grace-note diagnostic where available. Tests:
  missing layout data remains unavailable, not zero.
  Implementation context:
  - Must read:
    `src/passage_practice/views/written_stream.py`,
    `tests/unit/test_written_stream.py`,
    `src/passage_practice/models/observations.py`.
  - Existing pattern to copy: `written_stream` projects notation facts while
    declaring omissions; readability observations should consume those facts and
    record missing layout data as unavailable, never as zero.
  - Likely edits: observation code plus a focused notation-readability test.
  - Verification: run the notation-readability observation test file and
    `tests/unit/test_written_stream.py`.
  - Do not inspect rendering, MusicXML parser internals, or difficulty-analysis
    code unless blocked by missing normalized facts.
  Status 2026-09-10: implemented in `src/passage_practice/observations/__init__.py`
  (`observe_accidental_density`, `observe_ledger_line_proxy`, `observe_clef_change_presence`,
  `observe_articulation_density`, `observe_ornament_grace_notes`) with
  `tests/unit/test_notation_readability_observations.py`; missing layout declared unavailable via diagnostics.

- [x] **S2.13 Add semantic-view integration payload.** Depends on: S2.4-S2.12.
  Scope: one compact payload showing passage, view refs, observation refs, and
  diagnostics. Tests: deterministic JSON and resolvable refs.
  Implementation context:
  - Must read:
    `src/passage_practice/semantics/contracts.py`,
    `src/passage_practice/models/observations.py`,
    `src/passage_practice/models/passage.py`,
    `src/passage_practice/views/__init__.py`,
    `tests/unit/test_semantic_contracts.py`.
  - Existing pattern to copy: semantic contracts are immutable, versioned,
    deterministic, and ref-oriented. The integration payload should reference
    passage/view/observation IDs compactly; do not embed full view or
    observation payloads unless the contract explicitly requires it.
  - Likely edits: semantic contract/integration code plus focused tests for
    deterministic JSON, resolvable refs, missing optional views, and diagnostics.
  - Verification: run semantic contract/integration tests plus the observation
    tests touched by S2.9-S2.12.
  - Do not build detectors, confidence scoring, or pedagogical diagnosis here.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/integration.py`
  (`build_semantic_integration`) with `tests/unit/test_semantic_integration.py` (7 tests:
  deterministic, resolvable refs, missing optional salience, diagnostics, empty passage);
  hypotheses empty, view/observation refs are opaque passage-scoped IDs.

## Phase S3 — First Deterministic Semantic Detectors

- [x] **S3.1 Define detector interface and registry.** Depends on: S1.5,
  S2.13. Scope: metadata, required views, optional views, supported subset,
  method version, output hypothesis types, and registry lookup. Tests:
  unsupported view diagnostic, deterministic ordering, detector selection by
  family.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/registry.py`
  (`DetectorSpec`, `BaseDetector`, `DetectorRegistry`) with
  `tests/unit/test_detector_registry.py` (6 tests: unsupported view, selectable_for, ordering, by_family).

- [x] **S3.2 Implement melody salience detector v1.** Depends on: S3.1.
  Scope: produce ranked `role.melody` hypotheses using register, duration,
  metric, articulation/dynamic where available, contour continuity, and
  accompaniment-pattern exclusion. Tests: top-voice melody, left-hand melody,
  hidden melody, ambiguous top voice, transposition.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/melody.py`
  with `tests/unit/test_melody_detector.py` (6 tests: top-voice, left-hand, hidden, ambiguous, transposition).

- [x] **S3.3 Implement bass-anchor detector v1.** Depends on: S3.1. Scope:
  identify likely harmonic bass using lowest material, duration, metric
  placement, recurrence, and pitch-class stability. Tests: ordinary bass,
  walking bass, pedal point, melodic left hand negative, ambiguous low voice.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/bass.py`
  with `tests/unit/test_bass_detector.py`.

- [x] **S3.4 Implement accompaniment-pattern detector v1.** Depends on: S3.1.
  Scope: detect repeated broken chord, block chord support, Alberti-like shape,
  ostinato, tremolo-like alternation when supported. Tests: clear positives,
  scalar negative, too-short pattern low confidence, repeated-note ambiguity.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/accompaniment.py`
  with `tests/unit/test_accompaniment_detector.py`.

- [x] **S3.5 Implement rhythm-layer detector v1.** Depends on: S3.1. Scope:
  identify independent hand rhythms, syncopated layer, common-attack skeleton,
  and stable accompaniment rhythm. Tests: aligned hands negative, syncopated
  melody, staggered accompaniment, mixed subdivision.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/rhythm.py`
  with `tests/unit/test_rhythm_detector.py`.

- [x] **S3.6 Implement texture classifier v1.** Depends on: S3.2-S3.5. Scope:
  rank monophonic, homophonic block, melody-plus-accompaniment, arpeggiated,
  and polyphonic candidates. Tests: each class positive, close negatives,
  ambiguous output with multiple medium/low hypotheses.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/texture.py`
  with `tests/unit/test_texture_classifier.py`.

- [x] **S3.7 Add semantic bundle builder.** Depends on: S3.2-S3.6. Scope:
  run selected detectors, merge hypotheses, sort by confidence and family, and
  keep contradictions visible. Tests: deterministic ordering, mixed detector
  diagnostics, no-supported-hypothesis case.
  Status 2026-09-10: implemented in `src/passage_practice/semantics/bundle_builder.py`
  with `tests/unit/test_semantic_bundle_builder.py` and empty-bundle fixture
  `tests/unit/test_semantic_empty_bundle.py`; registry `selectable_for` used.

- [x] **S3.8 Add first semantic regression fixtures.** Depends on: S3.7.
  Scope: freeze compact payloads for top-voice melody, left-hand melody,
  accompaniment, independent rhythm, and ambiguous passage. Tests: regression
  update path documented.
  Status 2026-09-10: frozen in `tests/regression/semantic_payloads/` (5 JSON:
  `top_voice_melody`, `left_hand_melody`, `accompaniment`, `independent_rhythm`,
  `ambiguous`) with `tests/unit/test_semantic_regression.py` (4 tests: exist/valid,
  rebuild match, expected families, update path). See `docs/semantic_music_extraction_plan.md` § Testing strategy regression.

## Phase S4 — Pedagogical Hypothesis Bridge

- [x] **S4.1 Define pedagogical hypothesis input boundary.** Scope: document
  which parts of semantic bundles, difficulty context, and learner feedback may
  feed diagnosis rules. Tests: contract-level rejection of raw free-text advice
  and unsupported score refs.
  Status 2026-09-10: documented in `docs/pedagogical_input_boundary.md` and
  `src/passage_practice/pedagogy/boundary.py` (`validate_pedagogical_inputs`);
  `tests/unit/test_pedagogical_input_boundary.py` (8 tests) asserts
  `advice_text`/`free_text_diagnosis` rejection and unresolvable `SourceRef` handling.

- [x] **S4.2 Add semantic-to-diagnosis rule metadata.** Depends on: S4.1.
  Scope: rule ID, required semantic hypotheses, optional difficulty dimensions,
  learner data caveats, candidate objectives, candidate strategies, and
  contraindications. Tests: missing required hypothesis, contradictory evidence.
  Status 2026-09-10: `src/passage_practice/pedagogy/rules.py`
  (`PedagogicalRule`, `PedagogicalRuleRegistry`, `evaluate_rule`) with
  `tests/unit/test_pedagogical_rules.py` (8 tests: missing hypothesis, contradiction).

- [x] **S4.3 Add melody-projection pedagogical hypothesis.** Depends on: S4.2.
  Scope: map melody-hidden or melody-plus-accompaniment evidence to a qualified
  learner challenge and learner question. Tests: evidence present, learner data
  absent caveat, contradiction reduces confidence.
  Status 2026-09-10: `src/passage_practice/pedagogy/contracts.py`
  (`PedagogicalHypothesis`) + `melody_projection.py`
  (`build_melody_projection_hypothesis`, rule `melody_projection.v1`) with
  `tests/unit/test_melody_projection_pedagogy.py` (5 tests: evidence, learner caveat,
  contradiction blocking, confidence derivation, real bundle integration).

- [x] **S4.4 Add bass/leap targeting pedagogical hypothesis.** Depends on:
  S4.2. Scope: map bass-anchor plus leap/motor-proxy observations to possible
  relocation or landing-target focus. Tests: leap positive, smooth bass
  negative, learner-dependent caveat.
  Status 2026-09-10: `src/passage_practice/pedagogy/bass_leap.py`
  (`build_bass_leap_hypothesis`, rule `bass_leap.v1`) with
  `tests/unit/test_bass_leap_pedagogy.py` (5 tests: leap positive, smooth negative,
  learner caveat, missing bass, real bundle+leap observations).

- [x] **S4.5 Add rhythmic coordination pedagogical hypothesis.** Depends on:
  S4.2. Scope: map independent rhythm and hand-alignment evidence to a
  qualified coordination focus. Tests: aligned hands negative, staggered hands
  positive, low confidence when rhythm evidence incomplete.
  Status 2026-09-10: `src/passage_practice/pedagogy/rhythmic_coordination.py`
  (`build_rhythmic_coordination_hypothesis`, rule `rhythmic_coordination.v1`) with
  `tests/unit/test_rhythmic_coordination_pedagogy.py` (6 tests: aligned negative,
  staggered positive, low confidence, high alignment block, learner caveat, real bundle).

- [x] **S4.6 Add reading-load pedagogical hypothesis.** Depends on: S4.2.
  Scope: map notation density, accidentals, rhythm complexity, and low pattern
  redundancy to possible reading burden. Tests: missing layout unavailable,
  accidentals alone not overclaimed, combined evidence higher.
  Status 2026-09-10: `src/passage_practice/pedagogy/reading_load.py`
  (`build_reading_load_hypothesis`, rule `reading_load.v1`) with
  `tests/unit/test_reading_load_pedagogy.py` (6 tests: layout unavailable, single
  vs combined, learner caveat, real observations integration).

- [x] **S4.7 Add semantic-to-strategy compatibility table.** Depends on:
  S4.3-S4.6. Scope: map hypothesis IDs to objective IDs and candidate strategy
  IDs without invoking transformations. Tests: compatible strategies present,
  incompatible strategies absent.
  Status 2026-09-10: `src/passage_practice/pedagogy/compatibility.py`
  (`COMPATIBILITY_TABLE`, `get_compatible_strategies`) with
  `tests/unit/test_strategy_compatibility.py` (5 tests: compatible/incompatible/unknown).

- [x] **S4.8 Add integration report for passage to pedagogical hypotheses.**
  Depends on: S4.7. Scope: produce a compact report that shows difficulty
  context optional, semantic evidence required, learner caveats retained. Tests:
  user-selected passage without hotspot succeeds.
  Status 2026-09-10: `src/passage_practice/pedagogy/integration.py`
  (`PedagogicalReport`, `build_pedagogical_report`) with
  `tests/unit/test_pedagogical_integration.py` (5 tests: optional context, required
  evidence, caveats retained, user-selected without hotspot, deterministic).

## Phase S5 — Learner Feedback Loop

- [x] **S5.1 Resolve S-Q005 learner-feedback policy.** Scope: decide allowed
  feedback fields, retention state, privacy caveats, and whether free text can
  be committed in synthetic tests. Output: dated decision. Limit: no storage
  implementation yet.
  Status 2026-09-10: `docs/learner_feedback_policy.md` + `docs/decisions.md`
  D-019 (accepted). Allowed fields, `session`/`explicit_save` retention,
  synthetic-only free text labeled `synthetic_data`; real data blocked.

- [x] **S5.2 Add `LearnerFeedbackSignal` contract.** Depends on: S5.1. Scope:
  prompt ID, answer kind, selected value, optional free text, passage ref,
  mapped hypothesis/objective refs, retention scope, diagnostics. Tests:
  serialization, missing passage, unsupported answer kind.
  Status 2026-09-10: `src/passage_practice/learner_feedback/contracts.py`
  (`LearnerFeedbackSignal`, `AnswerKind`, `RetentionScope`) with
  `tests/unit/test_learner_feedback_signal.py` (5 tests).

- [x] **S5.3 Add standard feedback prompt registry.** Depends on: S5.2. Scope:
  define controlled prompts for hardest aspect, melody projection, rhythm,
  jumps, reading, harmony, and relaxation. Tests: stable IDs, no duplicate
  choices, prompt-to-hypothesis mappings.
  Status 2026-09-10: `src/passage_practice/learner_feedback/prompts.py`
  (`PROMPT_REGISTRY`, 7 prompts) with `tests/unit/test_feedback_prompts.py`
  (4 tests: stable IDs, no duplicates, hypothesis mappings).

- [x] **S5.4 Add feedback mapping rules.** Depends on: S5.3. Scope: map selected
  answers to hypothesis increases, decreases, rejection, or request for more
  evidence. Tests: melody answer boosts melody-projection focus, rhythm answer
  boosts coordination focus, "something else" preserves score hypotheses.
  Status 2026-09-10: `src/passage_practice/learner_feedback/mapping.py`
  (`map_feedback`, `FeedbackAdjustment`) with `tests/unit/test_feedback_mapping.py`
  (5 tests: melody boost, rhythm boost, something_else preserved, not_sure).

- [x] **S5.5 Add `LearnerAdjustedFocus` contract.** Depends on: S5.4. Scope:
  preserve base semantic bundle ID, feedback IDs, ranked pedagogical hypotheses,
  primary focus, secondary focuses, deprioritized hypotheses, and rationale.
  Tests: original semantic bundle unchanged, deterministic output.
  Status 2026-09-10: `src/passage_practice/learner_feedback/adjusted_focus.py`
  (`LearnerAdjustedFocus`, `build_learner_adjusted_focus`) with
  `tests/unit/test_learner_adjusted_focus.py` (5 tests: unchanged bundle,
  deterministic, primary boost, feedback IDs, empty feedback).

- [x] **S5.6 Add feedback integration tests.** Depends on: S5.5. Scope: run a
  passage through semantic bundle, pedagogical hypotheses, feedback signal, and
  adjusted focus. Tests: increase, decrease, reject, and no-op cases.
  Status 2026-09-10: `tests/unit/test_learner_feedback_integration.py` (5 tests:
  increase melody_hidden boost, decrease hands_together_ok demote, something_else
  preserve, not_sure request evidence, bundle unchanged); also fixed
  `src/passage_practice/learner_feedback/mapping.py:97` demotion for *_ok/meldody_clear.

## Phase S6 — Harmony and Phrase Expansion

- [x] **S6.1 Add coarse harmony-view contract.** Scope: define pitch-class
  collections, bass candidates, duration weighting, local-key candidates, and
  harmonic rhythm evidence. Tests: empty/atonal or insufficient evidence
  diagnostic.
  Status 2026-09-10: `src/passage_practice/views/harmony_view.py`
  (`HarmonyView`, `build_harmony_view`) with `tests/unit/test_harmony_view.py`
  (3 tests: empty diagnostic, normal fixture, insufficient notes).

- [x] **S6.2 Implement local key candidate heuristic v1.** Depends on: S6.1.
  Scope: rank local key candidates from pitch-class distribution and context.
  Tests: clear diatonic passage, chromatic ambiguity, transposition.
  Status 2026-09-10: `src/passage_practice/views/harmony_view.py`
  (`rank_local_key_candidates`) with `tests/unit/test_local_key_candidates.py`
  (3 tests: C major clear, chromatic low confidence, D major transposition).

- [x] **S6.3 Implement harmonic rhythm heuristic v1.** Depends on: S6.1.
  Scope: infer likely sonority-change points from bass, pitch-class changes,
  duration, and metric position. Tests: once-per-measure harmony, every-beat
  changes, ornamental non-chord tones.
  Status 2026-09-10: `src/passage_practice/views/harmony_view.py`
  (`infer_harmonic_rhythm`) with `tests/unit/test_harmonic_rhythm.py`
  (4 tests: once-per-measure, every-beat, ornamental filtered, longer not filtered).

- [x] **S6.4 Implement cadence candidate heuristic v1.** Depends on: S6.2-S6.3.
  Scope: detect coarse cadential arrivals using bass motion, local key,
  metric position, duration, and phrase-boundary evidence when available.
  Tests: simple cadence positive, cadence-like negative, low-key-confidence
  abstention.
  Status 2026-09-10: `src/passage_practice/semantics/cadence.py`
  (`detect_cadence_candidates`, `CadenceCandidate`) with
  `tests/unit/test_cadence_candidate.py` (4 tests: positive, off-beat/short negative,
  low-key abstention, phrase-boundary boost).

- [x] **S6.5 Implement phrase-boundary heuristic v1.** Scope: combine rests,
  long notes, slurs, repeated motifs, cadential candidates, and metric position.
  Tests: clear boundary, tie-over-boundary negative, phrase continuation
  ambiguity.
  Status 2026-09-10: `src/passage_practice/semantics/phrase.py`
  (`detect_phrase_boundaries`, `PhraseBoundary`) with
  `tests/unit/test_phrase_boundary.py` (4 tests: clear rest/long, tie-over negative,
  repeated motif ambiguity, slur unavailable).

- [x] **S6.6 Implement sequence/repetition heuristic v1.** Scope: detect local
  contour/rhythm recurrence under transposition or register change. Tests:
  transposed sequence, exact repetition, similar rhythm different contour,
  too-short negative.
  Status 2026-09-10: `src/passage_practice/semantics/sequence.py`
  (`detect_sequence_repetition`, `SequenceCandidate`) with
  `tests/unit/test_sequence_repetition.py` (4 tests: transposed, exact, rhythm/contour mismatch, too-short).

- [x] **S6.7 Connect harmony and phrase hypotheses to pedagogy.** Depends on:
  S6.2-S6.6. Scope: add compatibility with harmonic skeleton, cadence focus,
  phrase-shape, and sequence-chunking strategies. Tests: no action is suggested
  for unsupported harmony.
  Status 2026-09-10: `src/passage_practice/pedagogy/compatibility.py`
  (`HARMONIC_SKELETON_HYPOTHESIS_TYPE`, `CADENCE_FOCUS_HYPOTHESIS_TYPE`,
  `PHRASE_SHAPE_HYPOTHESIS_TYPE`, `SEQUENCE_CHUNKING_HYPOTHESIS_TYPE`,
  `get_strategies_for_harmony_view`) with `tests/unit/test_strategy_compatibility.py`
  updated (6 tests: includes harmonic skeleton/cadence/phrase/sequence and unsupported harmony no action).

## Phase S7 — Annotation and Learned-Model Experiments

- [x] **S7.1 Resolve S-Q006 annotation schema.** Scope: decide fields for human
  labels: melody, bass, accompaniment, texture, phrase, harmony, difficulty
  reason, learner issue, advice, and reviewer status. Output: dated decision.
  Status 2026-09-10: `docs/annotation_schema.md` + `docs/decisions.md` D-020
  (accepted, controlled vocabularies for 9 families, 12 record fields, synthetic-only).

- [x] **S7.2 Add annotation record contract.** Depends on: S7.1. Scope: passage
  ref, label family, label value, annotator role, confidence, provenance,
  review state, and privacy status. Tests: deterministic serialization, no
  private data in committed synthetic fixtures.
  Status 2026-09-10: `src/passage_practice/annotation/contracts.py`
  (`AnnotationRecord`, `LabelFamily`, `FAMILY_VOCABULARIES`) with
  `tests/unit/test_annotation_record.py` (5 tests: deterministic, vocabulary, synthetic privacy, review_state, source_refs).

- [x] **S7.3 Add synthetic annotation fixtures.** Depends on: S7.2. Scope:
  create tiny labels for existing semantic fixtures. Tests: fixture validity and
  annotation-to-passage reference resolution.
  Status 2026-09-10: `tests/fixtures/annotation/` (5 JSON: top_voice_melody,
  left_hand_melody, accompaniment_pattern, syncopation, ambiguity) with
  `tests/unit/test_synthetic_annotation_fixtures.py` (2 tests: validity, passage resolution).

- [x] **S7.4 Add heuristic baseline export.** Depends on: S7.3. Scope: export
  detector outputs and human labels to a compact comparison table. Tests:
  stable columns, source refs, method versions.
  Status 2026-09-10: `src/passage_practice/annotation/export.py`
  (`export_baseline_comparison`) with `tests/unit/test_heuristic_baseline_export.py`
  (3 tests: stable columns, deterministic source refs, empty).

- [x] **S7.5 Add model interface behind detector contract.** Depends on: S7.4.
  Scope: define local deterministic inference interface that returns
  `SemanticHypothesis` records. Tests: fake model adapter, deterministic output,
  version metadata required.
  Status 2026-09-10: `src/passage_practice/semantics/model_interface.py`
  (`ModelSemanticAdapter`, `make_fake_model_fn`) with
  `tests/unit/test_model_interface.py` (3 tests: deterministic, version required, contract).

- [x] **S7.6 Add first tiny learned-model experiment.** Depends on: S7.5. Scope:
  use small local data only to test plumbing, not claim quality. Tests: model
  output contract, abstention behavior, comparison to heuristic baseline.
  Status 2026-09-10: `src/passage_practice/semantics/tiny_experiment.py`
  (`run_tiny_experiment`) with `tests/unit/test_tiny_experiment.py` (3 tests: contract, abstention, comparison).

- [x] **S7.7 Add model evaluation report template.** Depends on: S7.6. Scope:
  document metrics, baseline comparison, training-data identity, limitations,
  and failure examples. Limit: no automatic quality claims.
  Status 2026-09-10: `src/passage_practice/semantics/evaluation_report.py`
  (`ModelEvaluationReport`, `build_template_report`) with
  `tests/unit/test_model_evaluation_report.py` (4 tests: required fields, baseline/training identity, limitations, no quality claim).

## Phase S8 — Pedagogical Corpus and Explanation Preparation

- [x] **S8.1 Define passage-level pedagogical corpus schema.** Scope: separate
  score facts, difficulty context, semantic hypotheses, learner feedback, human
  explanation, generated explanation, exercise candidate, and review status.
  Tests: schema round-trip with synthetic data.
  Status 2026-09-11: `src/passage_practice/corpus/schema.py`
  (`PedagogicalCorpusRecord`, `CorpusReviewState`) with
  `tests/unit/test_pedagogical_corpus_schema.py` (5 tests: round-trip, separation, optional fields, provenance, privacy).

- [x] **S8.2 Add source provenance fields for pedagogical text.** Depends on:
  S8.1. Scope: distinguish teacher-authored, learner-authored, literature
  paraphrase, and system-generated text. Tests: unsupported source category
  rejected.
  Status 2026-09-11: `src/passage_practice/corpus/text_provenance.py`
  (`PedagogicalText`, `TextSourceCategory`) with
  `tests/unit/test_text_provenance.py` (5 tests: four categories, unsupported rejected, literature source_ref, distinction).

- [x] **S8.3 Add synthetic corpus examples.** Depends on: S8.2. Scope: create
  small non-copyrighted records tied to semantic fixtures. Tests: references
  resolve, no private learner data.
  Status 2026-09-11: `tests/fixtures/corpus/` (top_voice_melody, left_hand_melody,
  accompaniment_pattern) + `tests/unit/test_synthetic_corpus_examples.py` (3 tests: manifest, resolve, no PII).

- [x] **S8.4 Add evidence-grounded explanation brief.** Depends on: S8.3.
  Scope: produce a structured prompt/input payload for explanation adapters
  from semantic and pedagogical hypotheses. Tests: unsupported claims absent,
  uncertainty wording fields present.
  Status 2026-09-11: `src/passage_practice/corpus/explanation_brief.py`
  (`ExplanationBrief`, `build_explanation_brief`) with
  `tests/unit/test_explanation_brief.py` (4 tests: unsupported absent, wording present, round-trip, no corpus).

- [x] **S8.5 Add explanation-audit tests.** Depends on: S8.4. Scope: verify that
  generated or template explanations cannot introduce melody, harmony, learner,
  or difficulty claims missing from the structured evidence. Tests: template
  output and mock LLM output path if such a path exists.
  Status 2026-09-11: `src/passage_practice/corpus/explanation_audit.py`
  (`audit_explanation`, `template_explanation`, `mock_llm_explanation`) with
  `tests/unit/test_explanation_audit.py` (4 tests: template grounded, mock LLM audit, learner claim, melody).

- [x] **S8.6 Add corpus evaluation checklist.** Depends on: S8.5. Scope:
  define teacher-review questions for plausibility, usefulness, traceability,
  overclaiming, and exercise fit. Limit: no real participant data.
  Status 2026-09-11: `docs/corpus_evaluation_checklist.md` +
  `src/passage_practice/corpus/evaluation.py` (`load_checklist`, `evaluate_checklist`) with
  `tests/unit/test_corpus_evaluation_checklist.py` (4 tests: covers dimensions, doc match, rejects incomplete, no PII).

## Cross-cutting quality tasks

- [x] **S-X1 Add semantic diagnostic code registry.** Scope: stable codes for
  missing view, unsupported notation, low confidence, contradictory criteria,
  missing source refs, and learner-dependent claim. Tests: no duplicate codes.
  Status 2026-09-11: `src/passage_practice/semantics/diagnostic_codes.py`
  (97 codes in 7 categories) with `tests/unit/test_diagnostic_code_registry.py` (4 tests: duplicates, snake_case, categories).

- [x] **S-X2 Add semantic fixture provenance audit.** Scope: ensure every
  semantic fixture is synthetic, licensed, or otherwise commit-safe. Tests:
  manifest coverage assertion.
  Status 2026-09-11: `tests/unit/test_fixture_provenance_audit.py` (4 tests: manifest coverage, synthetic provenance, corpus, no copyrighted material) vs `tests/fixtures/semantic_manifest.md`.

- [x] **S-X3 Add semantic metamorphic test helpers.** Scope: helper functions
  for transposition, duration scaling, staff swap, neighboring-measure addition,
  and serialize/reopen comparisons. Tests: helper self-tests on tiny fixtures.
  Status 2026-09-11: `src/passage_practice/helpers/metamorphic.py`
  (`transpose_score`, `scale_durations`, `swap_staves`, `add_neighboring_measure`) with `tests/unit/test_metamorphic_helpers.py` (5 tests).

- [x] **S-X4 Add review checklist for semantic PRs.** Scope: checklist covering
  provenance, uncertainty, source refs, layer boundaries, learner caveats,
  positive/negative tests, and no hidden LLM dependency.
  Status 2026-09-11: `docs/semantic_pr_checklist.md` (7 sections) with `tests/unit/test_pr_checklist.py` (2 tests: sections, checkboxes).

- [x] **S-X5 Add CIPI semantic review worksheet.** Scope: documentation template
  for manually reviewing predicted difficult CIPI passages and recording likely
  semantic detectors, learner questions, and exercise actions. Limit: no CIPI
  files committed.
  Status 2026-09-11: `docs/cipi_semantic_review_worksheet.md` (template + synthetic example) with `tests/unit/test_cipi_worksheet.py` (3 tests: fields, example, no CIPI files).

- [x] **S-X6 Add periodic architecture audit task.** Scope: after each semantic
  phase, review whether any code crossed layer boundaries or duplicated
  difficulty parsing. Output: short audit note and required cleanup tasks.
  Status 2026-09-11: `docs/architecture_audit_S8.md` (PASS on all layer checks) with `tests/unit/test_architecture_audit.py` (5 tests: semantics/observations/corpus boundaries, shared, doc).
