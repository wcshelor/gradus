# LS-02 — Entry-point reconciliation map

Status: accepted passage-first design, with the LS-03–LS-07 subset now
implemented. This document performs LS-02 of the
[three-area plan](../../../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md):
it maps what existing passage-practice contracts already support for
user-selected regions, what still assumes a hotspot, and the smallest adapter
that gives both entries one downstream interface. The original LS-02 change was
prose-only; later LS work added the shared investigation contract, exact
selection, user-selected adapter, pitch-transition observations, and one
text-only aid. The existing hotspot route and its regression tests are preserved
unchanged.

Authorities: [project direction](../../../../docs/project_direction.md) (entry
without hotspot gate), [first slice](../../first_slice.md) (scenarios S1–S7),
[architecture](architecture.md), [contracts](contracts.md),
[prototype_v1](prototype_v1.md), [testing_strategy](testing_strategy.md),
[WORK_PACKAGES](../WORK_PACKAGES.md) with
[IMPLEMENTATION_CHECKLIST](../IMPLEMENTATION_CHECKLIST.md) tasks, and
[decisions](decisions.md) D-011/D-012. Design decision D-013 (revised,
accepted after project-owner/lead review on 2026-09-05) records the adapter choice.

## 1. Two entries, one downstream interface

```text
(A) analyzer-suggested:  difficulty result + ScoreIR -> adapter
(B) user-selected:       exact region + ScoreIR      -> adapter
                                   \_________________/
                                            |
                       PassageInvestigation (existing Passage,
                         structured origin, optional difficulty context)
                                            |
                       views -> observations -> optional real attribution
                              -> patterns -> diagnosis ->
                       strategies -> transformations -> presentation
```

Route (A) is the existing bounded hotspot-to-exercise experiment; it is kept,
not rebuilt. Route (B) serves first-slice scenarios S1–S5 without computing a
difficulty profile or requiring a hotspot ID. Both routes converge at the
`PassageInvestigation` contract over the existing `Passage`: every refined region
keeps a `parent_id` chain back to its root; the investigation retains structured
selection origin independently of that lineage. See `contracts.md` for fields.

## 2. Reused contracts (verified in source, no change needed)

| Contract | Location | Reuse for route (B) |
| --- | --- | --- |
| `ScorePosition` / `ScoreInterval` (exact rational, half-open `[start,end)`) | `src/passage_practice/models/time.py` | Expresses any user-selected region; 25 unit tests pass |
| `SourceRef` / `SourceKind` + resolver (D-011) | `src/passage_practice/models/source.py` | Stable event identity for selected regions; 19 unit tests pass |
| `Diagnostic` / `Severity` | `src/passage_practice/models/diagnostics.py` | Records ambiguity and unsupported input; not the sole carrier of selection origin; 13 unit tests passed in the LS-02 run |
| `Passage` (id, score, interval, purpose, parent, event refs, method, omissions, diagnostics) | `src/passage_practice/models/passage.py` | Reused musical subject for either route; `parent_id=None` marks a root, not selection origin; no duplicate region model |
| `View` container | `src/passage_practice/models/passage.py` | Downstream views consume either route identically |
| D-012 (generic region stays in passage practice; `passage_practice -> piano_difficulty` import direction) | `docs/decisions.md` | Manual selection builds on `ScoreIR` without new shared types |
| Dual entry modes (automatic + controlled baseline) | `docs/prototype_v1.md` | Controlled path already required for testing; route (B) is its generalization |
| Diagnosis criterion “hotspot dimension **or** controlled baseline region” | `docs/prototype_v1.md` | Rule shape already admits route (B); regression scope below keeps it |

Verified 2026-09-05: `src/passage_practice/` contains zero `hotspot`
references, so no implemented code bakes in a hotspot gate; assumptions live
in planned (unimplemented) contracts and prose, which this map corrects
before selection code (WP-02 T02.2+) is written.

## 3. Implemented subset and genuinely missing pieces

1. **Manual exact-region selection API (WP-02 T02.2–T02.5) — implemented
   2026-09-05 in `src/passage_practice/passages/selection.py`.** Fixtures,
   `[start,end)` attack/boundary-context selection, inherited context,
   purpose/refinement, and whole-piece range are covered by
   `tests/unit/test_selection.py`. Q-003 selection-side policy proposed as
   D-014. Route (B) runs through `passages/investigate.py` (LS-05).
2. **Controlled manual-region adapter task (WP-05 T05.3) — LS route
   implemented 2026-09-05 in `passages/investigate.py`.** It constructs the same
   `PassageInvestigation` envelope for user-selected regions, preserves learner
   concern refs opaquely, and does not fabricate difficulty scores, hotspot IDs,
   or contributions. The broader WP-05 analyzer translation remains pending.
3. **Shared passage-first request (LS-03a) — implemented 2026-09-05 in
   `models/investigation.py`.** Both routes require a passage, not a hotspot.
   Diagnosis references passages and supporting observations; real attribution
   identifies its target. LS-03a does not implement full future
   diagnosis/attribution trees. LS-03b handles learner-context contracts separately.
4. **“Why investigated” reason for user-selected roots (WP-15 T15.1).**
   `ExplanationBrief` construction must accept a user-selection reason
   alongside hotspot reasons.

