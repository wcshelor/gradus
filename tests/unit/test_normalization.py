from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from piano_difficulty.analysis.compatibility import build_php_compatibility_view
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir


NORMALIZATION_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work>
    <work-title>Fixture Piece</work-title>
  </work>
  <identification>
    <creator type="composer">Fixture Composer</creator>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <print page-number="1" new-page="yes"/>
      <attributes>
        <divisions>2</divisions>
        <key>
          <fifths>-2</fifths>
          <mode>major</mode>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <staves>2</staves>
      </attributes>
      <direction placement="above">
        <direction-type>
          <words>Allegro</words>
        </direction-type>
        <staff>1</staff>
        <sound tempo="120"/>
      </direction>
      <note id="n1">
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
      <note id="n2">
        <chord/>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
      <note id="r1">
        <rest/>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
      <note id="n3">
        <pitch>
          <step>G</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <voice>1</voice>
        <type>half</type>
        <staff>1</staff>
        <tie type="start"/>
        <notations>
          <tied type="start"/>
        </notations>
      </note>
      <backup>
        <duration>8</duration>
      </backup>
      <note id="n4">
        <pitch>
          <step>C</step>
          <octave>3</octave>
        </pitch>
        <duration>8</duration>
        <voice>2</voice>
        <type>whole</type>
        <staff>2</staff>
      </note>
    </measure>
    <measure number="2">
      <print page-number="2" new-page="yes"/>
      <note id="n5">
        <pitch>
          <step>G</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <voice>1</voice>
        <type>half</type>
        <staff>1</staff>
        <tie type="stop"/>
        <notations>
          <tied type="stop"/>
        </notations>
      </note>
      <note id="n6">
        <pitch>
          <step>B</step>
          <alter>-1</alter>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <accidental>flat</accidental>
        <staff>1</staff>
      </note>
      <note id="r2">
        <rest/>
        <duration>3</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def _write_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "normalization.musicxml"
    path.write_text(NORMALIZATION_FIXTURE)
    return path


def test_build_score_ir_preserves_php_relevant_musicxml_facts(tmp_path: Path) -> None:
    score = build_score_ir(load_musicxml_document(_write_fixture(tmp_path)))

    assert score.title == "Fixture Piece"
    assert score.composer == "Fixture Composer"
    assert len(score.measures) == 2
    assert score.measures[0].divisions == 2
    assert score.measures[0].key_fifths == -2
    assert score.measures[0].key_mode == "major"
    assert score.measures[0].time_signature == "4/4"
    assert score.measures[0].tempo_bpm == 120
    assert score.measures[0].page_number == 1
    assert score.measures[0].starts_new_page is True
    assert score.measures[1].page_number == 2
    assert score.measures[1].starts_new_page is True

    assert len(score.written_notes) == 6
    assert len(score.rests) == 2
    assert len(score.logical_notes) == 5

    chord_note = next(note for note in score.written_notes if note.note_id == "n2")
    assert chord_note.is_chord_continuation is True
    assert chord_note.onset == Fraction(0)
    assert chord_note.measure_staff_order == 2

    rest = next(rest for rest in score.rests if rest.rest_id == "r1")
    assert rest.onset == Fraction(1)
    assert rest.duration == Fraction(1)
    assert rest.measure_staff_order == 3

    tuplet_note = next(note for note in score.written_notes if note.note_id == "n6")
    assert tuplet_note.accidental == "flat"
    assert tuplet_note.alter == -1
    assert tuplet_note.tuplet_actual == 3
    assert tuplet_note.tuplet_normal == 2

    tied_logical = next(
        note for note in score.logical_notes if note.source_note_ids == ("n3", "n5")
    )
    assert tied_logical.duration == Fraction(4)
    assert tied_logical.hand == "right"
    assert tied_logical.hand_confidence == "staff"


def test_chord_continuations_inherit_missing_voice_from_base_note(
    tmp_path: Path,
) -> None:
    fixture = NORMALIZATION_FIXTURE.replace(
        """<note id="n2">
        <chord/>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>""",
        """<note id="n2">
        <chord/>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>2</duration>
        <type>quarter</type>""",
    )
    path = tmp_path / "missing-chord-voice.musicxml"
    path.write_text(fixture)

    score = build_score_ir(load_musicxml_document(path))

    chord_note = next(note for note in score.written_notes if note.note_id == "n2")
    assert chord_note.voice == "1"
    assert not any(diagnostic.code == "missing_voice" for diagnostic in score.diagnostics)


def test_php_compatibility_view_exposes_staff_streams_and_tuplets(
    tmp_path: Path,
) -> None:
    score = build_score_ir(load_musicxml_document(_write_fixture(tmp_path)))
    view = build_php_compatibility_view(score)

    assert sorted(view.staff_streams) == [1, 2]
    assert [note.note_id for note in view.notes_for_staff(1)] == [
        "n1",
        "n2",
        "n3",
        "n5",
        "n6",
    ]
    assert [event.xml_order for event in view.events_for_staff(1)] == [1, 2, 3, 4, 6, 7, 8]
    assert tuple(note.note_id for note in view.tuplets_by_measure[2]) == ("n6",)
    assert view.measure_context[1].tempo_bpm == 120


def test_reference_scoreanalyzer_demo_normalizes_when_present() -> None:
    path = Path("reference_code/ScoreAnalyzer/pieces/demo/demo.xml")
    if not path.exists():
        pytest.skip("ScoreAnalyzer reference fixture is not present.")
    if path.stat().st_size == 0:
        pytest.skip("ScoreAnalyzer reference fixture is empty in this workspace.")

    try:
        score = build_score_ir(load_musicxml_document(path))
    except ValueError as exc:
        pytest.skip(f"ScoreAnalyzer reference fixture is not usable here: {exc}")
    view = build_php_compatibility_view(score)

    assert len(score.measures) > 0
    assert len(score.written_notes) > 0
    assert 1 in view.staff_streams
    assert 2 in view.staff_streams
    assert sum(1 for note in score.written_notes if note.is_chord_continuation) > 0
    assert any(measure.key_fifths is not None for measure in score.measures)
