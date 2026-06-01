from __future__ import annotations

import argparse
import csv
from pathlib import Path

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir


def _default_artifacts_dir() -> Path:
    return Path("tests/artifacts/scoreanalyzer_parity")


def _default_in_csv() -> Path:
    return _default_artifacts_dir() / "comparison.csv"


def _default_out_dir() -> Path:
    return _default_artifacts_dir() / "diagnostics"


def _default_pieces_root() -> Path:
    candidates = (
        Path("external/ScoreAnalyzer/pieces"),
        Path("reference_code/ScoreAnalyzer/pieces"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _safe_slug(text: str) -> str:
    return (
        text.replace("\\", "_")
        .replace("/", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )


def _split_metrics(row: dict[str, str]) -> list[str]:
    metrics: list[str] = []
    for key, value in row.items():
        if not key.startswith("equal_"):
            continue
        metric = key[len("equal_") :]
        if value.strip().lower() == "false":
            metrics.append(metric)
    return metrics


def _hand_for_metric(metric: str) -> str | None:
    if metric.endswith("RH"):
        return "right"
    if metric.endswith("LH"):
        return "left"
    return None


def _suspect_measures_and_notes(metric: str, score) -> tuple[list[int], list[str], str]:
    metrics = compute_reference_metrics(score)
    rh = metrics.hand_metrics["right"]
    lh = metrics.hand_metrics["left"]
    hand = _hand_for_metric(metric)
    hm = rh if hand == "right" else lh if hand == "left" else None

    if metric in {"speed", "tempo", "beats", "beatType", "quickestValue", "fifths", "mode", "tonalityDifficulty"}:
        return [1], [], "Global setup/metadata mismatch (tempo, signature, or key parsing)."
    if metric == "nbmeasures":
        return list(range(1, len(score.measures) + 1)), [], "Measure counting divergence (repeats/implicit measures)."
    if metric in {"displacementsRH", "displacementsLH", "displacementsDifficulty"} and hm is not None:
        m = sorted(hm.displacement_measure_counts.keys())
        n = [event.note_id for event in hm.displacement_events[:20]]
        return m, n, "Likely leap-gap timing rule mismatch (>12 semitone with short gap)."
    if metric in {"maxIntervalRH", "maxIntervalLH"} and hm is not None:
        maxv = hm.max_timed_difficult_displacement
        events = [event for event in hm.displacement_events if event.semitones == maxv]
        return sorted({event.measure_index for event in events}), [event.note_id for event in events[:20]], "Largest leap detection differs."
    if metric in {"chordsRH", "chordsLH", "chordsDifficulty", "octavesRatioRH", "octavesRatioLH"} and hm is not None:
        m = sorted(hm.chord_measure_counts.keys())
        notes = [note.note_id for note in hm.notes if note.measure_index in set(m)][:20]
        return m, notes, "Chord onset or octave-in-chord detection differs."
    if metric in {"harmonyRH", "harmonyLH", "harmonyDifficulty"} and hm is not None:
        m = sorted(hm.accidental_measure_counts.keys())
        notes = [note.note_id for note in hm.notes if note.accidental and note.measure_index in set(m)][:20]
        return m, notes, "Accidental counting/normalization differs."
    if metric == "rhythm":
        m = list(metrics.polyrhythm_measures)
        return sorted(m), [], "Tuplet/polyrhythm matching across hands differs."
    if metric in {"noteCounterRH", "noteCounterLH"} and hm is not None:
        notes = [note.note_id for note in hm.notes[:20]]
        return sorted({note.measure_index for note in hm.notes if note.measure_index is not None}), notes, "Hand assignment or note filtering differs."
    if metric in {"nbPositionsRH", "nbPositionsLH"} and hm is not None:
        return sorted({note.measure_index for note in hm.notes if note.measure_index is not None}), [], "Position transition counting differs."
    if metric in {"length", "lengthDifficulty"}:
        return [1], [], "Page counting differs (print/page markers)."
    if metric == "baseDuration":
        return sorted({note.measure_index for note in score.written_notes if note.measure_index is not None}), [], "Shortest base duration extraction differs."
    if metric == "quantise":
        return sorted({note.measure_index for note in score.written_notes if note.measure_index is not None}), [], "Quantization denominator selection differs."
    if metric in {"overallDifficulty", "speedDifficulty", "rhythmDifficulty"}:
        return [], [], "Derived score mismatch caused by one or more upstream metric mismatches."
    return [], [], "No metric-specific heuristic yet."


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose piece/metric mismatches from comparison CSV.")
    parser.add_argument("--in-csv", type=Path, default=_default_in_csv())
    parser.add_argument("--pieces-root", type=Path, default=_default_pieces_root())
    parser.add_argument("--out-dir", type=Path, default=_default_out_dir())
    args = parser.parse_args()

    rows = list(csv.DictReader(args.in_csv.open()))
    mismatches = [row for row in rows if row.get("status", "").lower() != "ok" or row.get("all_equal") == "False"]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    song_names = sorted({Path(row.get("piece_relpath", "")).stem for row in mismatches if row.get("piece_relpath")})
    if len(song_names) == 1:
        label = _safe_slug(song_names[0])
    else:
        label = _safe_slug(args.in_csv.stem)
    overview_path = args.out_dir / f"mismatch_pieces_overview_{label}.csv"
    detail_path = args.out_dir / f"mismatch_piece_metric_diagnostics_{label}.csv"

    with overview_path.open("w", newline="") as ov, detail_path.open("w", newline="") as dt:
        ov_writer = csv.DictWriter(ov, fieldnames=["piece_relpath", "status", "mismatch_metric_count", "mismatch_metrics", "error"])
        dt_writer = csv.DictWriter(
            dt,
            fieldnames=[
                "piece_relpath",
                "metric",
                "og_value",
                "replica_value",
                "delta",
                "mismatch_measures",
                "suspected_note_ids",
                "hypothesis",
            ],
        )
        ov_writer.writeheader()
        dt_writer.writeheader()

        for row in mismatches:
            piece_relpath = row["piece_relpath"]
            metric_list = _split_metrics(row)
            ov_writer.writerow(
                {
                    "piece_relpath": piece_relpath,
                    "status": row.get("status", ""),
                    "mismatch_metric_count": len(metric_list),
                    "mismatch_metrics": ";".join(metric_list),
                    "error": row.get("error", ""),
                }
            )
            score_path = args.pieces_root / piece_relpath
            score = None
            if score_path.exists() and row.get("status", "").lower() == "ok":
                score = build_score_ir(load_musicxml_document(score_path))

            for metric in metric_list:
                if score is not None:
                    measures, note_ids, hypothesis = _suspect_measures_and_notes(metric, score)
                else:
                    measures, note_ids, hypothesis = ([], [], "OG runtime error prevented metric-level diagnosis.")
                dt_writer.writerow(
                    {
                        "piece_relpath": piece_relpath,
                        "metric": metric,
                        "og_value": row.get(f"og_{metric}", ""),
                        "replica_value": row.get(f"replica_{metric}", ""),
                        "delta": row.get(f"delta_{metric}", ""),
                        "mismatch_measures": ";".join(str(m) for m in measures),
                        "suspected_note_ids": ";".join(note_ids),
                        "hypothesis": hypothesis,
                    }
                )

    print(f"Wrote {overview_path}")
    print(f"Wrote {detail_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