## 4. Historical LS-02 reconciliation and subsequent review

The list below records the initial prose-only changes, not current unresolved
requirements. D-013's accepted revision supersedes the interim optional-ID notes,
and LS-03a/LS-05 now implement the minimal runtime boundary. Broader analyzer
translation, attribution, diagnosis, and transformation work remains outside
this LS slice.

- `README.md` target flow and status text read as hotspot-only; amended to
  name both entries.
- `architecture.md` system context showed `hotspot + ScoreIR` as the sole
  input; amended to `(hotspot | exact region) + ScoreIR`. Layer 5 wording
  (“hotspot triggers”) now notes the controlled-baseline equivalent.
- `contracts.md` `HotspotInvestigation` section already requires an explicit
  region path (kept); interim notes mark the hotspot-ID optionality gap for
  LS-03 without changing specified fields.
- `prototype_v1.md` entry modes clarified: the controlled path requires no
  hotspot ID, score, or profile; acceptance scenario gains a controlled twin
  of step 1.
- `testing_strategy.md`, `traceability.md`, `review_checkpoints.md`: each
  hotspot-only line gains its controlled-region twin.
- `WORK_PACKAGES.md`: WP-06 goal prose broadened to baseline observations;
  WP-05/WP-08/WP-14 specs already cover both paths (T05.3, T08.3 controlled
  baseline, T14.2/T14.3) and are left structurally unchanged. No status-board
  change (lead-owned).

## 5. Smallest adapter design (for T05.2/T05.3; D-013 accepted)

Input: exact region `[start,end)` with score identity, optional target hand,
optional analyzer evidence refs. Output for both routes: `PassageInvestigation`
containing an existing root `Passage`, structured selection origin, optional hand,
and a validated optional difficulty-context collection. There is no vague
“attached evidence” return shape or separate manual downstream interface.

- **Purpose:** reuse `PassagePurpose.DETECTION` for the root — it denotes
  “the region under investigation,” matching the architecture’s detection /
  evidence / pattern / practice region semantics. No new enum value, no
  contract change.
- **Origin:** `selection_origin` is an explicit validated field of the shared
  envelope. Producer method/version stays metadata; diagnostics may explain origin
  but are not its sole record. `parent_id=None` marks a root only. Refinements keep
  their lineage and the root investigation context. Adding difficulty context
  must not rewrite origin or passage identity.
- **Optional difficulty evidence:** when the region is analyzer-suggested,
  analyzer input is mapped into validated context (method, actual hotspot refs,
  available values/evidence, warnings). When absent, stages proceed on passage
  observations; attribution is empty unless a real aggregate target exists.
  Never use sentinel hotspot IDs or fabricate contribution scores/ranks. Reject
  incompatible source/version/coverage instead of treating it as local evidence.
- **Mismatch behavior:** `score_id` must match the `ScoreIR` source;
  unresolvable regions and cross-edition notes produce the explicit
  unresolved outcome of first-slice S7 — never a guessed region.
- **Alternatives rejected:** new `PassagePurpose` value (contract churn for
  no new semantics); new shared region type (rejected by D-012); separate
  downstream pipeline for manual regions (duplicates stages, violates the
  architecture’s dependency direction).

## 6. Affected work packages and required tests per entry

| WP | Effect | Required tests |
| --- | --- | --- |
| WP-02 (T02.2–T02.5) | Builds route (B) selection; manual API is the adapter’s foundation | Boundary, tie/sustain, context, purpose/refinement, unchanged source (already specified) |
| WP-05 (T05.1–T05.3) | T05.1 consumes LS-03a contract; T05.2/T05.3 emit the same envelope; manual selection also requires T02.5 | Equivalent musical observations at equal source/region/hand/settings; absent context; enrichment preserves origin/identity; mismatch rejection |
| WP-06 (T06.1–T06.5) | Keep ordinary observations separate from attribution to real aggregate/hotspot targets | No fabricated attribution; real-target reference checks; outlier/cluster/tie and empty-evidence cases |
| WP-07 | Unchanged (pattern logic is entry-agnostic) | Existing fixture matrix; both entries feed it |
| WP-08 (T08.1–T08.4) | Passage identity required; hotspot context optional; observation-backed rules need no attribution record | Canonical positive, scalar negative, missing-relocation, no-hotspot controlled baseline, no-match |
| WP-10 | Unchanged (strategy registry is diagnosis-driven) | Existing precondition/contraindication tests |
| WP-14 (T14.2–T14.3) | Both orchestrations kept; equivalence checked after the investigation boundary | Canonical positive per path, injected failure, repeat-run equality |
| WP-15 (T15.1) | Brief accepts user-selection reason | Allowlist + no-match language on both entries |

Hotspot regression kept: existing difficulty-overview, CLI integration, and
snapshot suites plus all 80 passage-practice contract unit tests must keep
passing; LS-02 adds no fixture and changes no numeric behavior.

Next eligible task: LS-03a, then LS-03b (minimal request, journal, and context
contracts). D-013's design review is resolved, but no adapter is implemented or
WP gate released by this documentation revision. LS-03a does not depend on T05.3.
