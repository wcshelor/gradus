# S0.5 — Semantic input readiness matrix

Status: combined inventory only. Committed documentation; no runtime changes.

Combines:

- S0.1 — `docs/semantic_score_fact_inventory.md` (score facts in passage practice).
- S0.2 — `docs/semantic_feature_evidence_inventory.md` (difficulty features + payloads).
- S0.3 — `docs/semantic_cipi_handoff.md` (CIPI run outputs → semantic inputs).
- S0.4 — `docs/semantic_duplicate_parsing_risks.md` (R1–R12, no re-parsing rule).

Column key: **source** = inventory doc + canonical code location;
**available now** = implemented / partial / missing as inventoried (no new
judgement); **needed for phase** = earliest plan phase consuming it;
**owner** = owning package per boundary rules; **test fixture** = existing
committed fixture or the phase task that creates one; **blocking decision** =
open decision ID or "none".

Existing committed fixtures (whole matrix): `tests/fixtures/manifest.md`,
`selection_two_staff.musicxml`, `selection_ties.musicxml`,
`selection_two_voices.musicxml`.

## A — Score facts and passage contracts (from S0.1)

| Input | Source | Available now | Needed for phase | Owner | Test fixture | Blocking decision |
|---|---|---|---|---|---|---|
| Event IDs (written/logical/rest/direction/clef/measure) + `SourceRef` resolver | S0.1; `piano_difficulty/normalize/schema.py`, `passage_practice/models/source.py` (D-011) | Yes — subset; `ONSET_GROUP` intentionally unresolvable | S1 (contracts reference covered events) | `piano_difficulty/normalize` (minting), `passage_practice/models` (refs) | Existing selection fixtures | None |
| Exact rational timing + half-open intervals | S0.1; `models/time.py`, `MeasureIR.start/end` | Yes (`ScorePosition`/`ScoreInterval`, floats rejected) | S1 (covered regions), S2 (`rhythm_grid`) | `passage_practice/models`, `piano_difficulty/normalize` (facts) | Existing selection fixtures | None |
| Encoded staff + encoded voice (kept separate) | S0.1; `WrittenNoteIR`/`LogicalNoteIR` staff/voice | Yes as facts; `VOICE_STREAM` contract-only, no builder | S1 (position qualifiers), S2 (`voice_stream`, S2.5) | `piano_difficulty/normalize` (facts), `passage_practice/views` (streams) | `selection_two_voices.musicxml`, `selection_two_staff.musicxml` | None for facts; S-Q004 for view requirements (S2.2) |
| Inferred hand (`hand` + `hand_confidence`) | S0.1; `_assign_staff_hands`, LS-06 `INFERENCE` basis pattern | Partial — staff-inferred, low confidence; no `hand_stream` builder | S2 (`hand_stream`), S3 (hand-scoped detectors) | `piano_difficulty/normalize` (inference), `passage_practice/views` (stream) | Existing fixtures (staff-scoped cases) | S-Q004 (S2.2): minimum hand facts before views are reliable |
| Tie-collapsed attacks + `source_note_ids` + collapse diagnostics | S0.1, S0.4 R2; `_collapse_ties_with_diagnostics`, `_logical_from_chain` | Partial — collapsed facts + 3 diagnostics; no tie-chain object in `Passage` | S2 (`attack_stream`, S2.4) | `piano_difficulty/normalize` (collapse), `passage_practice/views` (stream) | `selection_ties.musicxml` | S-Q004 (S2.2) |
| Articulation / grace / chord-continuation / tuplet / accidental flags | S0.1, S0.4 R1/R8/R11; `WrittenNoteIR` fields | Upstream only — not projected into `Passage`/`Observation` | S2 (`written_stream` S2.5, notation readability S2.12) | `piano_difficulty/normalize` (facts), `passage_practice/views` (projection) | None yet — S2.3 fixture manifest | S-Q004 (S2.2) |
| Dynamics / directions / tempo marks | S0.1, S0.4 R8; `DirectionIR`, `MeasureIR.tempo_*` | Context-thin — `PassageContext` keeps start-active only | S2 (salience evidence), S3 (melody detector) | `piano_difficulty/normalize` (facts), `passage_practice/passages` (context) | None yet — S2.3 | S-Q004 (S2.2) |
| Measure identity + key/meter/clef context | S0.1, S0.4 R7/R8; `MeasureIR`, `ClefIR`, `PassageContext` | Context-thin — inherited at passage start, no in-passage tracking | S2 (views), S6 (local key / harmony) | `piano_difficulty/normalize` (facts), `passage_practice/passages` (inheritance) | Existing fixtures (context propagation) | S-Q004 (S2.2) for S2; harmony policy later (S6) |
| Pitch-transition observations (LS-06, signed semitones) | S0.1; `passage_practice/observations/` | Yes — only observation family; `FACT` unscoped / `INFERENCE` hand-scoped | S2 (pitch observations S2.9), S3 (leap input) | `passage_practice/observations` | Existing observation tests | S-Q002 (S2.1): observation package ownership |
| Passage selection + `PassageInvestigation` envelope + diagnostics | S0.1; `passages/selection.py`, `models/investigation.py` (D-013, D-014 proposal) | Yes (LS-05 manual entry; T05.2 analyzer translation pending) | S1 (all contracts anchor on passage ID) | `passage_practice/passages`, `passage_practice/models` | Existing selection/investigation tests | None |

## B — Difficulty feature evidence (from S0.2)

