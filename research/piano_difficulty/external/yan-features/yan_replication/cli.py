from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from yan_replication.compare.compare_vectors import compare_feature_frames
from yan_replication.compare.diagnostics import write_diagnostic_note
from yan_replication.reference.feature_names import try_load_feature_names
from yan_replication.reference.inspect_mat import format_inspection_report, inspect_all_mat_files
from yan_replication.reference.load_reference import FEATURE_SETS, DATASETS, load_yan_reference


def _base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def cmd_inspect(_: argparse.Namespace) -> None:
    base = _base_dir()
    files = inspect_all_mat_files(base)
    print(format_inspection_report(files))


def cmd_inventory(_: argparse.Namespace) -> None:
    base = _base_dir()
    out = {"datasets": {}, "feature_name_files": {}, "mat_files": [p.name for p in sorted(base.glob("*.mat"))]}

    for ds in sorted(DATASETS):
        out["datasets"][ds] = {}
        for fs in sorted(FEATURE_SETS):
            ref = load_yan_reference(ds, fs, root=base)
            entry = {
                "shape": list(ref.X.shape),
                "dtype": str(ref.X.dtype),
                "matrix_key": ref.metadata.get("matrix_key"),
                "has_labels": ref.y is not None,
                "label_shape": list(ref.y.shape) if ref.y is not None else None,
                "label_distribution": pd.Series(ref.y).value_counts().sort_index().to_dict() if ref.y is not None else None,
                "feature_names_available": bool(ref.feature_names),
                "feature_names_source": "decoded_mat" if ref.metadata.get("feature_name_info", {}).get("decoded_names") else ("manual_placeholder" if ref.feature_names else "none"),
            }
            out["datasets"][ds][fs] = entry

    for p in sorted(base.glob("feature_name_*.mat")):
        out["feature_name_files"][p.name] = try_load_feature_names(p)

    print(json.dumps(out, indent=2, default=str))


def cmd_extract(args: argparse.Namespace) -> None:
    from yan_replication.features.yan_table3_features import extract_first_pass_features
    from yan_replication.parsing.load_midi import load_score
    from yan_replication.parsing.normalize_events import normalize_note_events

    score = load_score(args.input)
    events = normalize_note_events(score)
    features = extract_first_pass_features(events)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([features]).to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


def cmd_compare(args: argparse.Namespace) -> None:
    ours = pd.read_csv(args.ours)
    ref = load_yan_reference(args.dataset, args.feature_set, root=_base_dir())
    ref_df = pd.DataFrame(ref.X)
    if ref.feature_names and len(ref.feature_names) == ref_df.shape[1]:
        ref_df.columns = ref.feature_names

    report_dir = _base_dir() / "data" / "reports"
    result = compare_feature_frames(ours=ours, reference=ref_df, report_dir=report_dir, prefix=f"{args.dataset}_{args.feature_set}")
    note_lines = [
        f"dataset={args.dataset}",
        f"feature_set={args.feature_set}",
        f"row_alignment_known={result['row_alignment_known']}",
        "row-level alignment metadata was not found in source files; distribution-level comparison is safer unless alignment is externally provided.",
    ]
    write_diagnostic_note(report_dir / f"{args.dataset}_{args.feature_set}_diagnostic.txt", note_lines)
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Yan et al. replication CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Inspect .mat files")
    p_inspect.set_defaults(func=cmd_inspect)

    p_inventory = sub.add_parser("inventory", help="Summarize datasets and labels")
    p_inventory.set_defaults(func=cmd_inventory)

    p_extract = sub.add_parser("extract", help="Extract first-pass features from a MIDI/MusicXML/MXL score file")
    p_extract.add_argument("--input", required=True)
    p_extract.add_argument("--out", required=True)
    p_extract.set_defaults(func=cmd_extract)

    p_compare = sub.add_parser("compare", help="Compare our features against reference matrices")
    p_compare.add_argument("--ours", required=True)
    p_compare.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    p_compare.add_argument("--feature-set", required=True, choices=sorted(FEATURE_SETS))
    p_compare.set_defaults(func=cmd_compare)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
