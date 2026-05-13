"""Top-level package for the piano difficulty descriptor extractor.

The package is organized around a stable pipeline:

1. load score data,
2. normalize parser output into a parser-independent IR,
3. build reusable analysis views,
4. extract direct descriptors,
5. aggregate and export results.

The current repository state is partially implemented. The IR contracts and the
MusicXML / MXL loading boundary are in place, while normalization, extraction,
aggregation, and CLI execution are still under active development.
"""

from .pipeline import extract_score

__all__ = ["extract_score"]
