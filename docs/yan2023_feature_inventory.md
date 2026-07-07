# Yan 2023 Feature Inventory

Updated for the current repository state on 2026-07-01.

This is the running ledger for the Yan reconstruction lane. It records the
paper feature families, the features we can name from the paper text, and the
implementation status we maintain in the harness. The unlabeled archived
snapshot is a shape check, not the source of truth for names.

## Sources

- Paper: Hanhan Yan et al. (2023), "Joint-optimized feature selection and
  classifier hyperparameters by salp swarm algorithm in piano score difficulty
  measurement problem"
- Archived snapshot: `external/yan-features/`
- Lane boundary: `tests/harness/yan2023/boundary.py`

## What is confirmed

- The paper uses a 73-dimensional feature set.
- Features are extracted for the whole score and for staff-scoped views.
- The paper names the following feature families:
  - pitch-content features
  - rhythmic-content features
  - other features
  - pressing velocity entropy
  - pressing velocity variability
  - pitch variability
  - note duration variability
  - note density
  - melody complexity
  - chord number
  - variation of playing speed
  - staccato rate
  - dotted note rate
- The paper's MC family is described as three dimensions:
  melodic complexity, melodic originality, and degree of melodiousness.

## What is not yet recoverable from the local snapshot

The `.mat` name blobs in `external/yan-features/` do not expose the original
feature-name vectors in a readable way here, so the exact released slot names
for all 73 dimensions still need to be reconstructed from the paper table or a
better export. The snapshot is only useful as a count/shape check until that
mapping is recovered from the paper.

Until that happens, this document tracks:

- the features explicitly named in the paper text
- the current harness status for repo-native reconstruction
- the remaining unresolved 73-slot inventory as a count, not as guessed names
- the paper-visible figure labels when they are recovered directly from the
  PDF, rather than inferred from the unlabeled snapshot
- the machine-readable working slot ledger in
  `tests/harness/yan2023/slot_inventory.py`
- the machine-readable paper-facing 73-slot inventory in
  `tests/harness/yan2023/paper_inventory.py`
- the strict implemented-slot audit metadata in
  `tests/harness/yan2023/implementation_audit.py`

## Status legend

- `implemented`: already present in the Yan harness or a direct repo-native
  primitive
- `proxyable`: likely reconstructable from MusicXML / score geometry, but the
  exact paper formula is still ambiguous
- `blocked`: likely needs performance/MIDI data or an unrecovered formula

## Formula Variants

For ambiguous features, a single ledger row may correspond to several candidate
math definitions. The lane should preserve those candidates as switchable
options, not collapse them into one early guess.

Guidelines:

- treat the paper feature name as the contract, and the math as an experiment
  family when the paper does not fully specify it
- keep candidate implementations explicit so they can be toggled during
  extraction and evaluation
- prefer adding a new candidate over overwriting the existing one when a
  different plausible formula appears
- record why a candidate exists, what it measures, and what would disqualify it
- let downstream prediction results decide which candidate is best for a given
  experimental run

### Shared Variability Bank

The variability family should reuse one shared candidate bank across any
variability-style Yan feature we can express on MusicXML. The first-pass bank
should stay small and score-native:

- adjacent normalized successive-difference variability
- coefficient of variation
- normalized range
- mean absolute step variability

That shared bank is especially relevant for `pitch_variability`,
`note_duration_variability`, and `playing_speed_variation`, but the same menu
can be reused for any future score-derived variability proxy.

### Shared Rate Bank

The MXL-native rate family should also keep multiple explicit counting
conventions available. The current first-pass bank is intentionally small and
score-native:

- written-note ratio
- logical-note ratio
- onset ratio
- duration-weighted ratio

That bank is especially relevant for `black_key_rate`, `polyphony_rate`,
`staccato_rate`, and `dotted_note_rate`.

## Named feature ledger

