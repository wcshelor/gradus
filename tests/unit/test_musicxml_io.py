from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from piano_difficulty.io.musicxml import (
    MUSICXML_PARSER_BACKEND,
    load_musicxml,
    read_mxl_archive,
    validate_supported_score,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
MINIMAL_PIANO_FIXTURE = FIXTURES_DIR / "minimal_piano.musicxml"

MXL_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container
  version="1.0"
  xmlns="urn:oasis:names:tc:opendocument:xmlns:container"
>
  <rootfiles>
    <rootfile
      full-path="scores/score.musicxml"
      media-type="application/vnd.recordare.musicxml+xml"
    />
  </rootfiles>
</container>
"""

ENSEMBLE_FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Violin</part-name>
    </score-part>
    <score-part id="P2">
      <part-name>Flute</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>5</octave>
        </pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
      </attributes>
      <note>
        <pitch>
          <step>G</step>
          <octave>5</octave>
        </pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def _write_mxl_archive(tmp_path: Path, score_xml: str) -> Path:
    archive_path = tmp_path / "tiny_score.mxl"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", MXL_CONTAINER_XML)
        archive.writestr("scores/score.musicxml", score_xml)
    return archive_path


def test_musicxml_backend_is_partitura() -> None:
    assert MUSICXML_PARSER_BACKEND == "partitura"


def test_load_musicxml_reads_minimal_piano_fixture() -> None:
    parsed_score = load_musicxml(MINIMAL_PIANO_FIXTURE)

    assert len(parsed_score.parts) == 1
    assert parsed_score.parts[0].part_name == "Piano"
    assert validate_supported_score(parsed_score) == []


def test_read_mxl_archive_returns_primary_musicxml_payload(tmp_path: Path) -> None:
    archive_path = _write_mxl_archive(tmp_path, MINIMAL_PIANO_FIXTURE.read_text())

    payload = read_mxl_archive(archive_path)

    assert b"<score-partwise" in payload
    assert b"<part-name>Piano</part-name>" in payload


def test_load_musicxml_reads_mxl_archive(tmp_path: Path) -> None:
    archive_path = _write_mxl_archive(tmp_path, MINIMAL_PIANO_FIXTURE.read_text())

    parsed_score = load_musicxml(archive_path)

    assert len(parsed_score.parts) == 1
    assert parsed_score.parts[0].part_name == "Piano"


def test_validate_supported_score_flags_non_piano_multi_part_layout(
    tmp_path: Path,
) -> None:
    ensemble_path = tmp_path / "ensemble.musicxml"
    ensemble_path.write_text(ENSEMBLE_FIXTURE_XML)

    parsed_score = load_musicxml(ensemble_path)
    diagnostics = validate_supported_score(parsed_score)

    assert any("contains 2 parts" in diagnostic for diagnostic in diagnostics)
    assert any("does not advertise a piano" in diagnostic for diagnostic in diagnostics)
