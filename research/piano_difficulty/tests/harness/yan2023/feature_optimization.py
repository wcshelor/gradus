"""Feature-optimization scaffolding for the Yan 2023 lane.

This module is intentionally sequestered from the extractor itself. It can
search over feature inclusion, formula choices for ambiguous feature families,
and model hyperparameters without changing the default feature math used by the
Yan reconstruction lane.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from itertools import combinations, product
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

from tests.harness.difficulty_prediction.models import build_estimator, extract_feature_importance
from tests.harness.yan2023.extractor import extract_first_pass_from_path
from tests.harness.yan2023.rate_measures import (
    BLACK_KEY_RATE_FORMULA_NAMES,
    DEFAULT_BLACK_KEY_RATE_FORMULA,
    DEFAULT_DOTTED_NOTE_RATE_FORMULA,
    DEFAULT_POLYPHONY_RATE_FORMULA,
    DEFAULT_STACCATO_RATE_FORMULA,
    DOTTED_NOTE_RATE_FORMULA_NAMES,
    POLYPHONY_RATE_FORMULA_NAMES,
    STACCATO_RATE_FORMULA_NAMES,
)
from tests.harness.yan2023.slot_inventory import FeatureStatus, WORKING_FEATURE_SLOTS
from tests.harness.yan2023.variability import DEFAULT_VARIABILITY_FORMULA, VARIABILITY_FORMULA_NAMES

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "tests" / "artifacts" / "yan2023" / "feature_optimization"
DEFAULT_RUNS_ROOT = DEFAULT_ARTIFACTS_ROOT / "runs"

YanTaskKind = Literal["classification", "regression"]
YanSearchMode = Literal["grid", "explicit"]


@dataclass(frozen=True, slots=True)
class YanOptimizationSample:
    """One labeled score file used by the Yan optimization search."""

    sample_id: str
    score_path: Path
    label: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class YanPreprocessingConfig:
    """Estimator preprocessing knobs for the Yan search."""

    imputer_strategy: str = "median"
    scaler: str | None = "standard"


@dataclass(frozen=True, slots=True)
class YanModelCandidate:
    """One model family plus a fixed parameter payload."""

    model_family: str
    model_parameters: dict[str, Any] = field(default_factory=dict)
    label: str | None = None


@dataclass(frozen=True, slots=True)
class YanFeatureMathChoice:
    """One selectable math choice for a tunable Yan feature family."""

    choice_name: str
    extractor_kwargs: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class YanFeatureFamilySpec:
    """One feature family whose math choices may be optimized."""

    base_feature: str
    choices: tuple[YanFeatureMathChoice, ...] = ()
    notes: str = ""


@dataclass(frozen=True, slots=True)
class YanOptimizationCandidate:
    """One full search candidate."""

    selected_features: tuple[str, ...]
    math_choices: tuple[tuple[str, str], ...]
    model_candidate: YanModelCandidate

    def stable_id(self) -> str:
        payload = json.dumps(
            {
                "selected_features": list(self.selected_features),
                "math_choices": list(self.math_choices),
                "model_family": self.model_candidate.model_family,
                "model_parameters": self.model_candidate.model_parameters,
                "model_label": self.model_candidate.label,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.stable_id(),
            "selected_features": list(self.selected_features),
            "math_choices": [{"feature": feature, "choice": choice} for feature, choice in self.math_choices],
            "model_candidate": asdict(self.model_candidate),
        }


@dataclass(frozen=True, slots=True)
class YanOptimizationConfig:
    """Search configuration for Yan feature optimization."""

    samples: tuple[YanOptimizationSample, ...]
    task_kind: YanTaskKind = "classification"
    label_order: tuple[Any, ...] | None = None
    feature_pool: tuple[str, ...] = ()
    required_features: tuple[str, ...] = ()
    feature_subset_candidates: tuple[tuple[str, ...], ...] = ()
    feature_subset_mode: YanSearchMode = "grid"
    max_feature_count: int = 3
    feature_family_specs: tuple[YanFeatureFamilySpec, ...] = ()
    model_candidates: tuple[YanModelCandidate, ...] = ()
    preprocessing: YanPreprocessingConfig = field(default_factory=YanPreprocessingConfig)
    folds: int = 5
    shuffle: bool = True
    random_state: int | None = 42
    primary_metric: str | None = None
    max_candidates: int | None = None
    out_dir: Path | None = None
    run_name: str | None = None


@dataclass(frozen=True, slots=True)
class YanOptimizationResultRow:
    """One evaluated search candidate."""

    candidate_id: str
    rank: int | None
    selected_feature_count: int
    selected_features: tuple[str, ...]
    math_choices: tuple[tuple[str, str], ...]
    model_family: str
    model_label: str | None
    model_parameters: dict[str, Any]
    metric_name: str
    metric_value: float | None
    status: str
    error_message: str = ""
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "rank": self.rank,
            "selected_feature_count": self.selected_feature_count,
            "selected_features": list(self.selected_features),
            "math_choices": [{"feature": feature, "choice": choice} for feature, choice in self.math_choices],
            "model_family": self.model_family,
            "model_label": self.model_label,
            "model_parameters": self.model_parameters,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "status": self.status,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


@dataclass(frozen=True, slots=True)
class YanFeatureOptimizationRunResult:
    """Result bundle for a Yan optimization run."""

    run_dir: Path
    resolved_config_path: Path
    candidate_results_path: Path
    summary_path: Path
    best_candidate_path: Path | None
    best_feature_importance_path: Path | None
    candidate_results: pd.DataFrame
    summary: dict[str, Any]
    best_candidate: YanOptimizationResultRow | None
    best_feature_importance: pd.DataFrame | None = None


def load_optimization_samples_from_csv(
    csv_path: str | Path,
    *,
    score_path_column: str = "score_path",
    label_column: str = "label",
    sample_id_column: str | None = None,
) -> tuple[YanOptimizationSample, ...]:
    """Load labeled score samples from a simple manifest CSV."""

    manifest_path = Path(csv_path).expanduser().resolve()
    frame = pd.read_csv(manifest_path)
    missing_columns = [column for column in [score_path_column, label_column] if column not in frame.columns]
    if missing_columns:
        raise ValueError(
            f"Manifest {manifest_path} is missing required column(s): {', '.join(missing_columns)}"
        )

    samples: list[YanOptimizationSample] = []
    for index, row in frame.iterrows():
        raw_score_path = Path(str(row[score_path_column])).expanduser()
        score_path = raw_score_path if raw_score_path.is_absolute() else (manifest_path.parent / raw_score_path).resolve()
        sample_id = (
            str(row[sample_id_column]).strip()
            if sample_id_column and sample_id_column in frame.columns
            else f"sample_{index:05d}"
        )
        metadata = {
            column: row[column]
            for column in frame.columns
            if column not in {score_path_column, label_column}
            and (sample_id_column is None or column != sample_id_column)
        }
        samples.append(
            YanOptimizationSample(
                sample_id=sample_id,
                score_path=score_path,
                label=row[label_column],
                metadata=metadata,
            )
        )
    return tuple(samples)


def default_feature_pool(*, include_blocked: bool = False) -> tuple[str, ...]:
    """Return a stable default base-feature pool for feature-subset search."""

    seen: dict[str, None] = {}
    blocked_features = {
        slot.base_feature for slot in WORKING_FEATURE_SLOTS if slot.status == "blocked"
    }
    for slot in WORKING_FEATURE_SLOTS:
        if not include_blocked and slot.base_feature in blocked_features:
            continue
        seen.setdefault(slot.base_feature, None)
    return tuple(seen)


def default_feature_family_specs() -> tuple[YanFeatureFamilySpec, ...]:
    """Return the current tunable math families for the Yan lane."""

    variability_choices = tuple(
        YanFeatureMathChoice(
            choice_name=formula,
            extractor_kwargs={"variability_formula": formula},
            notes="Shared score-sequence variability bank candidate.",
        )
        for formula in VARIABILITY_FORMULA_NAMES
    )
    return (
        YanFeatureFamilySpec(
            base_feature="pitch_variability",
            choices=variability_choices,
            notes="Shared score-sequence variability family for pitch changes.",
        ),
        YanFeatureFamilySpec(
            base_feature="note_duration_variability",
            choices=variability_choices,
            notes="Shared score-sequence variability family for duration changes.",
        ),
        YanFeatureFamilySpec(
            base_feature="black_key_rate",
            choices=tuple(
                YanFeatureMathChoice(
                    choice_name=formula,
                    extractor_kwargs={"black_key_rate_formula": formula},
                    notes="Shared score-native black-key rate candidate.",
                )
                for formula in BLACK_KEY_RATE_FORMULA_NAMES
            ),
            notes="Score-native black-key rate family.",
        ),
        YanFeatureFamilySpec(
            base_feature="polyphony_rate",
            choices=tuple(
                YanFeatureMathChoice(
                    choice_name=formula,
                    extractor_kwargs={"polyphony_rate_formula": formula},
                    notes="Shared score-native polyphony rate candidate.",
                )
                for formula in POLYPHONY_RATE_FORMULA_NAMES
            ),
            notes="Score-native polyphony rate family.",
        ),
        YanFeatureFamilySpec(
            base_feature="staccato_rate",
            choices=tuple(
                YanFeatureMathChoice(
                    choice_name=formula,
                    extractor_kwargs={"staccato_rate_formula": formula},
                    notes="Shared score-native staccato rate candidate.",
                )
                for formula in STACCATO_RATE_FORMULA_NAMES
            ),
            notes="Score-native staccato rate family.",
        ),
        YanFeatureFamilySpec(
            base_feature="dotted_note_rate",
            choices=tuple(
                YanFeatureMathChoice(
                    choice_name=formula,
                    extractor_kwargs={"dotted_note_rate_formula": formula},
                    notes="Shared score-native dotted-note rate candidate.",
                )
                for formula in DOTTED_NOTE_RATE_FORMULA_NAMES
            ),
            notes="Score-native dotted-note rate family.",
        ),
    )


def default_model_candidates(task_kind: YanTaskKind) -> tuple[YanModelCandidate, ...]:
    """Return a compact model bank for the current task kind."""

    if task_kind == "regression":
        return (
            YanModelCandidate("ridge_regression", {"alpha": 1.0}, label="ridge"),
            YanModelCandidate("random_forest_regression", {"n_estimators": 300, "random_state": 42}, label="rf"),
            YanModelCandidate("gradient_boosting_regression", {"random_state": 42}, label="gbr"),
        )
    return (
        YanModelCandidate("ridge_classifier", {"alpha": 1.0}, label="ridge"),
        YanModelCandidate("logistic_regression", {"max_iter": 4000}, label="logreg"),
        YanModelCandidate("random_forest_classifier", {"n_estimators": 300, "random_state": 42}, label="rf"),
    )


def build_feature_subset_candidates(
    feature_pool: Sequence[str],
    *,
    required_features: Sequence[str] = (),
    max_feature_count: int = 3,
) -> tuple[tuple[str, ...], ...]:
    """Generate feature-subset candidates from a base-feature pool."""

    normalized_required = tuple(dict.fromkeys(str(feature) for feature in required_features))
    normalized_pool = [str(feature) for feature in feature_pool if str(feature) not in normalized_required]
    if not normalized_pool:
        return (normalized_required,) if normalized_required else ()

    upper_bound = min(len(normalized_pool), max(0, max_feature_count - len(normalized_required)))
    if upper_bound < 0:
        return ()

    subsets: list[tuple[str, ...]] = []
    for size in range(0, upper_bound + 1):
        for combo in combinations(normalized_pool, size):
            subset = tuple(dict.fromkeys((*normalized_required, *combo)))
            subsets.append(subset)
    return tuple(subsets)


def generate_candidate_blueprints(config: YanOptimizationConfig) -> tuple[YanOptimizationCandidate, ...]:
    """Expand the search space into concrete candidate blueprints."""

    subset_candidates = _resolve_feature_subset_candidates(config)
    family_specs = _resolved_feature_family_specs(config)
    math_choice_groups = [_choices_for_family(spec) for spec in family_specs]
    math_blueprints = list(product(*math_choice_groups)) if math_choice_groups else [tuple()]
    model_candidates = config.model_candidates or default_model_candidates(config.task_kind)

    candidates: list[YanOptimizationCandidate] = []
    for selected_features in subset_candidates:
        for math_blueprint in math_blueprints:
            math_choices = tuple(
                (spec.base_feature, choice.choice_name) for spec, choice in zip(family_specs, math_blueprint, strict=False)
            )
            for model_candidate in model_candidates:
                candidates.append(
                    YanOptimizationCandidate(
                        selected_features=selected_features,
                        math_choices=math_choices,
                        model_candidate=model_candidate,
                    )
                )
    return tuple(candidates)


def run_feature_optimization(
    config: YanOptimizationConfig,
) -> YanFeatureOptimizationRunResult:
    """Run a Yan feature search over the supplied labeled score samples."""

    if not config.samples:
        raise ValueError("Yan feature optimization needs at least one labeled sample.")

    run_dir = _allocate_run_dir(config)
    run_dir.mkdir(parents=True, exist_ok=False)

    resolved_config_path = run_dir / "resolved_config.json"
    candidate_results_path = run_dir / "candidate_results.csv"
    summary_path = run_dir / "summary.json"
    best_candidate_path = run_dir / "best_candidate.json"
    best_feature_importance_path = run_dir / "best_feature_importance.csv"

    candidate_rows: list[YanOptimizationResultRow] = []
    candidate_blueprints = generate_candidate_blueprints(config)
    if config.max_candidates is not None:
        candidate_blueprints = candidate_blueprints[: max(0, config.max_candidates)]

    feature_cache: dict[tuple[tuple[str, Any], ...], pd.DataFrame] = {}
    for candidate in candidate_blueprints:
        try:
            row = _evaluate_candidate(
                config=config,
                candidate=candidate,
                feature_cache=feature_cache,
            )
        except Exception as exc:  # pragma: no cover - candidate failures are expected in search
            row = YanOptimizationResultRow(
                candidate_id=candidate.stable_id(),
                rank=None,
                selected_feature_count=len(candidate.selected_features),
                selected_features=candidate.selected_features,
                math_choices=candidate.math_choices,
                model_family=candidate.model_candidate.model_family,
                model_label=candidate.model_candidate.label,
                model_parameters=dict(candidate.model_candidate.model_parameters),
                metric_name=_primary_metric_name(config),
                metric_value=None,
                status="failed",
                error_message=f"{exc.__class__.__name__}: {exc}",
                metrics={},
            )
        candidate_rows.append(row)

    ranked_rows = _rank_candidate_rows(candidate_rows, primary_metric=_primary_metric_name(config))
    best_candidate = ranked_rows[0] if ranked_rows else None
    best_feature_importance = None
    if best_candidate is not None and best_candidate.status == "success":
        best_feature_importance = _build_best_feature_importance(
            config=config,
            candidate=best_candidate,
            feature_cache=feature_cache,
        )

    resolved_config_path.write_text(
        json.dumps(
            _build_resolved_config(config, candidate_blueprints=candidate_blueprints, best_candidate=best_candidate),
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
    )
    _write_candidate_results(candidate_results_path, ranked_rows)
    summary = _build_summary(config=config, candidate_rows=ranked_rows, best_candidate=best_candidate)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=_json_default))
    if best_candidate is not None:
        best_candidate_path.write_text(json.dumps(best_candidate.to_dict(), indent=2, sort_keys=True, default=_json_default))
    else:
        best_candidate_path.unlink(missing_ok=True)
    if best_feature_importance is not None:
        best_feature_importance.to_csv(best_feature_importance_path, index=False)
    else:
        best_feature_importance_path.unlink(missing_ok=True)

    candidate_results_frame = pd.read_csv(candidate_results_path)
    return YanFeatureOptimizationRunResult(
        run_dir=run_dir,
        resolved_config_path=resolved_config_path,
        candidate_results_path=candidate_results_path,
        summary_path=summary_path,
        best_candidate_path=best_candidate_path if best_candidate is not None else None,
        best_feature_importance_path=best_feature_importance_path if best_feature_importance is not None else None,
        candidate_results=candidate_results_frame,
        summary=summary,
        best_candidate=best_candidate,
        best_feature_importance=best_feature_importance,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Yan 2023 feature optimization over labeled score files.")
    parser.add_argument("manifest", type=Path, help="CSV with score_path and label columns.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--score-path-column", type=str, default="score_path")
    parser.add_argument("--label-column", type=str, default="label")
    parser.add_argument("--sample-id-column", type=str, default=None)
    parser.add_argument("--task-kind", choices=("classification", "regression"), default="classification")
    parser.add_argument("--primary-metric", type=str, default=None)
    parser.add_argument("--max-feature-count", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--required-feature", action="append", default=[])
    parser.add_argument("--feature-pool", action="append", default=[])
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args(argv)

    samples = load_optimization_samples_from_csv(
        args.manifest,
        score_path_column=args.score_path_column,
        label_column=args.label_column,
        sample_id_column=args.sample_id_column,
    )
    feature_pool = tuple(args.feature_pool) if args.feature_pool else default_feature_pool()
    subset_candidates = build_feature_subset_candidates(
        feature_pool,
        required_features=tuple(args.required_feature),
        max_feature_count=args.max_feature_count,
    )
    config = YanOptimizationConfig(
        samples=samples,
        task_kind=args.task_kind,
        feature_pool=feature_pool,
        required_features=tuple(args.required_feature),
        feature_subset_candidates=subset_candidates,
        feature_subset_mode="grid",
        max_feature_count=args.max_feature_count,
        feature_family_specs=default_feature_family_specs(),
        model_candidates=default_model_candidates(args.task_kind),
        folds=args.folds,
        random_state=args.random_state,
        primary_metric=args.primary_metric,
        max_candidates=args.max_candidates,
        out_dir=args.out_dir,
        run_name=Path(args.manifest).stem,
    )
    result = run_feature_optimization(config)
    print(
        json.dumps(
            {
                "run_dir": str(result.run_dir),
                "summary_path": str(result.summary_path),
                "candidate_results_path": str(result.candidate_results_path),
                "best_candidate_path": str(result.best_candidate_path) if result.best_candidate_path else None,
                "best_feature_importance_path": str(result.best_feature_importance_path) if result.best_feature_importance_path else None,
                "best_candidate": result.best_candidate.to_dict() if result.best_candidate else None,
                "summary": result.summary,
            },
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
    )
    return 0


def _evaluate_candidate(
    *,
    config: YanOptimizationConfig,
    candidate: YanOptimizationCandidate,
    feature_cache: dict[tuple[tuple[str, Any], ...], pd.DataFrame],
) -> YanOptimizationResultRow:
    feature_frame = _build_feature_frame(
        samples=config.samples,
        candidate=candidate,
        feature_cache=feature_cache,
    )
    selected_columns = _resolve_selected_columns(feature_frame.columns, candidate.selected_features)
    if not selected_columns:
        raise ValueError("Candidate selected no available feature columns.")

    X = feature_frame.loc[:, selected_columns].apply(pd.to_numeric, errors="coerce")
    y = _build_target_vector(config.samples, config.task_kind)
    y_encoded, class_labels, ordinal_map = _encode_target(y, config)
    splitter = _build_splitter(config, y_encoded, class_labels)

    fold_metrics: list[dict[str, float]] = []
    y_true_all: list[Any] = []
    y_pred_all: list[Any] = []
    for train_index, test_index in splitter.split(X, y_encoded):
        estimator = build_estimator(
            candidate.model_candidate.model_family,
            dict(candidate.model_candidate.model_parameters),
            config.preprocessing,
        )
        train_X = X.iloc[train_index]
        test_X = X.iloc[test_index]
        train_y = y_encoded.iloc[train_index]
        test_y = y_encoded.iloc[test_index]

        estimator.fit(train_X, train_y)
        predictions = estimator.predict(test_X)
        fold_metrics.append(
            _compute_metrics(
                task_kind=config.task_kind,
                y_true=test_y,
                y_pred=predictions,
                class_labels=class_labels,
                ordinal_map=ordinal_map,
            )
        )
        y_true_all.extend(test_y.tolist())
        y_pred_all.extend(predictions.tolist())

    overall_metrics = _compute_metrics(
        task_kind=config.task_kind,
        y_true=pd.Series(y_true_all),
        y_pred=pd.Series(y_pred_all),
        class_labels=class_labels,
        ordinal_map=ordinal_map,
    )
    metric_name = _primary_metric_name(config)
    metric_value = overall_metrics.get(metric_name)
    if metric_value is None:
        raise ValueError(f"Primary metric {metric_name!r} is not available for this task.")

    metrics = dict(overall_metrics)
    metrics["fold_count"] = float(len(fold_metrics))
    metrics["selected_feature_count"] = float(len(selected_columns))
    metrics["candidate_id"] = candidate.stable_id()
    return YanOptimizationResultRow(
        candidate_id=candidate.stable_id(),
        rank=None,
        selected_feature_count=len(selected_columns),
        selected_features=tuple(selected_columns),
        math_choices=candidate.math_choices,
        model_family=candidate.model_candidate.model_family,
        model_label=candidate.model_candidate.label,
        model_parameters=dict(candidate.model_candidate.model_parameters),
        metric_name=metric_name,
        metric_value=float(metric_value),
        status="success",
        metrics={key: float(value) for key, value in metrics.items() if isinstance(value, (int, float, np.floating))},
    )


def _build_feature_frame(
    *,
    samples: Sequence[YanOptimizationSample],
    candidate: YanOptimizationCandidate,
    feature_cache: dict[tuple[tuple[str, Any], ...], pd.DataFrame],
) -> pd.DataFrame:
    formula_kwargs = _build_extractor_kwargs(candidate)
    cache_key = tuple(sorted((str(key), value) for key, value in formula_kwargs.items()))
    cached = feature_cache.get(cache_key)
    if cached is not None:
        return cached.copy()

    rows: list[dict[str, Any]] = []
    for sample in samples:
        _score, values = extract_first_pass_from_path(sample.score_path, **formula_kwargs)
        row: dict[str, Any] = {
            "sample_id": sample.sample_id,
            "score_path": str(sample.score_path),
            "label": sample.label,
        }
        row.update(sample.metadata)
        for slot in WORKING_FEATURE_SLOTS:
            row.setdefault(slot.slot_id, np.nan)
        for value in values:
            row[value.slot_id] = value.value
        rows.append(row)

    frame = pd.DataFrame(rows)
    feature_cache[cache_key] = frame
    return frame.copy()


def _build_extractor_kwargs(candidate: YanOptimizationCandidate) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    lookup = {feature: choice for feature, choice in candidate.math_choices}
    for spec in default_feature_family_specs():
        choice_name = lookup.get(spec.base_feature)
        if choice_name is None:
            continue
        for choice in spec.choices:
            if choice.choice_name == choice_name:
                kwargs.update(choice.extractor_kwargs)
                break
    return kwargs


def _resolve_feature_subset_candidates(config: YanOptimizationConfig) -> tuple[tuple[str, ...], ...]:
    if config.feature_subset_candidates:
        return tuple(tuple(dict.fromkeys(candidate)) for candidate in config.feature_subset_candidates)

    pool = config.feature_pool or default_feature_pool()
    return build_feature_subset_candidates(
        pool,
        required_features=config.required_features,
        max_feature_count=config.max_feature_count,
    )


def _resolved_feature_family_specs(config: YanOptimizationConfig) -> tuple[YanFeatureFamilySpec, ...]:
    return config.feature_family_specs or default_feature_family_specs()


def _choices_for_family(spec: YanFeatureFamilySpec) -> tuple[YanFeatureMathChoice, ...]:
    if spec.choices:
        return spec.choices
    return (YanFeatureMathChoice("default", {}),)


def _resolve_selected_columns(columns: Iterable[str], selected_features: Sequence[str]) -> list[str]:
    selected_feature_set = set(selected_features)
    resolved: list[str] = []
    for slot in WORKING_FEATURE_SLOTS:
        if slot.base_feature in selected_feature_set and slot.slot_id in columns:
            resolved.append(slot.slot_id)
    return list(dict.fromkeys(resolved))


def _selected_base_features_from_slot_ids(slot_ids: Sequence[str]) -> tuple[str, ...]:
    slot_lookup = {slot.slot_id: slot.base_feature for slot in WORKING_FEATURE_SLOTS}
    selected: list[str] = []
    for slot_id in slot_ids:
        base_feature = slot_lookup.get(slot_id)
        if base_feature is not None and base_feature not in selected:
            selected.append(base_feature)
    return tuple(selected)


def _build_target_vector(samples: Sequence[YanOptimizationSample], task_kind: YanTaskKind) -> pd.Series:
    values = [sample.label for sample in samples]
    if task_kind == "regression":
        return pd.Series([float(value) for value in values])
    return pd.Series(values)


def _encode_target(
    target: pd.Series,
    config: YanOptimizationConfig,
) -> tuple[pd.Series, tuple[Any, ...], dict[Any, int]]:
    if config.task_kind == "regression":
        return target.astype(float), (), {}

    if config.label_order:
        class_labels = tuple(range(len(config.label_order)))
        ordinal_map = {label: index for index, label in enumerate(config.label_order)}
        encoded_values = []
        for value in target:
            if value in ordinal_map:
                encoded_values.append(ordinal_map[value])
            else:
                encoded_values.append(ordinal_map[str(value)])
        return pd.Series(encoded_values, index=target.index), class_labels, ordinal_map

    encoder = LabelEncoder()
    encoded = pd.Series(encoder.fit_transform(target.astype(str)), index=target.index)
    class_labels = tuple(range(len(encoder.classes_)))
    ordinal_map = {label: label for label in class_labels}
    return encoded, class_labels, ordinal_map


def _build_splitter(
    config: YanOptimizationConfig,
    y_encoded: pd.Series,
    class_labels: tuple[Any, ...],
) -> KFold | StratifiedKFold:
    folds = max(2, int(config.folds))
    if config.task_kind == "classification":
        class_counts = pd.Series(y_encoded).value_counts()
        effective_folds = min(folds, int(class_counts.min())) if not class_counts.empty else folds
        if effective_folds < 2:
            raise ValueError("Classification search needs at least two samples per class.")
        return StratifiedKFold(
            n_splits=effective_folds,
            shuffle=config.shuffle,
            random_state=config.random_state,
        )
    return KFold(
        n_splits=folds,
        shuffle=config.shuffle,
        random_state=config.random_state,
    )


def _compute_metrics(
    *,
    task_kind: YanTaskKind,
    y_true: pd.Series,
    y_pred: pd.Series | np.ndarray,
    class_labels: tuple[Any, ...],
    ordinal_map: dict[Any, int],
) -> dict[str, float]:
    if task_kind == "regression":
        true_numeric = np.asarray(y_true, dtype=float)
        pred_numeric = np.asarray(y_pred, dtype=float)
        return {
            "mae": float(mean_absolute_error(true_numeric, pred_numeric)),
            "rmse": float(math.sqrt(mean_squared_error(true_numeric, pred_numeric))),
            "r2": float(r2_score(true_numeric, pred_numeric)),
        }

    true_labels = np.asarray(y_true)
    pred_labels = np.asarray(y_pred)
    metrics = {
        "accuracy": float(accuracy_score(true_labels, pred_labels)),
        "balanced_accuracy": float(balanced_accuracy_score(true_labels, pred_labels)),
        "macro_f1": float(f1_score(true_labels, pred_labels, labels=list(class_labels), average="macro")),
    }
    if ordinal_map:
        true_ord = np.asarray([ordinal_map[label] for label in true_labels], dtype=float)
        pred_ord = np.asarray([ordinal_map[label] for label in pred_labels], dtype=float)
        abs_error = np.abs(true_ord - pred_ord)
        metrics["off_by_one_accuracy"] = float(np.mean(abs_error <= 1.0))
        metrics["mean_absolute_class_error"] = float(np.mean(abs_error))
    return metrics


def _primary_metric_name(config: YanOptimizationConfig) -> str:
    if config.primary_metric:
        return config.primary_metric
    return "accuracy" if config.task_kind == "classification" else "r2"


def _rank_candidate_rows(
    rows: Sequence[YanOptimizationResultRow],
    *,
    primary_metric: str,
) -> list[YanOptimizationResultRow]:
    successful = [row for row in rows if row.status == "success" and row.metric_value is not None]
    failed = [row for row in rows if row.status != "success"]
    minimize_metrics = {"mae", "rmse", "mean_absolute_class_error"}
    successful.sort(
        key=lambda row: row.metric_value if row.metric_value is not None else float("-inf"),
        reverse=primary_metric not in minimize_metrics,
    )
    ranked: list[YanOptimizationResultRow] = []
    for index, row in enumerate(successful, start=1):
        ranked.append(
            YanOptimizationResultRow(
                candidate_id=row.candidate_id,
                rank=index,
                selected_feature_count=row.selected_feature_count,
                selected_features=row.selected_features,
                math_choices=row.math_choices,
                model_family=row.model_family,
                model_label=row.model_label,
                model_parameters=row.model_parameters,
                metric_name=row.metric_name,
                metric_value=row.metric_value,
                status=row.status,
                error_message=row.error_message,
                metrics=row.metrics,
            )
        )
    for row in failed:
        ranked.append(row)
    return ranked


def _build_best_feature_importance(
    *,
    config: YanOptimizationConfig,
    candidate: YanOptimizationResultRow,
    feature_cache: dict[tuple[tuple[str, Any], ...], pd.DataFrame],
) -> pd.DataFrame | None:
    candidate_model = YanModelCandidate(
        model_family=candidate.model_family,
        model_parameters=dict(candidate.model_parameters),
        label=candidate.model_label,
    )
    selected_base_features = _selected_base_features_from_slot_ids(candidate.selected_features)
    candidate_blueprint = YanOptimizationCandidate(
        selected_features=selected_base_features,
        math_choices=candidate.math_choices,
        model_candidate=candidate_model,
    )
    frame = _build_feature_frame(samples=config.samples, candidate=candidate_blueprint, feature_cache=feature_cache)
    selected_columns = _resolve_selected_columns(frame.columns, candidate_blueprint.selected_features)
    if not selected_columns:
        return None

    X = frame.loc[:, selected_columns].apply(pd.to_numeric, errors="coerce")
    y = _build_target_vector(config.samples, config.task_kind)
    y_encoded, _class_labels, _ordinal_map = _encode_target(y, config)
    estimator = build_estimator(
        candidate.model_family,
        dict(candidate.model_parameters),
        config.preprocessing,
    )
    estimator.fit(X, y_encoded)
    importance_records = extract_feature_importance(estimator, list(selected_columns))
    if not importance_records:
        return None
    return pd.DataFrame(
        {
            "feature": [record.feature for record in importance_records],
            "importance": [record.importance for record in importance_records],
            "absolute_importance": [record.absolute_importance for record in importance_records],
            "source": [record.source for record in importance_records],
        }
    ).sort_values("absolute_importance", ascending=False).reset_index(drop=True)


def _build_resolved_config(
    config: YanOptimizationConfig,
    *,
    candidate_blueprints: Sequence[YanOptimizationCandidate],
    best_candidate: YanOptimizationResultRow | None,
) -> dict[str, Any]:
    family_specs = _resolved_feature_family_specs(config)
    model_candidates = config.model_candidates or default_model_candidates(config.task_kind)
    return {
        "task_kind": config.task_kind,
        "label_order": list(config.label_order) if config.label_order else None,
        "feature_pool": list(config.feature_pool),
        "required_features": list(config.required_features),
        "feature_subset_mode": config.feature_subset_mode,
        "max_feature_count": config.max_feature_count,
        "folds": config.folds,
        "shuffle": config.shuffle,
        "random_state": config.random_state,
        "primary_metric": _primary_metric_name(config),
        "max_candidates": config.max_candidates,
        "samples": [
            {
                "sample_id": sample.sample_id,
                "score_path": str(sample.score_path),
                "label": sample.label,
                "metadata": sample.metadata,
            }
            for sample in config.samples
        ],
        "feature_family_specs": [
            {
                "base_feature": spec.base_feature,
                "choices": [
                    {
                        "choice_name": choice.choice_name,
                        "extractor_kwargs": choice.extractor_kwargs,
                        "notes": choice.notes,
                    }
                    for choice in spec.choices
                ],
                "notes": spec.notes,
            }
            for spec in family_specs
        ],
        "model_candidates": [asdict(candidate) for candidate in model_candidates],
        "candidate_blueprints": [candidate.to_dict() for candidate in candidate_blueprints],
        "best_candidate_id": best_candidate.candidate_id if best_candidate else None,
    }


def _build_summary(
    *,
    config: YanOptimizationConfig,
    candidate_rows: Sequence[YanOptimizationResultRow],
    best_candidate: YanOptimizationResultRow | None,
) -> dict[str, Any]:
    successful = [row for row in candidate_rows if row.status == "success" and row.metric_value is not None]
    failed = [row for row in candidate_rows if row.status != "success"]
    best_metric = best_candidate.metric_value if best_candidate else None
    return {
        "task_kind": config.task_kind,
        "primary_metric": _primary_metric_name(config),
        "candidate_count": len(candidate_rows),
        "successful_candidate_count": len(successful),
        "failed_candidate_count": len(failed),
        "best_candidate_id": best_candidate.candidate_id if best_candidate else None,
        "best_metric_value": best_metric,
        "best_model_family": best_candidate.model_family if best_candidate else None,
        "best_selected_feature_count": best_candidate.selected_feature_count if best_candidate else None,
        "feature_pool_size": len(config.feature_pool) or len(default_feature_pool()),
        "feature_family_count": len(_resolved_feature_family_specs(config)),
    }


def _write_candidate_results(path: Path, rows: Sequence[YanOptimizationResultRow]) -> None:
    frame = pd.DataFrame([row.to_dict() for row in rows])
    frame.to_csv(path, index=False)


def _allocate_run_dir(config: YanOptimizationConfig) -> Path:
    root = Path(config.out_dir or DEFAULT_RUNS_ROOT).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_label = _slugify(config.run_name or "yan-feature-optimization")
    candidate = root / f"{timestamp}__{run_label}"
    if candidate.exists():
        suffix = 2
        while True:
            numbered = root / f"{timestamp}__{run_label}-{suffix}"
            if not numbered.exists():
                return numbered
            suffix += 1
    return candidate


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value).strip().lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "run"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, set):
        return sorted(value)
    return str(value)


__all__ = [
    "DEFAULT_ARTIFACTS_ROOT",
    "DEFAULT_RUNS_ROOT",
    "YanFeatureFamilySpec",
    "YanFeatureMathChoice",
    "YanModelCandidate",
    "YanOptimizationCandidate",
    "YanOptimizationConfig",
    "YanOptimizationResultRow",
    "YanOptimizationSample",
    "YanFeatureOptimizationRunResult",
    "YanPreprocessingConfig",
    "build_feature_subset_candidates",
    "default_feature_family_specs",
    "default_feature_pool",
    "default_model_candidates",
    "generate_candidate_blueprints",
    "load_optimization_samples_from_csv",
    "main",
    "run_feature_optimization",
]
