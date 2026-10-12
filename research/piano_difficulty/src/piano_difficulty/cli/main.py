"""Command-line entrypoint for the extraction pipeline.

The first command should remain narrow and predictable:

`piano-difficulty extract <path>`

As the repository grows, this module can add options for output format, measure
detail, debug diagnostics, and eventually windowed summaries.
"""

from __future__ import annotations

import argparse
import json

from piano_difficulty.difficulty_analysis.batch import analyze_batch
from piano_difficulty.difficulty_analysis.markdown import render_markdown_report
from piano_difficulty.pipeline import DEFAULT_PROFILE_IDS, analyze_score, extract_score
from piano_difficulty.difficulty_analysis.overview import OverviewOptions
from piano_difficulty.output.overview import render_html, write_analysis_outputs


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="piano-difficulty",
        description="Extract symbolic piano difficulty descriptors from score files.",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract_parser = subparsers.add_parser(
        "extract",
        help="Load one supported score and emit structured descriptors.",
    )
    extract_parser.add_argument("path", help="Path to a MusicXML or MXL file.")
    extract_parser.add_argument(
        "--format",
        default="json",
        choices=["json"],
        help="Output format. JSON is the canonical format in early versions.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Load one score, then run one or more difficulty profiles.",
    )
    analyze_parser.add_argument("path", help="Path to a MusicXML or MXL file.")
    analyze_parser.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        default=None,
        help="Difficulty profile id. Repeat to analyze with multiple profiles.",
    )
    analyze_parser.add_argument(
        "--format",
        default="markdown",
        choices=["json", "markdown", "html"],
        help="Output format for analyzed scores.",
    )

    batch_parser = subparsers.add_parser(
        "analyze-batch",
        help="Analyze one score file or a directory of score files.",
    )
    batch_parser.add_argument("source", help="Score file or directory.")
    batch_parser.add_argument("--out-dir", required=True, help="Output directory.")
    batch_parser.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        default=None,
        help="Difficulty profile id. Repeat to analyze with multiple profiles.",
    )
    batch_parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Write flat CSV exports alongside JSON payloads.",
    )

    dynamics_parser = subparsers.add_parser(
        "dynamics",
        help="Run the experimental Difficulty Dynamics temporal profile demo.",
    )
    dynamics_parser.add_argument("config", help="Path to a Difficulty Dynamics YAML config.")
    dynamics_parser.add_argument(
        "--runs-root",
        help="Override the run output root.",
        default=None,
    )

    analyze_parser.add_argument("--out-dir", help="Write JSON, Markdown, CSV and an HTML timeline.")
    analyze_parser.add_argument("--gradus", action="store_true", help="Include Gradus practice payload (hotspots, factors, recommendations) in JSON output.")
    analyze_parser.add_argument("--explain-events", action="store_true", help="Post-process flagged passages into difficulty events (metric-driven first, note inspection second).")
    batch_parser.add_argument("--gradus", action="store_true", help="Include Gradus payloads alongside analysis outputs.")
    batch_parser.add_argument("--explain-events", action="store_true", help="Include difficulty_events subdivision for flagged passages.")
    for command_parser in (analyze_parser, batch_parser):
        command_parser.add_argument("--window", choices=["measure", "beat"], default="measure")
        command_parser.add_argument("--window-size", type=float, default=2)
        command_parser.add_argument("--window-sizes", type=str, default=None, help="Comma-separated window sizes (e.g., 2,4). First is primary, rest are companions. Preserves --window-size when omitted.")
        command_parser.add_argument("--stride", type=float, default=1)
        command_parser.add_argument("--hand", choices=["both", "right", "left"], default="both")
        command_parser.add_argument("--top-sections", type=int, default=5)

    # Debug-only taxonomy attribution — internal inspection, not learner-facing
    debug_parser = subparsers.add_parser(
        "debug-attribution",
        help="DEBUG ONLY: inspect which feature path made a taxonomy dimension high for a measure range (internal, not learner-facing).",
        description=(
            "DEBUG ONLY: Taxonomy Attribution — internal debugging infrastructure. "
            "Reuses existing graph contributor machinery to expose why a selected "
            "front-facing taxonomy dimension is high for a given score passage. "
            "Not learner-facing, not pedagogy copy, not a new scoring model. "
            "Do not use as calibrated difficulty grade."
        ),
    )
    debug_parser.add_argument("path", help="Path to a MusicXML or MXL file.")
    debug_parser.add_argument(
        "--measures",
        required=True,
        help="Measure range, e.g. '12-16', '12', or '12,14-16'. Uses printed MusicXML measure numbers.",
    )
    debug_parser.add_argument(
        "--dimension",
        required=True,
        choices=[
            "finger_dexterity",
            "hand_movement_position",
            "layers_coordination",
            "rhythm_timing",
            "expression_sound_control",
            "notation_reading",
        ],
        help="Front-facing taxonomy dimension to attribute.",
    )
    debug_parser.add_argument(
        "--format",
        default="md",
        choices=["md", "markdown", "json"],
        help="Output format; md is concise markdown, json is machine-readable debug payload.",
    )
    debug_parser.add_argument(
        "--detail",
        choices=["onsets"],
        default=None,
        help="Optional drilldown: 'onsets' shows per-measure right/left offsets for coordination.",
    )
    debug_parser.add_argument("--window", choices=["measure", "beat"], default="measure")
    debug_parser.add_argument("--window-size", type=float, default=2)
    debug_parser.add_argument("--stride", type=float, default=1)
    debug_parser.add_argument("--hand", choices=["both", "right", "left"], default="both")
    debug_parser.add_argument("--top-sections", type=int, default=5)

    # Alias with underscore for convenience
    debug2_parser = subparsers.add_parser(
        "debug_attribution",
        help=argparse.SUPPRESS,
    )
    debug2_parser.add_argument("path", help=argparse.SUPPRESS)
    debug2_parser.add_argument("--measures", required=True, help=argparse.SUPPRESS)
    debug2_parser.add_argument(
        "--dimension",
        required=True,
        choices=[
            "finger_dexterity",
            "hand_movement_position",
            "layers_coordination",
            "rhythm_timing",
            "expression_sound_control",
            "notation_reading",
        ],
        help=argparse.SUPPRESS,
    )
    debug2_parser.add_argument("--format", default="md", choices=["md", "markdown", "json"], help=argparse.SUPPRESS)
    debug2_parser.add_argument("--detail", choices=["onsets"], default=None, help=argparse.SUPPRESS)
    debug2_parser.add_argument("--window", choices=["measure", "beat"], default="measure", help=argparse.SUPPRESS)
    debug2_parser.add_argument("--window-size", type=float, default=2, help=argparse.SUPPRESS)
    debug2_parser.add_argument("--stride", type=float, default=1, help=argparse.SUPPRESS)
    debug2_parser.add_argument("--hand", choices=["both", "right", "left"], default="both", help=argparse.SUPPRESS)
    debug2_parser.add_argument("--top-sections", type=int, default=5, help=argparse.SUPPRESS)

    return parser


