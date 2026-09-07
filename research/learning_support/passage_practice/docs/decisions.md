# Architecture Decisions and Open Questions

This log prevents agents from silently making incompatible assumptions. Add a
dated entry when a decision materially affects more than one work package.

Statuses: `accepted`, `proposed`, `superseded`, `rejected`, `open`.

## Accepted decisions

### D-001 — Separate hotspot detection from passage diagnosis

- **Status:** accepted
- **Date:** 2026-09-02

The difficulty analyzer identifies regions worth investigating and reports
contributing dimensions. A separate passage engine attributes events,
recognizes patterns, and proposes diagnoses.

### D-002 — Use a rich canonical representation with multiple derived views

- **Status:** accepted
- **Date:** 2026-09-02

There is no single universal musical token stream. Algorithms consume typed,
documented projections derived from canonical score/passage facts.

### D-003 — Keep score fact, pattern, diagnosis, and intervention separate

- **Status:** accepted
- **Date:** 2026-09-02

This separation enables independent testing, evaluation, and uncertainty
reporting.

### D-004 — Use a hybrid source and normalized representation

- **Status:** accepted for v1
- **Date:** 2026-09-02

Retain the source document and stable source references while using normalized
objects for analysis and generation. Do not attempt a lossless model of the
entire MusicXML standard in v1.

### D-005 — Use exact half-open score regions

- **Status:** accepted
- **Date:** 2026-09-02

Canonical regions use exact rational time and `[start, end)` attack inclusion.
Sustaining boundary notes are represented separately.

### D-006 — Distinguish four region purposes

- **Status:** accepted
- **Date:** 2026-09-02

Detection, evidence, pattern, and practice regions are related but not assumed
identical.

### D-007 — Begin exercise generation deterministically

- **Status:** accepted for v1
- **Date:** 2026-09-02

Rule-driven, provenance-preserving transformations form the testable baseline.
An LLM may explain or organize approved results but is not required for score
mutation.

### D-008 — First vertical slice is a restricted broken-chord diagnosis

- **Status:** accepted
- **Date:** 2026-09-02

V1 produces blocked-chord and complementary rhythmic variants under the
supported subset in `prototype_v1.md`.

### D-009 — Preserve event-level evidence behind window summaries

- **Status:** accepted
- **Date:** 2026-09-02

Hotspot features expose or reference reproducible observations so the passage
engine can identify which events drove a window value.

### D-010 — Keep literature claims separate from formalized rules

- **Status:** accepted
- **Date:** 2026-09-02

Source claims, formalized heuristics, and executable strategies are independently
versioned and reviewed.

### D-011 — Stable source identity via normalized IDs + kind

- **Status:** accepted
- **Date:** 2026-09-03
- **Deciders:** T01.2 implementer (muse-spark), lead review pending
- **Affected work packages:** WP-01, WP-02, WP-03, WP-06, WP-07, WP-09

Context: ScoreIR generates deterministic IDs — `WrittenNoteIR.note_id = @id or f"n{xml_order}"`,
`RestEventIR.rest_id = @id or f"r{xml_order}"`, `LogicalNoteIR.note_id` reuses first written id
and keeps `source_note_ids`. Alternatives were XML paths, retained node handles, or pure @id.

Decision: Canonical references are `SourceRef(id, kind)` where `id` is the normalized
ScoreIR id and `kind` is a discrete `SourceKind` (written_note, logical_note, rest, measure,
direction, clef). Explicit MusicXML @id is preserved when present via ScoreIR generation, but
no XML parsing or mutation is performed by the resolver; resolver is a pure lookup over
ScoreIR collections. No composite locator; no node identity.

Alternatives considered: XML-path locator (brittle across renders), retained Element handles
(not serializable), @id-only (collides across kinds and missing for many notes).

Consequences: Uniqueness and deterministic regeneration inherited from ScoreIR xml_order;
selection can store only (kind,id) and re-resolve against the same ScoreIR without drift;
missing refs are explicit None, not silent.

Required tests or migration: `tests/unit/test_source.py` covers uniqueness, deterministic
regeneration, resolvable/missing, serialization round-trip, and unsupported version.

## Open questions requiring decisions during implementation

### Q-001 — Stable source identity mechanism

Should source references use normalized generated IDs, XML paths, retained node
identities, explicit MusicXML IDs when available, or a composite locator? WP-01
must propose a strategy that survives selection and serialization tests.

→ Resolved by D-011 above.

### D-012 — Keep generic region primitive in passage practice for v1

