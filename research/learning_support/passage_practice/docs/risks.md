# Risk Register

Review this register at every management gate. Add a risk when implementation
reveals a recurring failure mode rather than hiding it in local comments.

| ID | Risk | Early warning | Mitigation | Owner/gate |
|---|---|---|---|---|
| K-001 | `ScoreIR` lacks information required for safe transformation | repeated source reparsing or ad hoc XML access | document required additions; keep them generic and additive; test provenance | WP-01/G1 |
| K-002 | Passage windows are mistaken for exact difficult material | whole measures appear in beat results; irrelevant events dominate | exact selection plus evidence/pattern/practice region refinement | WP-02, WP-06/G3 |
| K-003 | Summary values cannot be localized | feature returns only one float | preserve observation traces and aggregation rules | WP-04/G2 |
| K-004 | Attribution language implies causality not established by calculation | prose says an event “caused difficulty” | say “contributed to this score signal”; expose method and limitations | WP-06/G3 |
| K-005 | Broken-chord detector labels scales or ornaments | close-negative fixtures match | precision-first restricted criteria and abstention | WP-07/G3 |
| K-006 | Hand, voice, staff, and musical role become conflated | APIs use one field interchangeably | separate types/annotations and ambiguous cases | all gates |
| K-007 | Diagnosis claims learner-specific difficulty | output uses “you cannot” or definitive language | structured caveats and wording tests | WP-08, WP-15/G5 |
| K-008 | Pedagogy registry launders informal ideas into sourced facts | strategy has citation but no exact claim mapping | separate source claims, heuristics, and executable strategies | WP-10, WP-17 |
| K-009 | Transformations create valid objects but musically invalid timing | overfull voices or drifting endpoints | exact fractions and invariant validators | WP-09–WP-13/G4 |
| K-010 | Writer scope expands toward full MusicXML | repeated support for layout-only elements | freeze v1 supported subset; emit omission diagnostics | WP-13/G4 |
| K-011 | Golden snapshots conceal semantic regressions | large unreadable diffs are routinely accepted | small goldens plus targeted musical assertions | every gate |
| K-012 | Generated runs overwhelm Git history | timestamped artifact trees appear in staging | ignore ad hoc runs; commit only compact named evidence | WP-00 and G5 |
| K-013 | Fixture scores cannot legally be redistributed | repertoire files lack license/provenance | prefer synthetic fixtures; record source and license | WP-00/every gate |
| K-014 | Multiple agents implement conflicting contracts | duplicate model classes or adapters appear | single package ownership and gate integration | lead |
| K-015 | Optional LLM becomes a hidden runtime dependency | deterministic tests need keys/network | template baseline and strict `ExplanationBrief` adapter | WP-15, WP-18 |
| K-016 | Thresholds are overfit to one attractive example | constants change until one piece looks right | synthetic matrix, held-out examples, version thresholds | WP-07/G3 |
| K-017 | Confidence numbers appear calibrated when they are not | users interpret 0.8 as 80% correctness | label v1 scores uncalibrated; show criterion composition | WP-07, WP-08 |
| K-018 | Submodule or environment changes make results unreproducible | tests pass only in one nested checkout | pin commits, document init, avoid unreviewed submodule edits | WP-00/G0 |
| K-019 | Pipeline orchestration duplicates stage logic | fixes must be made in two places | thin pipeline calling tested component APIs | WP-14/G5 |
| K-020 | “No diagnosis” is treated as failure and encourages overprediction | every hotspot receives a label | explicit no-match contract and negative end-to-end case | WP-08, WP-14 |

## Severity guidance

- **Critical:** threatens research integrity, data/license safety, or corrupts
  score output. Stop dependent work.
- **High:** invalidates a cross-layer contract or key thesis claim. Resolve
  before the next gate.
- **Medium:** limits supported cases but can be made explicit. Record and test.
- **Low:** presentation or ergonomics issue with no semantic impact. Schedule
  normally.

## Risk review entry

```text
### YYYY-MM-DD — Gate/package
New risks:
Changed likelihood or impact:
Triggered mitigations:
Accepted limitations:
Owner and review date:
```
