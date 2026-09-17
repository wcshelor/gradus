#!/usr/bin/env python3
"""Thin wrapper to generate Yan-runtime feature gap diagnostic CSV."""

import sys
sys.path.insert(0, "research/piano_difficulty")  # for direct invocation

from tests.harness.difficulty_prediction.yan_runtime_gap import write_gap_csv

if __name__ == "__main__":
    out = write_gap_csv()
    print(f"Wrote {out}")
