# Data Inventory: Yan Feature Repository

## What this repo provides
- Precomputed feature matrices for EN and AMBPT datasets.
- Labels for EN and AMBPT.
- Feature-name `.mat` files (`feature_name_old/new/total.mat`) that exist but currently decode as MATLAB opaque objects under `scipy.io.loadmat`.

## Exact files available
- `EN_old_features.mat` shape `(677, 39)` dtype `float64`
- `EN_new_features.mat` shape `(677, 34)` dtype `float64`
- `EN_total_features.mat` shape `(677, 73)` dtype `float64`
- `EN_label.mat` shape `(677, 1)` dtype `uint8`
- `AMBPT_old_features.mat` shape `(2040, 39)` dtype `float64`
- `AMBPT_new_features.mat` shape `(2040, 34)` dtype `float64`
- `AMBPT_total_features.mat` shape `(2040, 73)` dtype `float64`
- `AMBPT_label.mat` shape `(2040, 1)` dtype `uint8`
- `feature_name_old.mat` (MATLAB opaque key `None`)
- `feature_name_new.mat` (MATLAB opaque key `None`)
- `feature_name_total.mat` (MATLAB opaque key `None`)

## Label distributions
- EN labels: `{1: 129, 2: 188, 3: 187, 4: 173}`
- AMBPT labels: `{1: 264, 2: 247, 3: 292, 4: 280, 5: 255, 6: 264, 7: 197, 8: 131, 9: 110}`

## Feature names availability
- Files are present but not directly decoded by current SciPy loader due to MATLAB opaque representation.
- Partial/manual placeholder names are included in code for scaffolding only.

## Original MIDI/source metadata availability
- Original MIDI files are **not** included in this folder.
- No piece-level row identifiers, titles, composers, or row-index mapping are included in matrices.
- README references source websites (8notes, ambrosepianotabs) but no row-wise URLs are provided.

## Missing items before exact reproduction
- Row-wise identity mapping between each matrix row and source piece.
- Exact original MIDI set used by authors for EN and AMBPT.
- Full disambiguated feature definitions and preprocessing assumptions.
- Reliable decoding or external list of exact feature-name ordering.
