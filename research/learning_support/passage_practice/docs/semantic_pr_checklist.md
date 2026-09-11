# Semantic PR Review Checklist — S-X4

Use this checklist for any PR that touches semantic extraction, views,
observations, detectors, or pedagogical bridging. Synthetic-only phase; no
real participant data.

## Provenance

- [ ] All new fixtures are synthetic or have clear redistribution license; `semantic_manifest.md` or `annotation/manifest.json` updated
- [ ] New annotation/corpus records are `provenance=synthetic`, `privacy_status=synthetic`, with `synthetic_data` diagnostic
- [ ] Literature paraphrases carry `source_ref` (e.g., `lit.xxx`) and are not model summaries

## Uncertainty

- [ ] Confidence is bounded [0,1] via `check_confidence`; band derived via `band_for` (high 0.75/may 0.50/possible 0.25)
- [ ] `confidence_method` is `heuristic`/`calibrated`/`learned` from allowed vocabulary; heuristic remains default until S7
- [ ] Contradictory evidence reduces confidence (penalty), missing evidence is recorded separately (never zeroed)
- [ ] Abstention produces empty hypotheses with `no_supported_hypothesis` diagnostic, not hidden suppression

## Source Refs

- [ ] Every hypothesis and observation carries resolvable `SourceRef` (kind+id) and exact `ScoreInterval`; missing refs produce diagnostic
- [ ] Passage `source_passage_id` is required; detector output is invalid without it
- [ ] Hand/voice/role remain separate concepts (staff ≠ hand ≠ role)

## Layer Boundaries

- [ ] Score facts (ScoreIR) → views → observations → semantics → pedagogy → learner feedback; no downstream import by upstream layers
- [ ] Detectors read views/observations, not raw MusicXML; no duplicate parsing
- [ ] Pedagogical layer does not add diagnoses inside difficulty feature extractors

## Learner Caveats

- [ ] Learner-dependent claims carry `learner_caveat` diagnostic; self-report is not measured performance
- [ ] Explanations preserve learner report verbatim and mark hypothesis as tentative until confirmed

## Positive/Negative Tests

- [ ] Every positive fixture has a nearby negative or ambiguous case
- [ ] Metamorphic helpers (transposition, duration scaling, staff swap, neighboring-measure) show expected invariance
- [ ] New detector has positive, close-negative, and ambiguous tests with diagnostics asserted

## No Hidden LLM Dependency

- [ ] Deterministic tests pass without network/model credentials
- [ ] LLM is never the sole parser for MusicXML, diagnosis, or notation mutation
- [ ] `ExplanationBrief` is required input for any LLM prompt; audit (`audit_explanation`) passes

## Documentation

- [ ] Decisions that affect multiple packages have a dated `D-xxx` entry in `docs/decisions.md`
- [ ] New public contracts have `schema_version`, deterministic serialization, and a frozen payload test
- [ ] README/docs updated to reflect new detector families or limitations
