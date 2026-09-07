"""CEO CIPI walkthrough harness: curated demo evidence over existing analysis."""

from .artifacts import clean_planned_outputs, piece_artifact_paths, piece_dir, top_level_paths
from .cipi_selection import match_entry, plan_batch, resolve_dataset_root_for_ceo
from .manifest import CeoWalkthroughEntry, load_manifest
from .reports import (
    write_demo_notes,
    write_failures_csv,
    write_index_json,
    write_index_markdown,
    write_piece_context,
)
from .runner import analyze_single_piece, run_batch, run_walkthrough

__all__ = [
    "CeoWalkthroughEntry",
    "analyze_single_piece",
    "clean_planned_outputs",
    "load_manifest",
    "match_entry",
    "piece_artifact_paths",
    "piece_dir",
    "plan_batch",
    "resolve_dataset_root_for_ceo",
    "run_batch",
    "run_walkthrough",
    "top_level_paths",
    "write_demo_notes",
    "write_failures_csv",
    "write_index_json",
    "write_index_markdown",
    "write_piece_context",
]
