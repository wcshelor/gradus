# ScoreAnalyzer Harness

This lane holds the shared executor for the Sebastien `ScoreAnalyzer` repo.

Use it for:

- staging one score at a time into the PHP repo's `pieces/` tree
- enforcing a default 15-second timeout per piece
- capturing per-piece stdout, stderr, and raw JSON
- writing flat export matrices for downstream Oktav and CIPI runs

Do not move the runtime Python analysis into this directory. This lane is only
for the external PHP repository integration and its batch evidence.
