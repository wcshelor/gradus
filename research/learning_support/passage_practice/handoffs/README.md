# Work-Package Handoffs

Each completed implementation package creates one file named `WP-XX.md`. Unique
files let parallel branches merge review evidence without repeatedly conflicting
in the central status table.

Use this template:

```text
# WP-XX — Package title

Status requested: REVIEW
Date:
Implementer task/agent:
Branch:
Commits:
Starting gate commit:

## Outcome

## Changed areas by architectural layer

## Contracts added or changed

## Tests run and results

## Representative evidence

## Unsupported and ambiguous cases

## Known limitations

## Decisions added or requested

## Compatibility or migration consequences

## Packages eligible to unblock after review
```

Do not paste long logs or large generated payloads into handoffs. Link to a
small committed artifact or summarize the relevant assertions. The lead may add
a final review section to the same file after integration.
