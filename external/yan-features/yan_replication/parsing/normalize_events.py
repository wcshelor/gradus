from __future__ import annotations

from dataclasses import dataclass, field

from music21 import chord, note, stream


@dataclass
class NoteEvent:
    onset_quarter: float
    duration_quarter: float
    midi_pitch: int
    velocity: int | None
    channel: int | None
    track: int | None
    staff: int | None
    voice: int | None
    is_chord_tone: bool
    chord_id: int | None
    articulations: list[str] = field(default_factory=list)
    is_dotted: bool | None = None
    measure_number: int | None = None


def normalize_note_events(score: stream.Score) -> list[NoteEvent]:
    events: list[NoteEvent] = []
    chord_counter = 0
    for part_idx, part in enumerate(score.parts):
        for elem in part.recurse().notes:
            measure_number = getattr(elem, "measureNumber", None)
            if isinstance(elem, note.Note):
                events.append(
                    NoteEvent(
                        onset_quarter=float(elem.offset),
                        duration_quarter=float(elem.quarterLength),
                        midi_pitch=int(elem.pitch.midi),
                        velocity=getattr(elem.volume, "velocity", None),
                        channel=getattr(elem, "channel", None),
                        track=part_idx,
                        staff=None,
                        voice=None,
                        is_chord_tone=False,
                        chord_id=None,
                        articulations=[a.classes[0] for a in elem.articulations],
                        is_dotted=bool(getattr(elem.duration, "dots", 0)) if elem.duration else None,
                        measure_number=measure_number,
                    )
                )
            elif isinstance(elem, chord.Chord):
                chord_id = chord_counter
                chord_counter += 1
                for n in elem.notes:
                    events.append(
                        NoteEvent(
                            onset_quarter=float(elem.offset),
                            duration_quarter=float(elem.quarterLength),
                            midi_pitch=int(n.pitch.midi),
                            velocity=getattr(elem.volume, "velocity", None),
                            channel=getattr(elem, "channel", None),
                            track=part_idx,
                            staff=None,
                            voice=None,
                            is_chord_tone=True,
                            chord_id=chord_id,
                            articulations=[a.classes[0] for a in elem.articulations],
                            is_dotted=bool(getattr(elem.duration, "dots", 0)) if elem.duration else None,
                            measure_number=measure_number,
                        )
                    )
    return sorted(events, key=lambda e: (e.onset_quarter, e.track or -1, e.midi_pitch))