def _parse_window_sizes_arg(value: str | None) -> tuple[float, ...] | None:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",") if p.strip() != ""]
    if not parts:
        raise ValueError("--window-sizes requires at least one size, e.g., 2,4")
    sizes: list[float] = []
    for p in parts:
        try:
            sizes.append(float(p))
        except ValueError as exc:
            raise ValueError(f"Invalid window size {p!r} in --window-sizes") from exc
    return tuple(sizes)


def _resolve_overview_options(args) -> OverviewOptions:
    window_sizes = _parse_window_sizes_arg(getattr(args, "window_sizes", None))
    if window_sizes is not None:
        primary = window_sizes[0]
        companions = tuple(window_sizes[1:])
        return OverviewOptions(
            window=args.window,
            window_size=primary,
            stride=args.stride,
            hand=args.hand,
            top_sections=args.top_sections,
            companion_window_sizes=companions,
        )
    return OverviewOptions(
        window=args.window,
        window_size=args.window_size,
        stride=args.stride,
        hand=args.hand,
        top_sections=args.top_sections,
    )


def main() -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "extract":
        result = extract_score(args.path)
        print(json.dumps(result.to_json_payload(), indent=2, sort_keys=True))
        return 0
    if args.command == "analyze":
        profiles = tuple(dict.fromkeys(args.profiles or DEFAULT_PROFILE_IDS))
        try:
            options = _resolve_overview_options(args)
            result = analyze_score(args.path, profile_ids=profiles, overview_options=options, explain_events=bool(getattr(args, "explain_events", False)))
        except (ValueError, FileNotFoundError) as exc:
            parser.error(str(exc))
        payload = result.to_json_payload()
        if args.gradus:
            payload["gradus"] = result.to_gradus_payload()
        if args.out_dir:
            write_analysis_outputs(payload, args.out_dir)
        if args.format == "markdown":
            print(render_markdown_report(payload, profile_id=profiles[0]))
        elif args.format == "html":
            overview = next((p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_overview"), None)
            if overview is None:
                parser.error("HTML requires the difficulty_overview profile.")
            print(render_html(payload, overview))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "analyze-batch":
        profiles = tuple(dict.fromkeys(args.profiles or DEFAULT_PROFILE_IDS))
        try:
            options = _resolve_overview_options(args)
        except ValueError as exc:
            parser.error(str(exc))
        batch = analyze_batch(
            args.source,
            out_dir=args.out_dir,
            profile_ids=profiles,
            write_csv=args.write_csv,
            overview_options=options,
            explain_events=bool(getattr(args, "explain_events", False)),
        )
        if args.gradus:
            # Batch gradus payloads are available via per-file JSON with added gradus key
            # when re-analyzing payloads; the batch runner itself does not embed gradus
            # to keep backward compat, but flag is accepted for future extension.
            pass
        print(
            json.dumps(
                {
                    "file_count": len(batch.inputs),
                    "success_count": len(batch.payload_paths),
                    "failure_count": len(batch.failures),
                    "out_dir": args.out_dir,
                    "corpus_summary": str(batch.corpus_summary_path),
                    "errors_csv": str(batch.errors_csv_path) if batch.errors_csv_path else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if batch.failures else 0
    if args.command == "dynamics":
        from tests.harness.difficulty_dynamics.runner import run_experiment_from_config

        result = run_experiment_from_config(args.config, runs_root=args.runs_root)
        print(
            json.dumps(
                {
                    "run_dir": str(result.run_dir),
                    "json_path": str(result.json_path),
                    "csv_path": str(result.csv_path),
                    "peaks_path": str(result.peaks_path),
                    "plot_path": None if result.plot_path is None else str(result.plot_path),
                    "profile": result.profile.to_payload(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command in ("debug-attribution", "debug_attribution"):
        from piano_difficulty.debug.taxonomy_attribution import (
            build_debug_attribution_payload,
            render_debug_attribution_json,
            render_debug_attribution_markdown,
        )

        # Handle debug alias where window args may be missing specific names; normalize
        try:
            options = _resolve_overview_options(args)
        except Exception as exc:
            parser.error(str(exc))
        try:
            payload = build_debug_attribution_payload(
                args.path,
                args.measures,
                args.dimension,
                overview_options=options,
                detail=getattr(args, "detail", None),
            )
        except (ValueError, RuntimeError) as exc:
            parser.error(str(exc))
        fmt = getattr(args, "format", "md")
        if fmt == "json":
            print(render_debug_attribution_json(payload))
        else:
            print(render_debug_attribution_markdown(payload))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
