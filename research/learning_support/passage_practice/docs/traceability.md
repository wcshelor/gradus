# Traceability Matrix

This matrix connects program requirements to implementation packages, required
tests, and management review gates. Agents should update it when a requirement
changes or gains a new implementation path.

## Core requirements

| ID | Requirement | Primary packages | Minimum evidence | Gate |
|---|---|---|---|---|
| R-001 | Preserve exact score positions and stable source references | WP-01, WP-02 | fraction, ID, boundary contract tests | G1 |
| R-002 | Select an exact passage without mutating the source score | WP-02 | boundary matrix and immutability test | G1 |
| R-003 | Preserve active score context at passage start | WP-02, WP-13 | inherited key/meter/clef fixture | G1, G4 |
| R-004 | Derive multiple purpose-specific views from one passage | WP-03 | deterministic view payloads | G2 |
| R-005 | Keep staff, voice, hand, and role distinct | WP-01–WP-14 | ambiguous-hand and multi-voice tests | every gate |
| R-006 | Reproduce hotspot feature summaries from event observations | WP-04 | aggregate reconstruction tests | G2 |
| R-007 | Adapt existing hotspots without duplicating detection logic | WP-05 | compatibility contract test | G2 |
| R-008 | Identify event-level contributors to flagged dimensions | WP-06 | exact source-event attribution report | G3 |
| R-009 | Refine detection windows into evidence and pattern regions | WP-06, WP-07 | mixed-context boundary test | G3 |
| R-010 | Recognize the restricted broken-chord pattern | WP-07 | positive and close-negative fixture matrix | G3 |
| R-011 | Return supported, qualified diagnoses or explicit no-match | WP-08 | diagnosis/no-diagnosis golden payloads | G3 |
| R-012 | Expose confidence, criteria, contradictions, and caveats | WP-07, WP-08 | rule-branch tests | G3 |
| R-013 | Map diagnoses to provenance-labeled objectives and strategies | WP-10 | registry and contraindication tests | G3 |
| R-014 | Preserve generated-event provenance | WP-09, WP-11, WP-12 | provenance completeness validator | G2, G4 |
| R-015 | Generate a blocked-chord reduction | WP-11 | pitch-set, onset, duration invariants | G4 |
| R-016 | Generate complementary long-short and short-long variants | WP-12 | pair conservation and ordering tests | G4 |
| R-017 | Serialize the supported exercise subset to MusicXML | WP-13 | parse-after-write semantic comparison | G4 |
| R-018 | Reject unsupported transformations visibly | WP-09–WP-13 | stable negative diagnostic tests | G4 |
| R-019 | Run automatic and manually controlled end-to-end paths | WP-14 | v1 scenario and baseline equivalence | G5 |
| R-020 | Produce explanations only from allowed structured claims | WP-15 | unsupported-claim negative tests | G5 |
| R-021 | Separate software correctness from pedagogical evaluation | WP-16 | synthetic evaluation manifest/report | G5 |
| R-022 | Keep output deterministic and network-independent | WP-01–WP-15 | repeated-run comparisons | every gate |
| R-023 | Preserve literature provenance separately from formalized rules | WP-10, WP-17 | source-rule-strategy reference checks | G3, later |
| R-024 | Avoid learner-specific claims without learner evidence | WP-08, WP-10, WP-15 | wording and caveat tests | G3, G5 |

## V1 scenario trace

| Stage | Input | Output | Main contract | Owner |
|---|---|---|---|---|
| Parse | committed fixture | `ScoreIR` | existing piano-difficulty schema | existing system |
| Detect | score and window config | difficulty hotspot | existing Difficulty Dynamics profile | existing system |
| Detect (controlled twin) | exact region and optional hand | root `Passage` with manual origin, no profile | manual selection API | WP-02, WP-05 |
| Adapt | hotspot plus score | investigation request | `HotspotInvestigation` | WP-05 |
| Select | investigation region | exact passage | `PassageSelection` | WP-02 |
| Observe | passage views | feature evidence | `FeatureEvidence` | WP-03, WP-04 |
| Attribute | hotspot and evidence | attributed signals | `AttributedSignal` | WP-06 |
| Recognize | passage views and signals | pattern matches | `PatternMatch` | WP-07 |
| Diagnose | triggers, attribution, patterns | diagnoses | `PassageDiagnosis` | WP-08 |
| Plan | diagnosis and registry | exercise plans | `ExercisePlan` | WP-10 |
| Transform | plan and practice passage | generated passages | `TransformationResult` | WP-09, WP-11, WP-12 |
| Validate | generated passage | check report | `ExerciseValidation` | WP-09 |
| Export | validated passage | MusicXML and provenance JSON | v1 writer contract | WP-13 |
| Explain | diagnosis and plan | bounded explanation | `ExplanationBrief` | WP-15 |
| Evaluate | predictions and human annotations | research metrics | evaluation schema | WP-16 |

## Change rule

If an implementation cannot satisfy a row, the agent must not silently weaken
the test. It must propose one of:

- a contract revision with consequences;
- a narrower supported subset and explicit diagnostic;
- a new prerequisite work package; or
- deferral with an updated thesis claim boundary.
