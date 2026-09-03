# Agent Workflow

## Purpose

This workflow lets multiple coding agents make progress without making the
architecture or Git history dependent on their private assumptions.

The work-package board is the source of truth for implementation order. This
document describes how agents claim and hand off those packages.

## Roles

An agent may hold one role for one package:

- **Implementer**: owns the package changes and tests.
- **Reviewer**: independently checks contracts, musical meaning, tests, and
  boundaries; does not merely rerun the implementer's commands.
- **Integrator**: resolves reviewed cross-package API changes at a review gate.
- **Lead**: approves decisions, marks packages `DONE`, and releases downstream
  work.

The implementer and reviewer should be different agents for contracts,
transformations, MusicXML writing, and end-to-end integration.

## How agents divide work

1. Inspect the board for `READY` packages.
2. Select one whose files do not overlap another claimed package.
3. Announce the claim to the coordinator. The lead changes the integration
   branch board to `CLAIMED`.
4. Re-read dependencies and inspect their merged implementations.
5. Write a short implementation note or test list before editing runtime code.
6. Work only within the package scope.
7. Add the package's unique handoff file and announce readiness for review. The
   lead changes the integration branch board to `REVIEW`.
8. A reviewer records findings or approval.
9. The lead marks it `DONE` and releases dependent packages.

If several agents start simultaneously, claims must be acknowledged by the
coordinator before editing. One package has exactly one implementer at a time.

## Git and worktree model

Preferred model:

- Start from the reviewed baseline or latest passed review-gate commit.
- Give each package its own worktree and branch.
- Use branch names such as `codex/pp-wp-03-derived-views`.
- Do not switch branches inside a directory shared by another active agent.
- Keep commits narrow enough to separate generic piano-difficulty changes from
  passage-practice changes.
- Do not include unrelated staged changes from the umbrella repository.
- Do not update submodule commits unless the selected work package explicitly
  requires it and the lead approves the dependency change.
- Do not edit the board's live status from a parallel package branch. Add the
  package-specific handoff file instead.

Suggested commit structure for cross-area packages:

```text
1. Add additive generic contract/support in piano_difficulty
2. Add passage_practice consumer and focused tests
3. Add documentation/handoff update
```

Avoid merge commits inside package branches unless needed to refresh a long
running branch at a lead-approved gate.

## Preflight checklist

Before implementation, the agent reports:

- package ID and dependency status;
- files or areas likely to change;
- contract assumptions being used;
- tests it intends to add;
- known overlap with other packages; and
- unresolved decision requiring lead input, if any.

If an assumption changes the cross-layer contract, the agent records a proposed
decision before coding past it.

## Implementation loop

Use a narrow loop:

1. Add the smallest positive test describing intended behavior.
2. Add a close negative or ambiguous test.
3. Implement the contract minimally.
4. Add invariant and diagnostic tests.
5. Run the smallest relevant test set.
6. Run dependency and regression tests named by the package.
7. Inspect serialized evidence where applicable.
8. Update docs only for behavior actually implemented.

Agents should avoid creating empty future modules or placeholder APIs for
unclaimed packages.

## Handoff requirements

The implementer creates `handoffs/WP-XX.md` and provides:

- concise outcome;
- branch and commit identifiers;
- changed files grouped by layer;
- contracts added or changed;
- test commands and results;
- representative evidence artifact;
- unsupported cases and diagnostics;
- decisions made or still open;
- migration or compatibility consequences; and
- packages newly eligible to become `READY`.

Generated evidence must be small and intentional. Long logs stay outside Git.

## Reviewer checklist

The reviewer checks:

### Architecture

- Does the implementation belong in this layer?
- Does dependency direction remain intact?
- Did generic code leak pedagogical concepts?
- Were staff, voice, hand, and role kept distinct?
- Is optional LLM behavior outside deterministic core logic?

### Contracts

- Are identity, exact time, units, source references, method version, and
  diagnostics complete?
- Is serialization deterministic?
- Are schema changes additive or properly versioned?
- Can a downstream agent use the result without private implementation
  knowledge?

### Musical correctness

- Do test fixtures actually express the stated construct?
- Are chord, tie, voice, and boundary semantics correct?
- Are pattern labels supported by evidence?
- Does a transformation preserve its promised properties?

### Tests

- Is there a close negative case?
- Are invariants asserted rather than only output existence?
- Does the relevant older suite pass?
- Could a snapshot hide a wrong calculation?
- Are optional external tools clearly separated?

### Research integrity

- Are score-derived facts distinguished from learner claims?
- Are pedagogical claims provenance-labeled?
- Are confidence and limitations visible?
- Is all fixture material safe to commit?

The reviewer records actionable findings with file and line references. A
package returns to `CHANGES` until significant findings are resolved.

## Manager review cadence

The lead performs a broader codebase read at gates G1 through G5 rather than
waiting for the final pipeline. See `review_checkpoints.md`.

In addition, trigger an unscheduled review when:

- a contract changes after two consumers exist;
- more than one work package modifies `ScoreIR`;
- a transformation introduces a new boundary policy;
- a detector's threshold is tuned using repertoire data;
- a new dependency or external service is proposed;
- a generated artifact cannot reopen reliably; or
- an agent proposes moving material to `research/shared/`.

## Conflict protocol

When two branches need the same contract:

1. Pause the downstream package.
2. Choose one owner for the contract change.
3. Record the decision and add contract tests.
4. Merge and pass the relevant gate.
5. Rebase or recreate downstream work from the accepted contract.

Do not maintain subtly different duplicate models to avoid coordination.

## Stop conditions

An agent must stop and request lead review if:

- required source identity cannot be preserved;
- exact timing would be replaced by floating-point canonical time;
- a MusicXML construct must be silently discarded;
- a rule needs a pedagogical assertion without provenance status;
- a test requires copyrighted or private material;
- success would depend on network or LLM output;
- implementation materially expands the v1 supported subset; or
- passing the package would require weakening an existing regression test.

## Completion is not deployment

`DONE` means the work package meets its software and contract criteria. It does
not mean a diagnosis or exercise has been pedagogically validated. Research
validation is reported separately.
