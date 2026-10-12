"""Build a normalized event table from ScoreIR.

This is the milestone-1 adapter. It does not replace the MusicXML loader
or ScoreIR; it produces a stable token layer between ScoreIR and difficulty
reasoning, analogous to mxltoolbox core.events but native.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

from piano_difficulty.normalize.schema import LogicalNoteIR, MeasureIR, ScoreIR, WrittenNoteIR

from .models import LOCAL_EVENT_COLUMNS, ScoreEvent

_MIDI_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _midi_name(midi: int | None, *, alter: int | None = None, accidental: str | None = None) -> str | None:
    if midi is None:
        return None
    # Prefer MusicXML spelling when alter/accidental indicates flat vs sharp
    if alter == -1 or (isinstance(accidental, str) and "flat" in accidental.lower()):
        return f"{_FLAT_NAMES[midi % 12]}{(midi // 12) - 1}"
    if alter == 1 or (isinstance(accidental, str) and "sharp" in accidental.lower()):
        return f"{_MIDI_NAMES[midi % 12]}{(midi // 12) - 1}"
    return f"{_MIDI_NAMES[midi % 12]}{(midi // 12) - 1}"


def _pitch_class(midi: int | None) -> int | None:
    if midi is None:
        return None
    return midi % 12


def _octave(midi: int | None) -> int | None:
    if midi is None:
        return None
    return (midi // 12) - 1


def build_event_table(score: ScoreIR, *, include_rests: bool = True) -> list[ScoreEvent]:
    """Return sorted ScoreEvent rows for notes (+ rests) with provenance.

    Guarantees:
    - Each pitch in a chord is a separate row (chord splitting).
    - Rests preserved when include_rests=True.
    - Ties: logical notes already collapsed; tie_merged indicates chain length >1.
    - Stable provenance: source_note_ids, xml_order, measure_index/number.
    - Sorted by (onset, staff, voice, pitch_midi).
    """
    score_id = str(score.source_path) if score.source_path is not None else score.title
    # index measures
    measure_by_index: dict[int, MeasureIR] = {m.measure_index: m for m in score.measures}
    # Map xml_order provenance from written notes for logical notes?
    # logical notes already have source_note_ids; retrieve written for extra
    written_by_id: dict[str, WrittenNoteIR] = {n.note_id: n for n in score.written_notes}

    # chord detection: group logical notes by onset+staff+voice? Actually by onset+hand+measure?
    # Simpler: same onset + same staff = simultaneity. Count per onset.
    onset_groups: dict[Fraction, list[LogicalNoteIR]] = defaultdict(list)
    for n in score.logical_notes:
        onset_groups[n.onset].append(n)
    # also include rests group? Keep separate chord_id for notes.

    events: list[ScoreEvent] = []

    # Build chord_id map: for each onset where >1 note overall, assign id prefix
    chord_counter = 0
    chord_id_for_onset: dict[Fraction, str] = {}
    for onset, notes in onset_groups.items():
        if len(notes) > 1:
            # Check if notes share same hand/staff group => treat as chord?
            # If multiple notes at same onset regardless, consider chord-like; assign shared id
            # But to support per-hand chord analysis, assign per staff
            # Simplify: one chord_id per onset where >1 note at that onset
            chord_counter += 1
            chord_id_for_onset[onset] = f"chord:{onset}:{chord_counter}"
        # Also per-staff simultaneity
    # For more precise per-staff chord_id, later refinement if needed

    for idx, note in enumerate(sorted(score.logical_notes, key=lambda n: (n.onset, n.staff or 99, n.voice or "", n.pitch_midi))):
        m = measure_by_index.get(note.measure_index) if note.measure_index is not None else None
        beat = (note.onset - m.start) if m is not None else None
        # Determine is_chord_tone: more than one note at same onset in same staff/hand
        staff_notes_at_onset = [x for x in onset_groups[note.onset] if x.staff == note.staff]
        is_chord_tone = len(staff_notes_at_onset) > 1
        chord_id = chord_id_for_onset.get(note.onset) if is_chord_tone else None
        # Lookup written for articulation dynamics etc
        written = None
        if note.source_note_ids:
            # first source
            written = written_by_id.get(note.source_note_ids[0])
        # Derive key/time/clef/tempo from measure
        key_sig = m.key_signature if m is not None else None
        time_sig = m.time_signature if m is not None else None
        tempo = m.tempo_bpm if m is not None else None
        clef = None
        # pick clef matching staff and measure proximity
        if note.staff is not None:
            for c in score.clefs:
                if c.staff == note.staff and c.measure_index == note.measure_index:
                    clef = c.sign
                    break
        # dynamics: nearest direction with kind dynamics or wedge before onset
        dynamics = None
        # Quick: find directions with kind dynamics/wedge and start <= onset; pick latest
        # Not critical for milestone 1, but include for evidence
        latest_dyn = None
        for d in score.directions:
            if d.kind in ("dynamics", "wedge") and d.start <= note.onset:
                latest_dyn = d.value
        dynamics = latest_dyn
        articulation = tuple(written.articulations) if written is not None else ()
        tuplet = None
        if written is not None and written.tuplet_actual is not None:
            tuplet = f"{written.tuplet_actual}:{written.tuplet_normal}"

        event = ScoreEvent(
            event_id=f"e{idx+1}:{note.note_id}",
            score_id=score_id,
            measure_index=note.measure_index,
            measure_number=m.measure_number if m is not None else str(note.measure_index),
            staff=note.staff,
            voice=note.voice,
            hand=note.hand,
            hand_confidence=note.hand_confidence,
            beat=beat,
            offset_quarter=float(note.onset),
            duration_quarter=float(note.duration),
            onset=note.onset,
            end=note.onset + note.duration,
            duration=note.duration,
            is_rest=False,
            is_chord_tone=is_chord_tone,
            chord_id=chord_id,
            pitch_midi=note.pitch_midi,
            pitch_name=_midi_name(note.pitch_midi, alter=note.alter, accidental=written.accidental if written else None),
            pitch_class=_pitch_class(note.pitch_midi),
            octave=_octave(note.pitch_midi),
            accidental=written.accidental if written else None,
            alter=note.alter,
            tie_merged=len(note.source_note_ids) > 1,
            source_note_ids=tuple(note.source_note_ids),
            xml_order=note.xml_order,
            measure_staff_order=note.measure_staff_order,
            is_grace=written.is_grace if written else False,
            duration_type=written.duration_type if written else None,
            key_signature=key_sig,
            time_signature=time_sig,
            clef=clef,
            tempo_bpm=tempo,
            dynamics=dynamics,
            articulation=articulation,
            tuplet=tuplet,
            is_arpeggiated=bool(note.arpeggiate) or (written.arpeggiate if written is not None else False),
            has_slur_start=bool(note.has_slur_start) or (written.has_slur_start if written is not None else False),
            has_slur_stop=bool(note.has_slur_stop) or (written.has_slur_stop if written is not None else False),
            phrase_start=bool(getattr(note, "phrase_start", False)) or (getattr(written, "phrase_start", False) if written is not None else False),
            phrase_stop=bool(getattr(note, "phrase_stop", False)) or (getattr(written, "phrase_stop", False) if written is not None else False),
            extra={"logical_note_id": note.note_id, "arpeggiate": bool(note.arpeggiate)},
        )
        events.append(event)

    if include_rests:
        # Rests: preserve similar structure
        offset = len(events)
        for r_idx, rest in enumerate(sorted(score.rests, key=lambda r: (r.onset, r.staff or 99))):
            m = measure_by_index.get(rest.measure_index) if rest.measure_index is not None else None
            beat = (rest.onset - m.start) if m is not None else None
            key_sig = m.key_signature if m is not None else None
            time_sig = m.time_signature if m is not None else None
            tempo = m.tempo_bpm if m is not None else None
            clef = None
            if rest.staff is not None:
                for c in score.clefs:
                    if c.staff == rest.staff and c.measure_index == rest.measure_index:
                        clef = c.sign
                        break
            events.append(
                ScoreEvent(
                    event_id=f"e{offset+r_idx+1}:{rest.rest_id}",
                    score_id=score_id,
                    measure_index=rest.measure_index,
                    measure_number=m.measure_number if m is not None else str(rest.measure_index),
                    staff=rest.staff,
                    voice=rest.voice,
                    hand=rest.hand,
                    hand_confidence=rest.hand_confidence,
                    beat=beat,
                    offset_quarter=float(rest.onset),
                    duration_quarter=float(rest.duration),
                    onset=rest.onset,
                    end=rest.onset + rest.duration,
                    duration=rest.duration,
                    is_rest=True,
                    is_chord_tone=False,
                    chord_id=None,
                    pitch_midi=None,
                    pitch_name=None,
                    pitch_class=None,
                    octave=None,
                    accidental=None,
                    alter=None,
                    tie_merged=False,
                    source_note_ids=(rest.rest_id,),
                    xml_order=rest.xml_order,
                    measure_staff_order=rest.measure_staff_order,
                    is_grace=False,
                    duration_type=rest.duration_type,
                    key_signature=key_sig,
                    time_signature=time_sig,
                    clef=clef,
                    tempo_bpm=tempo,
                    dynamics=None,
                    articulation=(),
                    tuplet=None,
                    extra={"rest_id": rest.rest_id},
                )
            )

    # Final sort
    events_sorted = sorted(events, key=lambda e: (e.onset, e.staff or 99, e.voice or "", e.pitch_midi or -1))
    # Ensure event table columns available via helper
    return events_sorted


def event_table_to_dicts(events: list[ScoreEvent]) -> list[dict[str, Any]]:
    return [e.to_dict() for e in events]


def event_table_to_dataframe(events: list[ScoreEvent]):  # type: ignore[no-untyped-def]
    """Convert to pandas DataFrame if pandas installed; else raise."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas required for DataFrame conversion") from exc
    rows = event_table_to_dicts(events)
    df = pd.DataFrame(rows)
    # Ensure column order
    for col in LOCAL_EVENT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    cols = [c for c in LOCAL_EVENT_COLUMNS if c in df.columns]
    # sort as in mxltoolbox events_dataframe
    sort_cols = [c for c in ["onset", "staff", "voice", "measure_index", "pitch_midi"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)
    return df