| Feature | Family | Current status | Notes |
| --- | --- | --- | --- |
| `note_density` | new | implemented | Direct score-density primitive. |
| `chord_number` | new | implemented | Count of chordal events. |
| `triad` | new | implemented | First-pass chord-type count from same-onset pitch classes. |
| `seventh_chord` | new | implemented | First-pass chord-type count from same-onset pitch classes. |
| `ninth_chord` | new | implemented | First-pass chord-type count from same-onset pitch classes. |
| `length` | other | implemented | Reconstructed as total quarter-note score length. |
| `pitch_mean` | legacy | implemented | Basic pitch aggregate. |
| `pitch_std` | legacy | implemented | Basic pitch dispersion. |
| `pitch_range` | legacy | implemented | Basic pitch span. |
| `pitch_entropy` | legacy | implemented | Reconstructed as Shannon entropy over exact MIDI pitches. |
| `deviation_of_pitch_from_C4` | legacy | implemented | Reconstructed as mean absolute semitone distance from MIDI 60. |
| `duration_mean` | legacy | implemented | Basic duration aggregate. |
| `duration_std` | legacy | implemented | Basic duration dispersion. |
| `tempo` | other | implemented | Score tempo metadata. |
| `key_signature` | other | implemented | Score key metadata. |
| `black_key_rate` | legacy | implemented | Wired to a shared score-native rate bank; the default is written-note ratio. |
| `playing_speed` | legacy | proxyable | Current proxy uses attack rate (attacks per quarter, not note count). |
| `polyphony_rate` | legacy | implemented | Wired to a shared score-native rate bank; the default is polyphonic-onset ratio. |
| `distinct_stroke_rate` | legacy | proxyable | Stroke identity rule is not fully published. |
| `irregular_rhythm` | legacy | proxyable | Exact irregularity formula is not fully published. |
| `pitch_variability` | new | implemented | Wired to a shared score-sequence variability bank; the default is adjacent-normalized variation. |
| `note_duration_variability` | new | implemented | Wired to a shared score-sequence variability bank; the default is adjacent-normalized variation. |
| `playing_speed_variation` | new | implemented | Current contract is a tempo-variation ratio; it is tracked separately from the shared score-sequence variability bank for now. |
| `dotted_note_rate` | new | proxyable | Wired to a shared score-native rate bank; the default is heuristic-any dotted-note ratio. |
| `staccato_rate` | new | implemented | Wired to a shared score-native rate bank; the default is written-note ratio from explicit articulations. |
| `hand_displacement_rate` | legacy | proxyable | Repo currently uses a gap-weighted same-hand attack proxy with noticeable/difficult thresholds and a long-rest filter. |
| `hand_stretch` | legacy | proxyable | Requires a precise hand model. |
| `pressing_velocity_entropy` | new | blocked | Likely needs performance/MIDI data. |
| `pressing_velocity_variability` | new | blocked | Likely needs performance/MIDI data. |
| `melodic_complexity` | new | blocked | MC family dimension; formula not yet reconstructed. |
| `melodic_originality` | new | blocked | MC family dimension; formula not yet reconstructed. |
| `degree_of_melodiousness` | new | blocked | MC family dimension; formula not yet reconstructed. |

## Working slot ledger

The harness now carries a machine-readable working slot ledger in
`tests/harness/yan2023/slot_inventory.py`.

Current working-slot counts:

- working slot inventory size: 78
- implemented slots: 52
- proxyable slots: 17
- blocked slots: 9

This 78-slot registry is intentionally overcomplete. It is a practical
implementation ledger for paper-first reconstruction work, not yet a claimed
exact recovery of the paper's final 73-column matrix. Some scope expansions or
slot splits may collapse once the exact paper-to-matrix mapping is better
recovered.

## Paper-facing 73-slot inventory

The harness now also carries a frozen paper-facing 73-slot inventory in
`tests/harness/yan2023/paper_inventory.py`.

Current paper-facing counts:

- paper-facing slot inventory size: 73
- implemented slots: 52
- proxyable slots: 14
- blocked slots: 7

Current paper-facing scope overrides relative to the 78-slot working ledger:

- `hand_stretch`: collapse staff variants to one unsuffixed slot because
  Figure 6 shows `hand stretch` without `es` / `bs` / `ts`
- `playing_speed`: collapse staff variants to one unsuffixed slot because
  Figure 6 shows `playing speed` without `es` / `bs` / `ts`
- `pressing_velocity_entropy`: collapse scoped working variants to one global
  slot because Table 3 defines PVE on a whole-score probability distribution

This 73-slot registry is the locked auditable contract for the lane. It is not
yet a verified released-matrix column contract, but its scope and count are
frozen unless the paper evidence changes.

## Implementation audit

The lane now also carries a strict implemented-slot audit. Its source metadata
lives in `tests/harness/yan2023/implementation_audit.py`, the thin runner lives
in `tests/scripts/run_yan2023_implementation_audit.py`, and the generated audit
report is expected under `tests/artifacts/yan2023/`.

The audit is intentionally stricter than the provisional working inventories:
it distinguishes truly build-safe implementations from `math_drafted` features
whose current code is real but whose Yan-specific contract is still ambiguous.

## Current status summary

- implemented: 21
- proxyable: 6
- blocked: 5
- exact 73-slot mapping: now tracked as a frozen paper-facing contract, still
  not release-aligned or fully verified

## Next update rule

When a feature implementation lands, update both this ledger and
`tests/harness/yan2023/boundary.py` in the same change. When the exact paper
slot naming is recovered, append the recovered names here instead of replacing
the existing rows. Keep the machine-readable slot ledger in
`tests/harness/yan2023/slot_inventory.py` and the paper-facing inventory in
`tests/harness/yan2023/paper_inventory.py` aligned with that update. Treat the
paper as primary evidence and the archived snapshot as secondary evidence only.
