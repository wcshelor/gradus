# Literature

This directory is the thesis-wide home for papers, books, chapters, standards,
and other research sources.

## Structure

- `reading_lists/` contains curated lists organized by topic, question, or
  stage of the thesis.
- `themes/` defines broad lenses for searching and synthesis.
- `tags/` documents the small controlled descriptors used across themes.
- `inbox/` documents the intake and triage process for newly found sources.
- `bibliography/` contains the tagged library workbook and citation records.
- `notes/` contains original summaries, critiques, connections, and synthesis.
- `papers/` stores local copies of papers when licensing permits. Paper files
  are ignored by Git by default.
- `templates/` contains lightweight templates for adding sources consistently.

## Suggested workflow

1. Capture a source on the `Sources` sheet of `bibliography/library.xlsx` and,
   when useful, add a citation to `bibliography/references.bib`.
2. Place a legally obtained local copy under `papers/`, using a topic folder if
   the collection becomes large.
3. Assign a primary theme, optional secondary themes, and supported tags.
4. Add the source to one or more files in `reading_lists/`.
5. Create a note from `templates/paper_note.md` when the source deserves close
   reading.
6. Put cross-paper conclusions in synthesis notes rather than repeating them in
   every paper note.

## File naming

Use a stable, readable identifier where possible:

```text
author-year-short-title.pdf
author-year-short-title.md
```

The PDF and its note may share the same stem, but notes should not depend on the
PDF being present. Record a DOI, URL, ISBN, or other stable identifier in the
catalog whenever one exists.

## Copyright and access

Do not commit papers unless their license explicitly permits redistribution.
The default is to commit metadata and original notes while keeping downloaded
files local. Company-confidential sources and participant-related material do
not belong here.
