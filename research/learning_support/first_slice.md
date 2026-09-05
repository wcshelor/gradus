# LS-01 — First learning-support slice

Status: specification only (planned, not implemented). This document defines
the bounded first slice required by LS-01 of the
[three-area plan](../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md).
No runtime code, interface, AI model, or data collection is introduced here.
Candidate aids are named so their scope can be reviewed; none is implemented
by this document.

Authority: [project direction](../../docs/project_direction.md) (three
complementary areas, learner control, synthetic data first). This slice reuses
the existing restricted broken-chord program defined in
[prototype_v1](passage_practice/docs/prototype_v1.md), its
[contracts](passage_practice/docs/contracts.md), and its
[architecture](passage_practice/docs/architecture.md) as the semantic and
pedagogical subset. It does not rebuild that capability and does not change
its hotspot-to-exercise route; that route becomes one entry point among
several (see S1–S5).

## 1. Supported musical subset

One-hand broken-chord groups exactly as specified in `prototype_v1.md`:

- `score-partwise` MusicXML/MXL accepted by the existing raw loader; one
  selected piano-like part; one or two piano staves.
- Target-hand material in a single encoded voice: pitched, non-grace attacks
  with equal or simply related subdivisions within each candidate group.
- At least two adjacent candidate groups, each with at least three pitched
  attacks, a documentable metrical unit (initially one beat or a configured
  simple multiple), mostly non-simultaneous attacks, and at least three
  distinct pitches.
- No tuplet crossing a selected transformation boundary; no repeat-expansion
  requirement.

Why this subset: it is the narrowest already-documented pattern with
contracts for evidence, diagnosis, transformation, and explanation; reusing it
avoids a second implementation of an existing passage-practice capability.
Difficulty analysis (attack density, pitch-transition, span, timing-mismatch,
accidental factors) remains one optional source of candidate regions, never a
gate: every scenario below must work from a user-selected region alone.

## 2. Supported user needs

Exactly three needs are in scope for the slice. All other needs receive an
honest limitation or focused clarification (see section 6).

- **N1 — Semantic (Area A):** “What is happening in this passage, and where
  else does it occur?” Answer from score facts and the selected pattern only.
- **N2 — Pedagogical (Area B):** “What could I try to make this passage
  easier to learn?” One bounded aid: a blocked-chord reduction of the
  recognized groups and/or a long-short / short-long rhythmic variant, each
  with objective, rationale, scope, and caveats. A text-only practice
  approach is acceptable; notation export is not mandatory for a text-only
  aid.
- **N3 — Interaction (Area C):** “Keep this note / let me return to it
  later / ignore my history for this question.” Journal-only save, history
  inspection and correction, and per-request history exclusion.

## 3. Entry points exercised

The slice exercises five of the plan’s starting points: learner-selected
passage, whole piece with no history, self-reported difficulty, journal-only
entry, and return after a gap (including “ignore my history for this”).
Analyzer-suggested sections may appear as candidates with supporting
measurements but are not required by any scenario.

## 4. Scenarios

Each scenario names the entry, the expected behavior, and what must not
happen. S1–S5 are positive; S6–S7 are negative (abstention) cases.

### S1 — User-selected passage, no history (N1, N2)

Entry: exact region plus an optional question; no journal, no profile, no
difficulty computation.
Expected: locate the region to exact source events; report score observations
for the subset (grouping, pitch sets, onset regularity) with source-event
references and method; offer the N2 aid only if requested and supported.
Must not: require a hotspot, compute a difficulty profile, or redirect the
learner to a higher-ranked section.

### S2 — Whole piece, no history (N1)

Entry: piece-level question (“where does this figure occur?”), no history.
Expected: answer from score evidence, or state that the question is outside
the broken-chord subset with a focused clarification.
Must not: require a learner profile, difficulty grade, or journal.

### S3 — Reported difficulty disagrees with computed ranking (N2, N3)

Entry: “These measures are hard for me,” where the analyzer ranks the region
low (or was never run).
Expected: preserve the learner’s words verbatim with timestamp and scope;
optionally clarify which aspect feels hard (hand, voice, transition);
proceed with S1 behavior on the selected region.
Must not: translate the report into a measured deficit, claim a cause without
evidence, overrule the report with the computed ranking, or send the learner
to a higher-ranked hotspot.

### S4 — Journal-only entry (N3)

Entry: free-text note (optionally with piece/region scope), explicitly saved.
Expected: store the note with stable ID, original text, author/source,
recorded time, scope, and permission; confirm what was saved and that no
analysis or aid was generated.
Must not: trigger analysis, exercise generation, or trait/habit inference.

### S5 — Return, revise, withdraw, or ignore history (N1, N2, N3)

