from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

from piano_difficulty.analysis.compatibility import build_php_compatibility_view
from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.comparison.scoreanalyzer_parity import (
    CANONICAL_METRICS,
    compare_values,
    run_og_php_metrics,
    run_replica_metrics,
)
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.normalize.schema import MeasureIR, WrittenNoteIR

_HAND_TO_STAFF = {"right": 1, "left": 2}
_DERIVED_METRIC_DEPS = {
    "speedDifficulty": ("speed",),
    "displacementsDifficulty": ("displacementsRH", "displacementsLH"),
    "chordsDifficulty": ("chordsRH", "chordsLH"),
    "harmonyDifficulty": ("harmonyRH", "harmonyLH"),
    "rhythmDifficulty": ("rhythm",),
    "lengthDifficulty": ("length",),
    "tonalityDifficulty": ("fifths",),
    "overallDifficulty": (
        "speedDifficulty",
        "displacementsDifficulty",
        "chordsDifficulty",
        "harmonyDifficulty",
        "rhythmDifficulty",
        "lengthDifficulty",
        "tonalityDifficulty",
    ),
}


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


def _default_forensics_root() -> Path:
    return Path("tests/artifacts/scoreanalyzer_parity/forensics")


def _resolve_shim_path(pieces_root: Path) -> Path:
    candidate = pieces_root.parent / "scoreanalyzer_json.php"
    if candidate.exists():
        return candidate
    return _default_scoreanalyzer_root() / "scoreanalyzer_json.php"


@dataclass(slots=True)
class TransitionEvent:
    hand: str
    measure_index: int
    measure_number: str
    prev_note_id: str
    note_id: str
    semitones: int

    @property
    def transition_id(self) -> str:
        return f"{self.prev_note_id}->{self.note_id}"


@dataclass(slots=True)
class ChordEvent:
    hand: str
    measure_index: int
    measure_number: str
    base_note_id: str
    note_ids: tuple[str, ...]
    has_octave: bool


@dataclass(slots=True)
class AccidentalEvent:
    hand: str
    measure_index: int
    measure_number: str
    note_id: str
    accidental: str


@dataclass(slots=True)
class ForensicEventRow:
    piece_relpath: str
    metric: str
    og_value: Any
    replica_value: Any
    delta: Any
    measure_index: int | None
    measure_number: str
    suspect_note_id: str
    reason_code: str
    hypothesis: str
    confidence: str


@dataclass(slots=True)
class ForensicIndex:
    score: Any
    measure_number_by_index: dict[int, str]
    notes_by_hand: dict[str, list[WrittenNoteIR]]
    transition_events_by_hand: dict[str, list[TransitionEvent]]
    chord_events_by_hand: dict[str, list[ChordEvent]]
    octave_chord_events_by_hand: dict[str, list[ChordEvent]]
    accidental_events_by_hand: dict[str, list[AccidentalEvent]]
    tuplet_note_ids_by_measure: dict[int, list[str]]
    polyrhythm_measures: list[int]


def _safe_slug(text: str) -> str:
    return (
        text.replace("\\", "__")
        .replace("/", "__")
        .replace(".", "_")
        .replace(" ", "_")
    )


def build_artifact_paths(*, out_dir: Path, piece_relpath: str) -> dict[str, Path]:
    song_slug = _safe_slug(Path(piece_relpath).stem)
    return {
        "comparison_json": out_dir / f"single_piece_comparison_{song_slug}.json",
        "metric_events_csv": out_dir / f"single_piece_metric_events_{song_slug}.csv",
        "note_flags_csv": out_dir / f"single_piece_note_flags_{song_slug}.csv",
        "summary_md": out_dir / f"single_piece_summary_{song_slug}.md",
    }


def _measure_number_map(measures: list[MeasureIR]) -> dict[int, str]:
    return {measure.measure_index: measure.measure_number for measure in measures}


def _measure_number(measure_number_by_index: dict[int, str], measure_index: int | None) -> str:
    if measure_index is None:
        return ""
    return measure_number_by_index.get(measure_index, "")


def _measure_beat_type(measures: list[MeasureIR], measure_index: int | None) -> int | None:
    if measure_index is None:
        return None
    for measure in measures:
        if measure.measure_index == measure_index:
            return measure.time_beat_type
    return None


