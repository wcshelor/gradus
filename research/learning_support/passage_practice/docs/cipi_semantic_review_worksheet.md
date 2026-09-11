# CIPI Semantic Review Worksheet — S-X5

Use this worksheet to manually review predicted difficult CIPI passages and
record likely semantic detectors, learner questions, and exercise actions.
No CIPI files are committed; record only passage identifiers, measure numbers,
and synthesized observations (no score excerpts).

## How to use

1. Select a CIPI piece and its difficulty-overview output (candidate sections, factor peaks).
2. For each candidate section, fill one worksheet row below.
3. Run the semantic bundle for the same interval (via `select_passage` + `build_semantic_bundle`) and compare to human observation.
4. Do not commit CIPI MusicXML/MXL, audio, or copyrighted excerpts — only the worksheet rows and the overview JSON/indices (which are already versioned) are commit-safe.

## Worksheet template (copy per passage)

| Field | Value / notes |
|-------|---------------|
| **CIPI piece ID** | e.g., `CIPI_xxx` (catalog ID, not filename) |
| **Passage** | `score_id@[start,end)/purpose` (exact quarters), printed measures `M–N` |
| **Difficulty overview** | Top sections IDs, factor tracks (density, span, etc.), warnings |
| **Available evidence** | Which views/observations were available (attack_stream, salience_view, etc.) |
| **Human-observed semantics** | What a musician notices (melody top voice, broken chord, syncopation, cadence) |
| **Likely semantic detectors** | Detectors that should fire (melody_salience.v1, bass_anchor.v1, accompaniment.v1, rhythm.v1, texture.v1, cadence.v1, phrase.v1) |
| **Expected hypotheses** | Expected `hypothesis_type` and band (high/medium/low) |
| **Actual bundle** | Bundle `hypothesis_type` + confidence + diagnostics (or `no_supported_hypothesis`) |
| **Match / mismatch** | `match` / `partial` / `mismatch` + note |
| **Learner question candidate** | Constrained prompt ID (e.g., `melody_projection`, `hands_together`, `reading`) |
| **Exercise action candidate** | Strategy ID (e.g., `blocked_chord`, `simplify_accompaniment`) or `none` with rationale |
| **Missing score facts** | What would improve the decision (e.g., slur, dynamics) |
| **Reviewer** | Synthetic/teacher code, date |

## Example row (synthetic example, not CIPI)

- CIPI piece ID: `synthetic_top_voice`
- Passage: `semantic_top_voice_melody.musicxml@[0,4)/detection`, M1
- Difficulty overview: candidate section `[0,4)` composite high, factor `attack density` low
- Available evidence: salience_view (accent/dynamics available), texture_grid (chord_size 1)
- Human-observed: melody in RH top voice, LH anchor, homophonic
- Likely detectors: `melody_salience.v1` (top_voice), `bass_anchor.v1` (anchor), `texture.v1` (melody_plus_accompaniment)
- Expected: `role.melody` high, `role.bass` medium, `texture.melody_plus_accompaniment` high
- Actual: `role.melody` 0.82 high, `texture.melody_plus_accompaniment` 0.78 high
- Match: partial (bass anchor present but low confidence)
- Learner question: `melody_projection` — "Is the melody clear?"
- Exercise: `simplify_accompaniment`
- Missing: slur evidence unavailable (diagnostic present)

## Audit reminder

- Do not paste MusicXML, MEI, or measure images
- Do not include CIPI file paths that reveal licensed content
- Keep rows in `tests/artifacts/cipi_review/` ignored (not committed) unless the worksheet itself is the committed template
- For the thesis, only this template and synthetic example rows are commit-safe; real CIPI rows are local-only and must be summarized without score content
