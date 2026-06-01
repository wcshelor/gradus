# Yan 2023 Replication Lab (external/yan-features)

This folder is now a self-contained replication workspace for:

Hanhan Yan et al. (2023),
"Joint-optimized feature selection and classifier hyperparameters by salp swarm algorithm in piano score difficulty measurement problem."

## Purpose
This lab is for faithful feature-recreation and mismatch diagnostics against the published reference `.mat` matrices.

It does **not** currently claim exact reproduction of the paper's full pipeline.

## Preserved original files
The downloaded original `.mat` files remain in this folder and are not deleted:
- EN/AMBPT old/new/total feature matrices
- EN/AMBPT labels
- feature-name `.mat` files

## Layout
- `yan_replication/`: package with CLI, loaders, parsing, feature extraction, and comparison utilities.
- `docs/`: replication plan, feature definitions, inventory, mismatch diagnostics.
- `data/`: reference/raw/manifests/processed/reports folders for replication workflow.

## Install dependencies
From this folder:

```bash
pip install -r requirements.txt
```

## CLI
Run from `external/yan-features`:

```bash
python -m yan_replication.cli inspect
python -m yan_replication.cli inventory
python -m yan_replication.cli extract --input path/to/file.mid --out data/processed/example_features.csv
python -m yan_replication.cli compare --ours data/processed/example_features.csv --dataset EN --feature-set total
```

## Current replication status
- `.mat` matrices and labels load successfully.
- Feature-name `.mat` files are MATLAB opaque under `scipy.io.loadmat`; decoding is unresolved.
- MIDI normalization scaffold exists.
- First-pass features implemented:
  - `note_count`
  - `mean_pitch`
  - `pitch_std`
  - `pitch_range`
  - `note_density`
  - `chord_count`
  - `chord_rate`
- MC1/MC2/MC3 are intentionally `NotImplementedError` until MIDI Toolbox-compatible implementation is confirmed.

## Data limitations and warning
Exact reproduction is likely impossible until these are recovered:
- Row-level identity mapping for matrix rows.
- Original exact MIDI files used for EN and AMBPT rows.
- Fully disambiguated feature formulas/preprocessing assumptions.

Without row identities, distribution-level comparison is possible, but strict row-wise vector matching is unsafe.

## Next steps
1. Build/obtain EN/AMBPT row manifests with piece IDs and MIDI paths.
2. Decode/verify exact feature ordering from feature-name sources.
3. Implement all remaining Yan features with audit-friendly formulas and tests.
4. Iterate compare-debug loop using `data/reports/` outputs.
