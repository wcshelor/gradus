from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

import argparse
import json
from pathlib import Path

from tests.harness.yan2023.extractor import extract_first_pass_from_path
from tests.harness.yan2023.slot_inventory import WORKING_FEATURE_SLOTS, slot_status_counts
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
from tests.harness.yan2023.variability import (
    DEFAULT_VARIABILITY_FORMULA,
    VARIABILITY_FORMULA_NAMES,
)

_VISIBLE_SCOPE_ORDER = ("es", "bs", "ts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract first-pass paper-derived Yan 2023 feature values for one score."
    )
    parser.add_argument("score_path", help="Path to a MusicXML-family score file.")
    parser.add_argument(
        "--format",
        choices=("summary", "json", "table"),
        default="summary",
        help="Output format.",
    )
    parser.add_argument(
        "--variability-formula",
        choices=VARIABILITY_FORMULA_NAMES,
        default=DEFAULT_VARIABILITY_FORMULA,
        help="Variability formula to use for the score-sequence variability features.",
    )
    parser.add_argument(
        "--black-key-rate-formula",
        choices=BLACK_KEY_RATE_FORMULA_NAMES,
        default=DEFAULT_BLACK_KEY_RATE_FORMULA,
        help="Formula to use for black_key_rate.",
    )
    parser.add_argument(
        "--polyphony-rate-formula",
        choices=POLYPHONY_RATE_FORMULA_NAMES,
        default=DEFAULT_POLYPHONY_RATE_FORMULA,
        help="Formula to use for polyphony_rate.",
    )
    parser.add_argument(
        "--staccato-rate-formula",
        choices=STACCATO_RATE_FORMULA_NAMES,
        default=DEFAULT_STACCATO_RATE_FORMULA,
        help="Formula to use for staccato_rate.",
    )
    parser.add_argument(
        "--dotted-note-rate-formula",
        choices=DOTTED_NOTE_RATE_FORMULA_NAMES,
        default=DEFAULT_DOTTED_NOTE_RATE_FORMULA,
        help="Formula to use for dotted_note_rate.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    score, values = extract_first_pass_from_path(
        Path(args.score_path),
        variability_formula=args.variability_formula,
        black_key_rate_formula=args.black_key_rate_formula,
        polyphony_rate_formula=args.polyphony_rate_formula,
        staccato_rate_formula=args.staccato_rate_formula,
        dotted_note_rate_formula=args.dotted_note_rate_formula,
    )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "source_path": str(score.source_path) if score.source_path else None,
                    "slot_inventory_size": len(WORKING_FEATURE_SLOTS),
                    "extracted_value_count": len(values),
                    "variability_formula": args.variability_formula,
                    "variability_formula_bank": list(VARIABILITY_FORMULA_NAMES),
                    "black_key_rate_formula": args.black_key_rate_formula,
                    "black_key_rate_formula_bank": list(BLACK_KEY_RATE_FORMULA_NAMES),
                    "polyphony_rate_formula": args.polyphony_rate_formula,
                    "polyphony_rate_formula_bank": list(POLYPHONY_RATE_FORMULA_NAMES),
                    "staccato_rate_formula": args.staccato_rate_formula,
                    "staccato_rate_formula_bank": list(STACCATO_RATE_FORMULA_NAMES),
                    "dotted_note_rate_formula": args.dotted_note_rate_formula,
                    "dotted_note_rate_formula_bank": list(DOTTED_NOTE_RATE_FORMULA_NAMES),
                    "values": [value.to_payload() for value in values],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.format == "table":
        for value in values:
            print(
                "\t".join(
                    [
                        value.slot_id,
                        str(value.value),
                        value.units or "",
                        value.status,
                        value.reliability,
                    ]
                )
            )
        return 0

    status_counts = slot_status_counts()
    visible_scope_counts = {
        scope: sum(1 for value in values if value.slot_id.endswith(f"_{scope}"))
        for scope in _VISIBLE_SCOPE_ORDER
    }
    global_count = sum(
        1
        for value in values
        if not any(value.slot_id.endswith(f"_{scope}") for scope in _VISIBLE_SCOPE_ORDER)
    )
    print(f"score: {score.source_path}")
    print(f"variability formula: {args.variability_formula}")
    print(f"black key rate formula: {args.black_key_rate_formula}")
    print(f"polyphony rate formula: {args.polyphony_rate_formula}")
    print(f"staccato rate formula: {args.staccato_rate_formula}")
    print(f"dotted note rate formula: {args.dotted_note_rate_formula}")
    print(f"working slot inventory: {len(WORKING_FEATURE_SLOTS)}")
    print(
        "inventory status counts: "
        f"implemented={status_counts['implemented']}, "
        f"proxyable={status_counts['proxyable']}, "
        f"blocked={status_counts['blocked']}"
    )
    print(f"extracted values: {len(values)}")
    print(
        "scope counts: "
        f"es={visible_scope_counts['es']}, "
        f"bs={visible_scope_counts['bs']}, "
        f"ts={visible_scope_counts['ts']}, "
        f"global={global_count}"
    )
    for slot_id in (
        "pitch_range_es",
        "note_density_es",
        "pitch_variability_es",
        "triad_es",
        "seventh_chord_es",
        "playing_speed_variation",
    ):
        match = next((value for value in values if value.slot_id == slot_id), None)
        if match is not None:
            suffix = f" {match.units}" if match.units else ""
            print(f"{slot_id}: {match.value}{suffix} [{match.reliability}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
