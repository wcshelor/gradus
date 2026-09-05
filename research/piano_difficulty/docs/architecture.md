# Difficulty analysis architecture

Runtime dependency direction:

    io → normalize/ScoreIR → features → difficulty_analysis → output/CLI
                         ↘ temporal regions and selection ↗

| Owner | Responsibility |
| --- | --- |
| io, normalize | Canonical raw MusicXML/MXL parsing and score facts |
| features | Existing extractor modules and raw FeatureRecord values |
| features/registry.py | Reviewed overview factor metadata and selection |
| aggregation | Existing piece/measure raw summaries |
| temporal/windows.py | Sole implementation of measure and beat regions |
| temporal/selection.py | Non-mutating exact attack selection for analysis |
| temporal/transform.py | Sole normalization and smoothing config/value implementation |
| difficulty_analysis/dynamics | Promoted profile, peak, contribution and legacy consensus algorithms |
| difficulty_analysis/sections.py | Consolidated candidate sections |
| difficulty_analysis/overview.py | Versioned public overview and hand views |
| pipeline.py | Load once, extract once, apply requested profiles |
| output | Serialization, readable reports and HTML timelines |
| tests/harness | Experiment configs, dataset loops, sweeps and comparisons |

Compatibility paths analysis/windows.py and harness difficulty_dynamics
core/models/exports delegate to these owners. They contain no duplicate
algorithms. The normal overview does not import any tests or harness modules.
Legacy comparison code remains in its existing location to preserve imports;
it is reached only through explicit legacy profiles and comparison workflows.

No code moves into research/shared. Passage practice may later consume the
public JSON or ScoreRegion contract, but difficulty analysis does not depend on
passage_practice.