- **Status:** accepted
- **Date:** 2026-09-03
- **Deciders:** T02.1 implementer (muse-spark), lead review pending
- **Affected work packages:** WP-01, WP-02, WP-03, WP-09

Context: T01.1–T01.4 added `ScorePosition`/`ScoreInterval`/`SourceRef`/`Passage`/`View`
in `research/learning_support/passage_practice/src/passage_practice/models/`.
Existing `research/piano_difficulty` consumers use distinct types:
- `research/piano_difficulty/src/piano_difficulty/temporal/windows.py:18` `ScoreRegion`
  (measure_start/end + Fraction start_offset/end_offset and beat fields) for
  measure/beat windowing and plotting;
- `research/piano_difficulty/src/piano_difficulty/normalize/schema.py:27` `MeasureIR`
  (measure_index, start/end as Fraction) for score facts.
No `piano_difficulty` consumer imports or needs `ScorePosition` (which adds
measure_number, offset_in_measure, voice/staff/hand qualifiers and half-open
validation). No `piano_difficulty` consumer needs `PassagePurpose` or
`ViewType`. `research/learning_support/passage_practice/tests/unit/test_passage.py`
is the only current consumer of `Passage`.

Decision: Keep the most generic exact-region type (`ScoreInterval`/`ScorePosition`
and derived `Passage`) inside `research/learning_support/passage_practice` for v1.
`research/piano_difficulty` retains its own `ScoreRegion`/`MeasureIR` for
windowing. Passage-practice depends on piano_difficulty (`ScoreIR` for building
passages), not vice versa. No code moves to `research/shared/` and no new
generic type is added to `research/piano_difficulty`.

Alternatives considered:
- Move `ScoreInterval` to `research/piano_difficulty/src/piano_difficulty/temporal/` and
  re-export from passage practice — would require `piano_difficulty` to own a
  stable half-open interval contract it does not yet need, and would invert
  the current dependency direction while adding cross-package review cost.
- Promote to `research/shared/` — explicitly deferred per `research/learning_support/passage_practice/AGENTS.md`
  and `research/learning_support/passage_practice/docs/architecture.md` (shared only after
  multiple research areas use it).

Consequences:
- Import direction remains `passage_practice -> piano_difficulty` (via `ScoreIR`
  at selection time); `piano_difficulty` never imports from `passage_practice`.
- `ScoreInterval`/`Passage` remain passage-specific; if later `piano_difficulty`
  needs exact quarter-time intervals beyond `ScoreRegion`, a follow-up D-xxx can
  promote a minimal interval to `piano_difficulty` or `shared` after at least one
  concrete consumer is demonstrated.
- No migration: `Passage` stays in `passage_practice/models/passage.py`; `ScoreRegion`
  stays in `piano_difficulty/temporal/windows.py`.

Required tests or migration: No code move; `tests/unit/test_time.py` and
`tests/unit/test_passage.py` already cover `ScoreInterval`/`Passage` round-trips;
`research/piano_difficulty/tests/unit/test_difficulty_dynamics.py` still covers
`ScoreRegion` windowing.

### D-013 — Passage-first investigation with independent selection origin

- **Status:** accepted; minimal LS runtime boundary implemented
- **Date:** 2026-09-05
- **Deciders:** project owner accepted passage-first direction; lead incorporated
  the contract review on 2026-09-05. Runtime subset implemented by LS-03a/LS-05;
  this is not acceptance of broader WP analyzer translation, attribution,
  diagnosis, or transformation work.
- **Affected work packages:** WP-02 (T02.5), WP-05 (T05.3), WP-06, WP-08, WP-15

Context: LS-01 scenarios S1–S5 require assistance from a user-selected exact
region without a difficulty profile or hotspot ID. Implemented contracts
(`Passage` with `PassagePurpose` detection/evidence/pattern/practice, method
metadata, `parent_id` lineage, diagnostics) can already express such a root;
planned contracts (`HotspotInvestigation`, `AttributedSignal`, passage
`PassageDiagnosis` hotspot IDs) still assume analyzer-suggested entry. Full
design in `docs/entry_points.md`.

Decision: reuse the existing `Passage` as the musical subject. Both routes
produce one `PassageInvestigation` contract containing a required passage,
explicit structured `selection_origin`, optional requested hand, and an optional
difficulty-context collection (empty is valid). See `docs/contracts.md` for its
invariants. This envelope does not introduce another score or region model.

The root may retain `purpose=DETECTION` meaning “region under investigation,”
with producer method/version and `parent_id=None`. Origin belongs in a validated
field, not only in diagnostics or inferred from the parent ID. Adding difficulty
context to a manual request never changes its origin or passage identity.

