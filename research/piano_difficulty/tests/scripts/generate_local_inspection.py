"""Local Semantic Inspection harness — thin wrapper over runtime builder.

Generates a Local Semantic Inspection report for measures A-B (inclusive).

Usage:
  PYTHONPATH=research/piano_difficulty/src python research/piano_difficulty/tests/scripts/generate_local_inspection.py \
    research/piano_difficulty/tests/fixtures/phase5_demo_minimal.musicxml \
    --measures 1-3 \
    --output research/piano_difficulty/tests/artifacts/local_inspections/demo_1-3.md \
    [--flagged 2,3] [--source-label "music/demo.mxl"]

Outputs a single Markdown file matching docs/templates/local_semantic_inspection.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from tests.scripts._bootstrap import add_repo_root_to_sys_path

    add_repo_root_to_sys_path()
except ModuleNotFoundError:
    import pathlib as _pl

    _here = _pl.Path(__file__).resolve()
    _proj_root = _here.parents[2]
    _src_root = _proj_root / "src"
    for _c in (str(_proj_root), str(_src_root)):
        if _c not in sys.path:
            sys.path.insert(0, _c)

from piano_difficulty.io.musicxml import load_musicxml_document  # noqa: E402
from piano_difficulty.normalize.converters import build_score_ir  # noqa: E402
from piano_difficulty.semantic_tokens import build_semantic_bundle  # noqa: E402
from piano_difficulty.semantic_tokens.local_inspection import (  # noqa: E402
    build_local_inspection,
    render_markdown,
)


def _parse_measures(s: str) -> tuple[int, int]:
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a.strip()), int(b.strip())
    if ":" in s:
        a, b = s.split(":", 1)
        return int(a.strip()), int(b.strip())
    # single measure
    v = int(s)
    return v, v


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Local Semantic Inspection for Measures A-B")
    p.add_argument("source", help="Path to MusicXML/MXL")
    p.add_argument("--measures", required=True, help="Report span A-B (e.g., 34-37 or 5)")
    p.add_argument("--flagged", default=None, help="Flagged measures comma-separated (e.g., 34,35) — defaults to report span")
    p.add_argument("--source-label", default=None, help="Source score label for report (e.g., music/... )")
    p.add_argument("--output", required=True, help="Output markdown path")
    p.add_argument("--max-units", type=int, default=3, help="Max instruction units (default 3)")
    return p.parse_args(argv)


def run(source: str | Path, measures: str, output: str | Path, flagged: str | None = None, source_label: str | None = None, max_units: int = 3) -> Path:
    src = Path(source)
    out = Path(output)
    a, b = _parse_measures(measures)
    if flagged:
        flagged_measures = tuple(s.strip() for s in flagged.split(",") if s.strip())
    else:
        flagged_measures = tuple(str(x) for x in range(a, b + 1))
    label = source_label or str(src)
    doc = load_musicxml_document(src)
    score = build_score_ir(doc)
    bundle = build_semantic_bundle(score)
    inspection = build_local_inspection(
        bundle,
        report_span=(a, b),
        flagged_measures=flagged_measures,
        source_score=label,
        max_instruction_units=max_units,
    )
    md = render_markdown(inspection)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    # Write sibling machine-readable JSON for full raw evidence (readable-first Markdown truncation)
    import json

    json_path = out.with_suffix(".json")
    try:
        json_path.write_text(json.dumps(inspection.raw_evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return out


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        out = run(args.source, args.measures, args.output, flagged=args.flagged, source_label=args.source_label, max_units=args.max_units)
        print(f"Wrote Local Semantic Inspection to {out}")
        # Also report consistency warning count if JSON exists
        try:
            import json

            jpath = out.with_suffix(".json")
            if jpath.exists():
                data = json.loads(jpath.read_text(encoding="utf-8"))
                diags = data.get("instruction_unit_diagnostics", [])
                total = sum(len(d.get("consistency_warnings", [])) for d in diags) if diags else 0
                if total:
                    print(f"Consistency warnings: {total}")
                    print("See sibling JSON for details.")
                else:
                    print("Consistency warnings: 0")
        except Exception:
            pass
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
