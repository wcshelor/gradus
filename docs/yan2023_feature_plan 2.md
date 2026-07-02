# Yan 2023 Feature Reconstruction Plan

Updated for the current repository state on 2026-07-01.

## Purpose

This lane tracks the feature-extraction side of Yan et al. (2023), not the
paper-faithful classifier stack. The paper is the source of truth for feature
definitions; the unlabeled archived snapshot is only a secondary shape check.

The working goal is to:

- reconstruct the published feature inventory from the paper
- implement score-derived versions of those features from repo-native MusicXML
  and score IR
- reuse neutral score IR, traversal, and diagnostics from the Sebastien work
  where it helps
- compare our extracted values against released Yan feature tables or matrices
  when available as a sanity check for shape or coverage
- keep all Yan work out of `src/` until the feature math is stable enough to
  promote

## What We Already Know

- The paper describes a 73-dimensional feature set.
- Features are extracted for the whole score and for staff-scoped views
  (`es`, `bs`, `ts` in the figure caption).
- The paper groups the features into existing symbolic features plus new
  semantic-explicit features.
- The published text names the following families:
  - pitch-content features: mean and deviation of pitch, pitch range, pitch
    entropy, hand displacement rate, hand stretch, deviation from middle C,
    black key rate
  - rhythmic-content features: mean and deviation of note duration, playing
    speed, polyphony rate, distinct stroke rate, irregular rhythm
  - other features: length, tempo, key signature
  - new features: pressing velocity entropy, pressing velocity variability,
    pitch variability, note duration variability, note density, melody
    complexity, chord number, variation of playing speed, staccato rate,
    dotted note rate
- Table 3 also describes the MC family as three dimensions:
  melodic complexity, melodic originality, and degree of melodiousness.
- The paper does not fully publish the feature math, so the exact definitions
  still need to be reconstructed.

## Reference Targets

- The paper evaluates two benchmark datasets, EN and AMBPT.
- The first reference comparisons should use any released feature matrices or
  tables for those datasets, not classifier accuracy alone.
- Feature ranking results from SVM-RFE are a useful sanity signal, but they are
  not the extractor target.
- The external Yan snapshot is unlabeled, so it cannot be used to align
  feature columns back to MusicXML without additional paper-derived mapping.

## Reuse Strategy

We should reuse the Sebastien-derived work only where it is neutral:

- MusicXML normalization and score traversal
- staff segmentation and onset grouping
- note and measure diagnostics
- stable diff and report plumbing

We should not reuse parity assumptions as feature definitions, and we should
not use external Yan code or unlabeled outputs as the source of feature names.

## 5-Pass Plan

| Pass | Status | Goal | Exit criteria |
| --- | --- | --- | --- |
| 1. Inventory and taxonomy | In progress | Build the canonical paper-derived Yan feature list and classify each item as `implemented`, `proxyable`, or `blocked`. | Every paper feature has a tracked status and notes. |
| 2. Recoverable extraction | In progress | Implement the feature extractors we can compute from repo-native score data. | A stable feature vector schema runs over a sample corpus. |
| 3. Reference comparison | Not started | Compare our vectors with any released Yan feature values or matrices. | Each mismatch is reproducible and labeled by failure class. |
| 4. Ambiguity resolution | Not started | Write targeted probes for preprocessing, scope, or formula ambiguities. | Every remaining mismatch is either explained or explicitly blocked. |
| 5. Promotion decision | Not started | Decide what stays experimental and what, if anything, deserves promotion inward. | The lane has a documented promotion/no-promotion decision and a frozen contract. |

## Update Protocol

- Update this doc whenever a pass changes status or a feature definition
  changes.
- Keep the tracked inventory in sync with
  `tests/harness/yan2023/boundary.py`.
- Use [docs/yan2023_feature_inventory.md](yan2023_feature_inventory.md) as the
  running feature ledger for the paper inventory.
- Keep the machine-readable working slot ledger in
  `tests/harness/yan2023/slot_inventory.py`, the paper-facing 73-slot
  hypothesis in `tests/harness/yan2023/paper_inventory.py`, and the first-pass
  extractor in `tests/harness/yan2023/extractor.py`.
- Treat the paper as the primary source; treat the unlabeled archived snapshot
  as a secondary reference only.
- Put generated evidence under `tests/artifacts/yan2023/`.
- Record unresolved questions and mismatch hypotheses here instead of burying
  them in code comments.
- If a feature needs an approximation, mark it `proxyable` rather than
  describing it as exact.

