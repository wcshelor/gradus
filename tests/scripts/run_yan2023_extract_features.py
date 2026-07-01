from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

import argparse
import json
from pathlib import Path

from tests.harness.yan2023.extractor import extract_first_pass_from_path
from tests.harness.yan2023.slot_inventory import WORKING_FEATURE_SLOTS, slot_status_counts

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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    score, values = extract_first_pass_from_path(Path(args.score_path))

    if args.format == "json":
        print(
            json.dumps(
                {
                    "source_path": str(score.source_path) if score.source_path else None,
                    "slot_inventory_size": len(WORKING_FEATURE_SLOTS),
                    "extracted_value_count": len(values),
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
