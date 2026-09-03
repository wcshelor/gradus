from __future__ import annotations

import csv
from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity import (
    CANONICAL_METRICS,
    run_comparison,
)


def test_run_comparison_writes_wide_csv_with_mocked_og(tmp_path: Path) -> None:
    pieces_root = tmp_path / "pieces"
    piece_dir = pieces_root / "pieceA"
    piece_dir.mkdir(parents=True)
    score_path = piece_dir / "piece.xml"
    score_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths><mode>major</mode></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef>
      </attributes>
      <direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>120</per-minute></metronome></direction-type></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type><staff>1</staff></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>1</duration><voice>2</voice><type>quarter</type><staff>2</staff></note>
    </measure>
  </part>
</score-partwise>"""
    )

    def fake_og(_php_bin: Path, _shim_path: Path, _piece_dir: str):
        payload = {metric: 0 for metric in CANONICAL_METRICS}
        payload["mode"] = "major"
        return payload

    out_csv = tmp_path / "comparison.csv"
    exit_code = run_comparison(
        pieces_root=pieces_root,
        count=1,
        start_offset=0,
        php_bin=Path("/tmp/php"),
        shim_path=Path("/tmp/shim.php"),
        out_csv=out_csv,
        strict=False,
        include_raw_json_dir=None,
        og_runner=fake_og,
    )

    assert exit_code == 1
    assert out_csv.exists()
    with out_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["piece_relpath"] == "pieceA/piece.xml"
    assert rows[0]["status"] == "ok"
    assert "og_speed" in rows[0]
    assert "replica_speed" in rows[0]
    assert "delta_speed" in rows[0]
    assert "equal_speed" in rows[0]
    assert rows[0]["all_equal"] == "False"

