# Ad Hoc Scores

Use this directory for local score files you want to inspect but do not want to
commit.

This directory is ignored by git except for this README. Good uses:

- one-off `.mxl` files from a local export
- experiments with uncertain provenance
- large temporary corpora
- intermediate files while deciding whether a score belongs in
  `known_levels/`

Example:

```bash
PYTHONPATH=src python scripts/explain_score.py evaluation_scores/ad_hoc/local_piece.mxl
```
