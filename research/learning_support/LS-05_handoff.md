# LS-05 review handoff — user-selected regions independent of difficulty

Date: 2026-09-05. Implementer: muse-spark. Working tree; nothing committed.
Depends on LS-02, LS-03 (done). Required and built first: WP-02 T02.2–T02.6
(selection API); WP-02 handoff records that increment.

## Outcome

- Exact regions resolve to source events via `select_passage` over ScoreIR
  (WP-02); the LS-05 adapter (`passages/investigate.py`) builds
  `PassageInvestigation` envelopes with `USER_SELECTED` origin and no
  difficulty computation (import-delta test guards the boundary).
- Selection, reported concern (`reported_concern` diagnostic context, opaque
  IDs — this layer must not import learner contracts), and measured
  difficulty (validated `difficulty` collection) occupy distinct fields.
- Whole-piece requests resolve to the full measure span with an explicit
  `whole_piece` diagnostic. Unresolvable locations raise `UnresolvableRegion`
  with reason codes (`empty_interval`, `out_of_range`, `no_measures`,
  `unknown_measure`, `ambiguous_measure`, `outside_parent`) — never guessed.
- Analyzer-suggested route preserved as the other entry with no
  nonzero-score gate: empty difficulty and zero window scores are valid.
  The T05.2 `HotspotInvestigation` translation itself is explicitly pending.

## Changed files

- `passage_practice/src/passage_practice/passages/{__init__,selection,investigate}.py`
  (new); `models/` and `piano_difficulty` untouched.
- `tests/fixtures/selection_{two_staff,ties,two_voices}.musicxml`,
  `tests/fixtures/manifest.md` (new synthetic).
- `tests/unit/test_selection.py` (18 tests), `test_user_selected_entry.py`
  (7 tests).
- `docs/decisions.md` (D-014 proposed), `docs/entry_points.md` (status),
  `handoffs/WP-02.md` (T02.2–T02.6 increment), plan log (LS-05 row).

## Commands and results (repo root, `piano-difficulty` env)

- New suites: 18 + 7 passed.
- Full: `conda run -n piano-difficulty python -m pytest -q` →
  **302 passed, 7 skipped** (skips unchanged: optional local-corpus fixtures).
- `git diff --check` clean. Four test-side mistakes fixed (fixture path,
  two half-open arithmetic slips, suite-order-dependent import assertion);
  no behavior weakened, no snapshots touched.

## Acceptance mapping (LS-05 "done when")

- Low-ranked/user-selected passage, no profile: sparse-fixture test + delta.
- Suggested hotspot without gate: analyzer empty/zero-difficulty tests.
- Invalid/ambiguous without fabrication: `UnresolvableRegion` tests.

## Limitations and remaining dependencies

- Rests are declared selection omissions (views/export revisit).
- Concern references are opaque strings until LS-07 result assembly.
- D-014 needs lead review; T05.2 translation, WP-03 views, and G1 exit remain
  pending. No WP gate released. Next: LS-06 (bounded semantic observation).
