# Thesis Alignment

## Working system proposition

The difficulty analyzer identifies symbolic score regions likely to warrant
attention. A separate passage engine traces the window signals to local score
events, recognizes musical patterns, and produces structured hypotheses about
potential learning challenges. Those hypotheses ground inspectable,
source-derived practice exercises and explanations.

## Candidate research questions

The thesis does not need to answer all of these equally. They provide a ladder
from technical foundation to pedagogical evaluation.

### Representation

- Can one canonical symbolic representation support difficulty measurement,
  passage attribution, semantic pattern recognition, and score transformation
  through explicit derived views?
- Which score information must be preserved for traceable practice-exercise
  generation?

### Attribution

- Can high difficulty values calculated over overlapping windows be localized
  to meaningful event groups within those windows?
- Which attribution methods are most understandable and stable for direct
  symbolic features?

### Semantic diagnosis

- Can transparent rules combine feature evidence and musical patterns into
  diagnoses that piano teachers judge relevant and appropriately qualified?
- How often should the system abstain because the score evidence is ambiguous?

### Exercise generation

- Can deterministic transformations produce practice material that preserves
  source provenance and accurately instantiates a stated practice objective?
- Do teachers consider the generated reductions and rhythmic variants playable,
  purposeful, and connected to the source passage?

### Explanation and AI contribution

- Does a structured diagnosis improve explanation quality compared with an LLM
  given raw score material or an ungrounded prompt?
- Where does an LLM add value beyond deterministic analysis and templates, and
  where does it introduce unsupported claims?

## Claim ladder

Evidence should be accumulated in this order:

1. **Representational correctness**: selected and generated events match the
   documented score semantics.
2. **Algorithmic correctness**: observations, patterns, and transformations
   satisfy their formal rules.
3. **Expert agreement**: teachers consider patterns, diagnoses, and exercises
   musically and pedagogically plausible.
4. **Usability**: intended users understand and can act on the outputs.
5. **Learning benefit**: use of the system improves an appropriate outcome in a
   suitable study.

Passing a lower level does not establish a higher one.

## Safe v1 claims

If all v1 gates pass, the project may claim that it:

- connects windowed difficulty hotspots to event-level symbolic evidence;
- recognizes a deliberately restricted broken-chord pattern under documented
  conditions;
- produces transparent score-derived diagnostic hypotheses;
- generates deterministic blocked and rhythmic passage transformations;
- preserves machine-readable source provenance; and
- exports notation that passes the supported parse-after-write checks.

Without further study, it should not claim that it:

- finds the objectively hardest passage for every learner;
- diagnoses an individual's technical limitation;
- recommends the best exercise for a particular person;
- generates expert-equivalent teaching advice; or
- improves learning outcomes.

## Baselines

Useful comparisons include:

- manual passage selection versus automatic hotspot selection;
- raw feature ranking versus event attribution;
- feature-only diagnosis versus feature-plus-pattern diagnosis;
- generic slow/hands-separate advice versus diagnosis-linked transformations;
- deterministic template explanation versus grounded LLM explanation; and
- grounded LLM explanation versus raw-score LLM prompting.

These baselines help identify which component contributes value.

## Evidence ledger

At each review gate, record:

- what has been implemented;
- which contracts have tests;
- which musical cases are supported;
- which claims have only synthetic evidence;
- which claims have expert evidence;
- known failure cases;
- relevant method and schema versions; and
- decisions that narrowed or expanded thesis scope.

The gate review reports can later supply a chronological methods and limitations
record for the thesis.

## Scope-control questions

Before accepting a new feature, ask:

- Is it required to complete or evaluate the v1 chain?
- Which layer owns it?
- What baseline does it improve?
- What new test or research evidence would demonstrate value?
- Does it require learner information we do not have?
- Does it enlarge MusicXML support or pedagogical scope disproportionately?
- Could it remain a documented future extension?

## Possible thesis-sized outcomes

A successful thesis could emphasize one of several contributions:

- a traceable architecture from hotspot to practice material;
- a method for event-level explanation of windowed symbolic difficulty;
- a small, literature-grounded diagnostic and exercise rule base;
- a controlled score-transformation system for practice exercises; or
- a comparative study of grounded and ungrounded explanation/generation.

The architecture keeps these options open while v1 evidence reveals which is
strongest.
