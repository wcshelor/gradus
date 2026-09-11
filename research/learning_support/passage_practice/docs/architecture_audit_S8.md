# Architecture Audit — S8 (2026-09-11)

Scope: after S8 pedagogical corpus + explanation (corpus/schema, text_provenance, explanation_brief, explanation_audit, evaluation). Review whether any code crossed layer boundaries or duplicated difficulty parsing.

## Layer boundary checks

**Expected direction:** `score facts -> views -> observations -> semantics -> pedagogy -> learner feedback -> corpus/explanation`

- `semantics/` imports: `models/*`, `semantics/*`, `views/*`, `observations/*` only — no `pedagogy`, no `learner_feedback`, no `piano_difficulty.io` direct parsing. **Result: PASS** (grep confirms no `from passage_practice.pedagogy` or `from passage_practice.learner` in `semantics/`; no `ElementTree` or `load_musicxml_document` in `semantics/` except via ScoreIR passed in).
- `corpus/` imports: `models/diagnostics`, `semantics/contracts` (for brief), `corpus/*` — does not import `piano_difficulty.io` directly. **PASS**.
- `observations/` imports: `models/*`, `views/*`, `observations/*` — does not import `semantics` or `pedagogy`. **PASS** (checked: observations uses `build_rhythm_grid`/`texture_grid`/`written_stream`, not detectors).
- `views/` imports: `models/*`, `passages/*`, ScoreIR — no pedagogy. **PASS**.
- No code moved to `research/shared/` prematurely. **PASS** (shared use rule: only after multiple consumers).

## Difficulty parsing duplication

- No semantic module calls `load_musicxml_document` or parses MusicXML directly; all semantic inputs are via `ScoreIR` + `Passage` + views. The only direct parsing is in tests/helpers (`metamorphic.py` helpers and fixture loaders) which is allowed for test fixtures via `piano_difficulty.io`. **PASS**.
- `ScoreIR` fields used by S8 (pitch_midi, duration Fractions, staff/voice, measure start/end, ties) are all available without promotion; D-018 remains valid (no missing slur evidence beyond already-documented `slur_evidence_unavailable`).

## Findings

- **No boundary violation** detected in S8.
- **One minor cleanup candidate:** `helpers/metamorphic.py` duplicates some ScoreIR deep-copy logic that could be shared with test fixtures; keep as test-scoped helper, not runtime.
- **Diagnostic registry** (S-X1) now centralizes codes; no duplicate codes found (97 distinct).

## Required cleanup tasks

- [ ] No runtime cleanup required for S8. Keep `helpers/metamorphic.py` test-scoped.
- [ ] If future S9 adds a new view, ensure it is added to `diagnostic_codes.MISSING_VIEW_CODES` before use.
- [ ] Before moving any corpus type to `research/shared/`, demonstrate at least two consumers (S8 + future learning_support consumer).

## Reviewer

Synthetic audit (automated grep + manual review) — no teacher review yet.
