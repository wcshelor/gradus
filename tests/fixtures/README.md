# Fixtures

Current fixtures:

- `minimal_piano.musicxml`: smallest useful grand-staff piano score for loader
  and parser-boundary tests

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
