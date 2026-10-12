#!/usr/bin/env python3
"""Verify difficulty-events explanations vs hand labels.

Compare current blended difficulty reason (top FeatureContribution) vs new
multi-event explanation for each demo passage.
Manual success: pianist says events are actual separate practice things.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo src on path
REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))
FIXTURE_ROOT = REPO

from piano_difficulty import analyze_score  # noqa: E402


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="fixture path substring")
    parser.add_argument("--all", action="store_true", help="verify all demo passages")
    args = parser.parse_args()

    manifest = Path(__file__).with_name("demo_passages.json")
    data = json.loads(manifest.read_text())
    passages = data["passages"]
    if args.fixture:
        passages = [p for p in passages if args.fixture in p["fixture"]]

    overall_ok = True
    for passage in passages:
        fixture = FIXTURE_ROOT / passage["fixture"]
        print(f"\n=== {passage['id']} ===")
        print(f"Fixture: {fixture}")
        print(f"Description: {passage['description']}")
        if not fixture.exists():
            print("  SKIP: fixture missing")
            continue
        result = analyze_score(str(fixture), explain_events=True)
        payload = result.to_json_payload()
        overview = next((p for p in payload["analysis_profiles"] if p.get("profile_id") == "difficulty_overview"), None)
        if overview is None:
            print("  FAIL: no difficulty_overview profile")
            overall_ok = False
            continue
        # Current blended: top contributions of first candidate_section
        cand = (overview.get("candidate_sections") or [])
        if cand:
            top = cand[0].get("contributions", [])[:3]
            print("  Current (blended) top contributions:")
            for c in top:
                print(f"    - {c['feature_id']} share={c.get('contribution_share'):.2f} raw={c.get('raw_value')} norm={c.get('normalized_value'):.2f}")
        else:
            print("  No candidate_sections — no flagship flagged")
            print(f"  Series keys: {list(overview.get('series',{}).keys())[:6]}")
        events_payload = overview.get("difficulty_events") or {}
        events = events_payload.get("events", [])
        by_sec = events_payload.get("events_by_section", [])
        print(f"  New: {events_payload.get('event_count', len(events))} events across {len(by_sec)} flagged sections")
        for e in events:
            print(f"    - {e['difficulty_type']} ({e['difficulty_label']}) conf={e['confidence']:.2f} measures {e['measure_numbers']} win {e['window_indices']} unc={e['uncertainty']}")
            for ev in e.get("supporting_metric_evidence", [])[:3]:
                print(f"        metric {ev['feature_id']} norm={ev.get('normalized_value')} delta={ev.get('delta_normalized')}")
            if e.get("note_evidence"):
                extra = e["note_evidence"].get("extra", {})
                print(f"        note extra: { {k:v for k,v in extra.items() if k.startswith('has_') or k.startswith('is_')} }")
        # Check success criteria
        crit = passage.get("success_criteria", {})
        types = {e["difficulty_type"] for e in events}
        # overlap: any two events share at least one measure or window
        has_overlap = False
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                if set(events[i]["measure_numbers"]) & set(events[j]["measure_numbers"]):
                    has_overlap = True
                if set(events[i]["window_indices"]) & set(events[j]["window_indices"]):
                    has_overlap = True
        print(f"  Types found: {sorted(types)}")
        print(f"  Overlap: {has_overlap}")
        ok = True
        if crit.get("min_events") and len(events) < crit["min_events"]:
            print(f"  FAIL: need >= {crit['min_events']} events, got {len(events)}")
            ok = False
        for req in crit.get("requires_types", []):
            if req not in types:
                print(f"  FAIL: missing required type {req}")
                ok = False
        if crit.get("requires_overlap") and not has_overlap:
            print("  FAIL: expected overlapping events")
            ok = False
        print("  RESULT:", "PASS" if ok else "FAIL")
        overall_ok = overall_ok and ok

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
