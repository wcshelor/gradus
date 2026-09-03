# Pedagogy Knowledge Base Plan

## Purpose

The long-term knowledge base connects score situations, potential learning
challenges, practice objectives, and exercise strategies using traceable
pedagogical sources and expert review.

This is a separate research phase from building the representation and
transformation engine. V1 registry entries must remain labeled
`prototype_unvalidated` until supported by the process below.

## Three records that must remain distinct

```text
Source claim
    What an author or teacher actually says.

Formalized heuristic
    Our interpretation of when that guidance may apply to score evidence.

Executable strategy
    A transformation or routine the software can perform.
```

The second and third records are research interpretations. They must not be
presented as quotations or direct claims from the source.

## Source-claim record

Required fields:

- stable record ID;
- bibliography source ID;
- precise locator: page, section, chapter, or example;
- short paraphrase and, only when appropriate, a copyright-compliant excerpt;
- situation described by the source;
- intended learner level or context, if stated;
- stated practice procedure;
- intended outcome, if stated;
- cautions, preconditions, and dosage, if stated;
- tradition, author role, and publication type;
- note author and date;
- confidence in interpretation; and
- review status.

Only metadata actually supported by the source may be assigned. The canonical
bibliographic record stays under `literature/`.

## Formalized heuristic record

Required fields:

- stable heuristic ID and version;
- source-claim IDs;
- observable score criteria;
- optional pattern prerequisites;
- learner information required but unavailable from the score;
- supporting and contradictory criteria;
- intended diagnosis and objective IDs;
- uncertainty notes;
- formalizer and reviewer; and
- status: draft, reviewed, piloted, or rejected.

Heuristics should initially be readable rules. Learned ranking may later sit
behind the same output contract.

## Strategy record

Required fields are defined in `contracts.md` and additionally include:

- transformation fidelity to the described practice procedure;
- parameters fixed by the source versus introduced by implementation;
- reconnection step to the original music;
- known risks of overgeneralization; and
- expert-review outcomes.

## Curation workflow

1. Select a focused diagnosis or exercise family.
2. Search high-quality piano-pedagogy literature and existing thesis reading
   lists.
3. Add or confirm the bibliographic source in `literature/`.
4. Create source-claim records with exact locators.
5. Have a second reader check each paraphrase and scope.
6. Formalize candidate computable criteria separately.
7. Compare the criteria with representative positive and negative passages.
8. Map reviewed heuristics to objectives and executable strategies.
9. Ask teachers to evaluate relevance, contraindications, and wording.
10. Version accepted registry entries and preserve rejected alternatives.

## Quality hierarchy

Prefer, while recognizing that useful knowledge may occur across categories:

- peer-reviewed piano-pedagogy and motor-learning research;
- established pedagogical books with clear authorship and examples;
- conservatory or professional teaching resources;
- documented expert interviews or elicitation;
- historical methods interpreted in context;
- practitioner material used as exploratory evidence; and
- model-generated ideas only as unverified search prompts.

No source category automatically proves an exercise effective for all learners.

## Initial knowledge domains

After v1, grow one domain at a time:

- broken chords and arpeggios;
- leaps and landing preparation;
- repeated chords and notes;
- scales and passagework;
- chord voicing and melody projection;
- hand independence and rhythmic coordination;
- polyphonic voice work;
- ornaments;
- fingering-related practice, only with appropriate evidence; and
- reintegration, context, and practice sequencing.

## Evaluation questions

- Do teachers agree that the formalized criteria describe the cited situation?
- Does the detector retrieve passages that experts consider relevant?
- Are contraindications sufficient?
- Does the executable transformation preserve the pedagogical intention?
- Can teachers identify the source rationale from the structured record?
- Does literature grounding improve ratings over an ungrounded strategy
  baseline?

## Safety and restraint

- Do not infer pain, injury, anatomy, or medical advice from the score.
- Do not prescribe high repetition counts or forced tempos by default.
- Treat hand span, fingering, experience, and goals as learner-dependent.
- Preserve alternatives when pedagogical schools disagree.
- Make uncertainty and provenance visible in generated explanations.