## Current Working Inventory

The harness now has two concrete artifacts:

- a machine-readable working slot ledger in
  `tests/harness/yan2023/slot_inventory.py`
- a machine-readable paper-facing 73-slot hypothesis in
  `tests/harness/yan2023/paper_inventory.py`
- a first-pass extractor in `tests/harness/yan2023/extractor.py`

The current slot ledger is intentionally overcomplete. It expands to 78 working
slots, which is useful for implementation and paper-audit work but should not
yet be treated as a claimed exact recovery of the paper's final 73-column
matrix. Some slots are direct figure/table recoveries and some are systematic
scope expansions that may collapse later.

The lane now also carries a paper-facing 73-slot hypothesis. It keeps the
overcomplete 78-slot implementation ledger intact, but collapses three scope
patterns to match the paper count:

- `hand_stretch`: current paper-facing hypothesis keeps one unsuffixed slot
  because Figure 6 shows `hand stretch` without `es` / `bs` / `ts`
- `playing_speed`: current paper-facing hypothesis keeps one unsuffixed slot
  because Figure 6 shows `playing speed` without `es` / `bs` / `ts`
- `pressing_velocity_entropy`: current paper-facing hypothesis keeps one global
  slot because Table 3 defines PVE on a whole-score probability distribution

This 73-slot map is still a hypothesis, not a verified release-aligned matrix.

| Feature | Status | Notes |
| --- | --- | --- |
| `note_density` | implemented | Direct score-density primitive. |
| `chord_number` | implemented | Count of chordal events. |
| `pitch_mean` | implemented | Basic pitch aggregate. |
| `pitch_std` | implemented | Basic pitch dispersion. |
| `pitch_range` | implemented | Basic pitch span. |
| `duration_mean` | implemented | Basic duration aggregate. |
| `duration_std` | implemented | Basic duration dispersion. |
| `tempo` | implemented | Score tempo metadata. |
| `key_signature` | implemented | Score key metadata. |
| `black_key_rate` | implemented | Pitch-class derived. |
| `length` | implemented | Reconstructed as total quarter-note score length. |
| `pitch_entropy` | implemented | Reconstructed as Shannon entropy over exact MIDI pitches. |
| `deviation_of_pitch_from_C4` | implemented | Reconstructed as mean absolute semitone distance from MIDI 60. |
| `polyphony_rate` | implemented | Reconstructed as multi-note same-onset ratio. |
| `triad` | implemented | First-pass chord-type count from same-onset pitch classes. |
| `seventh_chord` | implemented | First-pass chord-type count from same-onset pitch classes. |
| `ninth_chord` | implemented | First-pass chord-type count from same-onset pitch classes. |
| `pitch_variability` | implemented | Table 3 adjacent-note normalized variability formula is now wired. |
| `note_duration_variability` | implemented | Table 3 adjacent-note normalized variability formula is now wired. |
| `playing_speed_variation` | implemented | Table 3 tempo-variation ratio is now wired. |
| `dotted_note_rate` | proxyable | Needs exact numerator/denominator convention. |
| `staccato_rate` | implemented | Direct articulation-rate reconstruction from written-note articulations. |
| `playing_speed` | proxyable | Current proxy uses attacks per quarter. |
| `hand_displacement_rate` | proxyable | Likely recoverable from score geometry. |
| `hand_stretch` | proxyable | Requires a precise hand model. |
| `distinct_stroke_rate` | proxyable | Stroke identity rule is not fully published. |
| `irregular_rhythm` | proxyable | Exact irregularity formula is not fully published. |
| `pressing_velocity_entropy` | blocked | Likely needs performance/MIDI data. |
| `pressing_velocity_variability` | blocked | Likely needs performance/MIDI data. |
| `melodic_complexity` | blocked | MC family dimension; formula not yet reconstructed. |
| `melodic_originality` | blocked | MC family dimension; formula not yet reconstructed. |
| `degree_of_melodiousness` | blocked | MC family dimension; formula not yet reconstructed. |

## Next Updates To Make

1. validate or refute the current 73-slot hypothesis, especially the scope
   collapse for `hand_stretch`, `playing_speed`, and
   `pressing_velocity_entropy`
2. decide whether `dotted_note_rate`, `playing_speed`,
   `distinct_stroke_rate`, and `irregular_rhythm` should stay proxy features or
   get stricter formulas
3. create a reference-comparison runner once a small labeled matrix is available
4. add mismatch probes for the features that remain ambiguous after comparison