def _short_gap(
    previous_note: WrittenNoteIR,
    current_note: WrittenNoteIR,
    events: list[Any],
    measures: list[MeasureIR],
) -> bool:
    gap_duration = Fraction(0, 1)
    for event in reversed(events):
        if event.onset >= current_note.onset:
            continue
        gap_duration += event.duration
        if isinstance(event, WrittenNoteIR) and not event.is_chord_continuation:
            previous_beat_type = _measure_beat_type(measures, event.measure_index)
            beat_type = _measure_beat_type(measures, current_note.measure_index)
            effective_beat_type = beat_type or previous_beat_type or 4
            return gap_duration <= Fraction(8, effective_beat_type)
    return abs(current_note.onset - previous_note.onset) <= Fraction(2, 1)


def build_forensic_index(score: Any) -> ForensicIndex:
    view = build_php_compatibility_view(score)
    metrics = compute_reference_metrics(score)
    measure_number_by_index = _measure_number_map(score.measures)
    tuplet_note_ids_by_measure: dict[int, list[str]] = {}
    for note in score.written_notes:
        if note.measure_index is None:
            continue
        if note.tuplet_actual is None and note.tuplet_normal is None:
            continue
        tuplet_note_ids_by_measure.setdefault(note.measure_index, []).append(note.note_id)

    notes_by_hand: dict[str, list[WrittenNoteIR]] = {}
    transition_events_by_hand: dict[str, list[TransitionEvent]] = {}
    chord_events_by_hand: dict[str, list[ChordEvent]] = {}
    octave_chord_events_by_hand: dict[str, list[ChordEvent]] = {}
    accidental_events_by_hand: dict[str, list[AccidentalEvent]] = {}

    for hand, staff in _HAND_TO_STAFF.items():
        notes = list(view.notes_for_staff(staff))
        events = list(view.events_for_staff(staff))
        notes_by_hand[hand] = notes
        transitions: list[TransitionEvent] = []
        chords: list[ChordEvent] = []
        octaves: list[ChordEvent] = []
        accidentals: list[AccidentalEvent] = []

        onset_notes = [note for note in notes if not note.is_chord_continuation]
        for note in notes:
            if note.accidental:
                accidentals.append(
                    AccidentalEvent(
                        hand=hand,
                        measure_index=note.measure_index or 0,
                        measure_number=_measure_number(measure_number_by_index, note.measure_index),
                        note_id=note.note_id,
                        accidental=note.accidental,
                    )
                )

        for idx, base_note in enumerate(onset_notes):
            onset_mates = [
                note
                for note in notes
                if note.measure_index == base_note.measure_index and note.onset == base_note.onset
            ]
            if len(onset_mates) > 1:
                has_octave = any(
                    note.pitch_midi == base_note.pitch_midi + 12 for note in onset_mates
                )
                chord_event = ChordEvent(
                    hand=hand,
                    measure_index=base_note.measure_index or 0,
                    measure_number=_measure_number(
                        measure_number_by_index, base_note.measure_index
                    ),
                    base_note_id=base_note.note_id,
                    note_ids=tuple(note.note_id for note in onset_mates),
                    has_octave=has_octave,
                )
                chords.append(chord_event)
                if has_octave:
                    octaves.append(chord_event)

            if idx == 0:
                continue
            previous = onset_notes[idx - 1]
            semitones = abs(base_note.pitch_midi - previous.pitch_midi)
            if semitones > 12 and _short_gap(previous, base_note, events, score.measures):
                transitions.append(
                    TransitionEvent(
                        hand=hand,
                        measure_index=base_note.measure_index or previous.measure_index or 0,
                        measure_number=_measure_number(
                            measure_number_by_index,
                            base_note.measure_index or previous.measure_index,
                        ),
                        prev_note_id=previous.note_id,
                        note_id=base_note.note_id,
                        semitones=semitones,
                    )
                )

        transition_events_by_hand[hand] = transitions
        chord_events_by_hand[hand] = chords
        octave_chord_events_by_hand[hand] = octaves
        accidental_events_by_hand[hand] = accidentals

    return ForensicIndex(
        score=score,
        measure_number_by_index=measure_number_by_index,
        notes_by_hand=notes_by_hand,
        transition_events_by_hand=transition_events_by_hand,
        chord_events_by_hand=chord_events_by_hand,
        octave_chord_events_by_hand=octave_chord_events_by_hand,
        accidental_events_by_hand=accidental_events_by_hand,
        tuplet_note_ids_by_measure=tuplet_note_ids_by_measure,
        polyrhythm_measures=list(metrics.polyrhythm_measures),
    )


