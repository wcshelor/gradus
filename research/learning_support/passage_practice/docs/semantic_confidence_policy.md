# Semantic Confidence Policy (S-Q003, initial)

Status: initial policy, recorded by S1.4 (decision D-016). Bands below are
presentation rules, not research claims; revise after fixture, teacher, or
learner-review evidence. Per the task limit, this policy sets **no**
per-detector numeric thresholds — those stay local to each detector version
(S3 onward).

Related: plan §Confidence policy; Q-006 (v1 deterministic uncalibrated
score); S1.2 contract (`SemanticHypothesis.confidence`,
`confidence_method`); S1.3 bundle preservation rule; S1.5 helpers (enforce
this policy); S1.6 empty payload (nothing-found case).

## 1. What confidence means

`confidence` is a deterministic, uncalibrated **ranking score** in
$[0, 1]$ (enforced by the S1.2 contract). It is not:

- a probability or calibrated likelihood;
- a difficulty grade;
- a claim about any individual learner.

It orders hypotheses *within one bundle* so consumers can prioritize
detectors, questions, and practice candidates. Cross-bundle and
cross-passage numeric comparisons are meaningless until a calibrated
status exists (none does in v1).

## 2. Bands (exact boundaries)

Lower-bound inclusive; upper-bound exclusive except high, which includes
1.0. S1.5 derives bands from these boundaries with boundary-value tests.

| Band | Range | Meaning |
|---|---|---|
| high | $0.75 \le c \le 1.00$ | Strong converging evidence, no material contradiction |
| medium | $0.50 \le c < 0.75$ | Supporting evidence with a caveat (partial coverage, weak cue, or minor contradiction) |
| low | $0.25 \le c < 0.50$ | Weak or single-cue evidence; a possibility, not a finding |
| unsupported | $c < 0.25$ | Below the presentation floor; never presented as a finding |

## 3. Calibration status labels (`confidence_method` vocabulary)

Allowed values for `SemanticHypothesis.confidence_method`:

| Status | Meaning | Usable now? |
|---|---|---|
| `heuristic` | Deterministic rule-based score with visible components (satisfied vs contradictory criteria) | Yes — the only v1 status |
| `calibrated` | Score fitted against labeled data with a recorded calibration procedure | Reserved — requires labeled data plus lead-approved method (see Q-006) |
| `learned` | Model-backed score behind the same contract | Reserved — S7 lane; requires training-data identity, deterministic inference, and a heuristic-baseline comparison |

Producers emitting any other status, or `calibrated`/`learned` without the
stated prerequisites, fail explicit validation. Enforcement lands in the
S1.5 helpers, not in this document.

## 4. Contradictions and missing evidence

- Contradictory evidence **must not increase** confidence and may reduce it.
  The exact penalty is detector-local (versioned with the detector); S1.5
  provides a shared penalty helper where detectors need one.
- Unavailable evidence is recorded in `missing_evidence` plus a diagnostic.
  It is never coded as zero, never treated as negative evidence, and never
  treated as contradiction. A hypothesis whose key evidence is unavailable
  belongs in low or unsupported, with the gap named — not silently dropped.

## 5. Abstention behavior

Abstention is split across two levels so uncertainty stays inspectable:

- **Detector/bundle level — never suppress.** Detectors emit what they
  computed, including low and unsupported hypotheses with their criteria
  and `missing_evidence`. Bundles preserve all of them, including
  contradictions (S1.3). Silent suppression would hide uncertainty from
  reviewers and break regression comparisons.
- **Presentation/selection level — filter by band:**
  - unsupported: excluded from every learner-facing output;
  - low: presented only as "possible" **with** a learner question (S5 path)
    that could confirm or reject it, otherwise abstained with a diagnostic;
  - medium: presented with its caveat attached, never smoothed into certainty;
  - high: presented with an evidence summary.
- **Nothing-found case:** when no hypothesis reaches 0.25, the producer
  returns an empty bundle with a `no_supported_hypothesis` diagnostic
  (S1.6) — never a low-confidence filler hypothesis manufactured to have
  something to show.

## 6. Presentation wording

| Band | Stance | Required accompaniment |
|---|---|---|
| high | "likely X" | evidence summary (supporting criteria + covered events) |
| medium | "may be X" | caveat (what is partial, weak, or contradictory) |
| low | "possible X" | learner question, or abstention with diagnostic |
| unsupported | — (not presented) | stays inspectable in the bundle payload only |

Wording must never introduce measurements, source claims, or
personalization absent from the structured hypothesis. Rich prose remains
presentation output governed by the explanation brief, not by this policy.

## 7. Revision triggers

Revise this policy (new dated decision, S1 minors as needed) when any of:
fixture suites show systematic band misalignment; teacher review rejects
the wording stances; learner-feedback data (S5) justifies new abstention
paths; or a calibration procedure (Q-006) is approved, which unlocks the
`calibrated` status and may re-anchor the boundaries.
