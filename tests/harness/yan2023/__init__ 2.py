"""Yan paper-first feature reconstruction harness.

This package keeps its public helpers available at package scope, but resolves
the heavier extractor and slot-inventory modules lazily so lightweight imports
do not pull in the whole score pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "EXPERIMENTAL_FEATURE_STATUSES",
    "LANE_BOUNDARY_RULES",
    "LANE_ID",
    "LANE_NAME",
    "PAPER_73_FEATURE_SLOTS",
    "WORKING_FEATURE_SLOTS",
    "Yan2023FeatureValue",
    "build_boundary_report",
    "extract_first_pass",
    "extract_first_pass_from_path",
    "paper_scope_evidence_counts",
    "paper_scope_override_map",
    "paper_slot_scope_counts",
    "paper_slot_source_counts",
    "paper_slot_status_counts",
    "slot_scope_counts",
    "slot_source_counts",
    "slot_status_counts",
]

if TYPE_CHECKING:
    from tests.harness.yan2023.boundary import (
        EXPERIMENTAL_FEATURE_STATUSES,
        LANE_BOUNDARY_RULES,
        LANE_ID,
        LANE_NAME,
        build_boundary_report,
    )
    from tests.harness.yan2023.extractor import (
        Yan2023FeatureValue,
        extract_first_pass,
        extract_first_pass_from_path,
    )
    from tests.harness.yan2023.paper_inventory import (
        PAPER_73_FEATURE_SLOTS,
        paper_scope_evidence_counts,
        paper_scope_override_map,
        paper_slot_scope_counts,
        paper_slot_source_counts,
        paper_slot_status_counts,
    )
    from tests.harness.yan2023.slot_inventory import (
        WORKING_FEATURE_SLOTS,
        slot_scope_counts,
        slot_source_counts,
        slot_status_counts,
    )


def __getattr__(name: str) -> Any:
    if name in {
        "EXPERIMENTAL_FEATURE_STATUSES",
        "LANE_BOUNDARY_RULES",
        "LANE_ID",
        "LANE_NAME",
        "build_boundary_report",
    }:
        from tests.harness.yan2023.boundary import (
            EXPERIMENTAL_FEATURE_STATUSES,
            LANE_BOUNDARY_RULES,
            LANE_ID,
            LANE_NAME,
            build_boundary_report,
        )

        exports = {
            "EXPERIMENTAL_FEATURE_STATUSES": EXPERIMENTAL_FEATURE_STATUSES,
            "LANE_BOUNDARY_RULES": LANE_BOUNDARY_RULES,
            "LANE_ID": LANE_ID,
            "LANE_NAME": LANE_NAME,
            "build_boundary_report": build_boundary_report,
        }
        return exports[name]

    if name in {
        "PAPER_73_FEATURE_SLOTS",
        "paper_scope_evidence_counts",
        "paper_scope_override_map",
        "paper_slot_scope_counts",
        "paper_slot_source_counts",
        "paper_slot_status_counts",
    }:
        from tests.harness.yan2023.paper_inventory import (
            PAPER_73_FEATURE_SLOTS,
            paper_scope_evidence_counts,
            paper_scope_override_map,
            paper_slot_scope_counts,
            paper_slot_source_counts,
            paper_slot_status_counts,
        )

        exports = {
            "PAPER_73_FEATURE_SLOTS": PAPER_73_FEATURE_SLOTS,
            "paper_scope_evidence_counts": paper_scope_evidence_counts,
            "paper_scope_override_map": paper_scope_override_map,
            "paper_slot_scope_counts": paper_slot_scope_counts,
            "paper_slot_source_counts": paper_slot_source_counts,
            "paper_slot_status_counts": paper_slot_status_counts,
        }
        return exports[name]

    if name in {
        "WORKING_FEATURE_SLOTS",
        "slot_scope_counts",
        "slot_source_counts",
        "slot_status_counts",
    }:
        from tests.harness.yan2023.slot_inventory import (
            WORKING_FEATURE_SLOTS,
            slot_scope_counts,
            slot_source_counts,
            slot_status_counts,
        )

        exports = {
            "WORKING_FEATURE_SLOTS": WORKING_FEATURE_SLOTS,
            "slot_scope_counts": slot_scope_counts,
            "slot_source_counts": slot_source_counts,
            "slot_status_counts": slot_status_counts,
        }
        return exports[name]

    if name in {
        "Yan2023FeatureValue",
        "extract_first_pass",
        "extract_first_pass_from_path",
    }:
        from tests.harness.yan2023.extractor import (
            Yan2023FeatureValue,
            extract_first_pass,
            extract_first_pass_from_path,
        )

        exports = {
            "Yan2023FeatureValue": Yan2023FeatureValue,
            "extract_first_pass": extract_first_pass,
            "extract_first_pass_from_path": extract_first_pass_from_path,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
