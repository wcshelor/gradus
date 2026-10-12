# Difficulty analysis architecture

Runtime dependency direction:

    io → normalize/ScoreIR → features → difficulty_analysis → output/CLI
                         ↘ temporal regions and selection ↗
                         ↘ pedagogy/practice payload ↗

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
| difficulty_analysis/aspects.py | Primary `difficulty_aspects.v1` grouping over the canonical 9-aspect taxonomy |
| difficulty_analysis/front_graph_taxonomy.py | 6-dimension learner-facing graph presentation layer over score-derived feature traces |
| difficulty_analysis/sections.py | Consolidated candidate sections |
| difficulty_analysis/overview.py | Versioned public overview and hand views |
| difficulty_analysis/events | Post-processing difficulty-events subdivision (metric-driven first, selective note inspection second; does not change scores) |
| pedagogy | Gradus practice payloads: hotspots, cards, logs, drills, feedback, and recommendations over score-derived evidence |
| pipeline.py | Load once, extract once, apply requested profiles (opt-in `explain_events` enriches overview with events) |
| output | Serialization, readable reports and HTML timelines |
| tests/harness | Experiment configs, dataset loops, sweeps and comparisons |

Compatibility paths analysis/windows.py and harness difficulty_dynamics
core/models/exports delegate to these owners. They contain no duplicate
algorithms. The normal overview does not import any tests or harness modules.
Legacy comparison code remains in its existing location to preserve imports;
it is reached only through explicit legacy profiles and comparison workflows.

No code moves into research/shared. The 9-aspect difficulty taxonomy is the
canonical conceptual vocabulary for score-derived demand. `difficulty_aspects`
is the first default analysis profile and exposes all 9 buckets as descriptive
traces. `difficulty_overview` remains the stable 5-factor timeline/export slice.
`front_graph_taxonomy` maps raw feature traces into the 6 learner-facing chart
dimensions used by the David demo (`finger_dexterity`,
`hand_movement_position`, `layers_coordination`, `rhythm_timing`,
`expression_sound_control`, `notation_reading`) while preserving 9-aspect
provenance for explanations and caveats. The Gradus practice payload should
consume the 9-aspect concepts for evidence/provenance and use learner-visible
graph vocabulary for compact charts or recommendations without claiming
validated learner outcomes.

Passage practice may later consume the public JSON or ScoreRegion contract, but
difficulty analysis does not depend on passage_practice.
