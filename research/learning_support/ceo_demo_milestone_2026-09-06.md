# CEO walkthrough prototype — milestone plan

Date: 2026-09-06. Author: muse-spark. Status: planning only, pending lead review.
Implements LS-11 of the [three-area plan](../../docs/Task_list_2026-09-05_flexible_piano_learning_support.md):
the selected next increment is a thin, local, unpolished demo harness for a
CEO/company walkthrough. No GUI or graph code is built by this document.

Input state: LS-01–LS-10 implemented and pending lead review; full suite
347 passed, 7 skipped; [LS-10 evaluation](evaluation_ls10.md) with checks
E01–E12; review status explicitly negative (no teacher/owner walkthrough yet,
no real-data approval). Related component plan:
[difficulty-analysis consolidation](../piano_difficulty/docs/Task_list_2026-09-05_difficulty_analysis_consolidation.md)
(DC-01–DC-16 pending; the demo must not wait for them nor claim them).

## 1. Why this is the next step after LS-10

LS-10 closed the research slice with evidence but no human review: its
section 9 proposes a walkthrough replaying V1–V7 against E01–E12, and its
section 8 lists personalization risks that need human eyes. A CEO/company
walkthrough serves both purposes at once — it is the review venue LS-10
asked for and the company-visibility step the owner requested. A thin live
demo (not slides, not canned outputs) forces the real seams to show: where
automation ends, where the learner speaks, and where the system abstains.
Anything heavier (new patterns, new aids, curriculum, product integration)
would expand scope before the slice has been reviewed.

## 2. What the repo can already do vs. what the demo layer must add

| Demo beat (owner flow) | Already exists (reuse, do not rebuild) | Demo layer must add |
| --- | --- | --- |
| Choose/load a piece | MusicXML loader + ScoreIR (`piano_difficulty`); CLI `piano-difficulty analyze` | DEMO-01: demo score choice + fixture policy; file picker wired to existing loader |
| Auto-detected difficulty info | `difficulty_overview` profile: 5 factors, candidate sections, diagnostics (`research/piano_difficulty/`) | DEMO-02: present existing overview output; no new factors/weights |
| Difficulty graph, factor checkboxes, average/composite overlay | Static per-factor SVG tracks + JSON/temporal-CSV exports (`output/overview.py`: `render_html`, `write_analysis_outputs`) | DEMO-03: interactive view (checkboxes, overlay); graph-data boundary per DEMO-02 |
| Type measure ranges for passages | Exact selection `select_passage`, `locate_measure_by_number`, `UnresolvableRegion` reason codes (LS-05) | DEMO-04: range form + mapping to exact quarters; show resolution diagnostics |
| Pretend to be a student; log practice/context | `InteractionSession.save_note`, `ContextStore`, `inspect_context` (LS-04/LS-08) | DEMO-06: note/help/ignore/correct/exclude controls; visible log |
| Request help for a selected region | `request_help` → investigation + observations + aid (`HelpResponse` layers) | DEMO-05/07: wire regions in, render the four layers separately |
| User input × automated analysis | `report_refs` framing vs. unchanged score facts (E07/E11) | DEMO-07: side-by-side score-only vs. score-plus-report |
| Non-hotspot user region still works | Manual entry, `difficulty == ()`, no hotspot fabrication (E08/E11, V7) | DEMO-08: scripted non-hotspot scenario |
| Presenter honesty | E12 language scans; `prototype_unvalidated` provenance | DEMO-09: "real vs. simulated" notes; DEMO-10: smoke tests + risk log |

## 3. Architecture guardrails (non-negotiable for the demo)

1. The demo is a **thin presentation harness** over `InteractionSession`,
   the difficulty overview, and existing selectors. It owns no musical
   inference, no scoring, no storage semantics, and no contracts.
2. **Difficulty stays one source of evidence and one visible feature**, not
   the architectural center: analyzer-suggested regions appear as candidates
   with measurements; user-selected regions work with `difficulty == ()`;
   the ranking never overrules a learner report (first-slice S3).
