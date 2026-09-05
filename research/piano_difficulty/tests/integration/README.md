# Integration Tests

This directory holds end-to-end tests that:

- load a real fixture score,
- normalize the score,
- run selected extractor families,
- verify the exported JSON structure and diagnostics.

The normal analysis tests also cover readable reports, HTML/CSV outputs,
explicit legacy profile selection, partial batch failures, and output-name
collisions. Dynamics and piece-lab tests exercise the research wrappers over
the promoted runtime implementation.
