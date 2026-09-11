# S0.3 — CIPI walkthrough outputs mapped to semantic inputs

Status: handoff note only. No runtime changes; no CIPI data required in
committed tests (per task limit). All CIPI score files stay outside the repo;
only manifests and generated reports are committed.

Sources inspected (code paths relative to `research/piano_difficulty/`):

- `tests/harness/cipi_dataset/README.md`, `catalog.py`, `python_analysis.py`
  — movement-manifest catalog (744 movement rows) and repo-native runtime
  export lane.
- `tests/harness/ceo_walkthrough/{README,manifest.py,cipi_selection.py,runner.py,artifacts.py,reports.py}.md`
  — curated 8-piece walkthrough (`evaluation_scores/manifests/ceo_walkthrough/cipi_familiar_v1.csv`)
  resolved against the canonical movement manifest
  (`evaluation_scores/manifests/cipi/cipi_movement_manifest.csv`).
- `src/piano_difficulty/pipeline.py` (`extract_score`, `analyze_score`),
  `difficulty_analysis/overview.py` (`difficulty_overview` profile,
  `OverviewOptions`), `difficulty_analysis/sections.py`
  (`consolidate_sections`), `output/overview.py`
  (`write_analysis_outputs`), `output/json_export.py` (`score_payload.v1`).
- `tests/harness/shared/{dataset_records.py,runtime_matrix_export.py}` —
  matrix-export lane (`cipi_labeled_feature_matrix.csv`,
  `corpus_summary.json`, `piece_json/`, `errors.csv`, `load_report.json`).
- Plan §"CIPI testing relationship" (note format) and S0.2
  (`docs/semantic_feature_evidence_inventory.md`) for feature/trace context.

Verified local state: committed walkthrough artifacts under
`tests/artifacts/ceo_walkthrough/cipi_familiar_v1/` currently contain only
`piece_context.json` + `demo_notes.md` with status `missing_source_file`
(no local CIPI root here; `failures.csv` lists all 8 pieces blocked). No
`analysis.json` is committed, so every payload field below is cited from
writer code, not from a sample run.

## What each CIPI run can hand to a passage semantic analyzer

