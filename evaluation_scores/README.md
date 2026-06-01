# Evaluation Scores

This directory is for real repertoire used to inspect extraction quality,
compare heuristic outputs, and build labeled evaluation corpora. It is separate
from `tests/fixtures/`, which should stay tiny, deterministic, and purpose-built
for automated tests.

## Intended use

Use `evaluation_scores/` for:

- real `.xml`, `.musicxml`, and `.mxl` piano scores
- benchmark sets with known external difficulty labels
- side-by-side comparisons across grading systems
- manual inspection with the verbose explain script
- later supervised-learning datasets built from extracted features

Do not use this directory for:

- minimal synthetic fixtures intended for unit tests
- frozen regression snapshots
- temporary downloads with unclear provenance

## Layout

```text
evaluation_scores/
  README.md
  known_levels/
    abrsm/
    henle/
    rcm/
  ad_hoc/
    README.md
  manifests/
    score_catalog.template.csv
```

## Subdirectories

- `known_levels/abrsm/`
  - scores labeled against ABRSM grades
- `known_levels/henle/`
  - scores labeled against Henle difficulty levels
- `known_levels/rcm/`
  - scores labeled against RCM grades
- `ad_hoc/`
  - local exploratory files that are intentionally ignored by git
- `manifests/`
  - catalog files describing provenance, labels, and notes for committed or
    external score sets

## Recommended workflow

1. Put a real score file under the appropriate `known_levels/<system>/`
   directory if it is safe and appropriate to commit.
2. Add or update a row in `manifests/score_catalog.template.csv` with:
   - relative path
   - provenance
   - labeling system
   - known label
   - composer and title
   - notes and caveats
3. Run the verbose explain script to inspect extracted values:

```bash
PYTHONPATH=src python scripts/explain_score.py evaluation_scores/known_levels/henle/example.musicxml
```

4. Run `piano-difficulty analyze-batch ...` over a labeled subset when you want
   aggregate JSON outputs and failure reporting.

## Provenance and licensing

Only commit files whose provenance and repository suitability are clear. For
licensed, large, or uncertain assets:

- keep the actual score outside the repo, or in `ad_hoc/` if it is for local
  exploration only
- keep a manifest row here so the corpus definition stays explicit
- record the source, date obtained, and any usage restrictions

## Validation use

This directory is the right place to build the first small benchmark corpus for:

- extraction correctness checks
- heuristic ranking sanity checks
- comparison against external grade labels
- future feature-to-difficulty model training
