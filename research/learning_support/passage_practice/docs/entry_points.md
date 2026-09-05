# LS-02 — Entry-point reconciliation map

Status: implementation map (planned, not implemented). This document performs
LS-02 of the
[three-area plan](../../../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md):
it maps what existing passage-practice contracts already support for
user-selected regions, what still assumes a hotspot, and the smallest adapter
that gives both entries one downstream interface. It changes no contracts and
adds no runtime code; the existing hotspot route and its regression tests are
preserved unchanged.

Authorities: [project direction](../../../../docs/project_direction.md) (entry
without hotspot gate), [first slice](../../first_slice.md) (scenarios S1–S7),
[architecture](architecture.md), [contracts](contracts.md),
[prototype_v1](prototype_v1.md), [testing_strategy](testing_strategy.md),
[WORK_PACKAGES](../WORK_PACKAGES.md) with
[IMPLEMENTATION_CHECKLIST](../IMPLEMENTATION_CHECKLIST.md) tasks, and
[decisions](decisions.md) D-011/D-012. Design decision D-013 (proposed,
pending lead review) records the adapter choice.

## 1. Two entries, one downstream interface

```text
(A) analyzer-suggested:  difficulty hotspot + ScoreIR -> HotspotInvestigation
(B) user-selected:       exact region + ScoreIR     -> Passage (manual origin)
                                   \_________________/
                                            |
                       identical downstream: views -> evidence ->
                       attribution -> patterns -> diagnosis ->
                       strategies -> transformations -> presentation
```

Route (A) is the existing bounded hotspot-to-exercise experiment; it is kept,
not rebuilt. Route (B) serves first-slice scenarios S1–S5 without computing a
difficulty profile or requiring a hotspot ID. Both routes converge at the
`Passage` contract: every refined region (evidence, pattern, practice) keeps
a `parent_id` chain back to its root, so selection origin is never lost.

## 2. Reused contracts (verified in source, no change needed)

| Contract | Location | Reuse for route (B) |
| --- | --- | --- |
| `ScorePosition` / `ScoreInterval` (exact rational, half-open `[start,end)`) | `src/passage_practice/models/time.py` | Expresses any user-selected region; 25 unit tests pass |
| `SourceRef` / `SourceKind` + resolver (D-011) | `src/passage_practice/models/source.py` | Stable event identity for selected regions; 19 unit tests pass |
| `Diagnostic` / `Severity` | `src/passage_practice/models/diagnostics.py` | Records selection origin, ambiguity, unsupported input; 13 unit tests pass |
| `Passage` (id, score, interval, purpose, parent, event refs, method, omissions, diagnostics) | `src/passage_practice/models/passage.py` | Root passage for route (B); origin in `method_id`/`method_version` plus a `Diagnostic`, `parent_id=None` marking a root; refinement lineage via `parent_id` |
| `View` container | `src/passage_practice/models/passage.py` | Downstream views consume either route identically |
| D-012 (generic region stays in passage practice; `passage_practice -> piano_difficulty` import direction) | `docs/decisions.md` | Manual selection builds on `ScoreIR` without new shared types |
| Dual entry modes (automatic + controlled baseline) | `docs/prototype_v1.md` | Controlled path already required for testing; route (B) is its generalization |
| Diagnosis criterion “hotspot dimension **or** controlled baseline region” | `docs/prototype_v1.md` | Rule shape already admits route (B); regression scope below keeps it |

Verified 2026-09-05: `src/passage_practice/` contains zero `hotspot`
references, so no implemented code bakes in a hotspot gate; assumptions live
in planned (unimplemented) contracts and prose, which this map corrects
before selection code (WP-02 T02.2+) is written.

## 3. Genuinely missing pieces (not yet implemented)

1. **Manual exact-region selection API (WP-02 T02.2–T02.5).** Fixtures,
   `[start,end)` attack/boundary-context selection, inherited context, and
   the public manual-selection entry are pending. Route (B) cannot run until
   T02.5 lands; nothing here reimplements it.
2. **Controlled manual-region adapter task (WP-05 T05.3).** Planned (“same
   downstream interface… do not fabricate feature contributions”) but not
   started. Section 5 below documents its design; implementation stays in
   T05.3.
3. **Hotspot-optional diagnosis input (contract gap, for LS-03).**
   `contracts.md` specifies `PassageDiagnosis` with “source hotspot and
   passage IDs” and `AttributedSignal` with “hotspot and feature IDs.” A
   user-selected root has neither. Flagged, not fixed: LS-03 contract work
   must make the hotspot reference optional (absent = valid, never
   fabricated). No contract file is edited by LS-02.
4. **“Why investigated” reason for user-selected roots (WP-15 T15.1).**
   `ExplanationBrief` construction must accept a user-selection reason
   alongside hotspot reasons.

## 4. Hotspot assumptions corrected by prose updates (this task)

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

## 5. Smallest adapter design (for T05.3; D-013 proposed)

Input: exact region `[start,end)` with score identity, optional target hand,
optional analyzer evidence refs. Output: a root `Passage` plus, when
provided, attached (never invented) difficulty evidence.

- **Purpose:** reuse `PassagePurpose.DETECTION` for the root — it denotes
  “the region under investigation,” matching the architecture’s detection /
  evidence / pattern / practice region semantics. No new enum value, no
  contract change.
- **Origin:** `method_id` names manual selection (e.g.,
  `manual_region_selection.v1`) with its version; a `Diagnostic` records the
  selection origin (user-selected vs. analyzer-suggested); `parent_id=None`
  marks a root. Refinements set `parent_id` back to this root.
- **Optional difficulty evidence:** when the region is analyzer-suggested,
  the existing `HotspotInvestigation` payload (method, score, dimensions,
  values, warnings) travels alongside by reference. When absent, downstream
  stages proceed on baseline observations; fabricating contributions is
  forbidden (same limit as T05.3).
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
| WP-05 (T05.1–T05.3) | T05.1 contract stays; T05.2 automatic translation unchanged (hotspot regression kept); T05.3 implements section-5 adapter | Manual-region downstream equivalence; absent-score handling; no fabricated contributions |
| WP-06 (T06.1–T06.5) | Attribution over baseline observations when no hotspot dims exist | Outlier vs. cluster, ties, empty evidence, unlocalizable signals — on both entries |
| WP-07 | Unchanged (pattern logic is entry-agnostic) | Existing fixture matrix; both entries feed it |
| WP-08 (T08.1–T08.4) | Rules accept controlled-baseline observations; hotspot ref optional (LS-03) | Canonical positive, scalar negative, missing-relocation, controlled baseline, no-match |
| WP-10 | Unchanged (strategy registry is diagnosis-driven) | Existing precondition/contraindication tests |
| WP-14 (T14.2–T14.3) | Both orchestrations kept; equivalence checked after the investigation boundary | Canonical positive per path, injected failure, repeat-run equality |
| WP-15 (T15.1) | Brief accepts user-selection reason | Allowlist + no-match language on both entries |

Hotspot regression kept: existing difficulty-overview, CLI integration, and
snapshot suites plus all 80 passage-practice contract unit tests must keep
passing; LS-02 adds no fixture and changes no numeric behavior.

Next eligible task: LS-03 (minimal request, journal, and context contracts).
