# AGENTS

Repository-wide working rules:

- Treat this repository as the umbrella for the master's thesis, not as a
  single deployable application.
- Keep the established difficulty-analysis project inside
  `research/piano_difficulty/`.
- Follow `research/piano_difficulty/AGENTS.md` for all work inside that
  subproject.
- Keep early learning-support work in `research/learning_support/` until a
  stable reusable boundary has been demonstrated.
- Use `research/shared/` only for material that is already used by multiple
  research areas; do not move speculative abstractions there.
- Treat `brainstorm/` and `prompts/` as exploratory material, not as accepted
  requirements or validated pedagogical claims.
- Keep literature metadata, reading lists, and original notes in `literature/`.
  Store local paper files under `literature/papers/`; do not commit copyrighted
  material without a license that permits redistribution.
- Use stable IDs from the theme and tag registries when cataloging literature.
  Assign only metadata supported by the source, and preserve provenance for
  sources found through searches.
- Keep repository-wide decisions in `docs/` and implementation-specific
  documentation with the research area it describes.
- Keep generated evidence with the research area that produced it.
- Do not commit participant-identifiable data, company secrets, credentials,
  or score material that cannot legally be redistributed.
- Prefer small, explicit research experiments over prematurely fixing the
  thesis to one model, interface, generation method, or learner workflow.
- If a research area becomes independently deployable or requires a different
  privacy, ownership, or licensing boundary, document that boundary before
  considering a separate repository.
