# Canonical score asset library

This directory is the canonical home for commit-safe score material used by
`piano-difficulty` tests, harnesses, and documented examples.

## Status

The directory is being established. Commit-safe scores are currently located in:

- `evaluation_scores/known_levels/` — labeled corpora with redistribution
  permission
- `tests/fixtures/` — tiny synthetic or public-domain snippets for unit tests
- `external/ScoreAnalyzer/pieces` — legacy pieces from the OG PHP project
  (prefer `music/` or `evaluation_scores/` for new work)

## What belongs here

- Public-domain or licensed score files that are referenced by committed tests
  or reproducible harness runs.
- A provenance note for every file (source, license, why it is here).

## What does not belong here

- Copyrighted repertoire without redistribution permission.
- Ad hoc timestamped outputs.
- Participant-identifiable or legally restricted material.

## Migration plan

As the thesis progresses, commit-safe scores from the legacy and fixture trees
above should migrate here with documented provenance. New harness work should
prefer this directory once the relevant scores are available.
