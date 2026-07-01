"""Yan paper-first feature reconstruction harness.

This package keeps its public helpers available at package scope, but resolves
the heavier extractor and inventory modules lazily so lightweight imports do
not pull in the whole score pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "ALLOWED_MATH_SOURCES",
    "ALLOWED_RECOMMENDED_STATUSES",
    "ALLOWED_VALIDATION_STATUSES",
    "EXPERIMENTAL_FEATURE_STATUSES",
    "FEATURE_FIXTURE_EXPECTATIONS",
    "FEATURE_FIXTURE_PATH",
    "FEATURE_FIXTURE_VALIDATION_REF",
    "LANE_BOUNDARY_RULES",
    "LANE_ID",
    "LANE_NAME",
    "PAPER_73_FEATURE_SLOTS",
    "WORKING_FEATURE_SLOTS",
    "Yan2023FeatureValue",
    "Yan2023ImplementationAuditRow",
    "build_boundary_report",
    "build_implementation_audit_rows",
    "build_json_payload",
    "build_markdown_report",
    "current_implemented_slot_ids",
    "downgraded_base_features",
    "extract_first_pass",
    "extract_first_pass_from_path",
    "paper_scope_evidence_counts",
    "paper_scope_override_map",
    "paper_slot_scope_counts",
    "paper_slot_source_counts",
    "paper_slot_status_counts",
    "pre_audit_counts",
    "recommended_base_status_counts",
    "recommended_status_counts",
    "safe_base_features",
    "slot_scope_counts",
    "slot_source_counts",
    "slot_status_counts",
    "validate_audit_metadata",
    "validate_feature_fixture_regression",
]

if TYPE_CHECKING:
    from tests.harness.yan2023.boundary import (
        EXPERIMENTAL_FEATURE_STATUSES,
        LANE_BOUNDARY_RULES,
        LANE_ID,
        LANE_NAME,
        build_boundary_report,
    )
    from tests.harness.yan2023.implementation_audit import (
        ALLOWED_MATH_SOURCES,
        ALLOWED_RECOMMENDED_STATUSES,
        ALLOWED_VALIDATION_STATUSES,
        FEATURE_FIXTURE_EXPECTATIONS,
        FEATURE_FIXTURE_PATH,
        FEATURE_FIXTURE_VALIDATION_REF,
        Yan2023ImplementationAuditRow,
        build_implementation_audit_rows,
        build_json_payload,
        build_markdown_report,
        current_implemented_slot_ids,
        downgraded_base_features,
        pre_audit_counts,
        recommended_base_status_counts,
        recommended_status_counts,
        safe_base_features,
        validate_audit_metadata,
        validate_feature_fixture_regression,
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
        "ALLOWED_MATH_SOURCES",
        "ALLOWED_RECOMMENDED_STATUSES",
        "ALLOWED_VALIDATION_STATUSES",
        "FEATURE_FIXTURE_EXPECTATIONS",
        "FEATURE_FIXTURE_PATH",
        "FEATURE_FIXTURE_VALIDATION_REF",
        "Yan2023ImplementationAuditRow",
        "build_implementation_audit_rows",
        "build_json_payload",
        "build_markdown_report",
        "current_implemented_slot_ids",
        "downgraded_base_features",
        "pre_audit_counts",
        "recommended_base_status_counts",
        "recommended_status_counts",
        "safe_base_features",
        "validate_audit_metadata",
        "validate_feature_fixture_regression",
    }:
        from tests.harness.yan2023.implementation_audit import (
            ALLOWED_MATH_SOURCES,
            ALLOWED_RECOMMENDED_STATUSES,
            ALLOWED_VALIDATION_STATUSES,
            FEATURE_FIXTURE_EXPECTATIONS,
            FEATURE_FIXTURE_PATH,
            FEATURE_FIXTURE_VALIDATION_REF,
            Yan2023ImplementationAuditRow,
            build_implementation_audit_rows,
            build_json_payload,
            build_markdown_report,
            current_implemented_slot_ids,
            downgraded_base_features,
            pre_audit_counts,
            recommended_base_status_counts,
            recommended_status_counts,
            safe_base_features,
            validate_audit_metadata,
            validate_feature_fixture_regression,
        )

        exports = {
            "ALLOWED_MATH_SOURCES": ALLOWED_MATH_SOURCES,
            "ALLOWED_RECOMMENDED_STATUSES": ALLOWED_RECOMMENDED_STATUSES,
            "ALLOWED_VALIDATION_STATUSES": ALLOWED_VALIDATION_STATUSES,
            "FEATURE_FIXTURE_EXPECTATIONS": FEATURE_FIXTURE_EXPECTATIONS,
            "FEATURE_FIXTURE_PATH": FEATURE_FIXTURE_PATH,
            "FEATURE_FIXTURE_VALIDATION_REF": FEATURE_FIXTURE_VALIDATION_REF,
            "Yan2023ImplementationAuditRow": Yan2023ImplementationAuditRow,
            "build_implementation_audit_rows": build_implementation_audit_rows,
            "build_json_payload": build_json_payload,
            "build_markdown_report": build_markdown_report,
            "current_implemented_slot_ids": current_implemented_slot_ids,
            "downgraded_base_features": downgraded_base_features,
            "pre_audit_counts": pre_audit_counts,
            "recommended_base_status_counts": recommended_base_status_counts,
            "recommended_status_counts": recommended_status_counts,
            "safe_base_features": safe_base_features,
            "validate_audit_metadata": validate_audit_metadata,
            "validate_feature_fixture_regression": validate_feature_fixture_regression,
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
