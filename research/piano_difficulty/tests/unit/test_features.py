from __future__ import annotations

from pathlib import Path

from piano_difficulty.features import extract_all
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.pipeline import extract_score


FEATURE_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work>
    <work-title>Feature Fixture</work-title>
  </work>
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
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <staves>2</staves>
        <clef number="1">
          <sign>G</sign>
          <line>2</line>
        </clef>
        <clef number="2">
          <sign>F</sign>
          <line>4</line>
        </clef>
      </attributes>
      <direction>
        <direction-type>
          <dynamics>
            <mf/>
          </dynamics>
        </direction-type>
        <staff>1</staff>
      </direction>
      <direction>
        <sound tempo="100"/>
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
        <notations>
          <articulations>
            <staccato/>
          </articulations>
        </notations>
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
      <note id="n3">
        <pitch>
          <step>G</step>
          <octave>4</octave>
        </pitch>
        <duration>4</duration>
        <voice>1</voice>
        <type>half</type>
        <staff>1</staff>
        <notations>
          <articulations>
            <accent/>
          </articulations>
        </notations>
      </note>
      <backup>
        <duration>6</duration>
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
      <attributes>
        <key>
          <fifths>1</fifths>
        </key>
        <time>
          <beats>3</beats>
          <beat-type>4</beat-type>
        </time>
        <clef number="1">
          <sign>F</sign>
          <line>4</line>
        </clef>
      </attributes>
      <direction>
        <direction-type>
          <dynamics>
            <ff/>
          </dynamics>
        </direction-type>
        <staff>1</staff>
      </direction>
      <direction>
        <direction-type>
          <wedge type="crescendo"/>
        </direction-type>
        <staff>1</staff>
      </direction>
      <direction>
        <sound tempo="120"/>
      </direction>
      <note id="n5">
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
        <notations>
          <articulations>
            <tenuto/>
          </articulations>
        </notations>
      </note>
      <note id="r1">
        <rest/>
        <duration>5</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""

DISPLACEMENT_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <print page-number="1" new-page="yes"/>
      <attributes>
        <divisions>4</divisions>
        <key>
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <staves>2</staves>
        <clef number="1">
          <sign>G</sign>
          <line>2</line>
        </clef>
        <clef number="2">
          <sign>F</sign>
          <line>4</line>
        </clef>
      </attributes>
      <direction>
        <sound tempo="120"/>
      </direction>
      <note id="rh1">
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration><voice>1</voice><type>quarter</type><staff>1</staff>
      </note>
      <note id="rh2">
        <chord/>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration><voice>1</voice><type>quarter</type><staff>1</staff>
      </note>
      <note id="rh3">
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration><voice>1</voice><type>quarter</type><staff>1</staff>
      </note>
      <backup><duration>8</duration></backup>
      <note id="lh1">
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>4</duration><voice>2</voice><type>quarter</type><staff>2</staff>
      </note>
      <note id="lh2">
        <pitch><step>D</step><octave>3</octave></pitch>
        <duration>4</duration><voice>2</voice><type>quarter</type><staff>2</staff>
      </note>
    </measure>
    <measure number="2">
      <print page-number="2" new-page="yes"/>
      <note id="rh4">
        <pitch><step>G</step><octave>5</octave></pitch>
        <duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff>
      </note>
      <note id="rh5">
        <pitch><step>A</step><octave>5</octave></pitch>
        <duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff>
      </note>
      <backup><duration>4</duration></backup>
      <note id="lh3">
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration><voice>2</voice><type>eighth</type><staff>2</staff>
      </note>
      <note id="lh4">
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration><voice>2</voice><type>eighth</type><staff>2</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def _write_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "features.musicxml"
    path.write_text(FEATURE_FIXTURE)
    return path


def _features_by_key(path: Path) -> dict[tuple[str, str, str], object]:
    score = build_score_ir(load_musicxml_document(path))
    return {
        (feature.feature_id, feature.scope, feature.scope_ref): feature.value
        for feature in extract_all(score)
    }


def _write_displacement_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "displacement.musicxml"
    path.write_text(DISPLACEMENT_FIXTURE)
    return path


