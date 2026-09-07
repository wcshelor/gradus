# Local dataset configuration

This directory holds machine-specific dataset configuration that is never
committed. Copy `datasets.example.toml` to `datasets.toml` and point it at
your local corpus roots.

- `oktav.root`: flat Oktav score folder (`.xml`, `.musicxml`, `.mxl`).
- `cipi.root`: CIPI dataset root containing `metadata/` and `pieces/`.

Environment variables (`GRADUS_OKTAV_ROOT`, `GRADUS_CIPI_ROOT`,
`GRADUS_DATASETS_CONFIG`) override this file. Explicit CLI flags override
everything.
