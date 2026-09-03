# CIPI Dataset Harness

This is one dataset adapter in the broader dataset-staging lane.

It currently owns the repository-side CIPI catalog and export helpers.

Use it to:

- resolve the catalog against the local CIPI corpus root
- run the legacy external ScoreAnalyzer repo over every cataloged piece when
  archival export evidence is needed
- keep export evidence under `tests/artifacts/retired/cipi_og_export/`

Raw score files stay outside the repository unless they are explicitly safe to
commit.
