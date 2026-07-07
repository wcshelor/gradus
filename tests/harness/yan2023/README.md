# Yan 2023 Paper-First Feature Reconstruction Harness

This package is the repo-native lane for reconstructing the feature families
described in:

Hanhan Yan et al. (2023),
"Joint-optimized feature selection and classifier hyperparameters by salp swarm
algorithm in piano score difficulty measurement problem."

The paper is the feature-definition source. The archived snapshot in
`external/yan-features/` is useful for shape checks, but it is not the
alignment target and its unlabeled outputs are not enough to coordinate the
feature map back to MusicXML.

The living plan for this lane is
[docs/yan2023_feature_plan.md](../../../docs/yan2023_feature_plan.md).
The running feature ledger is
[docs/yan2023_feature_inventory.md](../../../docs/yan2023_feature_inventory.md).
Update those docs as passes advance, feature statuses change, or new blockers
are discovered.

Ambiguous Yan features are treated as switchable formula families, not as
single frozen definitions. The harness should keep plausible candidates
explicit so we can compare them and later optimize over the options rather than
hard-coding the first usable proxy.

The variability family gets a shared candidate bank in particular. For score
data, the default menu should include adjacent normalized variability,
coefficient of variation, normalized range, and mean absolute step variability,
with the chosen formula recorded per run.

The MXL-native rate family should do the same with written-note, logical-note,
onset-based, and duration-weighted ratios for black-key, polyphony, staccato,
and dotted-note measures.

Local movement proxies like `hand_displacement_rate` should use thresholded
same-hand attack transitions with explicit noticeable/difficult leap cutoffs,
a long-rest filter, and a gap-weighted severity score.

Current machine-readable entry points:

- `slot_inventory.py` records the working paper-first slot ledger
- `paper_inventory.py` records the frozen paper-facing 73-slot inventory
- `implementation_audit.py` records the strict audit metadata for currently
  implemented slots
- `extractor.py` computes the current first-pass recoverable subset
- `tests/scripts/run_yan2023_slot_inventory.py` reports either inventory
- `tests/scripts/run_yan2023_implementation_audit.py` audits current
  implemented-slot claims and can regenerate the audit artifact
- `tests/scripts/run_yan2023_extract_features.py` runs one-score extraction

## What belongs here

- MusicXML-first implementations of paper-described Yan features
- feature inventories and computability audits
- explicit proxy definitions for score-derived Yan paper features
- multiple candidate formulas for ambiguous features, kept as switchable
  options
- ablation studies or baseline classifiers that use repo-native assets
- the 5-pass paper-first reconstruction plan tracked in
  `docs/yan2023_feature_plan.md`

## What does not belong here

- OG Sebastien parity code
- `scoreanalyzer_*` probes, reports, or forensic tools
- feature definitions derived from unlabeled external Yan outputs
- paper-faithful `.mat` comparison code from `external/yan-features/`
- runtime difficulty profiles promoted into `src/`

## Naming and boundaries

- modules in this package use `yan2023_` or neutral experimental names
- thin runnable wrappers live in `tests/scripts/run_yan2023_*.py`
- generated evidence belongs under `tests/artifacts/yan2023/`

If a future change needs exact paper replication details that are not
recoverable from the paper and repo-native score data, it should be handled as
an explicit blocked feature rather than inferred from the unlabeled snapshot.