| S0.3 requested input | Providing artifact (lane) | Exact fields | Notes for the semantic consumer |
|---|---|---|---|
| Score path | Walkthrough `piece_context.json` → `resolution.{source_path,dataset_root,root_source}`; matrix lane `source_path` metadata; payload `score.source.path` | `dataset_relative_path` (manifest, `pieces/`-prefixed, portable) resolved under a local root (`--dataset-root`, `GRADUS_CIPI_ROOT`, `.local/datasets.toml`); `piece_uid` (movement-unique), `cipi_id` (work-level, repeats) | Score identity for `Passage.score_id` and `DifficultyEvidence.source_score_id`. Raw files are never committed; a semantic run re-resolves the same manifest row against its own local root. `henle` is a work-level inherited label, not a system measurement |
| Selected region | Walkthrough `analysis.json` → `analysis_profiles[difficulty_overview].candidate_sections[]` | Per section: `section_id`, `rank`, `region{measure_start/end, measure_numbers[], start_offset/end_offset (quarter strings), window_index, hand, label}`, `representative_region`, `supporting_window_indices[]`, `supporting_peak_ids[]`, `method: overlapping_or_touching_peaks.v1` | Measure-granular window union (overlapping/touching peaks merged). Offsets serialize Fractions as strings, so exact rational bounds are recoverable. This is the analyzer-suggested entry region; the semantic side still builds its own exact `[start, end)` passage over `ScoreIR` and treats the hotspot region as suggestion context, never as passage identity (D-013) |
| Difficulty score | Same `candidate_sections[]` → `score`; profile `factors[]` → `profile_contribution`, `piece_value`, `local_min/max` | `score` = normalized composite at the representative window (relative within this piece only); `profile_contribution` = mean within-piece normalized value × weight; `rank` orders sections | **Not a calibrated grade.** Interpretation string is fixed: "Relative score demands within this piece; no calibrated difficulty grade." Semantic detectors may use it to prioritize regions, never as ground-truth difficulty or a learner claim. `henle` may travel as corpus metadata, never as a system score |
| Contributing dimensions | `candidate_sections[].{supporting_factor_ids[], contributions[]}` + `contribution_scope: representative_window`; profile `factors[]` ranking + `factor_peaks[]`/`composite_peaks[]` | Per contribution: raw/normalized/smoothed values, attribution/weight/share, rank, `is_peak_support` (`FeatureContribution.to_payload`); factor IDs are the 5 promoted overview factors (see S0.2) | Contributions describe the **representative window, not the union** (`contribution_scope` says so). `supporting_peak_ids` keep every merged window inspectable. A semantic analyzer maps `supporting_factor_ids` to detector prioritization (e.g. leap-driven section → leap/relocation observations first) |
| Available features | `analysis.json` → `features[]` (full `extract_all` record list), `series` per factor (raw/normalized/smoothed per window + `units`), `analysis.csv` rows (`hand, feature_id, window_index, measure_numbers, start/end offsets, values`) | Piece-level `FeatureRecord`s (see S0.2 table) plus windowed recomputation per `ScoreRegion` in the overview `series`; `region_evidence[]` per window: `{window_index, written_note_ids[], logical_note_ids[], source_note_ids[], scope: region_input_events}` | `region_evidence` is the **closest thing a CIPI run gives to event-level trace**: concrete note-ID lists per window, resolvable against the same `ScoreIR`. Hard limits (stated in the profile's own diagnostics): attack selection omits sustains entering a window; IDs identify region inputs, **not** causal/event-level attribution; hand labels are conservative staff-based inference; constant factors have no local peak |
| Exported evidence (envelope) | Walkthrough per-piece: `analysis.{json,md,html,csv}`, `piece_context.json`, `demo_notes.md`; top-level `index.{json,md}`, `failures.csv`. Matrix lane per run: `cipi_labeled_feature_matrix.csv`, `corpus_summary.json`, `piece_json/<index>__<piece_uid>.json`, `errors.csv`, `load_report.json` | `piece_context.json` audits demo row → CIPI row → resolved path → artifact paths → runtime versions → `top_section` summary; `demo_notes.md` frames analyzer-led vs user-selected vs disagreement + caveats; matrix rows carry `piece_uid/title/composer/filename/paths + henle/difficulty_numeric/overallDifficulty` labels | The semantic analyzer needs at most: one `analysis.json` (+ its `piece_context.json` for provenance) **or** one matrix `piece_json` + matrix row. Everything else is presentation (`md/html/csv`) or batch bookkeeping (`index`, `errors`, `load_report`, `failures`). Reruns overwrite per-piece dirs in place (CEO-CIPI-19); `--fresh-run-dir` isolates timestamped runs |

## Minimal handoff shape (fields, not a new contract)

A CIPI run hands over, per selected piece:

```text
score identity: piece_uid + dataset_relative_path + resolved source_path
region:         candidate_sections[i].{rank, region, representative_region,
                supporting_window_indices, supporting_peak_ids}
score:          candidate_sections[i].score (within-piece relative composite)
dimensions:     supporting_factor_ids + contributions[] (representative window)
features:       features[] + series{raw, normalized, smoothed, units} + analysis.csv
event refs:     region_evidence[window].{written_note_ids, logical_note_ids,
                source_note_ids}  (region inputs, not attribution)
provenance:     piece_context.json {manifest row, cipi match, resolution,
                runtime versions, timestamp} + profile methods + warnings
labels:         henle (work-level, inherited), demo framing notes (review only)
```

Entry into passage practice follows the existing D-013 boundary: an
analyzer-suggested `PassageInvestigation` whose `difficulty` collection
carries validated `DifficultyEvidence` (source score, covered region,
method, feature/evidence refs; `hotspot_id`/`window_score`/contributions
only from a real analyzer result — overview `section_id`s are section IDs,
not hotspot IDs, and must not be relabeled). Enrichment never changes
selection origin or passage identity; unavailable values stay unavailable.
The controlled user-selected twin (same passage, empty difficulty context)
remains the required test path, so no committed semantic test may depend on
a CIPI run existing.

## Gaps a CIPI run does not fill (for S0.5)

- No per-note observations, no aggregation rules, no attribution records —
  `region_evidence` lists window inputs; the section-to-event link is still
  unbuilt (WP-04/WP-06 work).
- No semantic labels of any kind (melody/bass/accompaniment/texture/phrase/
  harmony) and no learner data — the plan's note-format rows
  "Human-observed semantics" through "Possible exercise/advice action" can
  only be filled by manual review (see S-X5 worksheet), never mined from
  these artifacts.
- `demo_notes.md` framing (`analyzer_led_note`, `user_selected_note`,
  `disagreement_note`) is review prose, not evidence; it must not enter any
  observation or diagnosis payload.
- Coverage: 8 curated walkthrough pieces vs 744 movement rows — the
  walkthrough is a demo surface, the matrix lane is the corpus surface;
  neither is a fixed test fixture.

## What S0.3 does not claim

- No new contract, no detector prioritization rule, and no review worksheet
  (worksheet is S-X5, separately scoped with the same no-CIPI-in-tests limit).
- No CIPI score material, labels beyond field names, or run outputs are
  committed here; the blocked local run state is reported as-is, not repaired.
- No judgement on which sections *should* have been selected; rank
  interpretation is quoted from the profile verbatim.

## Next task

S0.3 is the third of four S0 inventories. Remaining before the S0.5
readiness matrix: **S0.4 (duplicate-parsing risks)**. S0.5 stays blocked
until S0.4 exists. S1.1 (S-Q001 decision) remains behind S0.5.
