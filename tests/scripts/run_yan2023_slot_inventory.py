from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

import argparse
import json

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report the working paper-first Yan 2023 slot inventory."
    )
    parser.add_argument(
        "--inventory",
        choices=("working", "paper73"),
        default="working",
        help="Inventory to report.",
    )
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

    if args.inventory == "paper73":
        inventory_name = "paper-73 inventory"
        slots = PAPER_73_FEATURE_SLOTS
        status_counts = paper_slot_status_counts()
        scope_counts = paper_slot_scope_counts()
        source_counts = paper_slot_source_counts()
        scope_evidence_counts = paper_scope_evidence_counts()
    else:
        inventory_name = "working"
        slots = WORKING_FEATURE_SLOTS
        status_counts = slot_status_counts()
        scope_counts = slot_scope_counts()
        source_counts = slot_source_counts()
        scope_evidence_counts = None

    if args.format == "json":
        payload = {
            "inventory": args.inventory,
            "inventory_name": inventory_name,
            "slot_count": len(slots),
            "status_counts": status_counts,
            "scope_counts": scope_counts,
            "source_counts": source_counts,
            "slots": [
                {
                    "slot_id": slot.slot_id,
                    "base_feature": slot.base_feature,
                    "family": slot.family,
                    "scope_code": slot.scope_code,
                    "status": slot.status,
                    "source_kinds": slot.source_kinds,
                    "notes": slot.notes,
                    **(
                        {"scope_evidence": slot.scope_evidence}
                        if hasattr(slot, "scope_evidence")
                        else {}
                    ),
                }
                for slot in slots
            ],
        }
        if scope_evidence_counts is not None:
            payload["scope_evidence_counts"] = scope_evidence_counts
            payload["scope_overrides"] = paper_scope_override_map()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.format == "table":
        for slot in slots:
            print(
                "\t".join(
                    [
                        slot.slot_id,
                        slot.status,
                        slot.scope_code,
                        slot.family,
                        ",".join(slot.source_kinds),
                        getattr(slot, "scope_evidence", "-"),
                    ]
                )
            )
        return 0

    print(f"{inventory_name} slot inventory: {len(slots)}")
    print(
        "status counts: "
        f"implemented={status_counts['implemented']}, "
        f"proxyable={status_counts['proxyable']}, "
        f"blocked={status_counts['blocked']}"
    )
    print(
        "scope counts: "
        f"es={scope_counts['es']}, "
        f"bs={scope_counts['bs']}, "
        f"ts={scope_counts['ts']}, "
        f"global={scope_counts['global']}"
    )
    print(
        "source counts: "
        f"paper_text={source_counts['paper_text']}, "
        f"table3={source_counts['table3']}, "
        f"figure6_visible={source_counts['figure6_visible']}, "
        f"paper_scope_expansion={source_counts['paper_scope_expansion']}"
    )
    if scope_evidence_counts is not None:
        print(
            "scope evidence counts: "
            f"working_global={scope_evidence_counts['working_global']}, "
            f"working_scoped={scope_evidence_counts['working_scoped']}, "
            f"figure6_unsuffixed={scope_evidence_counts['figure6_unsuffixed']}, "
            "table3_global_formula="
            f"{scope_evidence_counts['table3_global_formula']}"
        )
        print(
            "scope overrides: "
            + ", ".join(
                f"{base}={','.join(scopes)}"
                for base, scopes in sorted(paper_scope_override_map().items())
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
