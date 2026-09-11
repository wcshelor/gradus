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

### D-014 — Selection-side partial-measure policy (Q-003)

- **Status:** accepted
- **Date:** 2026-09-05; status reconciled with landed code 2026-09-09
- **Deciders:** WP-02 implementer (muse-spark); documented acceptance after WP-02 handoff and tests
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

### D-015 — Keep `SemanticHypothesis` independent from `PatternMatch` (S-Q001)

- **Status:** accepted
- **Date:** 2026-09-09
- **Deciders:** S1.1 implementer (muse-spark); documented acceptance after S1 contract tests landed
- **Affected work packages:** S1.2, S1.3, WP-07 (future `PatternMatch` runtime)

Context: S-Q001 asks whether semantic hypotheses are independent from
pattern matches or pattern matches become one subtype. `PatternMatch`
exists only as contracts.md prose; it has no runtime implementation
(detector runtime arrives with WP-07). A subtype relation against a
non-existent contract is unimplementable, and the semantic plan already
gives `SemanticHypothesis` a `supporting_pattern_ids` field, which assumes
reference-by-ID across separate contracts.

Decision: `SemanticHypothesis` (`src/passage_practice/semantics/`) is an
independent contract. It cites pattern matches as evidence through
`supporting_pattern_ids` (opaque ID strings resolvable where the pattern
owner publishes them), never through inheritance or shared payload shape.
`PatternMatch` keeps its own contract, layer (patterns feed semantics as
evidence), and versioning. A later decision may add a promote/copy adapter
(or revisit unification) once both runtimes exist and a real consumer needs
it; that adapter will live downstream of both contracts, not inside either.

Alternatives considered: `PatternMatch` as a `SemanticHypothesis` subtype
(blocked — no base or sibling runtime to subtype); merging both into one
contract (couples S1 work to WP-07 detector design and forces every
non-pattern hypothesis — texture, phrase, harmony — through pattern
semantics).

Consequences: S1.2/S1.3 proceed without WP-07; `supporting_pattern_ids`
entries are unvalidated ID strings until the pattern registry publishes
resolvable IDs; contradiction preservation in `SemanticBundle` covers
hypothesis-vs-hypothesis conflicts, not hypothesis-vs-pattern conflicts
(those arrive with pattern runtimes).

Required tests or migration: S1.2/S1.3 contract tests in
`tests/unit/test_semantic_contracts.py`; no migration (no prior semantic
runtime existed).

### D-016 — Initial semantic confidence policy (S-Q003)

- **Status:** accepted
- **Date:** 2026-09-09
- **Deciders:** S1.4 implementer (muse-spark); documented acceptance after confidence-policy and band tests landed
- **Affected work packages:** S1.4–S1.7, S3.1 onward

Context: S-Q003 asks for the initial confidence scale and wording bands,
blocking S1.4 and S3.1 onward. The plan suggests bands
(high 0.75–1.00 "likely", medium 0.50–0.74 "may", low 0.25–0.49
"possible", unsupported <0.25) as presentation rules, not research claims;
Q-006 requires v1 scores to be deterministic and uncalibrated with visible
components; S1.2 leaves `confidence_method` vocabulary open for this
policy to constrain.

Decision: adopt the plan's bands with exact inclusive boundaries (high
$0.75 \le c \le 1.00$, medium $0.50 \le c < 0.75$, low
$0.25 \le c < 0.50$, unsupported $c < 0.25$) as specified in
`docs/semantic_confidence_policy.md`, with: `confidence_method`
vocabulary `heuristic` (only v1-permitted) plus reserved
`calibrated`/`learned`; contradiction never increases confidence;
missing evidence recorded, never zeroed; abstention split across
detector/bundle level (never suppress — S1.3 preservation) and
presentation level (unsupported excluded, low needs a learner question or
abstains, nothing-found yields an empty bundle with diagnostic per S1.6);
per-band wording map ("likely/may be/possible"). No per-detector numeric
thresholds are set here; those stay local to each detector version.

Alternatives considered: probabilistic interpretation of confidence
(rejected — no calibration data exists); global per-detector thresholds
in policy (rejected — thresholds stay detector-local per plan minimum
requirements); detector-level suppression below 0.25 (rejected — hides
uncertainty from reviewers and regression tests).

Consequences: S1.5 enforces the vocabulary and derives bands with
boundary-value tests; S1.6 implements the empty-bundle nothing-found rule;
S3 detectors keep local thresholds and record penalties under the
contradiction rule; presentation adapters are bound by the wording map.

Required tests or migration: S1.5 boundary-value, unsupported-score, and
deterministic band-mapping tests; no migration (no prior confidence
runtime existed).

### D-017 — Semantic observations live in `passage_practice/observations` (S-Q002)

- **Status:** accepted
- **Date:** 2026-09-09
- **Deciders:** S2.1 implementer (muse-spark); documented acceptance after S2 view/observation code landed
- **Affected work packages:** S2.9–S2.12, S3.1 onward, WP-04 (upstream evidence)