| Input | Source | Available now | Needed for phase | Owner | Test fixture | Blocking decision |
|---|---|---|---|---|---|---|
| Piece-level `FeatureRecord`s (all 8 families) with measure-span provenance | S0.2; `piano_difficulty/features/*`, `analysis/source_map.py` | Yes as aggregates; **no event-level trace** (span only), empties silently zero | S4 (difficulty context for pedagogical bridge) | `piano_difficulty/features/*` | Difficulty-side fixtures (not passage fixtures) | None for consumption; S-Q002 (S2.1) for observation-vs-evidence placement |
| Promoted overview subset (5 factors, `difficulty_factors.v1`) | S0.2; `features/registry.py` | Yes, with stated limitations | S3 (detector prioritization), S4 (dimension mapping) | `piano_difficulty/features` (registry) | Difficulty-side fixtures | None |
| Windowed series / peaks / hotspots with contributions (Dynamics lane) | S0.2; `difficulty_analysis/dynamics/*`, `temporal/windows.py` | Yes on analyzer runs; measure/beat granularity, never notes | S3 (region prioritization), S4 (hotspot context) | `piano_difficulty/difficulty_analysis`, `temporal` | Analyzer run outputs (not committed fixtures) | None |
| Event-level observation breakdown behind aggregates (`FeatureEvidence` per contracts) | S0.2 gap; contracts §Feature evidence | **Missing** — WP-04 work | S2 (direct observations need it) | `piano_difficulty` (with passage-side contract tests) | None yet — WP-04 | S-Q002 (S2.1), S-Q004 (S2.2) |

## C — CIPI handoff (from S0.3)

| Input | Source | Available now | Needed for phase | Owner | Test fixture | Blocking decision |
|---|---|---|---|---|---|---|
| Score identity (`piece_uid`, `dataset_relative_path`, resolved path) | S0.3; `tests/harness/shared/*`, movement manifest (744 rows) | Yes — resolution logic; raw files local-only, never committed | S3/S4 runs (analyzer-suggested entry) | `piano_difficulty/tests/harness` (lane-scoped) | Canonical manifest (committed); no score fixtures | None |
| Candidate sections (region, relative score, supporting factors, representative-window contributions) | S0.3; `difficulty_analysis/overview.py`, `sections.py` | Yes on local runs; committed artifacts currently all `missing_source_file` | S3 (prioritization), S4 (context) | `piano_difficulty/difficulty_analysis` | Analyzer run outputs (not committed) | None |
| `region_evidence` per-window note-ID lists | S0.3; `output/overview.py` | Yes on local runs — region inputs, **not** attribution | S3/S4 (resolvable refs into `DifficultyEvidence`) | `piano_difficulty/output` | Analyzer run outputs (not committed) | None |
| Matrix-lane exports (`piece_json`, labeled matrix, load report) | S0.3; `tests/harness/shared/runtime_matrix_export.py` | Yes on local runs | S7 (corpus/annotations later) | `piano_difficulty/tests/harness` | Run outputs (not committed) | S-Q006 (S7.1) for annotation use |
| Human semantic labels / learner data for CIPI passages | S0.3 gap; plan note format | **Missing** — manual review only (S-X5 worksheet) | S4+ (grounding), S7 (annotations) | `passage_practice` (worksheet), reviewers | None yet — S-X5 | S-Q005 (S5.1, learner retention), S-Q006 (S7.1, annotation schema) |

## D — Parse-boundary rule (from S0.4)

| Input | Source | Available now | Needed for phase | Owner | Test fixture | Blocking decision |
|---|---|---|---|---|---|---|
| No duplicate MusicXML parsing (R1–R12: durations, ties, groups, hand, role-from-voice, pitch, measure context, clefs/directions, IDs, rests, grace/chord/tuplet flags, part selection) | S0.4; rule enforced by review, no automated lint yet | Rule documented; compliance by inspection | Every phase S2 onward | `piano_difficulty/io` + `normalize` (sole readers); all semantic consumers | Existing fixtures exercise the *correct* path (e.g. tie collapse); a negative re-parse test belongs to S2 | None (rule, not a decision); S-Q004 (S2.2) settles any promotion needs so the rule never forces a re-parse |

## Readiness verdict

- **S1 (contracts + confidence policy) is unblocked, in order:** S1.1
  (S-Q001) first, then S1.2–S1.3 (`SemanticHypothesis`/`SemanticBundle`
  reference passage/event/observation IDs that exist), then S1.4–S1.5
  (confidence bands/helpers — no detector thresholds). Nothing in S1
  requires the missing rows above.
- **S2 is partially blocked:** S2.1 (S-Q002) and S2.2 (S-Q004) decisions
  must resolve observation ownership and minimum source facts; the missing
  rows (event-level feature breakdown, in-passage key/meter/dynamics
  tracking, `written_stream`-dependent flags) are exactly their input.
  S2.3 fixtures cannot be finalized before those decisions.
- **S3–S4 can proceed on controlled user-selected passages** (the required
  twin path) once S1–S2 land; analyzer-suggested entry additionally needs a
  live CIPI-capable run, which is an environment condition, not a code gate.
- **S5/S6/S7 are parked behind their decisions** (S-Q005 learner policy,
  S-Q006 annotation schema) plus S2–S4 outputs; no S0 row unblocks them
  early.

## What S0.5 does not claim

- No new facts beyond S0.1–S0.4; "available now" restates those inventories.
- No phase is started or scheduled here; "needed for phase" cites plan
  phases, not work-package commitments (conversion to `WP-*` stays with the
  lead).
- The tasks file remains an execution aid, not a status board: boxes are not
  checked off here.
