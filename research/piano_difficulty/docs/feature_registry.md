# Overview factor registry

Authoritative executable metadata: src/piano_difficulty/features/registry.py.
Version: difficulty_factors.v1. Existing extractors remain authoritative for raw
formulas and units; none of their formulas were changed by consolidation.

| Feature ID | Label | Selection rationale |
| --- | --- | --- |
| rhythm.attack_density | Attack density | Distinct attacks per quarter, avoiding double-counted note density |
| leaps.max_melodic_leap | Largest pitch transition | Closest pitch-set distance between successive hand onsets |
| pitch_geometry.max_simultaneity_span | Largest simultaneous span | Hand-local onset span |
| coordination.subdivision_mismatch_proxy | Hand timing mismatch | Combined-hand temporal relation, explicitly a proxy |
| notation.accidental_density | Accidental density | Local reading-demand descriptor with ratio units |

All five have increasing descriptive demand direction. The registry records
scope, definition, units, default weight and limitations. Other descriptors are
still extracted and exported; absence from the composite does not retire them.

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
