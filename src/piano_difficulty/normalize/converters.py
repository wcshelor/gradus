"""Converters from raw MusicXML documents into the repository IR."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from piano_difficulty.io.musicxml import MusicXMLDocument, load_musicxml_document
from piano_difficulty.normalize.schema import (
    ClefIR,
    DiagnosticIR,
    DirectionIR,
    LogicalNoteIR,
    MeasureIR,
    OnsetGroupIR,
    RestEventIR,
    ScoreIR,
    WrittenNoteIR,
)

_PITCH_CLASS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
_PIANO_NAME_TOKENS = ("piano", "pno", "pf", "klavier")


@dataclass(slots=True)
class _ActiveState:
    divisions: int = 1
    key_fifths: int | None = None
    key_mode: str | None = None
    time_beats: int | None = None
    time_beat_type: int | None = None
    tempo_bpm: float | None = None
    tempo_text: str | None = None
    page_number: int | None = None


@dataclass(slots=True)
class _ParsedScore:
    score: ScoreIR
    rests: list[RestEventIR]


def build_score_ir(parsed_score: Any) -> ScoreIR:
    """Build the top-level normalized score object from raw MusicXML."""

    document = _coerce_document(parsed_score)
    parsed = _parse_document(document)
    return parsed.score


def normalize_measures(parsed_score: Any) -> list[MeasureIR]:
    """Extract normalized measures with stable timing and numbering."""

    return build_score_ir(parsed_score).measures


def normalize_written_notes(parsed_score: Any) -> list[WrittenNoteIR]:
    """Extract written-note tokens suitable for notation-aware features."""

    return build_score_ir(parsed_score).written_notes


def normalize_rests(parsed_score: Any) -> list[RestEventIR]:
    """Extract notated rests preserved for PHP-compatible gap analysis."""

    return build_score_ir(parsed_score).rests


def normalize_directions(parsed_score: Any) -> list[DirectionIR]:
    """Extract normalized score directions and control markings."""

    return build_score_ir(parsed_score).directions


def normalize_clefs(parsed_score: Any) -> list[ClefIR]:
    """Extract normalized clef declarations."""

    return build_score_ir(parsed_score).clefs


def collapse_ties(written_notes: list[WrittenNoteIR]) -> list[LogicalNoteIR]:
    """Collapse tied written notes into logical attack events."""

    logical_notes, _diagnostics = _collapse_ties_with_diagnostics(written_notes)
    return logical_notes


def _coerce_document(parsed_score: Any) -> MusicXMLDocument:
    if isinstance(parsed_score, MusicXMLDocument):
        return parsed_score

    if isinstance(parsed_score, (str, Path)):
        return load_musicxml_document(parsed_score)

    if isinstance(parsed_score, ElementTree.Element):
        return MusicXMLDocument(
            source_path=Path("<memory>"),
            root=parsed_score,
            xml_payload=ElementTree.tostring(parsed_score),
        )

    raise TypeError(
        "Expected a MusicXMLDocument, raw XML Element, or MusicXML-family path."
    )


def _parse_document(document: MusicXMLDocument) -> _ParsedScore:
    root = document.root
    diagnostics: list[DiagnosticIR] = []

    root_name = _local_name(root.tag)
    if root_name == "score-timewise":
        diagnostics.append(
            DiagnosticIR(
                code="unsupported_score_timewise",
                severity="error",
                message="score-timewise MusicXML is not supported yet.",
            )
        )
        return _ParsedScore(ScoreIR(source_path=document.source_path, diagnostics=diagnostics), [])

    if root_name != "score-partwise":
        diagnostics.append(
            DiagnosticIR(
                code="unsupported_root",
                severity="error",
                message=f"Expected score-partwise MusicXML, got {root_name!r}.",
            )
        )
        return _ParsedScore(ScoreIR(source_path=document.source_path, diagnostics=diagnostics), [])

    part_names = _part_names(root)
    parts = _children(root, "part")
    if not parts:
        diagnostics.append(
            DiagnosticIR(
                code="empty_score",
                severity="error",
                message="MusicXML score contains no part elements.",
            )
        )
        return _ParsedScore(ScoreIR(source_path=document.source_path, diagnostics=diagnostics), [])

    if len(parts) > 1:
        diagnostics.append(
            DiagnosticIR(
                code="multi_part_score",
                severity="warning",
                message=(
                    f"MusicXML score contains {len(parts)} parts; normalization "
                    "selected one piano-like part."
                ),
            )
        )

    selected_part = _select_part(parts, part_names, diagnostics)
    if selected_part is None:
        return _ParsedScore(ScoreIR(source_path=document.source_path, diagnostics=diagnostics), [])

    score = ScoreIR(
        source_path=document.source_path,
        title=_score_title(root),
        composer=_score_composer(root),
        diagnostics=diagnostics,
    )

    _parse_part(selected_part, score)
    logical_notes, tie_diagnostics = _collapse_ties_with_diagnostics(score.written_notes)
    score.diagnostics.extend(tie_diagnostics)
    score.logical_notes = logical_notes

    _assign_staff_hands(score)
    score.onset_groups = _build_onset_groups(score.logical_notes)
    return _ParsedScore(score, score.rests)


def _parse_part(part: ElementTree.Element, score: ScoreIR) -> None:
    state = _ActiveState()
    score_time = Fraction(0)
    xml_order = 0

    for measure_index, measure in enumerate(_children(part, "measure"), start=1):
        measure_number = measure.get("number") or str(measure_index)
        measure_start = score_time
        cursor = Fraction(0)
        max_cursor = Fraction(0)
        last_note_onset = cursor
        last_note_staff: int | None = None
        last_note_voice: str | None = None
        staff_orders: dict[int | None, int] = defaultdict(int)
        measure_starts_new_page = False
        measure_page_number = state.page_number

        for child in list(measure):
            name = _local_name(child.tag)

            if name == "attributes":
                _update_attributes(child, state, score.diagnostics, measure_index)
                _parse_clefs(child, score, measure_index)
                continue

            if name == "print":
                page_number_text = child.get("page-number")
                if page_number_text is not None:
                    page_number = _parse_int(page_number_text)
                    if page_number is not None:
                        state.page_number = page_number
                        measure_page_number = page_number
                if child.get("new-page") == "yes":
                    measure_starts_new_page = True
                continue

            if name == "direction":
                directions = _parse_direction(
                    child,
                    state,
                    measure_start + cursor,
                    measure_index,
                    len(score.directions) + 1,
                )
                score.directions.extend(directions)
                continue

            if name == "sound":
                tempo = _parse_float(child.get("tempo"))
                if tempo is not None:
                    state.tempo_bpm = tempo
                    score.directions.append(
                        DirectionIR(
                            direction_id=f"d{len(score.directions) + 1}",
                            kind="tempo",
                            value=str(tempo),
                            start=measure_start + cursor,
                            measure_index=measure_index,
                        )
                    )
                continue

            if name == "backup":
                cursor -= _duration_from_child(child, state, score.diagnostics, measure_index)
                if cursor < 0:
                    score.diagnostics.append(
                        DiagnosticIR(
                            code="negative_cursor",
                            severity="warning",
                            message="A backup element moved before the measure start.",
                            measure_start=measure_index,
                            measure_end=measure_index,
                        )
                    )
                    cursor = Fraction(0)
                continue

            if name == "forward":
                cursor += _duration_from_child(child, state, score.diagnostics, measure_index)
                max_cursor = max(max_cursor, cursor)
                continue

            if name != "note":
                continue

            xml_order += 1
            duration = _note_duration(child, state, score.diagnostics, measure_index)
            is_chord = _child(child, "chord") is not None
            onset = last_note_onset if is_chord else cursor
            if is_chord and xml_order == 1:
                score.diagnostics.append(
                    DiagnosticIR(
                        code="orphan_chord",
                        severity="warning",
                        message="A chord-continuation note appeared before any base note.",
                        measure_start=measure_index,
                        measure_end=measure_index,
                    )
                )

            staff = _optional_int(_text(_child(child, "staff")))
            voice = _text(_child(child, "voice"))
            staff, voice = _normalize_note_context(
                staff=staff,
                voice=voice,
                is_chord=is_chord,
                last_note_staff=last_note_staff,
                last_note_voice=last_note_voice,
            )
            if staff is None:
                score.diagnostics.append(
                    DiagnosticIR(
                        code="missing_staff",
                        severity="warning",
                        message="A note or rest is missing a staff label.",
                        measure_start=measure_index,
                        measure_end=measure_index,
                    )
                )
            if voice is None:
                score.diagnostics.append(
                    DiagnosticIR(
                        code="missing_voice",
                        severity="info",
                        message="A note or rest is missing a voice label.",
                        measure_start=measure_index,
                        measure_end=measure_index,
                    )
                )

            staff_orders[staff] += 1
            staff_order = staff_orders[staff]

            if _child(child, "rest") is not None:
                score.rests.append(
                    RestEventIR(
                        rest_id=child.get("id") or f"r{xml_order}",
                        onset=measure_start + onset,
                        duration=duration,
                        staff=staff,
                        voice=voice,
                        measure_index=measure_index,
                        duration_type=_text(_child(child, "type")),
                        xml_order=xml_order,
                        measure_staff_order=staff_order,
                    )
                )
            else:
                note = _parse_written_note(
                    child=child,
                    onset=measure_start + onset,
                    duration=duration,
                    staff=staff,
                    voice=voice,
                    measure_index=measure_index,
                    xml_order=xml_order,
                    staff_order=staff_order,
                    diagnostics=score.diagnostics,
                )
                if note is not None:
                    score.written_notes.append(note)

            if not is_chord:
                last_note_onset = cursor
                last_note_staff = staff
                last_note_voice = voice
                cursor += duration
                max_cursor = max(max_cursor, cursor)

        measure_end = measure_start + max_cursor
        score.measures.append(
            MeasureIR(
                measure_index=measure_index,
                measure_number=measure_number,
                start=measure_start,
                end=measure_end,
                time_signature=_format_time_signature(state),
                key_signature=_format_key_signature(state),
                tempo_text=state.tempo_text,
                divisions=state.divisions,
                key_fifths=state.key_fifths,
                key_mode=state.key_mode,
                time_beats=state.time_beats,
                time_beat_type=state.time_beat_type,
                tempo_bpm=state.tempo_bpm,
                page_number=measure_page_number,
                starts_new_page=measure_starts_new_page,
            )
        )
        score_time = measure_end


def _parse_written_note(
    *,
    child: ElementTree.Element,
    onset: Fraction,
    duration: Fraction,
    staff: int | None,
    voice: str | None,
    measure_index: int,
    xml_order: int,
    staff_order: int,
    diagnostics: list[DiagnosticIR],
) -> WrittenNoteIR | None:
    pitch = _child(child, "pitch")
    if pitch is None:
        diagnostics.append(
            DiagnosticIR(
                code="missing_pitch",
                severity="warning",
                message="A non-rest note is missing pitch data.",
                measure_start=measure_index,
                measure_end=measure_index,
            )
        )
        return None

    step = _text(_child(pitch, "step"))
    octave = _optional_int(_text(_child(pitch, "octave")))
    alter = _optional_int(_text(_child(pitch, "alter"))) or 0
    if step not in _PITCH_CLASS or octave is None:
        diagnostics.append(
            DiagnosticIR(
                code="malformed_pitch",
                severity="warning",
                message="A note has malformed pitch data.",
                measure_start=measure_index,
                measure_end=measure_index,
            )
        )
        return None

    tuplet_actual, tuplet_normal = _time_modification(child)
    tie_start, tie_stop = _tie_flags(child)
    midi = (octave + 1) * 12 + _PITCH_CLASS[step] + alter

    return WrittenNoteIR(
        note_id=child.get("id") or f"n{xml_order}",
        pitch_midi=midi,
        onset=onset,
        duration=duration,
        staff=staff,
        voice=voice,
        is_grace=_child(child, "grace") is not None,
        tie_start=tie_start,
        tie_stop=tie_stop,
        articulations=_articulations(child),
        accidental=_text(_child(child, "accidental")),
        measure_index=measure_index,
        pitch_step=step,
        pitch_octave=octave,
        alter=alter,
        duration_type=_text(_child(child, "type")),
        is_chord_continuation=_child(child, "chord") is not None,
        tuplet_actual=tuplet_actual,
        tuplet_normal=tuplet_normal,
        xml_order=xml_order,
        measure_staff_order=staff_order,
    )


def _collapse_ties_with_diagnostics(
    written_notes: list[WrittenNoteIR],
) -> tuple[list[LogicalNoteIR], list[DiagnosticIR]]:
    diagnostics: list[DiagnosticIR] = []
    logical_notes: list[LogicalNoteIR] = []
    open_ties: dict[tuple[int, int | None, str | None], list[WrittenNoteIR]] = {}

    for note in sorted(written_notes, key=lambda n: (n.onset, n.xml_order or 0)):
        key = (note.pitch_midi, note.staff, note.voice)

        if note.tie_stop:
            chain = open_ties.get(key)
            if chain is None:
                diagnostics.append(
                    DiagnosticIR(
                        code="unmatched_tie_stop",
                        severity="warning",
                        message="A tie stop did not match an open tie start.",
                        measure_start=note.measure_index,
                        measure_end=note.measure_index,
                    )
                )
                chain = [note]
            else:
                chain.append(note)

            if note.tie_start:
                open_ties[key] = chain
            else:
                open_ties.pop(key, None)
                logical_notes.append(_logical_from_chain(chain))
            continue

        if note.tie_start:
            previous_chain = open_ties.get(key)
            if previous_chain is not None:
                diagnostics.append(
                    DiagnosticIR(
                        code="overlapping_tie_start",
                        severity="warning",
                        message="A tie start appeared before the previous tie closed.",
                        measure_start=note.measure_index,
                        measure_end=note.measure_index,
                    )
                )
                logical_notes.append(_logical_from_chain(previous_chain))
            open_ties[key] = [note]
            continue

        logical_notes.append(_logical_from_chain([note]))

    for chain in open_ties.values():
        first = chain[0]
        diagnostics.append(
            DiagnosticIR(
                code="unclosed_tie",
                severity="warning",
                message="A tie start was not closed before the end of the score.",
                measure_start=first.measure_index,
                measure_end=chain[-1].measure_index,
            )
        )
        logical_notes.append(_logical_from_chain(chain))

    logical_notes.sort(key=lambda n: (n.onset, n.xml_order or 0))
    return logical_notes, diagnostics


def _logical_from_chain(chain: list[WrittenNoteIR]) -> LogicalNoteIR:
    first = chain[0]
    duration = sum((note.duration for note in chain), Fraction(0))
    return LogicalNoteIR(
        note_id=first.note_id,
        pitch_midi=first.pitch_midi,
        onset=first.onset,
        duration=duration,
        staff=first.staff,
        voice=first.voice,
        hand=first.hand,
        hand_confidence=first.hand_confidence,
        measure_index=first.measure_index,
        source_note_ids=tuple(note.note_id for note in chain),
        pitch_step=first.pitch_step,
        pitch_octave=first.pitch_octave,
        alter=first.alter,
        xml_order=first.xml_order,
        measure_staff_order=first.measure_staff_order,
    )


def _assign_staff_hands(score: ScoreIR) -> None:
    for event in [*score.written_notes, *score.rests, *score.logical_notes]:
        if event.staff == 1:
            event.hand = "right"
            event.hand_confidence = "staff"
        elif event.staff == 2:
            event.hand = "left"
            event.hand_confidence = "staff"
        elif event.staff is not None:
            event.hand = None
            event.hand_confidence = "unknown_staff"
            score.diagnostics.append(
                DiagnosticIR(
                    code="unknown_staff_hand",
                    severity="info",
                    message=f"Staff {event.staff} could not be mapped to a piano hand.",
                    measure_start=event.measure_index,
                    measure_end=event.measure_index,
                )
            )


def _build_onset_groups(notes: list[LogicalNoteIR]) -> list[OnsetGroupIR]:
    from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand

    return [*group_onsets(notes), *group_onsets_by_hand(notes)]


def _normalize_note_context(
    *,
    staff: int | None,
    voice: str | None,
    is_chord: bool,
    last_note_staff: int | None,
    last_note_voice: str | None,
) -> tuple[int | None, str | None]:
    """Fill note context that MusicXML chord continuations commonly inherit."""

    if not is_chord:
        return staff, voice

    normalized_staff = staff if staff is not None else last_note_staff
    normalized_voice = voice if voice is not None else last_note_voice
    return normalized_staff, normalized_voice


def _select_part(
    parts: list[ElementTree.Element],
    part_names: dict[str, str],
    diagnostics: list[DiagnosticIR],
) -> ElementTree.Element | None:
    if len(parts) == 1:
        return parts[0]

    for part in parts:
        part_id = part.get("id") or ""
        name = part_names.get(part_id, "").lower()
        if any(token in name for token in _PIANO_NAME_TOKENS):
            return part

    diagnostics.append(
        DiagnosticIR(
            code="no_piano_part",
            severity="warning",
            message="No piano-like part name found; selected the first part.",
        )
    )
    return parts[0] if parts else None


def _part_names(root: ElementTree.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    part_list = _child(root, "part-list")
    if part_list is None:
        return result

    for score_part in _children(part_list, "score-part"):
        part_id = score_part.get("id")
        if part_id:
            result[part_id] = _text(_child(score_part, "part-name")) or ""
    return result


def _score_title(root: ElementTree.Element) -> str | None:
    work = _child(root, "work")
    work_title = _text(_child(work, "work-title")) if work is not None else None
    movement_title = _text(_child(root, "movement-title"))
    if work_title or movement_title:
        return " ".join(part for part in (work_title, movement_title) if part)

    credit_words = [
        text
        for credit in _children(root, "credit")
        for text in [_text(_child(credit, "credit-words"))]
        if text
    ]
    return ", ".join(credit_words) if credit_words else None


def _score_composer(root: ElementTree.Element) -> str | None:
    identification = _child(root, "identification")
    if identification is None:
        return None

    creators = _children(identification, "creator")
    for creator in creators:
        if creator.get("type") == "composer":
            return _text(creator)
    return _text(creators[0]) if creators else None


def _update_attributes(
    attributes: ElementTree.Element,
    state: _ActiveState,
    diagnostics: list[DiagnosticIR],
    measure_index: int,
) -> None:
    divisions = _optional_int(_text(_child(attributes, "divisions")))
    if divisions is not None:
        if divisions <= 0:
            diagnostics.append(
                DiagnosticIR(
                    code="invalid_divisions",
                    severity="warning",
                    message="A divisions value must be positive; kept previous value.",
                    measure_start=measure_index,
                    measure_end=measure_index,
                )
            )
        else:
            state.divisions = divisions

    key = _child(attributes, "key")
    if key is not None:
        state.key_fifths = _optional_int(_text(_child(key, "fifths")))
        state.key_mode = _text(_child(key, "mode"))

    time = _child(attributes, "time")
    if time is not None:
        state.time_beats = _optional_int(_text(_child(time, "beats")))
        state.time_beat_type = _optional_int(_text(_child(time, "beat-type")))


def _parse_clefs(
    attributes: ElementTree.Element,
    score: ScoreIR,
    measure_index: int,
) -> None:
    for clef in _children(attributes, "clef"):
        sign = _text(_child(clef, "sign"))
        if not sign:
            continue

        score.clefs.append(
            ClefIR(
                clef_id=f"c{len(score.clefs) + 1}",
                sign=sign,
                line=_optional_int(_text(_child(clef, "line"))),
                staff=_optional_int(clef.get("number")),
                measure_index=measure_index,
            )
        )


def _parse_direction(
    direction: ElementTree.Element,
    state: _ActiveState,
    start: Fraction,
    measure_index: int,
    first_direction_number: int,
) -> list[DirectionIR]:
    result: list[DirectionIR] = []
    staff = _optional_int(_text(_child(direction, "staff")))
    direction_type = _child(direction, "direction-type")

    if direction_type is not None:
        words = _text(_child(direction_type, "words"))
        if words:
            state.tempo_text = words
            result.append(
                DirectionIR(
                    direction_id=f"d{first_direction_number + len(result)}",
                    kind="words",
                    value=words,
                    start=start,
                    measure_index=measure_index,
                    staff=staff,
                )
            )

        dynamics = _child(direction_type, "dynamics")
        if dynamics is not None:
            value = ",".join(_local_name(child.tag) for child in list(dynamics))
            if value:
                result.append(
                    DirectionIR(
                        direction_id=f"d{first_direction_number + len(result)}",
                        kind="dynamics",
                        value=value,
                        start=start,
                        measure_index=measure_index,
                        staff=staff,
                    )
                )

        metronome = _child(direction_type, "metronome")
        if metronome is not None:
            value = " ".join(text for text in metronome.itertext() if text.strip())
            if value:
                result.append(
                    DirectionIR(
                        direction_id=f"d{first_direction_number + len(result)}",
                        kind="metronome",
                        value=value,
                        start=start,
                        measure_index=measure_index,
                        staff=staff,
                    )
                )

    sound = _child(direction, "sound")
    tempo = _parse_float(sound.get("tempo") if sound is not None else None)
    if tempo is not None:
        state.tempo_bpm = tempo
        result.append(
            DirectionIR(
                direction_id=f"d{first_direction_number + len(result)}",
                kind="tempo",
                value=str(tempo),
                start=start,
                measure_index=measure_index,
                staff=staff,
            )
        )

    return result


def _duration_from_child(
    element: ElementTree.Element,
    state: _ActiveState,
    diagnostics: list[DiagnosticIR],
    measure_index: int,
) -> Fraction:
    duration_text = _text(_child(element, "duration"))
    duration_units = _optional_int(duration_text)
    if duration_units is None:
        diagnostics.append(
            DiagnosticIR(
                code="missing_duration",
                severity="warning",
                message="A timed MusicXML element is missing duration.",
                measure_start=measure_index,
                measure_end=measure_index,
            )
        )
        return Fraction(0)
    return Fraction(duration_units, state.divisions)


def _note_duration(
    note: ElementTree.Element,
    state: _ActiveState,
    diagnostics: list[DiagnosticIR],
    measure_index: int,
) -> Fraction:
    if _child(note, "grace") is not None and _child(note, "duration") is None:
        return Fraction(0)
    return _duration_from_child(note, state, diagnostics, measure_index)


def _time_modification(note: ElementTree.Element) -> tuple[int | None, int | None]:
    time_modification = _child(note, "time-modification")
    if time_modification is None:
        return None, None
    actual = _optional_int(_text(_child(time_modification, "actual-notes")))
    normal = _optional_int(_text(_child(time_modification, "normal-notes")))
    return actual, normal


def _tie_flags(note: ElementTree.Element) -> tuple[bool, bool]:
    starts = False
    stops = False
    for element in list(note):
        if _local_name(element.tag) == "tie":
            starts, stops = _merge_tie_type(element.get("type"), starts, stops)

    notations = _child(note, "notations")
    if notations is not None:
        for element in _children(notations, "tied"):
            starts, stops = _merge_tie_type(element.get("type"), starts, stops)

    return starts, stops


def _merge_tie_type(
    tie_type: str | None,
    starts: bool,
    stops: bool,
) -> tuple[bool, bool]:
    if tie_type == "start":
        starts = True
    elif tie_type == "stop":
        stops = True
    elif tie_type == "continue":
        starts = True
        stops = True
    return starts, stops


def _articulations(note: ElementTree.Element) -> tuple[str, ...]:
    notations = _child(note, "notations")
    if notations is None:
        return ()
    articulations = _child(notations, "articulations")
    if articulations is None:
        return ()
    return tuple(_local_name(child.tag) for child in list(articulations))


def _format_time_signature(state: _ActiveState) -> str | None:
    if state.time_beats is None or state.time_beat_type is None:
        return None
    return f"{state.time_beats}/{state.time_beat_type}"


def _format_key_signature(state: _ActiveState) -> str | None:
    if state.key_fifths is None:
        return None
    if state.key_mode:
        return f"{state.key_fifths} {state.key_mode}"
    return str(state.key_fifths)


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _child(
    element: ElementTree.Element | None,
    name: str,
) -> ElementTree.Element | None:
    if element is None:
        return None
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    return _optional_int(value)


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
