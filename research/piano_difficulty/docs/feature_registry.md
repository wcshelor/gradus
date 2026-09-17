# Overview factor registry

Canonical taxonomy: the 9-aspect difficulty taxonomy in
[difficulty_aspect_taxonomy.md](difficulty_aspect_taxonomy.md) is the thesis/product
target framing. The learner-facing graph vocabulary is being designed
separately in
[front_facing_graph_taxonomy.md](front_facing_graph_taxonomy.md). This document
defines the conservative, reviewed 5-factor overview that remains available as
a compatibility/timeline profile. The 9 aspects are the backend Gradus
vocabulary and remain an unweighted framework, not validated weights.

Authoritative executable metadata: src/piano_difficulty/features/registry.py.
Version: difficulty_factors.v1 / schema difficulty_overview.v1. Existing extractors
remain authoritative for raw formulas and units; none of their formulas were
changed by consolidation.

| Feature ID | Aspect | Label | Selection rationale |
| --- | --- | --- | --- |
| rhythm.attack_density | 1 Rhythmic | Attack density | Distinct attacks per quarter, avoiding double-counted note density |
| leaps.max_melodic_leap | 2 Pitch/movement | Largest pitch transition | Closest pitch-set distance between successive hand onsets |
| pitch_geometry.max_simultaneity_span | 3 Hand-shape/span | Largest simultaneous span | Hand-local onset span |
| coordination.subdivision_mismatch_proxy | 5 Coordination | Hand timing mismatch | Combined-hand temporal relation, explicitly a proxy |
| notation.accidental_density | 6 Notation/reading | Accidental density | Local reading-demand descriptor with ratio units |

All five have increasing descriptive demand direction. The registry records
scope, definition, units, default weight and limitations. Other descriptors are
still extracted and exported; absence from the composite does not retire them.

This is a conservative 5-factor subset of the broader 9-aspect target:

- Covered aspects: 1 (Rhythmic), 2 (Pitch/movement), 3 (Hand-shape/span), 5 (Coordination), 6 (Notation/reading).
- Intentionally excluded from the ranked overview: Aspect 4 (Texture/polyphony) — correlated chord/density signals alongside span; Aspect 7 (Expression/control) — needs explicit demand-direction interpretation before ranking; Aspect 8 (Structural/pattern) — no validated extractor yet, primary gap; Aspect 9 (Performance/interpretive) — partially observable and learner-dependent, stays caveated.
- Texture, expression, and Yan candidates remain available raw or in experimental lanes but are not promoted into the overview composite.

## Preservation inventory

| Existing family/work | Disposition |
| --- | --- |
| metadata | Runtime contextual descriptors; retained outside the composite |
| rhythm | Runtime retained; attack density selected; other variants available raw |
| leaps | Runtime retained; maximum melodic leap selected |
| pitch_geometry | Runtime retained; maximum simultaneity span selected |
| coordination | Runtime retained; subdivision mismatch selected for combined view |
| notation | Runtime retained; accidental density selected |
| texture | Runtime retained; avoid correlated chord/density signals in initial composite |
| expression | Runtime retained; needs an explicit demand-direction interpretation before ranking |
| Yan reconstruction and optimization | Experimental formulas, inventories and evidence retained in the Yan lab |
| ScoreAnalyzer metrics | Explicit legacy profile and comparison adapters retained |
| Prediction/clustering | Existing matrices, feature selection and models retained in evaluation labs |

The older core_feature_registry.md remains a raw-descriptor reference; this
document defines the narrower reviewed overview selection. A new factor requires
documented semantics, direction, scope, units and close-negative tests. Learned
feature importance is not silently substituted for these descriptive weights.

## Relation to the 9-aspect target and future profile

- **Taxonomy vs. overview vs. validation:** See
  [difficulty_aspect_taxonomy.md](difficulty_aspect_taxonomy.md). The taxonomy is
  the conceptual target; this registry is the stable demo/runtime subset;
  validation (teacher/learner/corpus evidence) is a future layer.
- **Yan work:** Connected as candidate subfeatures mapped into the same 9 aspects
  (see taxonomy). No Yan candidate is promoted into `difficulty_factors.v1` in
  this step; `yan2023_feature_inventory.md` and `yan2023_feature_plan.md` remain
  authoritative for reconstruction status.
- **Runtime status:** `difficulty_aspects.v1` is the primary/default Gradus
  analysis profile. It groups existing and future subfeatures by the 9 aspect
  buckets with subfeature traces, but it is distinct from the overview
  composite.
- **Overview status:** `difficulty_overview.v1` remains the stable 5-factor
  compatibility/timeline profile.
- **Practice payloads:** Gradus learner-facing practice payloads should map
  hotspots and recommendations back to the 9 aspects. They may use musically
  precise vocabulary visible to students, but should avoid creating a separate
  teacher-only taxonomy that competes with the canonical aspect framework.
- **Promotion rule:** Aspect 9 must remain marked as caveated/partially
  observable. Promotion into the stable overview requires explicit review and
  validation evidence.
