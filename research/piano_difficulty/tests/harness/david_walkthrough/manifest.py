"""Curated-manifest schema and loader for the David CIPI walkthrough.

One-row-per-piece CSV loading with deterministic records, stable-ID safety
checks, and scenario-note requirements. No analysis or filesystem access
beyond reading the manifest CSV itself.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS: tuple[str, ...] = (
    "demo_id",
    "composer",
    "title",
    "henle",
    "dataset_relative_path",
    "recognition_tier",
    "demo_role",
    "analyzer_led_note",
    "user_selected_note",
    "disagreement_note",
    "caveat_note",
)

# Lowercase slug style so output directories cannot collide or escape the
# artifact root (David-CIPI-05).
DEMO_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

# At least one product-framing note plus an explicit caveat (David-CIPI-20).
SCENARIO_NOTE_COLUMNS: tuple[str, ...] = (
    "analyzer_led_note",
    "user_selected_note",
    "disagreement_note",
)


@dataclass(frozen=True, slots=True)
class DavidWalkthroughEntry:
    demo_id: str
    composer: str
    title: str
    henle: str
    dataset_relative_path: str
    recognition_tier: str
    demo_role: str
    analyzer_led_note: str
    user_selected_note: str
    disagreement_note: str
    caveat_note: str
    metadata: dict[str, str] = field(default_factory=dict)
    source_row_index: int = 0


def validate_demo_id(demo_id: str, *, source: str = "<manifest>") -> str:
    """Return the trimmed ID or raise if it is blank or unsafe."""
    cleaned = str(demo_id or "").strip()
    if not cleaned:
        raise ValueError(f"Invalid demo_id in {source}: blank values are rejected.")
    if not DEMO_ID_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid demo_id {cleaned!r} in {source}: use lowercase slug style "
            "(letters, digits, single underscores; e.g. 'mozart_k545')."
        )
    return cleaned


def load_manifest(path: str | Path) -> list[DavidWalkthroughEntry]:
    """Load and validate the curated walkthrough manifest in file order."""
    manifest_path = Path(path).expanduser()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"David walkthrough manifest not found: {manifest_path}")
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            raise ValueError(
                f"David walkthrough manifest {manifest_path} is missing required "
                f"columns: {', '.join(missing)}."
            )
        raw_rows = list(reader)

    if not raw_rows:
        raise ValueError(f"David walkthrough manifest {manifest_path} contains no rows.")

    entries: list[DavidWalkthroughEntry] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_rows):
        cleaned = {key: str(value or "").strip() for key, value in raw.items() if key is not None}
        demo_id = validate_demo_id(cleaned.get("demo_id", ""), source=str(manifest_path))
        if demo_id in seen:
            raise ValueError(
                f"Duplicate demo_id {demo_id!r} in {manifest_path}: "
                "demo_id values must be unique and stable."
            )
        seen.add(demo_id)
        dataset_relative_path = cleaned.get("dataset_relative_path", "")
        if not dataset_relative_path:
            raise ValueError(
                f"Row {demo_id!r} in {manifest_path} has a blank dataset_relative_path."
            )
        if not any(cleaned.get(column, "") for column in SCENARIO_NOTE_COLUMNS):
            raise ValueError(
                f"Row {demo_id!r} in {manifest_path} has no scenario note: fill at "
                f"least one of {', '.join(SCENARIO_NOTE_COLUMNS)}."
            )
        if not cleaned.get("caveat_note", ""):
            raise ValueError(
                f"Row {demo_id!r} in {manifest_path} has a blank caveat_note: every "
                "walkthrough row needs an explicit interpretation boundary."
            )
        extra = {
            key: value
            for key, value in cleaned.items()
            if key not in REQUIRED_COLUMNS and value != ""
        }
        entries.append(
            DavidWalkthroughEntry(
                **{column: cleaned.get(column, "") for column in REQUIRED_COLUMNS},  # type: ignore[arg-type]
                metadata=extra,
                source_row_index=index,
            )
        )
    return entries
