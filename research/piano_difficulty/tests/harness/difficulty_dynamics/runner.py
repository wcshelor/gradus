"""Command-line runner for the Difficulty Dynamics lane."""

from __future__ import annotations

import argparse
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .config import load_difficulty_dynamics_config
from .core import build_difficulty_profile, run_difficulty_dynamics
from .exports import (
    export_hotspots_csv,
    export_peaks_json,
    export_profile_csv,
    export_profile_json,
    export_summary_markdown,
)
from .models import DifficultyDynamicsConfig, DifficultyDynamicsRunResult

PlotXAxisMode = Literal["measure", "score_position"]


def run_experiment_from_config(
    config: DifficultyDynamicsConfig | str | Path,
    runs_root: str | Path | None = None,
) -> DifficultyDynamicsRunResult:
    experiment_config = config if isinstance(config, DifficultyDynamicsConfig) else load_difficulty_dynamics_config(config)
    if runs_root is not None:
        experiment_config = DifficultyDynamicsConfig(
            experiment_name=experiment_config.experiment_name,
            score_path=experiment_config.score_path,
            feature_ids=experiment_config.feature_ids,
            hand_mode=experiment_config.hand_mode,
            score_id=experiment_config.score_id,
            window=experiment_config.window,
            normalization=experiment_config.normalization,
            smoothing=experiment_config.smoothing,
            composite=experiment_config.composite,
            peaks=experiment_config.peaks,
            export=experiment_config.export.__class__(
                output_root=Path(runs_root).expanduser(),
                run_name=experiment_config.export.run_name,
                json_filename=experiment_config.export.json_filename,
                csv_filename=experiment_config.export.csv_filename,
                peaks_filename=experiment_config.export.peaks_filename,
                hotspots_filename=experiment_config.export.hotspots_filename,
                report_filename=experiment_config.export.report_filename,
                plot_filename=experiment_config.export.plot_filename,
                write_plot=experiment_config.export.write_plot,
            ),
            config_path=experiment_config.config_path,
        )
    return run_experiment(experiment_config)