def _append_rows(
    rows: list[ForensicEventRow],
    *,
    piece_relpath: str,
    metric: str,
    og_value: Any,
    replica_value: Any,
    delta: Any,
    hypothesis: str,
    confidence: str,
    reason_code: str,
    events: list[tuple[int | None, str, str]],
) -> None:
    if not events:
        rows.append(
            ForensicEventRow(
                piece_relpath=piece_relpath,
                metric=metric,
                og_value=og_value,
                replica_value=replica_value,
                delta=delta,
                measure_index=None,
                measure_number="",
                suspect_note_id="",
                reason_code=reason_code,
                hypothesis=hypothesis,
                confidence=confidence,
            )
        )
        return
    for measure_index, measure_number, suspect_note_id in events:
        rows.append(
            ForensicEventRow(
                piece_relpath=piece_relpath,
                metric=metric,
                og_value=og_value,
                replica_value=replica_value,
                delta=delta,
                measure_index=measure_index,
                measure_number=measure_number,
                suspect_note_id=suspect_note_id,
                reason_code=reason_code,
                hypothesis=hypothesis,
                confidence=confidence,
            )
        )


def _resolve_base_metric_dependencies(metric: str) -> tuple[str, ...]:
    deps = _DERIVED_METRIC_DEPS.get(metric)
    if not deps:
        return ()
    resolved: list[str] = []
    queue = list(deps)
    while queue:
        item = queue.pop(0)
        nested = _DERIVED_METRIC_DEPS.get(item)
        if nested:
            queue.extend(list(nested))
            continue
        if item not in resolved:
            resolved.append(item)
    return tuple(resolved)


