# ScoreAnalyzer Harness

This package contains the reusable OG-parity machinery for piano-difficulty.

It is test-scoped by design:

- overview compare: `scoreanalyzer_parity.py`
- report formatting: `scoreanalyzer_parity_summary.py`
- batch orchestration: `scoreanalyzer_parity_pipeline.py`
- single-piece forensics: `scoreanalyzer_single_piece_forensics.py`
- verbose event diffing: `scoreanalyzer_verbose_diff.py`
- displacement probe: `scoreanalyzer_displacement_probe.py`
- displacement trace: `scoreanalyzer_displacement_trace.py`
- octave-ratio probe: `scoreanalyzer_octave_ratio_probe.py`
- chord-event map: `scoreanalyzer_chord_event_map.py`
- normalization battery: `scoreanalyzer_normalization_battery.py`
- window failure taxonomy: `scoreanalyzer_window_failure_taxonomy.py`
- file-path wrapper for full-piece parity:
  `tests/scripts/run_scoreanalyzer_parity_piece.py`

Thin runnable wrappers live in `tests/scripts/`.
Generated evidence lives in `tests/artifacts/`.

The displacement trace is the per-note forensic companion to the broader
probe. It compares three layers for one suspect note:

- current Python compatibility-stream behavior
- Python replay with OG-style gap policy
- raw MusicXML replay that mirrors the PHP `getPreviousNoteElement` walk

OG displacement rows are matched by stable musical coordinates, not by the
synthetic note ids alone.

Displacement investigations should always report the gap in musical terms for
manual review. When a trace is run, use the reported interval and gap to answer
whether the jump should count as difficult on the page itself:

- interval: the pitch jump in semitones between the two attacks
- gap: the time between attacks expressed as beats or note values when possible
- threshold: the OG cutoff translated into the same musical units

If a displacement difference is being investigated, the review output should
make it obvious which side is counting the leap and whether the score visually
supports that classification.

`maxIntervalRH` and `maxIntervalLH` are treated as OG locator fields in the
parity lane. The Python replica keeps the pointer and the actual semitone size
separate via `maxIntervalMeasureRH/LH` and `maxIntervalSemitonesRH/LH`.

Known OG boundary behavior:

- the legacy PHP octave-event extraction only evaluates chord onset logic while
  a lookahead note exists
- this means the final candidate note in a score can be skipped by the OG octave
  ratio logic if the event is only discoverable at the stream tail
- parity and forensic probes should treat a missing final-measure octave event
  as an OG-side boundary quirk unless a separate Python regression is proven

Prefer the file-path wrapper for everyday parity runs:

- `tests/scripts/run_scoreanalyzer_parity_piece.py --piece-file /absolute/path/to/score.musicxml --php-bin /path/to/php`

It derives the OG `pieces_root` from the score location when possible, which
avoids the recurring `piece-relpath` and `pieces-root` mismatches.

For hand-specific displacement investigations, use the thin wrappers:

- right hand: `tests/scripts/run_scoreanalyzer_rh_displacement_probe.py`
- left hand: `tests/scripts/run_scoreanalyzer_lh_displacement_probe.py`

Both wrappers share the same probe engine; the default measure filter now keys
off the selected hand so LH runs no longer inherit RH-only hotspot windows.