Context: S-Q002 asks whether semantic direct observations live in a new
`observations/` package or extend the feature-evidence layer. The
"new package" option is already reality: `passage_practice/observations/`
(LS-06 pitch transitions) is passage-scoped (`PassageInvestigation` in,
`ObservationResult` out), resolves events through `SourceRef`, carries
exact `ScoreInterval` regions, marks FACT vs INFERENCE basis, and holds no
attribution records or learner concepts. The upstream alternative,
`piano_difficulty` `FeatureRecord`, is piece-level aggregates with
measure-span-only provenance, no passage or event identity, and
plain-string diagnostics (S0.2) — extending it with observations would
require upstream to import passage identity, exact regions, and
hand/voice qualifiers, inverting the dependency direction and mixing
observation semantics into difficulty extractors.

Decision: semantic direct observations live in
`passage_practice/observations/`, reusing the `Observation` /
`ObservationResult` contracts, the source resolver, and the FACT/INFERENCE
diagnostic pattern. Import direction stays strictly passage → difficulty:
observations read `ScoreIR` and may consume `FeatureRecord`s only as opaque
difficulty context (via `DifficultyEvidence`), never as observation input.
The missing event-level `FeatureEvidence` breakdown behind difficulty
aggregates stays WP-04-owned upstream work; any shape bridging happens in
downstream adapters (WP-04/T05.2 territory), never through upstream imports
of passage types. No code moves; a future shared observation type requires
both areas depending on it first (shared-use rule, D-012 precedent).

Alternatives considered: extend the feature-evidence layer (rejected —
inverts dependency direction, drags passage/role concepts upstream); new
third package under `research/shared/` (rejected — single consumer,
explicitly deferred per shared-use rule and D-012).

Consequences: S2.9–S2.12 add observation families to the existing package;
S3 detectors depend on `Observation`, never on `FeatureRecord`; WP-04
defines the upstream evidence shape independently with passage-side
contract tests.

Required tests or migration: S2.9–S2.12 family tests reuse observation
contract assertions (resolvable refs, exact regions, basis diagnostics);
no migration (existing LS-06 observations already live where decided).

### D-018 — Minimum source facts for semantic views (S-Q004)

- **Status:** accepted
- **Date:** 2026-09-09
- **Deciders:** S2.2 implementer (muse-spark); documented acceptance after S2 view tests exercised the decided fact sets
- **Affected work packages:** S2.3–S2.13, WP-04 (upstream evidence, tracked)

Context: S-Q004 asks how much of `ScoreIR` must be promoted before
semantic views can avoid duplicate parsing (S0.4 rule). Audited each
S2 view/observation family against `normalize/schema.py`,
`normalize/converters.py`, and the S0.1 inventory:

- `attack_stream` (S2.4): tie-collapsed `LogicalNoteIR` + exact
  onset/duration Fractions + `xml_order` + collapse diagnostics
  (`unmatched_tie_stop`, `overlapping_tie_start`, `unclosed_tie`) +
  `select_passage` boundary context — all present.
- `written_stream` (S2.5): `WrittenNoteIR` staff/voice/articulations/
  accidental/spelling/duration-type + `source_note_ids` links +
  `RestEventIR` — all present. Whether rests join the stream is
  S2.5-internal selection policy, not an upstream gap.
- `rhythm_grid` (S2.6): attack stream + `MeasureIR` start/end,
  `time_signature`, `time_beats`/`time_beat_type` + `tuplet_actual`/
  `tuplet_normal` flags — all present.
- `texture_grid` (S2.7): attack/written streams + `OnsetGroupIR` +
  durations for sustained-under-moving computation — all present.
- `salience_view` (S2.8): above + articulation tuples + `DirectionIR`
  dynamics values — present; **slurs are absent** (no slur handling
  anywhere in `normalize/`), so slur evidence is unavailable, not zero.
- S2.9–S2.12 observations: pitch/interval (present), rhythm
  (present), texture incl. voice count and staff crossing (voice/staff
  present, crossing computed), readability (accidental, ledger proxy via
  step/octave + clef, clef changes, articulation density, `is_grace` —
  all present; layout data unavailable by design).

Decision: **no `ScoreIR` promotion is required before S2 views are
reliable.** S2.4–S2.13 proceed as passage-side projections over already
normalized facts; slur evidence is declared unavailable-with-diagnostic
until the gated task U1 below proves need. Clarifies S0.5: WP-04
event-level `FeatureEvidence` is not an S2 gate — passage observations
compute from `ScoreIR` via views (LS-06 pattern, D-017) — it stays
relevant for hotspot attribution (WP-06) and S4 difficulty bridging.

