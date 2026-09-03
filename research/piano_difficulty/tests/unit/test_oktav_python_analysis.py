from __future__ import annotations

import csv
from pathlib import Path

from tests.harness.oktav_dataset.python_analysis import run_oktav_python_analysis

_FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef>
      </attributes>
      <direction>
        <direction-type><dynamics><mf/></dynamics></direction-type>
        <staff>1</staff>
      </direction>
      <note id="n1">
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration><voice>1</voice><type>quarter</type><staff>1</staff>
        <notations><articulations><staccato/></articulations></notations>
      </note>
      <backup><duration>2</duration></backup>
      <note id="n2">
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>2</duration><voice>2</voice><type>quarter</type><staff>2</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def test_run_oktav_python_analysis_exports_runtime_matrix_with_expression_columns(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "Example OK00001.musicxml").write_text(_FIXTURE_XML)

    label_source = tmp_path / "labels.csv"
    label_source.write_text(
        "filename,dataset_relative_path,difficulty_numeric\n"
        "Example OK00001.musicxml,Example OK00001.musicxml,23\n"
    )

    out_dir = tmp_path / "out"
    summary = run_oktav_python_analysis(
        dataset_root=dataset_root,
        out_dir=out_dir,
        label_source_csv=label_source,
    )

    assert summary["failure_count"] == 0
    matrix_path = Path(summary["matrix_csv_path"])
    assert matrix_path.is_file()
    with matrix_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["difficulty_numeric"] == "23"
    assert row["status"] == "success"
    assert row["expression_staccato_note_ratio"] == "0.5"
    assert row["expression_dynamic_marking_count"] == "1"
    assert row["piece_id"] == "OK00001"

    summary_path = Path(summary["summary_json_path"])
    assert summary_path.is_file()
    assert (out_dir / "piece_json").is_dir()