def test_extract_all_emits_registry_feature_families(tmp_path: Path) -> None:
    features = _features_by_key(_write_fixture(tmp_path))

    expected_feature_ids = {
        "metadata.page_count",
        "metadata.measure_count",
        "metadata.note_count",
        "metadata.pitch_range",
        "metadata.tempo_change_count",
        "metadata.key_change_count",
        "metadata.meter_change_count",
        "metadata.length_quarters",
        "metadata.primary_tempo",
        "metadata.key_signature",
        "statistics.pitch_mean",
        "statistics.pitch_std",
        "statistics.pitch_entropy",
        "statistics.deviation_from_c4",
        "statistics.duration_mean",
        "statistics.duration_std",
        "statistics.pitch_variability",
        "statistics.duration_variability",
        "statistics.black_key_rate",
        "statistics.polyphony_rate",
        "statistics.triad_count",
        "statistics.seventh_chord_count",
        "statistics.ninth_chord_count",
        "rhythm.note_density",
        "rhythm.attack_density",
        "rhythm.shortest_written_duration",
        "rhythm.tuplet_count",
        "rhythm.duration_value_ratio",
        "rhythm.significant_shortest_value",
        "rhythm.asymmetric_tuplet_measure_ratio",
        "rhythm.polyrhythm_measure_ratio",
        "rhythm.polyrhythm_flag",
        "pitch_geometry.mean_simultaneity_span",
        "pitch_geometry.max_simultaneity_span",
        "pitch_geometry.register_range",
        "leaps.mean_melodic_leap",
        "leaps.max_melodic_leap",
        "leaps.count_ge_5",
        "leaps.count_ge_8",
        "leaps.count_ge_12",
        "leaps.timed_difficult_displacement_ratio",
        "leaps.max_timed_difficult_displacement",
        "texture.notes_per_onset",
        "texture.simultaneity_density",
        "texture.vertical_density_proxy",
        "texture.chord_count",
        "texture.chord_ratio",
        "texture.octave_chord_ratio",
        "coordination.aligned_hand_onset_count",
        "coordination.asynchronous_hand_onset_count",
        "coordination.aligned_hand_onset_ratio",
        "coordination.subdivision_mismatch_proxy",
        "notation.accidental_density",
        "notation.accidental_count",
        "notation.accidental_ratio",
        "notation.clef_change_count",
        "notation.cross_staff_note_count",
        "notation.ledger_line_burden",
        "expression.articulated_note_ratio",
        "expression.articulation_density",
        "expression.staccato_note_ratio",
        "expression.accent_note_ratio",
        "expression.strong_accent_note_ratio",
        "expression.tenuto_note_ratio",
        "expression.dynamic_marking_count",
        "expression.dynamic_marking_rate",
        "expression.dynamic_change_count",
        "expression.dynamic_range_span",
        "expression.wedge_start_count",
        "expression.crescendo_start_count",
        "expression.diminuendo_start_count",
        "expression.staff_specific_dynamic_ratio",
        "hand_shape.octave_onset_rate",
        "hand_shape.large_span_onset_rate",
        "hand_shape.mean_large_span_burden",
        "hand_shape.wide_chord_density",
        "hand_shape.repeated_octave_texture_rate",
        "hand_shape.chord_shape_change_rate",
        "hand_shape.chord_shape_entropy",
        "hand_shape.chord_shape_edit_distance_mean",
        "hand_shape.chord_size_change_rate",
        "hand_shape.repeated_shape_ratio",
        "hand_shape.chord_tone_motion_variability",
        "hand_shape.nonparallel_chord_tone_motion_rate",
        "hand_shape.inner_chord_tone_change_rate",
        "hand_position.max_center_shift",
        "hand_position.mean_center_shift",
        "hand_position.large_center_shift_rate",
        "hand_position.timed_center_shift",
    }

    assert {feature_id for feature_id, _scope, _ref in features} == expected_feature_ids


