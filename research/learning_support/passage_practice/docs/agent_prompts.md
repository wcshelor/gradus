# Agent Assignment Prompts

These templates can be copied into coding-agent tasks. Replace bracketed fields
and include only one work package per implementer.

## Implementer prompt

```text
You are implementing [WP-XX — title] in the gradus repository.

Before editing, read:
- repository-root AGENTS.md;
- research/piano_difficulty/AGENTS.md if your work touches that area;
- research/learning_support/passage_practice/AGENTS.md;
- passage_practice/README.md;
- docs/architecture.md;
- docs/contracts.md;
- docs/prototype_v1.md;
- docs/testing_strategy.md; and
- the full WP-XX entry in WORK_PACKAGES.md.

Confirm that every dependency for WP-XX is DONE and inspect its merged code.
Report a short preflight with intended files, contract assumptions, tests, and
possible overlap. Implement only WP-XX. Add its positive, close-negative,
invariant, diagnostic, and compatibility tests in the same change. Preserve
exact time, source provenance, layer boundaries, and input immutability.

If implementation requires changing an accepted decision or cross-layer
contract, stop and add a proposed entry to docs/decisions.md for lead review.
Do not weaken existing tests, add private/copyright-unclear scores, commit ad hoc
run artifacts, modify submodules, or introduce network/LLM requirements.

When finished, create the required `handoffs/WP-XX.md` record with
branch/commit, changed areas, contracts, test commands/results, evidence,
limitations, and newly unblocked packages. Announce readiness for review. Do
not edit live board status from a parallel branch or mark the package DONE.
```

## Reviewer prompt

```text
Independently review [WP-XX — title] against its work-package entry, the local
AGENTS.md, architecture, contracts, prototype specification, testing strategy,
traceability matrix, and current decisions.

Inspect the implementation and tests rather than relying on the handoff. Check
layer ownership, dependency direction, exact timing, ID/source provenance,
staff/voice/hand separation, deterministic serialization, musical correctness,
positive and close-negative cases, unsupported diagnostics, input immutability,
and relevant regression suites.

Run focused tests and inspect representative structured output. Report findings
in priority order with exact file/line references. Distinguish blocking contract
or correctness problems from suggestions. If no blocking finding remains,
record review evidence and recommend that the lead mark the package DONE; do not
mark it DONE yourself.
```

## Review-gate audit prompt

```text
Act as lead architecture reviewer for [G0/G1/G2/G3/G4/G5]. Read the required
packages and demonstrations in docs/review_checkpoints.md. Inspect all code and
tests added since the previous accepted gate.

Trace one representative result across every contract touched by this gate.
Look specifically for duplicate concepts, hidden information loss, provenance
breaks, timing drift, semantic claims in the wrong layer, overly broad
MusicXML support, tests that only assert file existence, and documentation that
describes behavior not implemented.

Run the required focused and regression suites. Produce a gate report using the
template in review_checkpoints.md. List findings before conclusions. State which
known limitations are accepted, which decisions changed, and exactly which work
packages may now move from BLOCKED to READY.
```

## Integration-failure prompt

```text
Diagnose the integration failure between [upstream package/contract] and
[downstream package]. Do not implement a broad fix immediately.

Reproduce the failure with the smallest fixture, identify which documented
contract is violated or underspecified, and determine whether the defect belongs
upstream, downstream, or in orchestration. Add a proposed decision if the
contract is ambiguous. Recommend the smallest owner-scoped fix and the
regression test that should accompany it. Preserve both agents' unrelated work.
```

## Periodic thesis/code alignment prompt

```text
Audit the current passage-practice implementation against
docs/thesis_alignment.md and docs/traceability.md. For each implemented claim,
identify its code owner, tests, fixture evidence, method version, and remaining
research evidence. Flag claims that exceed implementation or evaluation,
implemented behavior absent from the thesis plan, stale decisions, and risks
whose early-warning condition has appeared. Recommend scope corrections and the
next lead review; do not implement new features during this audit.
```