def run_experiment(config: DifficultyDynamicsConfig) -> DifficultyDynamicsRunResult:
    score, profile = run_difficulty_dynamics(config)

    config.export.output_root.mkdir(parents=True, exist_ok=True)
    run_dir = _allocate_run_dir(config.export.output_root, config)
    run_dir.mkdir(parents=True, exist_ok=False)

    json_path = run_dir / config.export.json_filename
    csv_path = run_dir / config.export.csv_filename
    peaks_path = run_dir / config.export.peaks_filename
    hotspots_path = run_dir / config.export.hotspots_filename
    report_path = run_dir / config.export.report_filename
    plot_path = run_dir / config.export.plot_filename if config.export.write_plot else None

    export_profile_json(profile, json_path)
    export_profile_csv(profile, csv_path)
    export_peaks_json(profile, peaks_path)
    export_hotspots_csv(profile, hotspots_path)
    export_summary_markdown(profile, report_path)
    if plot_path is not None:
        _export_profile_plot(profile, plot_path, x_axis="measure")

    (run_dir / "resolved_config.json").write_text(
        _json_text(
            {
                "experiment_name": config.experiment_name,
                "score_path": str(config.score_path),
                "score_id": config.score_id,
                "feature_ids": list(config.feature_ids),
                "hand_mode": config.hand_mode,
                "window": {
                    "kind": config.window.kind,
                    "size": config.window.size,
                    "step": config.window.step,
                    "final_window_behavior": config.window.final_window_behavior,
                },
                "normalization": {"method": config.normalization.method},
                "smoothing": {
                    "method": config.smoothing.method,
                    "window_size": config.smoothing.window_size,
                    "centered": config.smoothing.centered,
                },
                "composite": {
                    "enabled": config.composite.enabled,
                    "feature_ids": list(config.composite.feature_ids or config.feature_ids),
                    "weights": dict(config.composite.weights),
                    "minimum_valid_features": config.composite.minimum_valid_features,
                    "exclude_missing": config.composite.exclude_missing,
                    "output_feature_id": config.composite.output_feature_id,
                },
                "peaks": {
                    "method": config.peaks.method,
                    "top_n": config.peaks.top_n,
                    "percentile": config.peaks.percentile,
                    "minimum_separation": config.peaks.minimum_separation,
                },
                "export": {
                    "output_root": str(config.export.output_root),
                    "run_name": config.export.run_name,
                    "json_filename": config.export.json_filename,
                    "csv_filename": config.export.csv_filename,
                    "peaks_filename": config.export.peaks_filename,
                    "hotspots_filename": config.export.hotspots_filename,
                    "report_filename": config.export.report_filename,
                    "plot_filename": config.export.plot_filename,
                    "write_plot": config.export.write_plot,
                },
                "source_path": str(score.source_path) if score.source_path is not None else None,
            }
        )
    )

    return DifficultyDynamicsRunResult(
        run_dir=run_dir,
        json_path=json_path,
        csv_path=csv_path,
        peaks_path=peaks_path,
        hotspots_path=hotspots_path,
        report_path=report_path,
        plot_path=plot_path,
        profile=profile,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Difficulty Dynamics demo pipeline.")
    parser.add_argument("config", type=Path, help="Path to a Difficulty Dynamics YAML config.")
    parser.add_argument("--runs-root", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run_experiment_from_config(args.config, runs_root=args.runs_root)
    print(
        _json_text(
            {
                "run_dir": str(result.run_dir),
                "json_path": str(result.json_path),
                "csv_path": str(result.csv_path),
                "peaks_path": str(result.peaks_path),
                "hotspots_path": str(result.hotspots_path),
                "report_path": str(result.report_path),
                "plot_path": None if result.plot_path is None else str(result.plot_path),
                "profile": result.profile.to_payload(),
            }
        )
    )
    return 0


def _allocate_run_dir(output_root: Path, config: DifficultyDynamicsConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    label = _slugify(config.export.run_name or config.experiment_name)
    candidate = output_root / f"{timestamp}__{label}"
    if candidate.exists():
        suffix = 2
        while True:
            numbered = output_root / f"{timestamp}__{label}-{suffix}"
            if not numbered.exists():
                return numbered
            suffix += 1
    return candidate


def _slugify(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in text).strip("-") or "difficulty-dynamics"


def _json_text(payload: object) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


def _export_profile_plot(
    profile,
    path: Path,
    *,
    x_axis: PlotXAxisMode = "measure",
    top_contributor_count: int | None = None,
) -> None:
    feature_series = _select_plot_feature_series(profile, top_contributor_count=top_contributor_count)
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        figure, axis = plt.subplots(figsize=(9, 4))
        series_to_plot = [*feature_series]
        if profile.overall_series is not None:
            series_to_plot.append(profile.overall_series)
        for series in series_to_plot:
            values = [value if value is not None else float("nan") for value in series.smoothed_values]
            axis.plot(
                [_region_axis_value(region, x_axis) for region in series.regions],
                values,
                marker="o",
                label=series.feature_name or series.feature_id,
            )
        axis.set_title("Difficulty Dynamics")
        axis.set_xlabel("Measure" if x_axis == "measure" else "Score position")
        axis.set_ylabel("Normalized difficulty")
        axis.legend(loc="best")
        figure.tight_layout()
        figure.savefig(path)
        plt.close(figure)
        return
    except Exception:
        pass

    _export_profile_plot_with_pillow(profile, path, x_axis=x_axis, top_contributor_count=top_contributor_count)


def _export_profile_plot_with_pillow(
    profile,
    path: Path,
    *,
    x_axis: PlotXAxisMode = "measure",
    top_contributor_count: int | None = None,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width = 1440
    height = 760
    left_margin = 88
    top_margin = 84
    right_margin = 410
    bottom_margin = 92

    plot_left = left_margin
    plot_top = top_margin
    plot_right = width - right_margin
    plot_bottom = height - bottom_margin

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    title = profile.score_title or profile.score_id or "unknown score"
    composer = profile.score_composer or "unknown composer"
    subtitle = f"{composer} | {len(profile.regions)} windows | {len(profile.series)} tracks"
    draw.text((plot_left, 22), "Difficulty Dynamics", fill=(20, 20, 20), font=font)
    draw.text((plot_left, 42), title, fill=(50, 50, 50), font=font)
    draw.text((plot_left, 58), subtitle, fill=(90, 90, 90), font=font)

    series_to_plot = [*_select_plot_feature_series(profile, top_contributor_count=top_contributor_count)]
    if profile.overall_series is not None:
        series_to_plot.append(profile.overall_series)

    plotted_series: list[tuple[object, list[tuple[float, float]]]] = []
    all_points: list[tuple[float, float]] = []
    for series in series_to_plot:
        values = list(series.smoothed_values)
        if not any(value is not None for value in values):
            values = list(series.normalized_values)
        points: list[tuple[float, float]] = []
        for region, value in zip(series.regions, values):
            if value is None:
                continue
            try:
                x_value = _region_axis_value(region, x_axis)
                y_value = float(value)
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(x_value) and math.isfinite(y_value)):
                continue
            point = (x_value, y_value)
            points.append(point)
            all_points.append(point)
        plotted_series.append((series, points))

    if not all_points:
        draw.text((plot_left, plot_top), "No finite series values available for plotting.", fill=(180, 0, 0), font=font)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        return

    x_min = min(point[0] for point in all_points)
    x_max = max(point[0] for point in all_points)
    y_min = min(point[1] for point in all_points)
    y_max = max(point[1] for point in all_points)
    if x_max == x_min:
        x_min -= 0.5
        x_max += 0.5
    if y_max == y_min:
        y_min -= 0.5
        y_max += 0.5
    y_padding = max((y_max - y_min) * 0.08, 0.05)
    y_min -= y_padding
    y_max += y_padding

    def map_x(x_value: float) -> float:
        return plot_left + (x_value - x_min) / (x_max - x_min) * (plot_right - plot_left)

    def map_y(y_value: float) -> float:
        return plot_bottom - (y_value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

    draw.rectangle([plot_left, plot_top, plot_right, plot_bottom], outline=(200, 200, 200), width=1)

    grid_color = (228, 228, 228)
    tick_color = (90, 90, 90)
    for index in range(5):
        tick_value = y_min + (y_max - y_min) * index / 4
        y_position = map_y(tick_value)
        draw.line((plot_left, y_position, plot_right, y_position), fill=grid_color, width=1)
        draw.text((18, y_position - 6), f"{tick_value:.2f}", fill=tick_color, font=font)

    for index in range(3):
        tick_value = x_min + (x_max - x_min) * index / 2
        x_position = map_x(tick_value)
        draw.line((x_position, plot_top, x_position, plot_bottom), fill=(236, 236, 236), width=1)
        draw.text((x_position - 12, plot_bottom + 8), _format_axis_value(tick_value), fill=tick_color, font=font)

    x_axis_label = "Measure" if x_axis == "measure" else "Score position"
    draw.text((plot_left + (plot_right - plot_left) / 2 - 52, plot_bottom + 28), x_axis_label, fill=tick_color, font=font)
    draw.text((10, plot_top - 10), "Normalized difficulty", fill=tick_color, font=font)

    palette = [
        (66, 135, 245),
        (227, 82, 72),
        (56, 170, 113),
        (171, 101, 230),
        (242, 156, 49),
        (76, 165, 190),
        (118, 124, 138),
        (222, 84, 147),
        (139, 195, 74),
        (255, 112, 67),
    ]

    composite = profile.overall_series
    for index, (series, points) in enumerate(plotted_series):
        color = (0, 0, 0) if composite is not None and series is composite else palette[index % len(palette)]
        width = 4 if composite is not None and series is composite else 2
        label = series.feature_name or series.feature_id
        if composite is not None and series is composite:
            label = f"{label} (composite)"

        if len(points) == 1:
            x_value, y_value = points[0]
            x_position = map_x(x_value)
            y_position = map_y(y_value)
            draw.ellipse((x_position - 3, y_position - 3, x_position + 3, y_position + 3), fill=color, outline=color)
        elif len(points) > 1:
            scaled_points = [(map_x(x_value), map_y(y_value)) for x_value, y_value in points]
            draw.line(scaled_points, fill=color, width=width)
            for x_position, y_position in scaled_points:
                draw.ellipse((x_position - 2, y_position - 2, x_position + 2, y_position + 2), fill=color, outline=color)

    legend_x = plot_right + 24
    legend_y = plot_top + 4
    draw.text((legend_x, legend_y - 24), "Series", fill=(20, 20, 20), font=font)
    for index, (series, _points) in enumerate(plotted_series):
        color = (0, 0, 0) if composite is not None and series is composite else palette[index % len(palette)]
        width = 4 if composite is not None and series is composite else 2
        label = series.feature_name or series.feature_id
        if composite is not None and series is composite:
            label = f"{label} (composite)"
        draw.line((legend_x, legend_y + 7, legend_x + 26, legend_y + 7), fill=color, width=width)
        draw.text((legend_x + 36, legend_y), label, fill=(20, 20, 20), font=font)
        legend_y += 22

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _select_plot_feature_series(
    profile,
    *,
    top_contributor_count: int | None = None,
) -> list[object]:
    feature_series = list(profile.series.values())
    if top_contributor_count is None:
        return feature_series
    if top_contributor_count <= 0:
        return []

    ranked_series = sorted(feature_series, key=lambda series: _plot_series_sort_key(profile, series))
    return ranked_series[:top_contributor_count]


def _plot_series_sort_key(profile, series) -> tuple[int, float, float, str, str]:
    hotspot_score = _feature_hotspot_score(profile, series.feature_id)
    activity_score = _series_activity_score(series)
    return (
        0 if hotspot_score > 0 else 1,
        -hotspot_score,
        -activity_score,
        series.feature_name or series.feature_id,
        series.feature_id,
    )


def _feature_hotspot_score(profile, feature_id: str) -> float:
    score = 0.0
    for hotspot in profile.hard_spots:
        if not hotspot.feature_contributions:
            continue
        contribution = next(
            (item for item in hotspot.feature_contributions if item.feature_id == feature_id),
            None,
        )
        if contribution is None:
            continue
        weighted_value = max(float(contribution.weighted_value), 0.0)
        if weighted_value <= 0.0:
            continue
        score += weighted_value * max(hotspot.support_count, 1)
    return score


def _series_activity_score(series) -> float:
    values = list(series.smoothed_values)
    if not any(value is not None for value in values):
        values = list(series.normalized_values)

    finite_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not finite_values:
        return 0.0
    positive_values = [max(value, 0.0) for value in finite_values]
    return sum(positive_values) / len(positive_values)


def _region_axis_value(region, x_axis: PlotXAxisMode) -> float:
    if x_axis == "measure":
        if region.measure_start is not None and region.measure_end is not None:
            return float((region.measure_start + region.measure_end) / 2)
        if region.measure_start is not None:
            return float(region.measure_start)
    if region.position is not None:
        return float(region.position)
    return float(region.window_index)


def _format_axis_value(value: float) -> str:
    rounded = round(value)
    if math.isclose(value, rounded):
        return f"{rounded:.0f}"
    return f"{value:.1f}"
