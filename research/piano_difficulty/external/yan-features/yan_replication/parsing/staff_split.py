from __future__ import annotations

from .normalize_events import NoteEvent


def split_by_staff(events: list[NoteEvent]) -> dict[int | None, list[NoteEvent]]:
    out: dict[int | None, list[NoteEvent]] = {}
    for ev in events:
        out.setdefault(ev.staff, []).append(ev)
    return out
