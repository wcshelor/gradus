# Mismatch Diagnostics Guide

## Comparison modes
- If row alignment is unknown: compare only per-feature distributions (mean/std/min/max).
- If row alignment is known: compare vector-level MAE and correlation per feature.

## Current limitation
The published `.mat` files in this folder do not include explicit row-level piece identities; strict row-wise error diagnostics are unsafe without an external alignment mapping.

## Outputs
Reports are written to `data/reports/`:
- `*_ours_summary.csv`
- `*_reference_summary.csv`
- `*_pairwise.csv` (only when comparable columns exist)
- `*_diagnostic.txt`