def locate_metric_suspects(
    *,
    piece_relpath: str,
    metric: str,
    og_metrics: dict[str, Any],
    replica_metrics: dict[str, Any],
    mismatched_metrics: set[str],
    forensic_index: ForensicIndex,
    max_suspects_per_metric: int,
) -> list[ForensicEventRow]:
    rows: list[ForensicEventRow] = []
    og_value = og_metrics.get(metric)
    replica_value = replica_metrics.get(metric)
    _equal, delta = compare_values(metric, og_value, replica_value)
    cap = max(1, max_suspects_per_metric)

    def mm(index: int | None) -> str:
        return _measure_number(forensic_index.measure_number_by_index, index)

    if metric in {"maxIntervalRH", "maxIntervalLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        events = forensic_index.transition_events_by_hand[hand]
        max_jump = max((event.semitones for event in events), default=0)
        selected = [event for event in events if event.semitones == max_jump][:cap]
        event_rows = [
            (event.measure_index, event.measure_number, event.transition_id)
            for event in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Largest difficult displacement transition differs.",
            confidence="high",
            reason_code="MAX_INTERVAL_TRANSITION",
            events=event_rows,
        )
        return rows

    if metric in {"displacementsRH", "displacementsLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        selected = forensic_index.transition_events_by_hand[hand][:cap]
        event_rows = [
            (event.measure_index, event.measure_number, event.transition_id)
            for event in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Timed difficult displacement rule differs.",
            confidence="high",
            reason_code="DIFFICULT_DISPLACEMENT",
            events=event_rows,
        )
        return rows

    if metric in {"chordsRH", "chordsLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        selected = forensic_index.chord_events_by_hand[hand][:cap]
        event_rows = [
            (event.measure_index, event.measure_number, event.base_note_id)
            for event in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Chord-base onset detection/counting differs.",
            confidence="medium",
            reason_code="CHORD_BASE_EVENT",
            events=event_rows,
        )
        return rows

    if metric in {"octavesRatioRH", "octavesRatioLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        selected = forensic_index.octave_chord_events_by_hand[hand][:cap]
        event_rows = [
            (event.measure_index, event.measure_number, event.base_note_id)
            for event in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Octave-in-chord detection differs.",
            confidence="medium",
            reason_code="OCTAVE_CHORD_EVENT",
            events=event_rows,
        )
        return rows

    if metric in {"harmonyRH", "harmonyLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        selected = forensic_index.accidental_events_by_hand[hand][:cap]
        event_rows = [
            (event.measure_index, event.measure_number, event.note_id)
            for event in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Accidental counting/normalization differs.",
            confidence="high",
            reason_code="ACCIDENTAL_EVENT",
            events=event_rows,
        )
        return rows

    if metric in {"noteCounterRH", "noteCounterLH"}:
        hand = "right" if metric.endswith("RH") else "left"
        notes = forensic_index.notes_by_hand[hand]
        ambiguous = [
            note for note in notes if note.hand is None or note.hand_confidence not in {"high", "medium"}
        ]
        selected = ambiguous[:cap]
        if len(selected) < cap:
            selected.extend(notes[: cap - len(selected)])
        event_rows = [
            (note.measure_index, mm(note.measure_index), note.note_id)
            for note in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Hand assignment or note inclusion/exclusion differs.",
            confidence="medium",
            reason_code="HAND_NOTE_POPULATION",
            events=event_rows,
        )
        return rows

    if metric == "baseDuration":
        candidates = [
            note
            for note in forensic_index.score.written_notes
            if note.duration > 0 and not note.tuplet_actual
        ]
        if candidates:
            min_duration = min(note.duration for note in candidates)
            selected = [note for note in candidates if note.duration == min_duration][:cap]
        else:
            selected = []
        event_rows = [
            (note.measure_index, mm(note.measure_index), note.note_id)
            for note in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Shortest non-tuplet base duration extraction differs.",
            confidence="high",
            reason_code="BASE_DURATION_NOTE",
            events=event_rows,
        )
        return rows

    if metric == "rhythm":
        selected_measures = forensic_index.polyrhythm_measures[:cap]
        event_rows = [
            (
                measure_index,
                mm(measure_index),
                (forensic_index.tuplet_note_ids_by_measure.get(measure_index) or [""])[0],
            )
            for measure_index in selected_measures
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Tuplet/polyrhythm measure matching differs across hands.",
            confidence="medium",
            reason_code="POLYRHYTHM_MEASURE",
            events=event_rows,
        )
        return rows

    if metric == "quantise":
        type_map = {
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
        candidates = []
        for note in forensic_index.score.written_notes:
            value = type_map.get(note.duration_type or "")
            if value is None:
                continue
            candidates.append((value, note))
        if candidates:
            max_value = max(value for value, _note in candidates)
            selected = [note for value, note in candidates if value == max_value][:cap]
        else:
            selected = []
        event_rows = [
            (note.measure_index, mm(note.measure_index), note.note_id)
            for note in selected
        ]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Quantization denominator selection differs.",
            confidence="medium",
            reason_code="QUANTISE_DRIVER",
            events=event_rows,
        )
        return rows

    base_deps = [
        dep
        for dep in _resolve_base_metric_dependencies(metric)
        if dep in mismatched_metrics
    ]
    if base_deps:
        event_rows = [(None, "", f"metric:{dep}") for dep in base_deps[:cap]]
        _append_rows(
            rows,
            piece_relpath=piece_relpath,
            metric=metric,
            og_value=og_value,
            replica_value=replica_value,
            delta=delta,
            hypothesis="Derived metric mismatch linked to upstream base metric mismatches.",
            confidence="low",
            reason_code="DERIVED_FROM_METRIC",
            events=event_rows,
        )
        return rows

    _append_rows(
        rows,
        piece_relpath=piece_relpath,
        metric=metric,
        og_value=og_value,
        replica_value=replica_value,
        delta=delta,
        hypothesis="No specialized locator configured for this metric.",
        confidence="low",
        reason_code="UNMAPPED_METRIC",
        events=[],
    )
    return rows


def _write_metric_events_csv(path: Path, rows: list[ForensicEventRow]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "piece_relpath",
                "metric",
                "og_value",
                "replica_value",
                "delta",
                "measure_index",
                "measure_number",
                "suspect_note_id",
                "reason_code",
                "hypothesis",
                "confidence",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "piece_relpath": row.piece_relpath,
                    "metric": row.metric,
                    "og_value": row.og_value,
                    "replica_value": row.replica_value,
                    "delta": row.delta,
                    "measure_index": row.measure_index,
                    "measure_number": row.measure_number,
                    "suspect_note_id": row.suspect_note_id,
                    "reason_code": row.reason_code,
                    "hypothesis": row.hypothesis,
                    "confidence": row.confidence,
                }
            )


def _write_note_flags_csv(path: Path, rows: list[ForensicEventRow]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "piece_relpath",
                "metric",
                "measure_index",
                "measure_number",
                "note_id",
                "reason_code",
                "confidence",
                "hypothesis",
            ],
        )
        writer.writeheader()
        for row in rows:
            if not row.suspect_note_id:
                continue
            writer.writerow(
                {
                    "piece_relpath": row.piece_relpath,
                    "metric": row.metric,
                    "measure_index": row.measure_index,
                    "measure_number": row.measure_number,
                    "note_id": row.suspect_note_id,
                    "reason_code": row.reason_code,
                    "confidence": row.confidence,
                    "hypothesis": row.hypothesis,
                }
            )


def _write_summary_md(
    *,
    path: Path,
    piece_relpath: str,
    mismatched_metrics: list[str],
    event_rows: list[ForensicEventRow],
) -> None:
    lines: list[str] = []
    lines.append(f"# Single-Piece Forensic Summary: `{piece_relpath}`")
    lines.append("")
    lines.append(f"- Mismatched metrics: {len(mismatched_metrics)}")
    lines.append(f"- Metrics: {', '.join(mismatched_metrics) if mismatched_metrics else 'none'}")
    lines.append("")

    high_conf = [row for row in event_rows if row.confidence == "high"]
    medium_conf = [row for row in event_rows if row.confidence == "medium"]
    low_conf = [row for row in event_rows if row.confidence == "low"]

    lines.append("## Top likely root causes")
    if high_conf:
        for row in high_conf[:20]:
            measure_bit = (
                f"measure {row.measure_number} (index {row.measure_index})"
                if row.measure_index is not None
                else "derived/global context"
            )
            note_bit = f", suspect `{row.suspect_note_id}`" if row.suspect_note_id else ""
            lines.append(f"- `{row.metric}` at {measure_bit}{note_bit}: {row.hypothesis}")
    else:
        lines.append("- No high-confidence event-level root-cause rows were generated.")

    lines.append("")
    lines.append("## Medium-confidence contributors")
    if medium_conf:
        for row in medium_conf[:20]:
            measure_bit = (
                f"measure {row.measure_number} (index {row.measure_index})"
                if row.measure_index is not None
                else "derived/global context"
            )
            note_bit = f", suspect `{row.suspect_note_id}`" if row.suspect_note_id else ""
            lines.append(f"- `{row.metric}` at {measure_bit}{note_bit}: {row.hypothesis}")
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Derived/summary mismatches")
    derived_rows = [
        row
        for row in low_conf
        if row.reason_code in {"DERIVED_FROM_METRIC", "UNMAPPED_METRIC"}
    ]
    if derived_rows:
        for row in derived_rows[:20]:
            dep = row.suspect_note_id or "upstream metric"
            lines.append(f"- `{row.metric}` linked to `{dep}`: {row.hypothesis}")
    else:
        lines.append("- None.")

    path.write_text("\n".join(lines) + "\n")


def run_single_piece_forensics(
    *,
    piece_relpath: str,
    php_bin: Path,
    pieces_root: Path = _default_pieces_root(),
    out_dir: Path | None = None,
    max_suspects_per_metric: int = 20,
    og_runner: Callable[[Path, Path, str], dict[str, Any]] = run_og_php_metrics,
) -> int:
    if max_suspects_per_metric <= 0:
        print("Invalid argument: --max-suspects-per-metric must be > 0.")
        return 2
    piece_path = pieces_root / piece_relpath
    if not piece_path.exists():
        print(f"Piece path not found: {piece_path}")
        return 2
    if not piece_path.is_file():
        print(f"Piece path is not a file: {piece_path}")
        return 2

    slug = _safe_slug(piece_relpath)
    resolved_out_dir = (
        out_dir
        if out_dir is not None
        else _default_forensics_root() / slug
    )
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    try:
        piece_dir = str(Path(piece_relpath).parent).replace("\\", "/")
        shim_path = _resolve_shim_path(pieces_root)
        og_metrics = og_runner(php_bin, shim_path, piece_dir)
        replica_metrics = run_replica_metrics(piece_path)
        score = build_score_ir(load_musicxml_document(piece_path))
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to run single-piece forensics: {exc}")
        return 2

    metric_comparison: list[dict[str, Any]] = []
    mismatched_metrics: list[str] = []
    for metric in CANONICAL_METRICS:
        og_value = og_metrics.get(metric)
        replica_value = replica_metrics.get(metric)
        equal, delta = compare_values(metric, og_value, replica_value)
        metric_comparison.append(
            {
                "metric": metric,
                "og_value": og_value,
                "replica_value": replica_value,
                "delta": delta,
                "equal": equal,
            }
        )
        if not equal:
            mismatched_metrics.append(metric)

    forensic_index = build_forensic_index(score)
    mismatch_set = set(mismatched_metrics)
    event_rows: list[ForensicEventRow] = []
    for metric in mismatched_metrics:
        event_rows.extend(
            locate_metric_suspects(
                piece_relpath=piece_relpath,
                metric=metric,
                og_metrics=og_metrics,
                replica_metrics=replica_metrics,
                mismatched_metrics=mismatch_set,
                forensic_index=forensic_index,
                max_suspects_per_metric=max_suspects_per_metric,
            )
        )

    comparison_payload = {
        "piece_relpath": piece_relpath,
        "piece_path": str(piece_path),
        "mismatched_metrics": mismatched_metrics,
        "mismatch_count": len(mismatched_metrics),
        "og_metrics": og_metrics,
        "replica_metrics": replica_metrics,
        "metric_comparison": metric_comparison,
    }

    artifact_paths = build_artifact_paths(
        out_dir=resolved_out_dir,
        piece_relpath=piece_relpath,
    )
    comparison_json_path = artifact_paths["comparison_json"]
    metric_events_csv_path = artifact_paths["metric_events_csv"]
    note_flags_csv_path = artifact_paths["note_flags_csv"]
    summary_md_path = artifact_paths["summary_md"]

    comparison_json_path.write_text(json.dumps(comparison_payload, indent=2, sort_keys=True) + "\n")
    _write_metric_events_csv(metric_events_csv_path, event_rows)
    _write_note_flags_csv(note_flags_csv_path, event_rows)
    _write_summary_md(
        path=summary_md_path,
        piece_relpath=piece_relpath,
        mismatched_metrics=mismatched_metrics,
        event_rows=event_rows,
    )
    print(f"Piece: {piece_relpath}")
    print(f"Mismatched metrics: {len(mismatched_metrics)}")
    print(f"Output JSON: {comparison_json_path}")
    print(f"Output metric events CSV: {metric_events_csv_path}")
    print(f"Output note flags CSV: {note_flags_csv_path}")
    print(f"Output summary markdown: {summary_md_path}")
    return 1 if mismatched_metrics else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_single_piece_forensic_parity",
        description="Run forensic OG-vs-replica parity analysis for one explicit piece.",
    )
    parser.add_argument("--piece-relpath", required=True, help="Piece path relative to pieces root.")
    parser.add_argument("--php-bin", type=Path, required=True, help="Path to php executable.")
    parser.add_argument(
        "--pieces-root",
        type=Path,
        default=_default_pieces_root(),
        help="Root folder containing score piece directories.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional output folder. Defaults to scoreanalyzer parity forensic path.",
    )
    parser.add_argument(
        "--max-suspects-per-metric",
        type=int,
        default=20,
        help="Maximum suspect events to emit per mismatched metric.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_single_piece_forensics(
        piece_relpath=args.piece_relpath,
        php_bin=args.php_bin,
        pieces_root=args.pieces_root,
        out_dir=args.out_dir,
        max_suspects_per_metric=args.max_suspects_per_metric,
    )
