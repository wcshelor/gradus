from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.difficulty_analysis.scoreanalyzer_reference import (
    mark_chords,
    mark_displacement,
    mark_harmony,
    mark_length,
    mark_rhythm,
    mark_speed,
    mark_tonality,
)
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir

CANONICAL_METRICS: tuple[str, ...] = (
    "fifths",
    "mode",
    "nbmeasures",
    "quantise",
    "baseDuration",
    "tempo",
    "beats",
    "beatType",
    "quickestValue",
    "maxIntervalRH",
    "maxIntervalLH",
    "octavesRatioRH",
    "octavesRatioLH",
    "noteCounterRH",
    "noteCounterLH",
    "nbPositionsRH",
    "nbPositionsLH",
    "speed",
    "displacementsRH",
    "chordsRH",
    "harmonyRH",
    "displacementsLH",
    "chordsLH",
    "harmonyLH",
    "rhythm",
    "length",
    "speedDifficulty",
    "displacementsDifficulty",
    "chordsDifficulty",
    "harmonyDifficulty",
    "rhythmDifficulty",
    "lengthDifficulty",
    "tonalityDifficulty",
    "overallDifficulty",
)

FLOAT_TOLERANCE = 1e-9
ROUND_TO_INT_METRICS = frozenset(
    {
        "displacementsRH",
        "displacementsLH",
        "chordsRH",
        "chordsLH",
        "harmonyRH",
        "harmonyLH",
        "rhythm",
    }
)


