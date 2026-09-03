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
- reuse neutral score IR, traversal, and diagnostics from the legacy
  compatibility layer where it helps
- compare our extracted values against released Yan feature tables or matrices
  when available as a sanity check for shape or coverage
- keep feature-search scaffolding in the Yan lane as a separate layer that
  selects among explicit extractor kwargs instead of mutating the default
  feature definitions
- keep all Yan work out of `src/` until the feature math is stable enough to
  promote

## Formula Policy

Many Yan feature names are mathematically under-specified in the paper. For
those features, the lane should treat the name as a feature family, not a single
frozen formula. The default stance is to preserve multiple candidate
implementations where the paper does not uniquely determine the math, then
switch among those candidates during evaluation and optimization.

That means:

- keep candidate formulas explicit and named instead of baking in one hidden
  convention
- allow several implementations to coexist for the same paper feature when the
  contract is ambiguous
- mark such features as `proxyable` or `blocked` until the best candidate is
  selected
- use downstream optimization against predictive performance to decide which
  candidate becomes the preferred extractor for a given experiment
- document the candidate set, the selection rule, and the evidence for each
  choice in the Yan lane docs rather than only in code

For the variability family specifically, the default workflow should keep a
shared menu of score-native candidates available across pitch variability,
duration variability, and related variation features. A small starting bank is
enough:

- adjacent normalized successive-difference variability
- coefficient of variation
- normalized range
- mean absolute step variability

Those candidates are all sheet-music friendly, easy to swap, and easy to score
against predictive performance later.

For the MXL-native rate family, keep the same mindset:

- `black_key_rate`, `polyphony_rate`, `staccato_rate`, and `dotted_note_rate`
  should each expose several explicit counting conventions
- prefer switching between written-note, logical-note, onset-based, and
  duration-weighted ratios rather than hiding one counting rule inside the
  extractor
- keep the default formula conservative, but preserve the alternatives for
  later optimization and comparison

For local movement proxies like `hand_displacement_rate`, prefer a
thresholded same-hand attack transition model with explicit noticeable and
difficult leap cutoffs, a long-rest filter, and a gap-weighted severity score.
That keeps the proxy closer to leap behavior without making it collapse into
the global `playing_speed` feature.

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

We should reuse the legacy compatibility work only where it is neutral:

- MusicXML normalization and score traversal
- staff segmentation and onset grouping
- note and measure diagnostics
- stable diff and report plumbing

We should not reuse parity assumptions as feature definitions, and we should
not use external Yan code or unlabeled outputs as the source of feature names.

## 5-Pass Plan

| Pass | Status | Goal | Exit criteria |
| --- | --- | --- | --- |
| 1. Inventory and taxonomy | Completed | Build the canonical paper-derived Yan feature list and classify each item as `implemented`, `proxyable`, or `blocked`. | Every paper feature has a tracked status and notes. |
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
  inventory in `tests/harness/yan2023/paper_inventory.py`, and the first-pass
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
- a machine-readable paper-facing 73-slot inventory in
  `tests/harness/yan2023/paper_inventory.py`
- a first-pass extractor in `tests/harness/yan2023/extractor.py`
- a feature-optimization scaffold in
  `tests/harness/yan2023/feature_optimization.py`

The current slot ledger is intentionally overcomplete. It expands to 78 working
slots, which is useful for implementation and paper-audit work but should not
yet be treated as a claimed exact recovery of the paper's final 73-column
matrix. Some slots are direct figure/table recoveries and some are systematic
scope expansions that may collapse later.

The lane now also carries a frozen paper-facing 73-slot inventory. It keeps the
overcomplete 78-slot implementation ledger intact, but collapses three scope
patterns to match the paper count:

- `hand_stretch`: current paper-facing inventory keeps one unsuffixed slot
  because Figure 6 shows `hand stretch` without `es` / `bs` / `ts`
- `playing_speed`: current paper-facing inventory keeps one unsuffixed slot
  because Figure 6 shows `playing speed` without `es` / `bs` / `ts`
- `pressing_velocity_entropy`: current paper-facing inventory keeps one global
  slot because Table 3 defines PVE on a whole-score probability distribution

This 73-slot map is the locked lane contract. It is not yet a verified
release-aligned matrix, but the scope and count are now frozen for the lane.

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

1. keep the locked 73-slot inventory synchronized if new paper evidence
   requires a revision
2. decide whether `dotted_note_rate`, `playing_speed`,
   `distinct_stroke_rate`, and `irregular_rhythm` should stay proxy features or
   get stricter formulas
3. create a reference-comparison runner once a small labeled matrix is available
4. add mismatch probes for the features that remain ambiguous after comparison
