# Semantic fixture manifest (S2.3)

All fixtures are synthetic, hand-authored for S2 view/observation work, and
committed as redistributable test material. Each isolates one construct for
the S2.4+ views and S3 detectors; no repertoire excerpts or CIPI material
are imported. Expected roles are review notes for fixture design, not
detector claims — detectors earn them in S3 tests.

| Fixture | Isolates | Expected semantic role | Ambiguity / negative note | Consumed by |
| --- | --- | --- | --- | --- |
| `semantic_top_voice_melody.musicxml` | Stepwise RH quarters over sustained LH bass (1 measure, 5 notes) | Melody in the right-hand top voice; LH is support | Companion positive to the left-hand fixture below | S2.4 attack stream, S2.8 salience, S3 melody |
| `semantic_left_hand_melody.musicxml` | Moving LH quarters under a sustained higher RH whole note (1 measure, 5 notes) | Melody in the left hand | Close negative for top-voice-equals-melody assumptions; register-only salience must lose here | S2.4, S2.8, S3 melody |
| `semantic_accompaniment_pattern.musicxml` | Repeated RH broken-chord eighths over LH bass (1 measure, 9 notes) | Accompaniment-like repetition, no melody | Close negative for contour-based melody claims | S2.6 rhythm grid, S2.7 texture grid, S3 accompaniment |
| `selection_two_voices.musicxml` (existing, T02.2) | Two encoded voices, one staff: moving voice 1 vs sustained voice 2 (3/4, D major) | Voice separation without role assumption | Voice count does not imply role count (D-015) | S2.5 written stream, S2.7, S2.11 |
| `semantic_syncopation.musicxml` | LH quarter pulse vs RH dotted sustain across beat 3 plus an off-beat eighth at 3.5 (1 measure, 8 notes) | Syncopation-proxy material: off-beat attack density, staggered hand alignment | Staggered-hands positive case; exact aligned-hands negatives are S2.10's fixture concern | S2.6, S2.10 rhythm observations |
| `semantic_ambiguity.musicxml` | Static repeated top voice vs moving lower voice, one staff (1 measure, 8 notes) | Ambiguous: top-voice cue and contour cue disagree; detectors must abstain or report low confidence with a diagnostic | The designated abstention case for S3 confidence tests | S2.8 salience, S3 detectors, S1.5 band mapping |
| `attack_stream_rests.musicxml` (S2.4) | Quarter rest between attacks over LH whole note (1 measure, 4 notes + 1 rest) | Rests are documented omissions, never attacks; the rest-gap interval selects an empty stream | Rest-gap `[1,2)` selects zero attacks with the rest listed as omitted | S2.4 attack stream (rests, empty streams); S2.5 written stream (rests as entries, rest-only interval) |

Provenance: synthetic fixtures authored 2026-09-09 for S2.3 (the reused
two-voices fixture dates to WP-02, 2026-09-05), plus
`attack_stream_rests.musicxml` added for S2.4 view tests (rest omission and
empty attack streams); no licensed material.
Loader smoke assertions (measure/note counts, staves, voices, the
syncopation off-beat onset, static-top vs moving-lower voices) live in
`test_semantic_fixtures.py`. Encoding mirrors only proven patterns
(divisions=4, `backup`, part-name Piano, dotted durations); ties, rests,
tuplets, and chords stay covered by the selection fixtures.
