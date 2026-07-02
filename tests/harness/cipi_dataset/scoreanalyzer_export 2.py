from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.cipi_dataset.catalog import (
    DEFAULT_CATALOG_CSV,
    REPO_ROOT,
    load_catalog_dataframe,
    resolve_score_path,
)
from tests.harness.scoreanalyzer.scoreanalyzer_export import (
    DEFAULT_TIMEOUT_SECONDS,
    ExportInput,
    default_scoreanalyzer_root,
    run_scoreanalyzer_export,
)

DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "retired" / "cipi_og_export" / "full_cipi_run"


def build_export_inputs(
    *,
    catalog_csv: str | Path = DEFAULT_CATALOG_CSV,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    repo_root: str | Path | None = REPO_ROOT,
) -> list[ExportInput]:
    frame = load_catalog_dataframe(catalog_csv)
    inputs: list[ExportInput] = []
    for row_index, record in frame.fillna("").to_dict(orient="records").__iter__().__next__():
        pass

