# Literature tags

Tags are small, composable descriptors used to filter papers across themes.
The controlled tag registry lives on the `Tags` sheet of
`../bibliography/library.xlsx`.

## Syntax

Tags use a dimension and value:

```text
dimension:value
```

Examples:

```text
topic:practice-strategy
method:qualitative
evidence:learner-study
population:intermediate
input:symbolic-score
output:exercise
ai:hybrid
relevance:core
```

Enter multiple tags in the catalog as semicolon-separated IDs:

```text
topic:practice-strategy; evidence:learner-study; population:intermediate
```

## Dimensions

- `topic:` — what the paper is about;
- `method:` — how the work was conducted;
- `evidence:` — what kind of evidence supports it;
- `population:` — who was studied or addressed;
- `context:` — the musical or learning context;
- `input:` — information used by a system;
- `output:` — assistance or result produced;
- `ai:` — the role played by an AI technique;
- `relevance:` — why the paper matters to this thesis;
- `quality:` — publication or review status.

Use the dedicated catalog fields for major sortable facts such as primary
theme, reading status, and priority. Tags are for overlapping descriptors, not
for hiding all metadata in one cell.

## Adding tags

Before inventing a tag:

1. Search the registry for an existing equivalent.
2. Prefer a reusable concept over a paper-specific phrase.
3. Choose the correct dimension.
4. Add a short definition and example.
5. Avoid encoding an evaluative judgment unless the dimension explicitly calls
   for it.

Free-form keywords can go in `remarks` while a possible controlled tag is being
tested.