Observations and diagnoses require passage references, not hotspot IDs.
Attribution requires a real named target and supporting observations: aggregate
attribution can exist without a hotspot; hotspot attribution requires a real
hotspot reference. Ordinary observations are not fake attribution records.
Never manufacture a hotspot, score, contribution, or sentinel ID for manual entry.

LS-03a specifies/tests the shared boundary; LS-05 implements the manual
user-selected adapter over the WP-02 selection API. LS-03b adds the separate
learner request/journal/context contracts. The remaining analyzer translation
and diagnosis consumers can depend on this boundary without creating a
dependency loop; no dependency loop is introduced by the LS split.

Alternatives considered: new `PassagePurpose` value (contract churn, no new
semantics); new shared region type (rejected by D-012); separate manual-region
pipeline (duplicates stages, violates dependency direction).

Consequences: T05.1 reuses/validates the shared contract rather than redefining
it; T05.2 still adapts automatic analyzer inputs to that contract, while the LS
manual path is implemented in `passages/investigate.py`. WP-06/WP-08 accept
passage observations without requiring attribution; T15.1 exposes selection
origin separately from optional difficulty evidence. Existing detector behavior
and regressions are preserved.

Required tests or migration: versioned LS-03a examples for both origins, absent
context, origin preservation after enrichment, invalid references, and exact time
are implemented. LS-05/LS-06 cover manual observation equivalence for the same
source/region/settings. Remaining work: T05.2 automatic analyzer translation,
T06.x no invented attribution, T08.3 manual diagnosis, and T14.2/T14.3
orchestrations. Reuse existing runtime models and version any genuinely changed
public schema; no detector rewrite or shared move.

### Q-002 — Ownership of generic passage types

Should the most generic exact-region type live in `piano_difficulty`, with
passage-practice semantics layered above it, or should v1 keep all new contracts
inside passage practice? Resolve only after inspecting actual consumers.

→ Resolved by D-012 above.

### D-014 — Selection-side partial-measure policy (Q-003 proposal)

- **Status:** proposed
- **Date:** 2026-09-05
- **Deciders:** WP-02 implementer (muse-spark), lead review pending
- **Affected work packages:** WP-02 (T02.5), WP-13 (T13.1 finalizes)

Context: Q-003 asks whether exercise export should preserve partial measures,
pad with rests, or rebar. Selection (T02.5) must state its side first.

Decision (proposed): selection keeps the exact requested interval with no
padding or rebarring; partial-measure endings are preserved with inherited
context (`whole_piece_range` covers full measures only for whole-piece
requests). Padding, rest-filling, and rebarring are export concerns for the
T13.1 writer decision (Q-008), which finalizes Q-003.

Alternatives considered: pad-at-selection (hides boundary truth from
attribution); rebar-at-selection (rewrites measure identity the diagnosis
references).

Consequences: `select_passage`/`refine_selection` never synthesize rests;
`T13.5` parse-after-write tests judge the export policy, not selection.

Required tests or migration: partial-measure selection tests in
`test_selection.py`; no migration (no prior behavior existed).

### Q-003 — Boundary handling for partial measures

Should exercise export preserve partial measures with implicit measure
semantics, pad with rests, or rebar the passage? WP-02 and WP-13 must propose one
v1 default plus explicit alternatives/rejections.

### Q-004 — Broken-chord group duration

Should a blocked group sustain for the whole source group, until the next group,
or for a configured articulation-aware duration? WP-11 must connect the choice
to the stated practice objective.

### Q-005 — Attribution for averages

Which method should be the v1 default: top observations, threshold exceedances,
contiguous cluster, or leave-one-group-out delta? WP-06 should compare behavior
on the minimal fixture before proposing a default.

### Q-006 — Confidence scale and calibration

V1 needs a deterministic uncalibrated score with visible components. Later work
must decide whether expert-labeled data supports calibration and what the score
then means.

### Q-007 — Explanation implementation

Deterministic templates are the v1 baseline. Whether an LLM variant adds value
is deferred until grounded briefs and unsupported-claim evaluation exist.

### Q-008 — MusicXML writer implementation strategy

WP-13 must compare a small repository-native writer with a maintained library
adapter. The decision should consider exact timing, source provenance, minimal
dependencies, reopenability, and supported-subset diagnostics.

## Decision-entry template

```text
### D-NNN — Title

- Status:
- Date:
- Deciders:
- Affected work packages:

Context:

Decision:

Alternatives considered:

Consequences:

Required tests or migration:
```
