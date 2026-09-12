# Corpus Evaluation Checklist — S8.6

Status: draft 2026-09-11. For teacher review of passage-level pedagogical corpus records and their explanations. Synthetic-only phase; no real participant data.

## How to use

Review one `PedagogicalCorpusRecord` + its `ExplanationBrief` + the underlying `SemanticBundle` and score excerpt together. Answer each question on a 3-point scale: `yes` / `partial` / `no`, with a short note. Record reviewer ID, date, and record IDs.

## Questions

### Plausibility

- [ ] **P1** Does the top semantic hypothesis match what a musician hears?
- [ ] **P2** Are plausible alternatives also present (no false certainty)?

### Usefulness

- [ ] **U1** Does the explanation suggest an actionable next step fitting the passage?
- [ ] **U2** Is the exercise candidate appropriate for the hypothesized difficulty?

### Traceability

- [ ] **T1** Can every explanation sentence be traced to a supporting claim in the brief?
- [ ] **T2** Do source IDs resolve and point to the correct passage?

### Overclaiming

- [ ] **O1** Does the explanation avoid unsupported melody/harmony/learner/difficulty claims?
- [ ] **O2** Is uncertainty wording present and appropriate (likely/may/possible)?

### Exercise Fit

- [ ] **E1** Does the exercise preserve pitch/voice relationships where required?
- [ ] **E2** Is the exercise within the supported subset?

## Review record fields

- `record_id`, `brief_id`, `bundle_id`, `reviewer_id` (synthetic/teacher code), `date`, `answers` (map question -> yes/partial/no + note), `overall` (plausible/useful/traceable).

## Limitations (from S8.1/S7.7)

- Tiny synthetic data only; no quality claim.
- Heuristic detectors only; learned models are plumbing (synthetic.tiny.v1).
- Explanations are templates; pedagogical effectiveness is unproven.

## Audit note

This checklist is for human review; it does not enroll participants or collect personal data. Synthetic records are used for tooling tests only.
