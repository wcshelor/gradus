# Fixtures

Current fixtures:

- `minimal_piano.musicxml`: smallest useful grand-staff piano score for loader
  and parser-boundary tests
- `real_mxl_basic_grand_staff.mxl`: self-authored compressed MusicXML grand
  staff fixture committed to this repo for end-to-end `.mxl` regression
  coverage; includes title/composer metadata, tempo, chords, accidentals, and
  ordinary rests/notes
- `parity_feature_probe.musicxml` / `parity_feature_probe.mxl`: compact
  feature-rich parity probe with tempo, octave chords, accidentals, wide leaps,
  and asymmetric tuplets across hands (useful for OG-vs-replica debugging)

Planned fixture types:

- octave chords and wide spans
- large melodic leaps
- ties across barlines
- tuplets
- clef changes
- cross-staff notation
- grace notes
- tempo and dynamic directions

Fixtures should stay tiny and purpose-built so exact expected values are easy to
reason about in unit and regression tests.
