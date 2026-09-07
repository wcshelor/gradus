"""Passage selection and investigation entry points (WP-02, LS-05)."""

from .investigate import (
    MANUAL_METHOD_ID,
    MANUAL_METHOD_VERSION,
    WHOLE_PIECE_METHOD_ID,
    manual_investigation,
    whole_piece_investigation,
)
from .selection import (
    PASSAGE_CONTEXT_SCHEMA_VERSION,
    SELECTED_PASSAGE_SCHEMA_VERSION,
    SELECTION_METHOD_ID,
    SELECTION_METHOD_VERSION,
    ClefState,
    PassageContext,
    SelectedPassage,
    UnresolvableRegion,
    locate_measure_by_number,
    refine_selection,
    select_passage,
    whole_piece_range,
)

__all__ = [
    "MANUAL_METHOD_ID",
    "MANUAL_METHOD_VERSION",
    "WHOLE_PIECE_METHOD_ID",
    "PASSAGE_CONTEXT_SCHEMA_VERSION",
    "SELECTED_PASSAGE_SCHEMA_VERSION",
    "SELECTION_METHOD_ID",
    "SELECTION_METHOD_VERSION",
    "ClefState",
    "PassageContext",
    "SelectedPassage",
    "UnresolvableRegion",
    "locate_measure_by_number",
    "manual_investigation",
    "refine_selection",
    "select_passage",
    "whole_piece_investigation",
    "whole_piece_range",
]
