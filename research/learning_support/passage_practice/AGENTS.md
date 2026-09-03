# AGENTS

Rules for all work under `research/learning_support/passage_practice/`:

## Read before changing anything

1. Read this file and the repository-root `AGENTS.md`.
2. If touching `research/piano_difficulty/`, also read its `AGENTS.md`.
3. Read `README.md`, `docs/architecture.md`, `docs/contracts.md`,
   `docs/prototype_v1.md`, `docs/testing_strategy.md`, and the selected entry in
   `WORK_PACKAGES.md`.
4. Inspect current code and tests. Plans describe intended boundaries, not proof
   that an API already exists.

## Architectural rules

- Preserve the dependency direction:

  ```text
  score facts -> views -> observations -> patterns -> diagnoses
              -> strategies -> transformations -> presentation
  ```

- A downstream layer may depend on an upstream contract. An upstream layer
  must not import or encode downstream pedagogical concepts.
- Do not put diagnoses or exercise recommendations inside difficulty-feature
  extractors.
- Do not let an LLM parse raw MusicXML, invent source evidence, mutate notation,
  or become necessary for deterministic tests.
- Keep staff, encoded voice, inferred hand, and inferred musical role as
  separate concepts.
- Every inference must carry method, evidence, confidence, and diagnostics.
- Every generated event must retain source provenance or be explicitly marked
  synthesized.
- Preserve exact rational score time internally. Convert to floats only at
  presentation or model boundaries that explicitly require it.
- Prefer a supported subset with explicit diagnostics over silent best-effort
  behavior.
- Do not move code into `research/shared/` during initial implementation.

## Scope and ownership

- Changes to generic MusicXML loading, `ScoreIR`, generic feature extraction,
  temporal windows, or hotspot discovery belong in
  `research/piano_difficulty/` and must satisfy that subproject's tests.
- Passage-specific views, diagnosis rules, strategy selection, transformations,
  and exercise export orchestration belong here.
- If a work package appears to require changing both areas, keep the changes in
  distinct commits and document the boundary in the handoff.
- Do not modify vendored or submodule code to make the prototype pass.

## Work-package discipline

- Implement one `WP-*` work package at a time unless the lead explicitly groups
  them.
- Confirm every listed dependency is complete before starting.
- Announce a claim through the active task coordinator. The lead records live
  status in `WORK_PACKAGES.md` on the integration branch so parallel package
  branches do not conflict.
- Write the completed handoff from the template under `handoffs/`. Use one file
  per package and do not rewrite another package's handoff.
- Create a decision entry in `docs/decisions.md` when implementation requires a
  choice not settled by the existing contracts.
- Stop and request review when a change would reverse an accepted decision,
  weaken provenance, combine architectural layers, or expand the supported
  MusicXML subset materially.

## Testing requirements

- Add tests in the same work package as behavior.
- Prefer tiny, purpose-built, legally redistributable MusicXML fixtures.
- Every positive fixture needs at least one nearby negative or ambiguous case.
- Test musical invariants, not only object shape or snapshot text.
- Any serializer or transformation change requires parse-after-write tests.
- Any new JSON-ready contract requires a schema-version assertion and a frozen
  representative payload.
- Any defect found during integration requires the smallest reasonable
  regression test before the fix is considered complete.
- Keep generated test evidence small and deterministic. Do not commit ad hoc
  timestamped runs.

## Completion checklist

A work package is complete only when:

- its acceptance criteria are met;
- required tests pass locally;
- relevant existing piano-difficulty tests still pass;
- public contracts and diagnostics are documented;
- unsupported cases fail explicitly or emit the documented warning;
- no copyrighted score or participant-identifiable data was added;
- the implementation notes name changed files, commands run, limitations, and
  the next unblocked work packages; and
- an independent reviewer can understand why the code belongs in its chosen
  layer.
