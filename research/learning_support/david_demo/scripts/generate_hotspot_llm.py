#!/usr/bin/env python3
"""Generate optional LLM hotspot polish offline (server-side, stable, reviewable).

Reads a demo_manifest.json, derives the deterministic evidence brief for each hotspot,
and generates an LLM explanation that must be derived from that brief.

Product rule: live analysis may use heuristic fallback unless LLM generation is explicitly configured.
For the David demo, prefer pre-generated/server-side explanations so outputs are stable.

Design:
  - Never call LLM from the browser. This script is the only generation path.
  - The brief is the evidence record; LLM narrates it. Outputs stored with evidence_hash + model/version metadata.
  - Validation: LLM output violations are recorded; hallucinations should be reviewed and rejected.
  - Default mode is deterministic mock (no network) so CI can run without keys.
  - Optional live mode uses OPENAI_API_KEY if --model openai is passed.

Usage (from repo root):

  # Mock (deterministic, reviewable, no network) — writes sidecar for one piece:
  python research/learning_support/david_demo/scripts/generate_hotspot_llm.py \
    --manifest research/learning_support/david_demo/artifacts/debussy_arabesque_1/demo_manifest.json \
    --out research/learning_support/david_demo/artifacts/debussy_arabesque_1/llm_explanations.json

  # Real LLM (requires OPENAI_API_KEY):
  OPENAI_API_KEY=sk-... python research/learning_support/david_demo/scripts/generate_hotspot_llm.py \
    --manifest research/learning_support/david_demo/artifacts/debussy_arabesque_1/demo_manifest.json \
    --out research/learning_support/david_demo/artifacts/debussy_arabesque_1/llm_explanations.json \
    --model openai --openai-model gpt-4o-mini

  # Apply to all 11 pieces:
  for d in research/learning_support/david_demo/artifacts/*/demo_manifest.json; do
    out="$(dirname "$d")/llm_explanations.json"
    python research/learning_support/david_demo/scripts/generate_hotspot_llm.py --manifest "$d" --out "$out"
  done

Sidecar shape:
  {
    "schema_version": "david_llm_sidecar.v1",
    "generated_at": "2026-...",
    "model": "mock|openai:gpt-4o-mini",
    "prompt_version": "david_llm_polish.v1",
    "evidence_version": "david_evidence.v1",
    "hotspots": {
      "graph_section:both:140:148": {
        "schema_version": "david_llm.v1",
        "model": "mock",
        "evidence_hash": "abc123...",
        "summary": "...",
        "musical_connection": "...",
        "practice_focus": "...",
        ...
      }
    }
  }

Build integration:
  build_demo_piece.py automatically picks up llm_explanations.json next to the manifest
  and attaches llm_explanation only if evidence_hash matches current evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "research" / "piano_difficulty" / "src"
if str(_SRC_ROOT) not in sys.path:
    try:
        import piano_difficulty  # noqa: F401
    except ModuleNotFoundError:
        sys.path.insert(0, str(_SRC_ROOT))

# Load helpers via importlib for robustness
import importlib.util

_helper_path = Path(__file__).with_name("hotspot_explanation.py")
_spec = importlib.util.spec_from_file_location("hotspot_explanation", _helper_path)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)  # type: ignore

build_evidence_brief = _mod.build_evidence_brief
build_heuristic_from_brief = _mod.build_heuristic_from_brief
build_llm_prompt = _mod.build_llm_prompt
build_llm_explanation = _mod.build_llm_explanation
validate_llm_output = _mod.validate_llm_output
EVIDENCE_VERSION = _mod.EVIDENCE_VERSION
LLM_PROMPT_VERSION = _mod.LLM_PROMPT_VERSION
LLM_SCHEMA_VERSION = _mod.LLM_SCHEMA_VERSION


def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> dict[str, str]:
    """Call OpenAI chat completions with strict evidence-only instruction."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError("openai python package not installed; pip install openai") from e

    client = OpenAI(api_key=api_key)
    system = (
        "You narrate piano score evidence. Use ONLY the EVIDENCE_BRIEF JSON provided. "
        "Do not invent features, grades, fingerings, diagnoses, or benefits. "
        "Hide raw feature IDs in prose; cite at least one micro-feature with its raw value and units. "
        "Return JSON with keys summary, musical_connection, practice_focus."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"OpenAI returned non-JSON: {raw[:500]}") from e
    # Ensure keys present
    summary = str(parsed.get("summary") or parsed.get("polished_summary") or "").strip()
    musical = str(parsed.get("musical_connection") or parsed.get("connection") or "").strip()
    focus = str(parsed.get("practice_focus") or parsed.get("practice") or "").strip()
    if not summary:
        raise RuntimeError(f"LLM response missing summary: {parsed}")
    return {"summary": summary, "musical_connection": musical, "practice_focus": focus}


