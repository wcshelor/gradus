# Selection fixture manifest (T02.2)

All fixtures are synthetic, hand-authored for this task, and committed as
redistributable test material. Each isolates one or two constructs; no
repertoire excerpts are imported.

| Fixture | Isolates | Expected loader result | Used by |
| --- | --- | --- | --- |
| `selection_two_staff.musicxml` | Exact `[start,end)` boundaries; two staves (RH quarters, LH whole notes) | 2 measures; 10 written notes; LH whole notes sustain across the mid boundary | `test_selection.py` boundary/staff tests |
| `selection_ties.musicxml` | Tie chain across beats 4–5; half note sustaining across the barline | Tie collapses to one logical attack (no double count); E4 is outgoing boundary context for `[0,4)` | `test_selection.py` tie/sustain tests |
| `selection_two_voices.musicxml` | Two voices on one staff; key/meter/clef/tempo/direction context | Voice 1 (3 quarters) vs. voice 2 (dotted half) separable; D major, 3/4, G clef, 72bpm + “dolce” inherited at start | `test_selection.py` voice/context tests |

Provenance: synthetic fixtures authored 2026-09-05 for WP-02; no licensed
material. Loader smoke assertions (measure/note counts, tie collapse, voice
labels) live in `test_selection.py`.
