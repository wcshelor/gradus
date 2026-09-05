# Consolidation validation — 2026-09-05

## Automated evidence

The repo-root suite passed 197 tests with 7 skips before adding the compact
contract snapshot; the snapshot is verified separately. The skips are optional
PHP/local Alla Turca corpus checks, not skipped overview behavior.

The installed package was also invoked from /private/tmp: difficulty_overview.v1
was produced without importing any tests or harness modules.

The original pre-consolidation Dynamics core was compared with the promoted
core on the committed feature fixture and local Beethoven Bagatelle over:

- normalization: none, min_max, z_score, robust;
- smoothing: none, moving_average.

All 16 configurations matched for regions, raw/normalized/smoothed tracks,
composites, selected peaks, and hotspot contributions. The legacy metadata now
also identifies its overlapping-measure selection policy.

## Local score smoke checks

Each score was analyzed twice with default overview settings. The complete
payloads were identical and every region's written-note ID resolved to the
parsed source. These are technical checks, not expert judgments.

| Input already present locally | Measures | Logical notes | Windows | Candidate sections |
| --- | ---: | ---: | ---: | ---: |
| Self-authored real_mxl_basic_grand_staff fixture | 2 | 6 | 2 | 1 |
| Beethoven Bagatelle Op.119 No.10 | 20 | 117 | 20 | 3 |
| Bach Prelude BWV 881, movement 1 | 64 | 846 | 64 | 5 |

The Bagatelle's candidate unions were measures 1–8, 10–12, and 15–20.
The Bach ranking selected 38–41, 58–60, 3–12, 23–31, and 49–50.
Broad unions are an expected consequence of transitive overlap and should be
reviewed musically. Representative windows and individual factor peaks are
retained so these unions can be investigated.

No score payloads or new corpus files are included in this record. Local report
outputs are kept in ignored previews/. The HTML report was opened in the
browser and its table, section text, shaded timeline regions and factor tracks
were visually inspected.

## Scope of evidence

Synthetic tests verify a known density/leap spike, a constant negative,
hand-specific values, missing hand evidence, half-open beat boundaries,
source immutability, contributor shares, a stride perturbation, stable JSON,
HTML escaping, and collision-safe batch outputs.

The two refreshed legacy snapshots have identical old descriptor values and
legacy profile results. Their additions are 24 expression records per fixture
already implemented before consolidation; no raw extraction formula changed.

Expert review, cross-corpus peak stability, calibrated feature importance and
learning benefit have not been measured by this consolidation.
