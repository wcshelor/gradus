from __future__ import annotations

from tests.scripts._bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.oktav_dataset.catalog import load_oktav_dataset


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="build_oktav_dataset_catalog",
        description="Check Oktav dataset loading without running feature extraction.",
    )
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--label-source", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = load_oktav_dataset(dataset_root=args.dataset_root, label_source=args.label_source)
    payload = {
        "dataset_root": result.summary.get("dataset_root"),
        "dataset_root_source": result.summary.get("dataset_root_source"),
        "record_count": len(result.records),
        "missing_files": list(result.missing_files),
        "extra_files": list(result.extra_files),
        "duplicate_piece_ids": list(result.duplicate_piece_ids),
        "duplicate_piece_uids": list(result.duplicate_piece_uids),
        "nonconforming_ids": list(result.nonconforming_ids),
        "unsupported_files": list(result.unsupported_files),
        "warnings": list(result.warnings),
        "summary": result.summary,
    }
    if args.out is not None:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
