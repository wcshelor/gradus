"""PHP ScoreAnalyzer-oriented views over normalized score data."""

from __future__ import annotations

from dataclasses import dataclass

from piano_difficulty.normalize.schema import (
    MeasureIR,
    RestEventIR,
    ScoreIR,
    WrittenNoteIR,
)

StaffEvent = WrittenNoteIR | RestEventIR


@dataclass(slots=True)
class PHPStaffStream:
    """Staff-local stream matching the PHP analyzer's MusicXML traversal style."""

    staff: int
    notes: list[WrittenNoteIR]
    rests: list[RestEventIR]
    events: list[StaffEvent]


@dataclass(slots=True)
class PHPCompatibilityView:
    """Convenience container for PHP-compatible feature extraction."""

    staff_streams: dict[int, PHPStaffStream]
    tuplets_by_measure: dict[int, tuple[WrittenNoteIR, ...]]
    measure_context: dict[int, MeasureIR]

    def notes_for_staff(self, staff: int) -> list[WrittenNoteIR]:
        stream = self.staff_streams.get(staff)
        return [] if stream is None else stream.notes

    def events_for_staff(self, staff: int) -> list[StaffEvent]:
        stream = self.staff_streams.get(staff)
        return [] if stream is None else stream.events


def build_php_compatibility_view(score: ScoreIR) -> PHPCompatibilityView:
    """Build staff-local streams for porting ScoreAnalyzer feature math."""

    events_by_staff: dict[int, list[StaffEvent]] = {}
    notes_by_staff: dict[int, list[WrittenNoteIR]] = {}
    rests_by_staff: dict[int, list[RestEventIR]] = {}

    for note in score.written_notes:
        if note.staff is None:
            continue
        notes_by_staff.setdefault(note.staff, []).append(note)
        events_by_staff.setdefault(note.staff, []).append(note)

    for rest in score.rests:
        if rest.staff is None:
            continue
        rests_by_staff.setdefault(rest.staff, []).append(rest)
        events_by_staff.setdefault(rest.staff, []).append(rest)

    staff_streams: dict[int, PHPStaffStream] = {}
    for staff in sorted(events_by_staff):
        staff_streams[staff] = PHPStaffStream(
            staff=staff,
            notes=sorted(notes_by_staff.get(staff, []), key=_event_order),
            rests=sorted(rests_by_staff.get(staff, []), key=_event_order),
            events=sorted(events_by_staff[staff], key=_event_order),
        )

    tuplets_by_measure: dict[int, list[WrittenNoteIR]] = {}
    for note in score.written_notes:
        if note.measure_index is None:
            continue
        if note.tuplet_actual is not None or note.tuplet_normal is not None:
            tuplets_by_measure.setdefault(note.measure_index, []).append(note)

    return PHPCompatibilityView(
        staff_streams=staff_streams,
        tuplets_by_measure={
            measure_index: tuple(sorted(notes, key=_event_order))
            for measure_index, notes in sorted(tuplets_by_measure.items())
        },
        measure_context={measure.measure_index: measure for measure in score.measures},
    )


def _event_order(event: StaffEvent) -> tuple[object, int, int]:
    return (
        event.onset,
        event.measure_staff_order or 0,
        event.xml_order or 0,
    )
