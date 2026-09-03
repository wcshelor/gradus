# Yan et al. 2023 Replication Plan

This folder is a self-contained replication lab focused on reproducing Yan et al. feature extraction and comparing recreated features against the published `.mat` matrices.

## Scope of this first pass
- Preserve original downloaded files.
- Build robust `.mat` inspection/loading utilities.
- Build MIDI-first feature extraction scaffolding.
- Build comparison and diagnostics reports.
- Document ambiguities and missing data needed for exact row-level replication.

## Current status
- Reference matrices and labels are loadable for EN/AMBPT and old/new/total feature sets.
- Feature-name `.mat` files are present but currently decode as MATLAB opaque objects via SciPy.
- First-pass extractors implemented: `note_count`, `mean_pitch`, `pitch_std`, `pitch_range`, `note_density`, `chord_count`, `chord_rate`.
- Melody complexity (MC1/MC2/MC3) implemented as experimental proxies that
  mirror the MIDI Toolbox formulas on a music21-parsed score stream.

## Next loop
1. Recover row-level piece identities and source MIDI list for EN/AMBPT.
2. Resolve feature-name decoding from MATLAB opaque format (or recover names from authors/code).
3. Tighten the experimental proxy implementations and, if exact MATLAB parity becomes available, replace them behind the same lab boundary.
4. Tighten row alignment and compute strict vector-level errors.
