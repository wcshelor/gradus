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
- Archived snapshot: `external/yan-features 2/`
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

The `.mat` name blobs in `external/yan-features 2/` do not expose the original
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
- the machine-readable paper-facing 73-slot hypothesis in
  `tests/harness/yan2023/paper_inventory.py`
- the strict implemented-slot audit metadata in
  `tests/harness/yan2023/implementation_audit.py`

## Status legend

- `implemented`: already present in the Yan harness or a direct repo-native
  primitive
- `proxyable`: likely reconstructable from MusicXML / score geometry, but the
  exact paper formula is still ambiguous
- `blocked`: likely needs performance/MIDI data or an unrecovered formula

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
| `black_key_rate` | legacy | implemented | Pitch-class derived. |
| `playing_speed` | legacy | proxyable | Current proxy uses attacks per quarter. |
| `polyphony_rate` | legacy | implemented | Reconstructed as multi-note same-onset ratio. |
| `distinct_stroke_rate` | legacy | proxyable | Stroke identity rule is not fully published. |
| `irregular_rhythm` | legacy | proxyable | Exact irregularity formula is not fully published. |
| `pitch_variability` | new | implemented | Table 3 adjacent-note normalized variability formula is now wired. |
| `note_duration_variability` | new | implemented | Table 3 adjacent-note normalized variability formula is now wired. |
| `playing_speed_variation` | new | implemented | Table 3 tempo-variation ratio is now wired. |
| `dotted_note_rate` | new | proxyable | Needs exact numerator/denominator convention. |
| `staccato_rate` | new | implemented | Direct articulation-rate reconstruction from written-note articulations. |
| `hand_displacement_rate` | legacy | proxyable | Likely recoverable from score geometry. |
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

## Paper-facing 73-slot hypothesis

The harness now also carries a paper-facing 73-slot hypothesis in
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

This 73-slot registry should be treated as an auditable paper hypothesis, not
as a verified released-matrix column contract.

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
- exact 73-slot mapping: now tracked as a paper-facing hypothesis, still not
  release-aligned or fully verified

## Next update rule

When a feature implementation lands, update both this ledger and
`tests/harness/yan2023/boundary.py` in the same change. When the exact paper
slot naming is recovered, append the recovered names here instead of replacing
the existing rows. Keep the machine-readable slot ledger in
`tests/harness/yan2023/slot_inventory.py` and the paper-facing hypothesis in
`tests/harness/yan2023/paper_inventory.py` aligned with that update. Treat the
paper as primary evidence and the archived snapshot as secondary evidence only.