3. All demo outputs are **computed live** from the same tested code paths —
   no canned outputs, no mock aids, no scripted numbers. Role-played
   "student" inputs are the only simulated element, labeled as such.
4. Layer separation from LS-08 is preserved on screen: selected context,
   observations, practice aid, and limitations render as distinct panels.
5. No live MIDI/audio feedback, no real learner data, no network/model calls,
   no new dependencies without lead approval (default: stdlib-only GUI; the
   existing renderer is already dependency-free HTML/SVG).

## 4. Graph-data boundary (input to DEMO-02/DEMO-03)

The demo reads, but never recomputes, the canonical overview payload:

- Per hand view: `series[feature_id]` → `normalized_values`, `raw_values`,
  `units`; `regions[]` → `position`, `measure_numbers`, `start_offset`,
  `end_offset`; `candidate_sections[]` with region + representative window.
- Factor IDs (fixed set of five): attack density, largest pitch transition,
  largest simultaneous hand span, hand timing mismatch, accidental density.
- Overlays: `composite` from the payload as-is; "average" = mean of the
  *checked* normalized factor tracks, computed in the view as a
  presentation-only aggregate and labeled as such — never a new difficulty
  claim, never written back into any result contract.
- Missing values break the line (as the static SVG already does); the demo
  must not interpolate continuity.

## 5. Atomic tasks DEMO-01–DEMO-10

Each task lists owner, dependency, and done-when. All tasks are planning
placeholders until claimed; none authorizes product, data, or scope changes.

### DEMO-01 — Demo scores, fixture policy, walkthrough script skeleton

Owner: demo prep. Depends on: LS-10. Define: 1–2 committed redistributable
scores suitable for graphing (self-authored or canonical `music/` assets with
clear licenses; local-only real scores optional and never committed without a
redistribution license); which LS-05 selection fixtures carry the
learner-context beats; the beat order from section 2. Done when: the score
list, license notes, and script skeleton are recorded here or in an appendix.

### DEMO-02 — Inventory reusable overview/graph outputs; freeze graph-data boundary

Owner: demo prep, with difficulty-component reader. Depends on: DEMO-01.
Verify the section-4 payload fields against actual `write_analysis_outputs`
JSON/CSV on the DEMO-01 scores; record any unavailable factors per score.
Done when: the boundary (payload fields + CSV columns consumed) is pinned in
this document and covered by a boundary test.

### DEMO-03 — Simple difficulty graph view (factor checkboxes, overlay)

Owner: demo UI. Depends on: DEMO-02. Build the smallest local interactive
view: one track per checked factor, candidate-section shading, optional
average/composite overlay, hover or readout with raw value + measure
location. Default to stdlib-only (e.g. tkinter canvas over the DEMO-02
boundary); record the toolkit choice and why. Done when: toggling factors or
the overlay never changes analysis results (view-only; tested).

### DEMO-04 — Measure-range selection form → exact passage selection

Owner: demo UI. Depends on: DEMO-01. Text inputs for measure ranges, mapped
via `locate_measure_by_number` to exact quarters; ambiguous/unknown numbers
surface the existing `UnresolvableRegion` diagnostics verbatim in the UI.
Done when: valid ranges resolve to the same passage IDs as the tested
selector; invalid ranges show diagnostics instead of guesses.

### DEMO-05 — Connect manual + auto-detected regions to `InteractionSession`

Owner: demo wiring. Depends on: DEMO-02, DEMO-04. Both entry routes feed
`request_help`: analyzer-suggested regions as candidates with measurements,
user-typed regions via `manual_investigation` with `difficulty == ()`.
Done when: the same region works with and without a computed profile, and
origin (`USER_SELECTED` vs `ANALYZER_SUGGESTED`) is visible.

### DEMO-06 — Learner-note controls and visible context log

Owner: demo wiring. Depends on: DEMO-05. Controls for save note, request
help, ignore history (`ContextScope.NONE`), correct, exclude/delete, plus an
inspect panel showing entries/permissions/current summaries. Done when: every
LS-09 V-stage is reachable by hand and the log matches `inspect_context`.

