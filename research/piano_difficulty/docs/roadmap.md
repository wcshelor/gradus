# Difficulty-analysis roadmap

This is the active roadmap. The earlier tasks.md is historical. See
consolidation.md for the implementation and preservation map.

The detailed remaining-work checklist is
[Task list — 2026-09-05 — Difficulty-analysis consolidation and acceptance](Task_list_2026-09-05_difficulty_analysis_consolidation.md).
It records the implemented baseline, atomic tasks, dependencies, acceptance
checks, and the separately scoped semantic work. Use it to execute this component's
consolidation, not as the whole thesis roadmap. The
[three-area learning-support plan](../../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md)
owns cross-area sequencing. Difficulty analysis supports piece understanding;
user-selected passages and questions do not need a difficulty ranking first.

## Implemented consolidation

- Promoted existing Dynamics algorithms/contracts and exporters into runtime.
- Kept experiment configs, runners, piece labs and compatibility imports.
- Added the versioned difficulty_overview default profile.
- Promoted `difficulty_aspects.v1` as the default/main Gradus difficulty
  profile, with `difficulty_overview.v1` retained as the compatibility timeline
  slice.
- Added reviewed factor definitions, exact attack selection, hand views,
  factor peaks, merged candidate sections and region input provenance.
- Connected Python API, CLI, batch, JSON, Markdown, CSV and HTML timeline.
- Repaired development dependencies and test discovery for the umbrella repo.
- Preserved explicit legacy analysis and updated stale expression snapshots.

## Next research checks

1. Review reports with the project owner and piano teachers. Test the usefulness
   of factor ordering and section boundaries, especially broad merged regions.
2. Measure peak/section sensitivity to window size and stride on a chosen
   evaluation corpus. Synthetic boundary checks are not corpus-level stability.
3. Decide whether additional existing raw descriptors belong in the overview;
   record direction, redundancy and limitations before adding their weights.
4. Add exact feature-observation attribution when the semantic passage program
   requires it. Input event IDs currently provide provenance only.
5. Let passage practice consume the 9-aspect demand profile, score regions, and
   optional factor evidence,
   including regions selected by the learner. Semantic interpretation and
   pedagogical assistance are separate capabilities, not a mandatory continuation
   of hotspot detection. Optional learner-context work belongs in learning support.

Compatibility shims remain until real consumers migrate. Yan reconstruction,
prediction/clustering, dataset work, OMR and legacy parity remain accessible.