def _default_scoreanalyzer_root() -> Path:
    candidates = (
        Path("external/ScoreAnalyzer"),
        Path("reference_code/ScoreAnalyzer"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _default_pieces_root() -> Path:
    return _default_scoreanalyzer_root() / "pieces"


def _resolve_shim_path(pieces_root: Path) -> Path:
    candidate = pieces_root.parent / "scoreanalyzer_json.php"
    if candidate.exists():
        return candidate
    return _default_scoreanalyzer_root() / "scoreanalyzer_json.php"


def _default_artifacts_dir() -> Path:
    return Path("tests/artifacts/scoreanalyzer_parity")


def _default_out_csv() -> Path:
    return _default_artifacts_dir() / "comparison.csv"


@dataclass(slots=True)
class CompareRow:
    piece_relpath: str
    status: str
    error: str
    values: dict[str, Any]
    all_equal: bool
    mismatch_count: int


def discover_piece_files(pieces_root: Path) -> list[Path]:
    supported = {".xml", ".musicxml", ".mxl"}
    return sorted(
        [
            path
            for path in pieces_root.rglob("*")
            if path.is_file() and path.suffix.lower() in supported
        ],
        key=lambda p: str(p.relative_to(pieces_root)),
    )


def select_piece_files(all_files: list[Path], *, count: int, start_offset: int) -> list[Path]:
    if count <= 0:
        raise ValueError("--count must be > 0")
    if start_offset < 0:
        raise ValueError("--start-offset must be >= 0")
    return all_files[start_offset : start_offset + count]


def run_og_php_metrics(php_bin: Path, shim_path: Path, piece_dir: str) -> dict[str, Any]:
    completed = subprocess.run(
        [str(php_bin), str(shim_path), "--piece", piece_dir],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "OG php run failed")
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("OG php output is not valid JSON") from exc
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return flatten_og_payload(payload)


def flatten_og_payload(payload: dict[str, Any]) -> dict[str, Any]:
    stats = payload.get("stats", {})
    criteria = payload.get("criteria", {})
    merged = {**stats, **criteria}
    return {metric: merged.get(metric) for metric in CANONICAL_METRICS}


def run_replica_metrics(score_path: Path) -> dict[str, Any]:
    score = build_score_ir(load_musicxml_document(score_path))
    metrics = compute_reference_metrics(score)
    rh = metrics.hand_metrics["right"]
    lh = metrics.hand_metrics["left"]

    quickest_value = float(metrics.significant_shortest_value)
    speed_value = (
        metrics.initial_tempo_bpm * quickest_value
        if metrics.initial_tempo_bpm is not None
        else None
    )
    speed_ratio = (speed_value * 100 / 2816) if speed_value is not None else None
    rhythm_ratio = (len(metrics.polyrhythm_measures) / len(score.measures) * 100.0) if score.measures else None
    fifths_abs = abs(metrics.initial_key_fifths) if metrics.initial_key_fifths is not None else None

    merged: dict[str, Any] = {
        "fifths": metrics.initial_key_fifths,
        "mode": score.measures[0].key_mode if score.measures and score.measures[0].key_mode else None,
        "nbmeasures": len(score.measures),
        "quantise": _quantise_value(score),
        "baseDuration": _base_duration_value(score),
        "tempo": metrics.initial_tempo_bpm,
        "beats": score.measures[0].time_beats if score.measures else None,
        "beatType": score.measures[0].time_beat_type if score.measures else None,
        "quickestValue": quickest_value,
        "maxIntervalRH": rh.max_timed_difficult_displacement,
        "maxIntervalLH": lh.max_timed_difficult_displacement,
        "octavesRatioRH": rh.octave_chord_ratio,
        "octavesRatioLH": lh.octave_chord_ratio,
        "noteCounterRH": rh.note_count,
        "noteCounterLH": lh.note_count,
        "nbPositionsRH": rh.position_count,
        "nbPositionsLH": lh.position_count,
        "speed": speed_value,
        "displacementsRH": rh.timed_difficult_displacement_ratio,
        "chordsRH": rh.chord_ratio,
        "harmonyRH": rh.accidental_ratio,
        "displacementsLH": lh.timed_difficult_displacement_ratio,
        "chordsLH": lh.chord_ratio,
        "harmonyLH": lh.accidental_ratio,
        "rhythm": rhythm_ratio,
        "length": metrics.page_count,
    }
    merged["speedDifficulty"] = mark_speed(speed_ratio)
    merged["displacementsDifficulty"] = mark_displacement(merged["displacementsRH"], merged["displacementsLH"])
    merged["chordsDifficulty"] = mark_chords(merged["chordsRH"], merged["chordsLH"])
    merged["harmonyDifficulty"] = mark_harmony(merged["harmonyRH"], merged["harmonyLH"])
    merged["rhythmDifficulty"] = mark_rhythm(merged["rhythm"])
    merged["lengthDifficulty"] = mark_length(metrics.page_count)
    merged["tonalityDifficulty"] = mark_tonality(fifths_abs)

    marks = [
        merged["speedDifficulty"],
        merged["displacementsDifficulty"],
        merged["chordsDifficulty"],
        merged["harmonyDifficulty"],
        merged["rhythmDifficulty"],
        merged["lengthDifficulty"],
        merged["tonalityDifficulty"],
    ]
    merged["overallDifficulty"] = round(sum(marks) / len(marks), 1) if all(mark is not None for mark in marks) else None
    return {metric: merged.get(metric) for metric in CANONICAL_METRICS}


def _quantise_value(score: Any) -> float | None:
    values = [_note_value(note, include_tuplet=False) for note in score.written_notes]
    filtered = [value for value in values if value is not None]
    return max(filtered) if filtered else None


def _base_duration_value(score: Any) -> float | None:
    durations = [float(note.duration) for note in score.written_notes if not note.tuplet_actual and note.duration > 0]
    return min(durations) if durations else None


def _note_value(note: Any, *, include_tuplet: bool) -> float | None:
    mapping = {
        "whole": 1.0,
        "half": 2.0,
        "quarter": 4.0,
        "eighth": 8.0,
        "16th": 16.0,
        "32nd": 32.0,
        "64th": 64.0,
        "128th": 128.0,
        "256th": 256.0,
    }
    base = mapping.get(note.duration_type)
    if base is None:
        return None
    if include_tuplet and note.tuplet_actual and note.tuplet_normal:
        return base * (note.tuplet_actual / note.tuplet_normal)
    return base


def compare_values(metric: str, og_value: Any, replica_value: Any) -> tuple[bool, float | None]:
    if og_value is None or replica_value is None:
        return (og_value is None and replica_value is None), None
    if isinstance(og_value, (int, float)) and isinstance(replica_value, (int, float)):
        left = float(og_value)
        right = float(replica_value)
        if metric in ROUND_TO_INT_METRICS:
            left = round(left)
            right = round(right)
        delta = right - left
        return abs(delta) <= FLOAT_TOLERANCE, delta
    return og_value == replica_value, None


def build_row(piece_relpath: str, og_metrics: dict[str, Any], replica_metrics: dict[str, Any]) -> CompareRow:
    values: dict[str, Any] = {}
    mismatch_count = 0
    for metric in CANONICAL_METRICS:
        og_value = og_metrics.get(metric)
        replica_value = replica_metrics.get(metric)
        equal, delta = compare_values(metric, og_value, replica_value)
        values[f"og_{metric}"] = og_value
        values[f"replica_{metric}"] = replica_value
        values[f"delta_{metric}"] = delta
        values[f"equal_{metric}"] = equal
        if not equal:
            mismatch_count += 1
    return CompareRow(
        piece_relpath=piece_relpath,
        status="ok",
        error="",
        values=values,
        all_equal=(mismatch_count == 0),
        mismatch_count=mismatch_count,
    )


def build_error_row(piece_relpath: str, error: str) -> CompareRow:
    values: dict[str, Any] = {}
    for metric in CANONICAL_METRICS:
        values[f"og_{metric}"] = None
        values[f"replica_{metric}"] = None
        values[f"delta_{metric}"] = None
        values[f"equal_{metric}"] = None
    return CompareRow(
        piece_relpath=piece_relpath,
        status="error",
        error=error,
        values=values,
        all_equal=False,
        mismatch_count=len(CANONICAL_METRICS),
    )


def write_rows_csv(rows: list[CompareRow], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    metric_columns: list[str] = []
    for metric in CANONICAL_METRICS:
        metric_columns.extend(
            [f"og_{metric}", f"replica_{metric}", f"delta_{metric}", f"equal_{metric}"]
        )
    headers = ["piece_relpath", "status", "error", *metric_columns, "all_equal", "mismatch_count"]
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {
                "piece_relpath": row.piece_relpath,
                "status": row.status,
                "error": row.error,
                "all_equal": row.all_equal,
                "mismatch_count": row.mismatch_count,
            }
            payload.update(row.values)
            writer.writerow(payload)


def run_comparison(
    *,
    pieces_root: Path,
    count: int,
    start_offset: int,
    php_bin: Path,
    shim_path: Path,
    out_csv: Path,
    strict: bool,
    include_raw_json_dir: Path | None,
    og_runner: Callable[[Path, Path, str], dict[str, Any]] = run_og_php_metrics,
) -> int:
    all_files = discover_piece_files(pieces_root)
    selected = select_piece_files(all_files, count=count, start_offset=start_offset)
    rows: list[CompareRow] = []
    mismatch_detected = False

    if include_raw_json_dir is not None:
        include_raw_json_dir.mkdir(parents=True, exist_ok=True)

    for score_path in selected:
        piece_relpath = str(score_path.relative_to(pieces_root))
        piece_dir = str(score_path.parent.relative_to(pieces_root))
        try:
            og_metrics = og_runner(php_bin, shim_path, piece_dir)
            replica_metrics = run_replica_metrics(score_path)
            row = build_row(piece_relpath, og_metrics, replica_metrics)
            rows.append(row)
            if include_raw_json_dir is not None:
                slug = piece_relpath.replace("/", "__")
                (include_raw_json_dir / f"{slug}.og.json").write_text(json.dumps(og_metrics, indent=2, sort_keys=True) + "\n")
                (include_raw_json_dir / f"{slug}.replica.json").write_text(json.dumps(replica_metrics, indent=2, sort_keys=True) + "\n")
            if not row.all_equal:
                mismatch_detected = True
                if strict:
                    break
        except Exception as exc:  # noqa: BLE001
            rows.append(build_error_row(piece_relpath, str(exc)))
            mismatch_detected = True
            if strict:
                break

    write_rows_csv(rows, out_csv)
    return 1 if mismatch_detected else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare_scoreanalyzer_outputs",
        description="Compare OG ScoreAnalyzer outputs with the Python replica.",
    )
    parser.add_argument("--count", type=int, required=True, help="Number of pieces to process.")
    parser.add_argument("--out-csv", type=Path, default=_default_out_csv(), help="Output CSV path.")
    parser.add_argument("--php-bin", type=Path, required=True, help="Path to php executable.")
    parser.add_argument(
        "--pieces-root",
        type=Path,
        default=_default_pieces_root(),
        help="Pieces root directory.",
    )
    parser.add_argument("--start-offset", type=int, default=0, help="Start index after sorting.")
    parser.add_argument("--strict", action="store_true", help="Stop at first mismatch or error.")
    parser.add_argument(
        "--include-raw-json-dir",
        type=Path,
        default=None,
        help="Optional directory to write raw per-piece OG/replica JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    shim_path = _resolve_shim_path(args.pieces_root)
    return run_comparison(
        pieces_root=args.pieces_root,
        count=args.count,
        start_offset=args.start_offset,
        php_bin=args.php_bin,
        shim_path=shim_path,
        out_csv=args.out_csv,
        strict=args.strict,
        include_raw_json_dir=args.include_raw_json_dir,
    )