def generate_for_manifest(manifest: dict, *, model: str, openai_model: str) -> dict:
    piece = manifest.get("piece") or {}
    chart = manifest.get("chart") or {}
    caveats = manifest.get("caveats") or []
    hotspots = manifest.get("hotspots") or []

    hotspots_out: dict[str, dict] = {}
    for h in hotspots:
        hid = h.get("id") or h.get("section_id") or h.get("hotspot_id") or ""
        # Re-derive brief deterministically (do not trust pre-existing evidence if stale)
        brief = h.get("evidence") or h.get("evidence_brief")
        if not brief or not isinstance(brief, dict) or "evidence_hash" not in brief:
            brief = build_evidence_brief(h, chart, piece, caveats)
        # Generate LLM text
        if model == "mock":
            llm_text = None  # build_llm_explanation will generate deterministic mock
            model_label = "mock"
        elif model == "openai":
            prompt = build_llm_prompt(brief)
            llm_text = _call_openai(prompt, model=openai_model)
            model_label = f"openai:{openai_model}"
        else:
            raise ValueError(f"Unknown model {model}")

        llm_obj = build_llm_explanation(brief, llm_text, model=model_label, prompt_version=LLM_PROMPT_VERSION)
        # Validate and record
        violations = validate_llm_output(
            " ".join([llm_obj.get("summary") or "", llm_obj.get("musical_connection") or "", llm_obj.get("practice_focus") or ""]),
            brief,
        )
        llm_obj["violations"] = violations
        llm_obj["evidence_hash_valid"] = llm_obj.get("evidence_hash") == brief.get("evidence_hash")
        hotspots_out[hid] = llm_obj

    sidecar = {
        "schema_version": "david_llm_sidecar.v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "model": model if model == "mock" else f"openai:{openai_model}",
        "prompt_version": LLM_PROMPT_VERSION,
        "evidence_version": EVIDENCE_VERSION,
        "llm_schema_version": LLM_SCHEMA_VERSION,
        "hotspots": hotspots_out,
        # Also store flat map for build_demo_piece backward compat (hotspot_id -> obj)
        **{k: v for k, v in hotspots_out.items()},
    }
    # Keep both nested and flat: top-level hotspots dict + flat keys for simple loader
    return sidecar


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LLM hotspot polish offline (server-side, stable)")
    p.add_argument("--manifest", type=Path, required=True, help="Path to demo_manifest.json")
    p.add_argument("--out", type=Path, required=True, help="Output sidecar path (llm_explanations.json)")
    p.add_argument("--model", type=str, default="mock", choices=["mock", "openai"], help="Model backend (default mock, no network)")
    p.add_argument("--openai-model", type=str, default="gpt-4o-mini", help="OpenAI model id when --model openai")
    p.add_argument("--dry-run", action="store_true", help="Validate and print but do not write")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest)
    out_path = Path(args.out)
    if not manifest_path.is_file():
        print(f"[error] Manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[error] Failed to read manifest: {e}", file=sys.stderr)
        return 2

    sidecar = generate_for_manifest(manifest, model=args.model, openai_model=args.openai_model)

    # Report violations
    hotspots_map = sidecar.get("hotspots") or {}
    violation_count = sum(1 for v in hotspots_map.values() if v.get("violations"))
    if violation_count:
        print(f"[warn] {violation_count} hotspot(s) have LLM validation violations (review required)", file=sys.stderr)
        for hid, obj in hotspots_map.items():
            if obj.get("violations"):
                print(f"  - {hid}: {obj['violations']}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(sidecar, indent=2, ensure_ascii=False, sort_keys=True)[:4000])
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[ok] Wrote LLM sidecar to {out_path} ({len(hotspots_map)} hotspots, model={sidecar['model']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