Entry: returning learner with a synthetic history containing an earlier
difficulty report; variants: (a) report changed (“the join feels better, the
position change still slips”); (b) earlier note corrected; (c) earlier entry
deleted; (d) “ignore my history for this.”
Expected: use only the latest permitted context with timestamps; keep
superseded reports dated rather than authoritative; honor exclusion and
deletion (deleted entries influence nothing further); run the same request
with history disabled on demand.
Must not: infer progress or inactivity from elapsed time or missing entries;
treat an old report as a standing diagnosis; require deleting history to
disable its use for one request.

### S6 — Unsupported pattern (negative; N1, N2)

Entry: user-selected scalar run, repeated-note figure, or already-blocked
chords, with or without a difficulty report.
Expected: abstain from any broken-chord observation or diagnosis; name the
failing criterion (e.g., no stable harmonic grouping; simultaneous rather
than sequential attacks); state the subset boundary.
Must not: produce a plausible but ungrounded diagnosis or a practice variant.

### S7 — Unresolved region or edition mismatch (negative; all needs)

Entry: region that cannot be resolved to exact source events (ambiguous
measure reference, missing edition identity) or a journal note scoped to a
different score version.
Expected: explicit unresolved outcome with what is missing and how to clarify;
never attach an old note to a different edition silently.
Must not: fabricate evidence, guess the intended measures, or proceed as if
resolved.

## 5. Useful outputs within the slice

- Assistance responses reference score evidence and self-reports separately,
  each with source IDs where applicable. An aid records the requested need,
  objective, evidence used (with entry IDs for any journal context that
  influenced it), pedagogical rationale/provenance, applicability, caveats,
  and limitations. Pedagogical effectiveness remains unproven.
- Journal actions confirm save scope (session-only vs. explicitly saved),
  permission, stable ID, and timestamp; corrections and deletions propagate
  visibly (dependent summaries, when introduced in LS-04, must reference
  source-entry IDs and be invalidated on change).
- Score facts, learner self-reports, and system hypotheses are labeled as
  such in every output. A self-report never becomes a verified fact about
  playing ability; a system suggestion never becomes an observed result.
- Full request/journal/context contracts are deferred to LS-03; this slice
  constrains only what the contracts must express (all scenarios above,
  without a mandatory profile, rating, hotspot, model call, or performance
  recording).

## 6. Abstention and clarification policy

Abstain (with the subset boundary stated) when: the material is outside the
section-1 subset; the target hand or voice cannot be determined with
documented confidence; required context (edition, region) is unresolved; or
contradictory evidence dominates. Clarify (one focused question, original text
retained) when: the learner’s concern is ambiguous between hand/voice/
transition; the region is ambiguous; or the request mixes needs (e.g., save a
note and answer a question) without stating which response is wanted. Never
diagnose the learner, never invent score evidence, and never present an
arbitrary cutoff as validated pedagogy.

## 7. Explicit exclusions

Out of this slice (and out of phase unless the plan says otherwise): live
MIDI/audio assessment or feedback; microphone performance analysis;
automatic performance or practice tracking; mandatory onboarding, profiles,
ratings, streaks, or adherence scores; automatic trait, habit, or
psychological/medical inference; prescribed courses or fixed practice
sequences; automatic fingering or biomechanical advice; unconstrained exercise
generation; general learner profiling; production account infrastructure;
deployment into the company app; collection of real learner data; sending data
to external models; and any claim of measured learning benefit. Synthetic
histories only in committed tests.

## 8. Success rubric (reviewable)

Each scenario passes review when an independent reviewer, using only this
document and synthetic fixtures, can confirm:

- S1: valid low-ranked/user-selected passage yields observations without any
  difficulty profile; analyzer route preserved but not required.
- S2: whole-piece request answered from score evidence or explicitly declined
  as outside the subset.
- S3: report preserved verbatim with time/scope; ranking neither overrules
  the report nor redirects the learner.
- S4: note saved with ID/text/time/scope/permission and no analysis
  generated.
- S5: all four variants (change, correct, delete, ignore) respect the latest
  permitted context; no progress/inactivity claim from gaps; same request
  runs without history.
- S6: no broken-chord claim; failing criterion named.
- S7: unresolved outcome; no silent cross-edition attach; no fabricated
  evidence.
- Global: score facts, self-reports, and hypotheses visibly separated;
  timestamps and scope on every report; entry IDs recorded for influencing
  context; deterministic behavior without network/model access; no
  exclusions from section 7 present.

Review method: document inspection plus a synthetic scenario walkthrough.
Automated scenario tests arrive with LS-04–LS-09; human evaluation of
usefulness is LS-10 with owner/reviewer approval. Synthetic success here
must not be reported as measured learning benefit.

## 9. Deferred work

Semantic broadening (further patterns), additional aids, context-interaction
refinements, and any company integration are LS-06–LS-11 decisions with the
owner, based on evidence from this slice. Difficulty-component hardening
follows the subordinate difficulty checklist and gates nothing in S1–S5
beyond the source/region contracts the slice actually consumes.

Next eligible task: LS-02 (reconcile existing passage plans with independent
entry points).
