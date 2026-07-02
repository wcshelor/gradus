# CIPI Dataset Harness

This lane owns the repository-side CIPI catalog and export helpers.

Use it to:

- resolve the catalog against the local CIPI corpus root
- run the external ScoreAnalyzer repo over every cataloged piece
- keep export evidence under `tests/artifacts/retired/cipi_og_export/`

Raw score files stay outside the repository unless they are explicitly safe to
commit.