def test_direct_feature_values_are_extracted_from_score_ir(tmp_path: Path) -> None:
    features = _features_by_key(_write_fixture(tmp_path))

    assert features[("metadata.page_count", "piece", "all")] == 2
    assert features[("metadata.measure_count", "piece", "all")] == 2
    assert features[("metadata.note_count", "piece", "all")] == 5
    assert features[("metadata.pitch_range", "piece", "all")] == 22
    assert features[("metadata.tempo_change_count", "piece", "all")] == 1
    assert features[("metadata.key_change_count", "piece", "all")] == 1
    assert features[("metadata.meter_change_count", "piece", "all")] == 1

    assert features[("rhythm.note_density", "piece", "all")] == 5 / 7
    assert features[("rhythm.attack_density", "piece", "all")] == 3 / 7
    assert features[("rhythm.shortest_written_duration", "piece", "all")] == 0.5
    assert features[("rhythm.tuplet_count", "piece", "all")] == 1
    assert features[("rhythm.duration_value_ratio", "duration_value", "1")] == 0.2
    assert features[("rhythm.duration_value_ratio", "duration_value", "2")] == 0.2
    assert features[("rhythm.duration_value_ratio", "duration_value", "4")] == 0.4
    assert features[("rhythm.duration_value_ratio", "duration_value", "12")] == 0.2
    assert features[("rhythm.significant_shortest_value", "piece", "all")] == 12.0
    assert features[("rhythm.asymmetric_tuplet_measure_ratio", "piece", "all")] == 0.5
    assert features[("rhythm.polyrhythm_measure_ratio", "piece", "all")] == 0.5
    assert features[("rhythm.polyrhythm_flag", "measure", "2")] == 1

    assert features[("pitch_geometry.mean_simultaneity_span", "piece", "all")] == 1.0
    assert features[("pitch_geometry.max_simultaneity_span", "hand", "right")] == 4
    assert features[("pitch_geometry.register_range", "hand", "right")] == 10

    assert features[("leaps.mean_melodic_leap", "hand", "right")] == 3.0
    assert features[("leaps.max_melodic_leap", "hand", "right")] == 3
    assert features[("leaps.count_ge_5", "hand", "right")] == 0
    assert features[("leaps.timed_difficult_displacement_ratio", "hand", "right")] == 0.0
    assert features[("leaps.max_timed_difficult_displacement", "hand", "right")] == 0

    assert features[("texture.notes_per_onset", "piece", "all")] == 5 / 3
    assert features[("texture.simultaneity_density", "piece", "all")] == 1 / 3
    assert features[("texture.chord_count", "hand", "right")] == 1
    assert features[("texture.chord_ratio", "hand", "right")] == 50.0
    assert features[("texture.octave_chord_ratio", "hand", "right")] == 0.0

    assert features[("coordination.aligned_hand_onset_count", "piece", "all")] == 1
    assert features[("coordination.asynchronous_hand_onset_count", "piece", "all")] == 2
    assert features[("coordination.aligned_hand_onset_ratio", "piece", "all")] == 1 / 3
    assert features[("coordination.subdivision_mismatch_proxy", "piece", "all")] == 0.5

    assert features[("notation.accidental_density", "piece", "all")] == 1 / 5
    assert features[("notation.accidental_count", "hand", "right")] == 1
    assert features[("notation.accidental_ratio", "hand", "right")] == 25.0
    assert features[("notation.clef_change_count", "piece", "all")] == 1
    assert features[("notation.cross_staff_note_count", "piece", "all")] == 0

    assert features[("expression.articulated_note_ratio", "piece", "all")] == 3 / 5
    assert features[("expression.articulated_note_ratio", "hand", "right")] == 3 / 4
    assert features[("expression.articulated_note_ratio", "hand", "left")] == 0.0
    assert features[("expression.staccato_note_ratio", "piece", "all")] == 1 / 5
    assert features[("expression.accent_note_ratio", "piece", "all")] == 1 / 5
    assert features[("expression.strong_accent_note_ratio", "piece", "all")] == 0.0
    assert features[("expression.tenuto_note_ratio", "piece", "all")] == 1 / 5
    assert features[("expression.dynamic_marking_count", "piece", "all")] == 2
    assert features[("expression.dynamic_marking_rate", "piece", "all")] == 2 / 7
    assert features[("expression.dynamic_change_count", "piece", "all")] == 1
    assert features[("expression.dynamic_range_span", "piece", "all")] == 2
    assert features[("expression.wedge_start_count", "piece", "all")] == 1
    assert features[("expression.crescendo_start_count", "piece", "all")] == 1
    assert features[("expression.diminuendo_start_count", "piece", "all")] == 0
    assert features[("expression.staff_specific_dynamic_ratio", "piece", "all")] == 1.0


def test_page_count_octave_ratio_and_timed_displacements_are_extracted(
    tmp_path: Path,
) -> None:
    features = _features_by_key(_write_displacement_fixture(tmp_path))

    assert features[("metadata.page_count", "piece", "all")] == 2
    assert features[("texture.chord_ratio", "hand", "right")] == 33.33333333333333
    assert features[("texture.octave_chord_ratio", "hand", "right")] == 100.0
    assert (
        features[("leaps.timed_difficult_displacement_ratio", "hand", "right")]
        == 33.33333333333333
    )
    assert (
        features[("leaps.timed_difficult_displacement_ratio", "hand", "left")]
        == 33.33333333333333
    )
    assert features[("leaps.max_timed_difficult_displacement", "hand", "right")] == 17
    assert features[("leaps.max_timed_difficult_displacement", "hand", "left")] == 17
    assert features[("leaps.timed_difficult_displacement_count", "measure", "2")] == 1


def test_extract_score_returns_json_ready_single_file_result(tmp_path: Path) -> None:
    result = extract_score(_write_fixture(tmp_path))
    payload = result.to_json_payload()

    assert payload["score"]["title"] == "Feature Fixture"
    assert payload["score"]["measure_count"] == 2
    assert payload["schema"] == "piano_difficulty.score_payload"
    assert payload["schema_version"] == "score_payload.v1"
    assert payload["core_feature_schema_version"] == "core_features.v1"
    assert payload["analysis_profiles"] == []
    assert len(payload["features"]) == 135
    assert payload["piece_summary"]["feature_count"] == 135
    assert payload["diagnostics"] == []
