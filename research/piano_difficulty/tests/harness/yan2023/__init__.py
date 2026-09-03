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
    "DEFAULT_ARTIFACTS_ROOT",
    "DEFAULT_RUNS_ROOT",
    "LANE_BOUNDARY_RULES",
    "LANE_ID",
    "LANE_NAME",
    "PAPER_73_FEATURE_SLOTS",
    "WORKING_FEATURE_SLOTS",
    "DatasetExportSpec",
    "YanDatasetExportResult",
    "YanFeatureFamilySpec",
    "YanFeatureMathChoice",
    "YanFeatureOptimizationRunResult",
    "Yan2023FeatureValue",
    "Yan2023ImplementationAuditRow",
    "YanModelCandidate",
    "YanOptimizationCandidate",
    "YanOptimizationConfig",
    "YanOptimizationResultRow",
    "YanOptimizationSample",
    "YanPreprocessingConfig",
    "build_boundary_report",
    "build_feature_subset_candidates",
    "build_implementation_audit_rows",
    "build_json_payload",
    "build_markdown_report",
    "current_implemented_slot_ids",
    "default_feature_family_specs",
    "default_feature_pool",
    "default_model_candidates",
    "downgraded_base_features",
    "discover_score_files",
    "extract_first_pass",
    "extract_first_pass_from_path",
    "generate_candidate_blueprints",
    "load_optimization_samples_from_csv",
    "run_yan_dataset_export",
    "run_feature_optimization",
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
    from tests.harness.yan2023.dataset_export import (
        DatasetExportSpec,
        YanDatasetExportResult,
        discover_score_files,
        run_yan_dataset_export,
    )
    from tests.harness.yan2023.feature_optimization import (
        DEFAULT_ARTIFACTS_ROOT,
        DEFAULT_RUNS_ROOT,
        YanFeatureFamilySpec,
        YanFeatureMathChoice,
        YanFeatureOptimizationRunResult,
        YanModelCandidate,
        YanOptimizationCandidate,
        YanOptimizationConfig,
        YanOptimizationResultRow,
        YanOptimizationSample,
        YanPreprocessingConfig,
        build_feature_subset_candidates,
        default_feature_family_specs,
        default_feature_pool,
        default_model_candidates,
        generate_candidate_blueprints,
        load_optimization_samples_from_csv,
        run_feature_optimization,
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
        "DatasetExportSpec",
        "YanDatasetExportResult",
        "DEFAULT_ARTIFACTS_ROOT",
        "DEFAULT_RUNS_ROOT",
        "YanFeatureFamilySpec",
        "YanFeatureMathChoice",
        "YanFeatureOptimizationRunResult",
        "YanModelCandidate",
        "YanOptimizationCandidate",
        "YanOptimizationConfig",
        "YanOptimizationResultRow",
        "YanOptimizationSample",
        "YanPreprocessingConfig",
        "discover_score_files",
        "build_feature_subset_candidates",
        "default_feature_family_specs",
        "default_feature_pool",
        "default_model_candidates",
        "generate_candidate_blueprints",
        "load_optimization_samples_from_csv",
        "Yan2023FeatureValue",
        "extract_first_pass",
        "extract_first_pass_from_path",
        "run_yan_dataset_export",
        "run_feature_optimization",
    }:
        from tests.harness.yan2023.extractor import (
            Yan2023FeatureValue,
            extract_first_pass,
            extract_first_pass_from_path,
        )
        from tests.harness.yan2023.dataset_export import (
            DatasetExportSpec,
            YanDatasetExportResult,
            discover_score_files,
            run_yan_dataset_export,
        )
        from tests.harness.yan2023.feature_optimization import (
            DEFAULT_ARTIFACTS_ROOT,
            DEFAULT_RUNS_ROOT,
            YanFeatureFamilySpec,
            YanFeatureMathChoice,
            YanFeatureOptimizationRunResult,
            YanModelCandidate,
            YanOptimizationCandidate,
            YanOptimizationConfig,
            YanOptimizationResultRow,
            YanOptimizationSample,
            YanPreprocessingConfig,
            build_feature_subset_candidates,
            default_feature_family_specs,
            default_feature_pool,
            default_model_candidates,
            generate_candidate_blueprints,
            load_optimization_samples_from_csv,
            run_feature_optimization,
        )

        exports = {
            "DEFAULT_ARTIFACTS_ROOT": DEFAULT_ARTIFACTS_ROOT,
            "DEFAULT_RUNS_ROOT": DEFAULT_RUNS_ROOT,
            "DatasetExportSpec": DatasetExportSpec,
            "YanDatasetExportResult": YanDatasetExportResult,
            "YanFeatureFamilySpec": YanFeatureFamilySpec,
            "YanFeatureMathChoice": YanFeatureMathChoice,
            "YanFeatureOptimizationRunResult": YanFeatureOptimizationRunResult,
            "YanModelCandidate": YanModelCandidate,
            "YanOptimizationCandidate": YanOptimizationCandidate,
            "YanOptimizationConfig": YanOptimizationConfig,
            "YanOptimizationResultRow": YanOptimizationResultRow,
            "YanOptimizationSample": YanOptimizationSample,
            "YanPreprocessingConfig": YanPreprocessingConfig,
            "discover_score_files": discover_score_files,
            "build_feature_subset_candidates": build_feature_subset_candidates,
            "default_feature_family_specs": default_feature_family_specs,
            "default_feature_pool": default_feature_pool,
            "default_model_candidates": default_model_candidates,
            "generate_candidate_blueprints": generate_candidate_blueprints,
            "load_optimization_samples_from_csv": load_optimization_samples_from_csv,
            "Yan2023FeatureValue": Yan2023FeatureValue,
            "extract_first_pass": extract_first_pass,
            "extract_first_pass_from_path": extract_first_pass_from_path,
            "run_yan_dataset_export": run_yan_dataset_export,
            "run_feature_optimization": run_feature_optimization,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