Required upstream task list (tracked here, implemented upstream under
that area's tests — nothing lands in this task per its limit):

- U1 (optional, gated): slur phrase-marking support in
  `piano_difficulty/normalize` (new field or `DirectionIR` kind + tests).
  Owner: `piano_difficulty`. Gate: S2.8 fixture review must demonstrate a
  salience case that needs slurs; default until then is
  unavailable-with-diagnostic. Must satisfy that subproject's tests.
- U2 (tracked, not S2-gating): WP-04 event-level `FeatureEvidence`.
  Owner: `piano_difficulty`, with passage-side contract tests. Needed for
  WP-06 attribution and S4 context bridging, not for S2 views.
- Explicitly not required: no new note/rest/measure/clef/direction
  fields, no ID scheme changes, no hand-inference upgrade (staff-based
  inference plus `unknown_staff_hand` diagnostics suffices for the v1
  subset with explicit low-confidence handling per S0.4 R4).

Required tests or migration (this task): none — decision only; S2.3
fixture work and S2.4+ view tests exercise the decided fact sets.

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

### D-019 — Learner-feedback retention and synthetic free-text policy (S-Q005)

- **Status:** accepted
- **Date:** 2026-09-10
- **Deciders:** S5.1 implementer (muse-spark), owner review pending for real-data handling
- **Affected work packages:** S5.1–S5.6, S8.1–S8.6

Context: S-Q005 blocks all learner-feedback work: which fields may be collected,
how long feedback lives, what privacy caveats apply, and whether synthetic
free text may be committed in tests. Prior `research/learning_support/
learner_context` contracts handle journal entries; passage_feedback needs its
own `LearnerFeedbackSignal`/`LearnerAdjustedFocus` with explicit retention and
privacy semantics for the thesis phase.

Decision: Adopt `docs/learner_feedback_policy.md`: allowed fields are
`feedback_id, source_passage_id, prompt_id, answer_kind, selected_value,
free_text, mapped_hypothesis/objective_ids, retention_scope (session/
explicit_save), method provenance, diagnostics`. Default retention is
`session` (ephemeral); `explicit_save` is only for learner-opted thesis-local
storage. All committed fixtures use **synthetic** free text (anonymized,
labeled synthetic in the fixture); real learner data collection remains blocked
until owner approval + consent/retention infrastructure. Free text is data, not
an instruction that can override pedagogy, and must pass through `S5.4` mappings.
Every record carries `synthetic_data` diagnostic; no PII, no external transmission,
no LLM training on feedback.

Alternatives considered: disallow any free text in synthetic tests (rejected —
prevents verbatim-preservation test from S4.1); allow free text to become
hypothesis IDs (rejected — violates pedagogical_input_boundary.md); allow
automatic cross-session persistence (rejected — retention must be explicit).

Consequences: S5.2 implements `LearnerFeedbackSignal` with this vocabulary;
S5.3 prompts use declared choice IDs only; S5.4 mappings operate on
`selected_value`/`answer_kind`, never raw advice; S5.5 adjusted focus
preserves synthetic provenance; real-data work remains gated.

Required tests or migration: `tests/unit/test_learner_feedback_signal.py`
asserts serialization, missing passage rejection, unsupported answer_kind, and
synthetic free-text acceptance; no migration.

### D-020 — Annotation schema for human labels (S-Q006)

- **Status:** accepted
- **Date:** 2026-09-10
- **Deciders:** S7.1 implementer (muse-spark)
- **Affected work packages:** S7.1–S7.7, S8.1–S8.6

Context: S-Q006 blocks S7 annotation work: which fields human labels must
contain for melody, bass, accompaniment, texture, phrase, harmony, difficulty
reason, learner issue, advice, and reviewer status. The schema must support
S7.2 contract, S7.3 synthetic fixtures, and S7.4 baseline export while
remaining synthetic-only for the thesis phase.

Decision: Adopt `docs/annotation_schema.md`: label families are `melody,
bass, accompaniment, texture, phrase, harmony, difficulty_reason,
learner_issue, advice` with controlled vocabularies (e.g., melody
`top_voice/left_hand/hidden/none`, texture `melody_plus_accompaniment`,
harmony `local_key_C/cadence`). Record fields are `annotation_id,
source_passage_id, label_family, label_value, annotator_role (teacher/
researcher/synthetic), confidence [0,1], provenance, review_state
(unreviewed/reviewed/disputed), privacy_status (synthetic/anonymized),
optional source_refs, diagnostics, schema_version `annotation.v1`. All
committed fixtures use `synthetic` role/provenance/privacy and synthetic
passage IDs; real data remains blocked until owner-approved workflow.

Alternatives considered: free-text label_value (rejected — need controlled
vocabulary for S7.4 comparison); separate schemas per family (rejected —
single record with family enum is simpler for S7.2); allow real learner data
in fixtures (rejected — privacy, synthesis only).

Consequences: S7.2 implements `AnnotationRecord` with this schema and
deterministic serialization; S7.3 fixtures use synthetic `semantic_*`
passages; S7.4 can export stable columns (family/value/annotator/confidence/
review_state); no ScoreIR or detector changes.

Required tests or migration: S7.2 tests will assert vocabulary enforcement,
deterministic round-trip, and no private data; no migration.

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
