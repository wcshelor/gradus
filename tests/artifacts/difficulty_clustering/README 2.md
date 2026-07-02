# Difficulty Clustering Artifacts

This directory holds generated evidence only.

Current active clustering evidence is organized by dataset:

- `oktav/`: Oktav clustering runs
  - `20260630T111225Z__oktav-sebastien-9features-k3/`: the current 9-feature
    Sebastien-style Oktav run
- `cipi/`: CIPI clustering runs
  - `20260630T111225Z__cipi-sebastien-9features-k3/`: the current 9-feature
    Sebastien-style CIPI run

Sweep outputs, when generated, live under the matching dataset root and then
inside a `sweeps/` subdirectory for the parent sweep run.

Keep new runs under the matching dataset root so Oktav and CIPI outputs do not
get mixed together.