### DEMO-07 — Render assistant output layers separately

Owner: demo UI. Depends on: DEMO-05, DEMO-06. Four panels: selected context
(with entry IDs/timestamps), observations (values + source refs), practice
aid (suggestion + objective), limitations/caveats (including the
`prototype_unvalidated` + unproven-effectiveness notices). Include the
score-only vs. score-plus-report comparison view. Done when: a reviewer can
point at which panel every displayed sentence came from.

### DEMO-08 — Scripted non-hotspot scenario

Owner: demo prep. Depends on: DEMO-05, DEMO-07. A fixed scenario on sparse
material (cf. V7/“voices”: `difficulty == ()`, below-threshold limitation)
showing manual help without hotspot fabrication. Done when: the script runs
end to end and the limitation panel carries the outcome, not a diagnosis.

### DEMO-09 — Walkthrough script + “real vs. simulated” presenter notes

Owner: demo prep, with owner. Depends on: DEMO-01–DEMO-08. Full presenter
script with timing, click path, fallback lines for abstention branches, and
an explicit ledger: computed-live vs. role-played elements. Done when: a new
presenter can run the walkthrough without inventing claims.

### DEMO-10 — Smoke tests and demo risk log

Owner: demo QA. Depends on: DEMO-03–DEMO-09. Headless smoke tests (imports,
graph-data boundary validation, scripted `InteractionSession` replay of the
walkthrough); risk log (fixture limits, threshold misreading, hand-label
uncertainty, no edition identity). Done when: smoke tests pass in the
`piano-difficulty` env and risks are recorded here.

## 6. Explicitly deferred (not in the demo milestone)

Live MIDI/audio or microphone feedback; performance assessment or tracking;
new observation families or aids; threshold calibration or validation studies;
automatic fingering/biomechanics; curriculum or practice plans; learner
profiling or trait inference; account/production infrastructure; company-app
integration; real learner data collection; any model/LLM involvement; pending
DC-01–DC-16 difficulty hardening (the demo consumes current overview output
as-is and labels it accordingly).

## 7. What the thesis can currently claim

Only what LS-10 evidences: a bounded, deterministic, inspectable slice in
which a user-selected passage plus optional verbatim reports yields a
traceable text aid or an honest abstention, with learner control over saved
context — on synthetic fixtures, with unproven pedagogical effectiveness, and
pending lead/teacher review. The demo may *show* these properties; it may not
extend them into product, effectiveness, or integration claims.

## 8. Acceptance for this milestone plan

This plan is complete when the DEMO-01–DEMO-10 tasks above have explicit
scope and done criteria (done here), difficulty stays a modular source rather
than the center (section 3), exclusions are listed (section 6), and claims
stay within section 7. Building the demo is separate work and must not start
under LS-11.

## 9. Computed evidence: CEO CIPI walkthrough harness (2026-09-07)

The piano-difficulty side now produces computed walkthrough evidence for the
demo beats in section 2 (load a piece, auto-detected difficulty info,
difficulty graph/timeline):

- Harness: `research/piano_difficulty/tests/harness/ceo_walkthrough/`
  (curated eight-piece manifest, CIPI resolution, existing
  `difficulty_overview` analysis, per-piece notes, reviewer checklist).
- Thin runner:
  `research/piano_difficulty/tests/scripts/run_ceo_cipi_walkthrough.py`
  (`--dry-run` checks local CIPI setup without running analysis).
- Generated artifact index:
  `research/piano_difficulty/tests/artifacts/ceo_walkthrough/cipi_familiar_v1/index.md`
  (with `index.json`, per-piece `analysis.*`, `piece_context.json`, and
  `demo_notes.md`).

Claim bounds carry over unchanged: the harness shows analysis computed from
symbolic scores and relative within-piece profiles only. It does not grade
learners, does not measure learning benefit, and a learner report still
overrules any system ranking in demo framing. Learning-support code consumes
this evidence; it does not parse CIPI directly.
