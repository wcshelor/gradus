# MuseScore PDF Export Diagnostics

**Timestamp:** 20261004_165335
**Out dir:** `/Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/musescore_diagnostics/20261004_165335`
**Binary:** `/opt/homebrew/Caskroom/musescore/4.7.5.260831071,4.7.5/.homebrew-command-wrappers/mscore`
**Timeout:** 20.0s
**Sources:** 1 score(s)
  - `/Users/campshelor/repos/gradus/research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml`

**Total attempts:** 36 (6 variants × 3 cwds × 2 envs × 1 scores)
**Successes:** 15  **Failures:** 21

## Answers

### 1. Does any command variant work?
**Yes** — 15 successes. Best variant: `-R` (83% success rate).

### 2. Are failures global or score-specific?
At least one variant succeeded for every score — failures are variant/cwd/env-specific, not score-specific.

| Score | Total | Success | Rate |
|---|---|---|---|
| debussy_arabesque-no-1.musicxml | 36 | 15 | 42% |

### 3. Are pasteboard/hiservices errors present?
**Yes** — pasteboard hits: 0, hiservices hits: 9 of 36 attempts.
This matches the observed macOS error: `PasteBoard: Error creating pasteboard` and `Connection Invalid for com.apple.hiservices-xpcservice` with return code -6.
Other markers: unsupported_option=12, crash_abort=9, timeout=0, missing_output=21.

### 4. Which binary/path was used?
**Resolved binary:** `/opt/homebrew/Caskroom/musescore/4.7.5.260831071,4.7.5/.homebrew-command-wrappers/mscore`
Checked via `tests.harness.oktav_dataset.pdf_export.resolve_musescore_binary` plus PATH/app bundles.

### 5. Recommended next action
At least one variant works (-R with 83% success). Pin OMR pipeline to the best variant (-R) and prefer cwd=repo_root or score_parent with inherited env. Avoid variants with unsupported_option (12 hits) — MuseScore 4 removed -s/-w.

## Per-variant success

| Variant | Total | Success | Rate |
|---|---|---|---|
| `plain` | 6 | 2 | 33% |
| `-f` | 6 | 4 | 67% |
| `-R` | 6 | 5 | 83% |
| `-R -f` | 6 | 4 | 67% |
| `-R -s -w` | 6 | 0 | 0% |
| `-R -s -w -f` | 6 | 0 | 0% |

## Per-cwd success

| CWD | Total | Success | Rate |
|---|---|---|---|
| repo_root | 12 | 5 | 42% |
| score_parent | 12 | 6 | 50% |
| output_dir | 12 | 4 | 33% |

## Per-env success

| Env | Total | Success | Rate |
|---|---|---|---|
| inherited | 18 | 10 | 56% |
| minimal | 18 | 5 | 28% |

## Failure categories
| Category | Count |
|---|---|
| success | 15 |
| unsupported_option | 12 |
| crash_abort | 9 |

## Evidence
- `attempts.csv` — one row per attempt with argv/cwd/env/returncode/duration/pdf/markers
- `diagnostic_summary.json` — machine-readable summary
- `logs/<attempt_id>.json` + `.stdout.txt`/`.stderr.txt` — per-attempt evidence
- `pdfs/` — per-attempt PDF outputs (valid ones start with %PDF)

### Pasteboard/hiservices samples (first 3)
- `attempt_0000` variant=`plain` cwd=`repo_root` env=`inherited` rc=`-6` — stderr: `/Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/musescore_diagnostics/20261004_165335/logs/attempt_0000.stderr.txt`
- `attempt_0001` variant=`plain` cwd=`repo_root` env=`minimal` rc=`-6` — stderr: `/Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/musescore_diagnostics/20261004_165335/logs/attempt_0001.stderr.txt`
- `attempt_0003` variant=`plain` cwd=`score_parent` env=`minimal` rc=`-6` — stderr: `/Users/campshelor/repos/gradus/research/piano_difficulty/tests/artifacts/omr_pipeline/musescore_diagnostics/20261004_165335/logs/attempt_0003.stderr.txt`

---
_This harness is test-scoped and does not change runtime difficulty extraction._
