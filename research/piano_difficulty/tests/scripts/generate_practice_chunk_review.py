"""Practice Chunk review artifact generator — static visual QA.

Generates a lightweight review/debug view for PracticeChunks for a selected
score passage. Not a product UI; for visually confirming whether chunks
are being separated logically.

Usage:
  PYTHONPATH=research/piano_difficulty/src python research/piano_difficulty/tests/scripts/generate_practice_chunk_review.py \
    /path/to/score.musicxml --measures 27-28 --output-dir research/piano_difficulty/tests/artifacts/practice_chunk_review/clair_de_lune_27_28

Optional flags:
  --flagged 27,28
  --source-label clair_de_lune
  --max-chunks N
  --include-context
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

try:
    from tests.scripts._bootstrap import add_repo_root_to_sys_path

    add_repo_root_to_sys_path()
except ModuleNotFoundError:
    import pathlib as _pl

    _here = _pl.Path(__file__).resolve()
    _proj_root = _here.parents[2]
    _src_root = _proj_root / "src"
    for _c in (str(_proj_root), str(_src_root)):
        if _c not in sys.path:
            sys.path.insert(0, _c)

from piano_difficulty.io.musicxml import load_musicxml_document  # noqa: E402
from piano_difficulty.normalize.converters import build_score_ir  # noqa: E402
from piano_difficulty.semantic_tokens import build_semantic_bundle  # noqa: E402


# ---------------------------------------------------------------------------
# helpers for span filtering (mirror local_inspection private helpers)
# ---------------------------------------------------------------------------

def _parse_measures(s: str) -> tuple[int, int]:
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a.strip()), int(b.strip())
    if ":" in s:
        a, b = s.split(":", 1)
        return int(a.strip()), int(b.strip())
    v = int(s)
    return v, v


def _int_measures(measure_numbers: tuple[str, ...]) -> list[int]:
    out: list[int] = []
    for m in measure_numbers:
        try:
            out.append(int(str(m).strip()))
        except Exception:
            continue
    return out


def _onset_bounds_for_span(bundle, a: int, b: int) -> tuple[Fraction | None, Fraction | None]:
    evs = [e for e in bundle.events if e.measure_index is not None and a <= int(str(e.measure_number or 0)) <= b]  # fallback
    # Better: use measure_number numeric if available
    evs2: list = []
    for e in bundle.events:
        mn = e.measure_number
        if mn is not None:
            try:
                iv = int(str(mn).strip())
            except Exception:
                continue
            if a <= iv <= b:
                evs2.append(e)
        elif e.measure_index is not None:
            # estimate: measure_number may be derived from index; use onset windows
            pass
    if evs2:
        evs = evs2
    else:
        # try onset window via measure_index mapping: use any events whose onset overlaps span's events?
        # If still empty, try generic filter via measure_index range if bundle has contiguous mapping
        # fallback: take all events and try to find measure_index range matching measure_numbers via first measure start
        # simplest: just return None bounds so span fallback via numeric check still works
        if not evs:
            # last fallback: use all events whose measure_number is parsable and in range? Already tried.
            # Use onset bounds of nearest found events? Return None.
            return None, None
    if not evs:
        return None, None
    return min(e.onset for e in evs), max(e.end for e in evs)


def _span_intersects_object(obj, a: int, b: int) -> bool:
    # Generic check for objects / chunks that have measure_numbers or measure_start/end
    mnums = getattr(obj, "measure_numbers", ())
    ints = _int_measures(tuple(mnums) if mnums else ())
    if ints:
        return any(a <= x <= b for x in ints)
    ms = getattr(obj, "measure_start", None)
    me = getattr(obj, "measure_end", None)
    if ms is not None and me is not None:
        try:
            # ms/me are measure indices or measure numbers? Treat as int if numeric
            return not (int(me) < a or int(ms) > b)
        except Exception:
            return False
    if ms is not None:
        try:
            return a <= int(ms) <= b
        except Exception:
            return False
    return False


def _in_onset_window(obj, start: Fraction | None, end: Fraction | None) -> bool:
    if start is None or end is None:
        return False
    o_start = getattr(obj, "start_onset", None)
    o_end = getattr(obj, "end_onset", None)
    # ScoreEvent uses onset/end, not start_onset
    if o_start is None:
        o_start = getattr(obj, "onset", None)
    if o_end is None:
        o_end = getattr(obj, "end", None)
    if o_start is None or o_end is None:
        return False
    return not (o_end <= start or o_start >= end)


def _event_in_span(event, a: int, b: int, onset_start, onset_end) -> bool:
    # check measure_number numeric
    mn = event.measure_number
    if mn is not None:
        try:
            iv = int(str(mn).strip())
            if a <= iv <= b:
                return True
        except Exception:
            pass
    # also try measure_index mismatch guard? measure_index may be 0-based; skip numeric check
    if _in_onset_window(event, onset_start, onset_end):
        return True
    # also allow if measure_index corresponds? Not reliable.
    return False


def _escape(s: str | None) -> str:
    if s is None:
        return "—"
    return html.escape(str(s))


# ---------------------------------------------------------------------------
# MusicXML snippet helpers — visual QA for chunk evidence
# ---------------------------------------------------------------------------

_DIVISIONS = 480
_MIDI_STEP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_MIDI_STEP_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _sanitize_filename(s: str) -> str:
    # replace characters unsafe for filenames (including : /)
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def _sanitize_chunk_id(chunk_id: str) -> str:
    # keep colons as underscores for readability
    return _sanitize_filename(chunk_id).strip("_") or "chunk"


def _midi_to_step_alter_octave(midi: int, pitch_name: str | None = None, alter_hint: int | None = None, accidental_hint: str | None = None):
    # Prefer pitch_name if available (encodes correct spelling for -5 etc)
    if pitch_name:
        m = re.match(r"^([A-G])([#b]?)(-?\d+)$", str(pitch_name).strip())
        if m:
            step, acc, oct_s = m.groups()
            octv = int(oct_s)
            alter = 0
            if acc == "#":
                alter = 1
            elif acc == "b":
                alter = -1
            # cross-check with midi? Keep spelling
            return step, alter, octv
    # fallback: derive from midi + alter_hint/accidental
    pc = midi % 12
    octave = (midi // 12) - 1
    if alter_hint == -1 or (isinstance(accidental_hint, str) and "flat" in accidental_hint.lower()):
        name = _MIDI_STEP_FLAT[pc]
    else:
        name = _MIDI_STEP_NAMES[pc]
    m2 = re.match(r"^([A-G])([#b]?)", name)
    if m2:
        step = m2.group(1)
        acc = m2.group(2)
        alter = 1 if acc == "#" else -1 if acc == "b" else 0
        return step, alter, octave
    # fallback to C
    return "C", 0, octave


def _fraction_to_type_and_dots(duration: Fraction) -> tuple[str, int]:
    # Map common durations to MusicXML type. Fallback to quarter with ticks.
    # durations are in quarter notes.
    d = float(duration)
    # standard types
    mapping = [
        (4.0, "whole", 0),
        (3.0, "half", 1),  # dotted half = 3 q
        (2.0, "half", 0),
        (1.5, "quarter", 1),
        (1.0, "quarter", 0),
        (0.75, "eighth", 1),
        (0.5, "eighth", 0),
        (0.375, "16th", 1),
        (0.25, "16th", 0),
        (0.1875, "32nd", 1),
        (0.125, "32nd", 0),
        (0.0625, "64th", 0),
    ]
    for val, typ, dots in mapping:
        if abs(d - val) < 1e-6:
            return typ, dots
    # dotted variants not listed (quarter dotted etc already); try heuristics
    if abs(d - 2.25) < 1e-6:
        return "quarter", 2  # not standard but approximate
    # fallback: choose closest type below and let duration ticks handle length
    # Use quarter for unknown but will render with correct duration ticks
    if d >= 4:
        return "whole", 0
    if d >= 2:
        return "half", 0
    if d >= 1:
        return "quarter", 0
    if d >= 0.5:
        return "eighth", 0
    if d >= 0.25:
        return "16th", 0
    if d >= 0.125:
        return "32nd", 0
    return "64th", 0


def _duration_to_divisions(duration: Fraction, divisions: int = _DIVISIONS) -> int:
    # duration is in quarter notes; divisions per quarter
    return int(Fraction(duration) * divisions)


def events_to_musicxml_snippet(
    events: list,
    *,
    title: str,
    single_staff: bool | None = None,
    color_by_id: dict[str, str] | None = None,
) -> str:
    """Return MusicXML string for given ScoreEvents.

    * title used in <work> / <creator> metadata
    * single_staff if None auto-detects; True -> one staff, False -> grand staff (two parts)
    * color_by_id maps event_id -> hex color like '#1a73e8' for primary/context distinction
    """
    if not events:
        # minimal empty snippet
        events = []

    # sort
    events_sorted = sorted(events, key=lambda e: (e.onset, e.pitch_midi or -1))

    # auto-detect staff handling
    if single_staff is None:
        staves = {e.staff for e in events_sorted if e.staff is not None}
        hands = {e.hand for e in events_sorted if e.hand in ("right", "left")}
        if len(staves) > 1 or len(hands) > 1:
            single_staff = False
        else:
            single_staff = True

    # Determine attributes from first event or defaults
    key_sig = None
    time_sig = None
    tempo = None
    clef_hint = None
    for e in events_sorted:
        if e.key_signature and not key_sig:
            key_sig = e.key_signature
        if e.time_signature and not time_sig:
            time_sig = e.time_signature
        if e.clef and not clef_hint:
            clef_hint = e.clef
        if e.tempo_bpm and not tempo:
            tempo = e.tempo_bpm
    if not time_sig:
        time_sig = "4/4"
    # parse fifths from key_sig if numeric like "-5" or "2 major"
    fifths = 0
    mode = None
    if key_sig:
        m = re.match(r"^\s*(-?\d+)", str(key_sig))
        if m:
            try:
                fifths = int(m.group(1))
            except Exception:
                fifths = 0
        if "minor" in str(key_sig).lower():
            mode = "minor"
        elif "major" in str(key_sig).lower():
            mode = "major"

    time_beats = 4
    time_beat_type = 4
    if time_sig and "/" in str(time_sig):
        try:
            a, b = str(time_sig).split("/", 1)
            time_beats = int(a.strip())
            time_beat_type = int(b.strip())
        except Exception:
            pass

    # Build MusicXML tree
    score = ET.Element("score-partwise", version="4.0")
    # identification
    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title
    identification = ET.SubElement(score, "identification")
    encoding = ET.SubElement(identification, "encoding")
    ET.SubElement(encoding, "software").text = "gradus practice_chunk_review snippet"

    part_list = ET.SubElement(score, "part-list")
    if single_staff:
        score_part = ET.SubElement(part_list, "score-part", id="P1")
        ET.SubElement(score_part, "part-name").text = "Snippet"
    else:
        # grand staff as two parts (RH/LH) - simple two staves across two parts
        for pid, pname in [("P1", "RH"), ("P2", "LH")]:
            sp = ET.SubElement(part_list, "score-part", id=pid)
            ET.SubElement(sp, "part-name").text = pname

    # Helper to create note element
    divisions = _DIVISIONS

    def _add_attributes(measure_el, clef_sign: str):
        attrs = ET.SubElement(measure_el, "attributes")
        ET.SubElement(attrs, "divisions").text = str(divisions)
        key_el = ET.SubElement(attrs, "key")
        ET.SubElement(key_el, "fifths").text = str(fifths)
        if mode:
            ET.SubElement(key_el, "mode").text = mode
        time_el = ET.SubElement(attrs, "time")
        ET.SubElement(time_el, "beats").text = str(time_beats)
        ET.SubElement(time_el, "beat-type").text = str(time_beat_type)
        clef_el = ET.SubElement(attrs, "clef")
        ET.SubElement(clef_el, "sign").text = clef_sign
        ET.SubElement(clef_el, "line").text = "2" if clef_sign == "G" else "4"

    # Group by onset for chord handling
    onset_groups: dict[Fraction, list] = defaultdict(list)
    for e in events_sorted:
        onset_groups[e.onset].append(e)
    sorted_onsets = sorted(onset_groups.keys())

    # Decide clef per staff
    def _clef_for_events(ev_list):
        if not ev_list:
            return "G"
        # median midi
        mids = [e.pitch_midi for e in ev_list if e.pitch_midi is not None]
        if not mids:
            return "G"
        median = sorted(mids)[len(mids)//2]
        return "G" if median >= 60 else "F"

    if single_staff:
        # Single part P1
        part = ET.SubElement(score, "part", id="P1")
        measure = ET.SubElement(part, "measure", number="1")
        # attributes
        first_clef = clef_hint or _clef_for_events(events_sorted)
        if first_clef not in ("G", "F"):
            first_clef = "G" if first_clef.upper().startswith("G") else "F"
        _add_attributes(measure, first_clef)
        # optional direction with title/measure info
        direction = ET.SubElement(measure, "direction", placement="above")
        dir_type = ET.SubElement(direction, "direction-type")
        ET.SubElement(dir_type, "words").text = title

        # If no events, add rest covering one measure
        if not sorted_onsets:
            n = ET.SubElement(measure, "note")
            ET.SubElement(n, "rest")
            ET.SubElement(n, "duration").text = str(divisions * time_beats // time_beat_type * 4 // 4 if time_beat_type else divisions * 4)
            # use whole rest type
            ET.SubElement(n, "type").text = "whole"
        else:
            prev_onset = None
            for idx, onset in enumerate(sorted_onsets):
                group = sorted(onset_groups[onset], key=lambda e: e.pitch_midi or 0)
                # gap handling: insert rest if gap > group's max duration? Simplify gap as onset diff minus max group duration not needed if we treat notes as chord simultaneous.
                if prev_onset is not None:
                    gap = onset - prev_onset
                    # We need to determine if previous group max duration is smaller than gap; then rest needed.
                    # But we treat chord groups as single max duration; however we don't have per-group duration var easily from previous iteration.
                    # Simpler: if gap is larger than ~1/64, insert rest representing gap minus previous max duration? For monophonic runs gap == duration so no rest needed.
                    # We'll approximate: if gap > Fraction(1,64), we already advanced via previous notes' duration, but we inserted notes sequentially so next note starts immediately after previous.
                    # To reflect gap, we insert rest of duration = gap - avg_prev_duration? This is heuristic.
                    # Instead we just insert forward/rest if gap != previous group's max duration.
                    prev_group = onset_groups[prev_onset]
                    prev_max_dur = max((e.duration for e in prev_group if e.duration is not None), default=Fraction(1, 4))
                    # gap includes time from prev_onset to onset, while prev note occupied prev_max_dur
                    rest_needed = gap - prev_max_dur
                    if rest_needed > Fraction(0):
                        # insert rest
                        dur_ticks = _duration_to_divisions(rest_needed, divisions)
                        if dur_ticks > 0:
                            n = ET.SubElement(measure, "note")
                            ET.SubElement(n, "rest")
                            ET.SubElement(n, "duration").text = str(dur_ticks)
                            typ, dots = _fraction_to_type_and_dots(rest_needed)
                            ET.SubElement(n, "type").text = typ
                            for _ in range(dots):
                                ET.SubElement(n, "dot")
                # write chord notes for this onset
                for n_idx, ev in enumerate(group):
                    is_rest = bool(ev.is_rest)
                    attrs = {}
                    if color_by_id and ev.event_id in color_by_id:
                        attrs["color"] = color_by_id[ev.event_id]
                    n = ET.SubElement(measure, "note", **attrs) if attrs else ET.SubElement(measure, "note")
                    if n_idx > 0 and not is_rest:
                        ET.SubElement(n, "chord")
                    if is_rest:
                        ET.SubElement(n, "rest")
                    else:
                        pitch_el = ET.SubElement(n, "pitch")
                        step, alter, octv = _midi_to_step_alter_octave(ev.pitch_midi or 60, ev.pitch_name, ev.alter, ev.accidental)
                        ET.SubElement(pitch_el, "step").text = step
                        if alter != 0:
                            ET.SubElement(pitch_el, "alter").text = str(alter)
                        ET.SubElement(pitch_el, "octave").text = str(octv)
                    dur_frac = ev.duration if ev.duration is not None else Fraction(1, 4)
                    if dur_frac <= 0:
                        dur_frac = Fraction(1, 4)
                    dur_ticks = _duration_to_divisions(dur_frac, divisions)
                    if dur_ticks <= 0:
                        dur_ticks = divisions // 4
                    ET.SubElement(n, "duration").text = str(dur_ticks)
                    # voice
                    ET.SubElement(n, "voice").text = "1"
                    typ, dots = _fraction_to_type_and_dots(dur_frac)
                    ET.SubElement(n, "type").text = typ
                    for _ in range(dots):
                        ET.SubElement(n, "dot")
                    if not is_rest and ev.pitch_midi is not None:
                        # add lyric to show midi/pitch for QA if color not enough
                        pass
                    # store staff if grand? not needed for single
                prev_onset = onset
    else:
        # Grand staff as two parts
        # Split events by staff/hand
        right_events = [e for e in events_sorted if (e.staff == 1 or e.hand == "right")]
        left_events = [e for e in events_sorted if (e.staff == 2 or e.hand == "left")]
        # If staff/hand ambiguous, distribute by pitch median
        ambiguous = [e for e in events_sorted if e not in right_events and e not in left_events]
        if ambiguous:
            # assign by pitch: higher -> right, lower -> left
            for e in ambiguous:
                if e.pitch_midi is not None and e.pitch_midi >= 60:
                    right_events.append(e)
                else:
                    left_events.append(e)
        # Ensure both have at least some? If one empty, still create part with rest
        for pid, evs, default_clef in [("P1", right_events, "G"), ("P2", left_events, "F")]:
            part = ET.SubElement(score, "part", id=pid)
            measure = ET.SubElement(part, "measure", number="1")
            clef_sign = default_clef
            if evs:
                # try to detect from events
                cands = [e.clef for e in evs if e.clef]
                if cands:
                    clef_sign = cands[0] if cands[0] in ("G","F") else default_clef
                else:
                    clef_sign = _clef_for_events(evs)
            _add_attributes(measure, clef_sign)
            if pid == "P1":
                direction = ET.SubElement(measure, "direction", placement="above")
                dir_type = ET.SubElement(direction, "direction-type")
                ET.SubElement(dir_type, "words").text = title
            if not evs:
                n = ET.SubElement(measure, "note")
                ET.SubElement(n, "rest")
                ET.SubElement(n, "duration").text = str(divisions * 4)
                ET.SubElement(n, "type").text = "whole"
            else:
                groups: dict[Fraction, list] = defaultdict(list)
                for e in evs:
                    groups[e.onset].append(e)
                sorted_o = sorted(groups.keys())
                prev = None
                for onset in sorted_o:
                    grp = sorted(groups[onset], key=lambda e: e.pitch_midi or 0)
                    if prev is not None:
                        gap = onset - prev
                        prev_grp = groups[prev]
                        prev_max = max((e.duration for e in prev_grp if e.duration is not None), default=Fraction(1,4))
                        rest_needed = gap - prev_max
                        if rest_needed > Fraction(0):
                            dur_ticks = _duration_to_divisions(rest_needed, divisions)
                            if dur_ticks > 0:
                                n = ET.SubElement(measure, "note")
                                ET.SubElement(n, "rest")
                                ET.SubElement(n, "duration").text = str(dur_ticks)
                                typ, dots = _fraction_to_type_and_dots(rest_needed)
                                ET.SubElement(n, "type").text = typ
                                for _ in range(dots):
                                    ET.SubElement(n, "dot")
                    for n_idx, ev in enumerate(grp):
                        is_rest = bool(ev.is_rest)
                        attrs = {}
                        if color_by_id and ev.event_id in color_by_id:
                            attrs["color"] = color_by_id[ev.event_id]
                        n = ET.SubElement(measure, "note", **attrs) if attrs else ET.SubElement(measure, "note")
                        if n_idx > 0 and not is_rest:
                            ET.SubElement(n, "chord")
                        if is_rest:
                            ET.SubElement(n, "rest")
                        else:
                            pitch_el = ET.SubElement(n, "pitch")
                            step, alter, octv = _midi_to_step_alter_octave(ev.pitch_midi or 60, ev.pitch_name, ev.alter, ev.accidental)
                            ET.SubElement(pitch_el, "step").text = step
                            if alter != 0:
                                ET.SubElement(pitch_el, "alter").text = str(alter)
                            ET.SubElement(pitch_el, "octave").text = str(octv)
                        dur_frac = ev.duration if ev.duration is not None else Fraction(1,4)
                        if dur_frac <= 0:
                            dur_frac = Fraction(1,4)
                        dur_ticks = _duration_to_divisions(dur_frac, divisions)
                        if dur_ticks <=0:
                            dur_ticks = divisions //4
                        ET.SubElement(n, "duration").text = str(dur_ticks)
                        ET.SubElement(n, "voice").text = "1"
                        typ, dots = _fraction_to_type_and_dots(dur_frac)
                        ET.SubElement(n, "type").text = typ
                        for _ in range(dots):
                            ET.SubElement(n, "dot")
                    prev = onset

    # serialize
    xml_decl = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype = '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
    raw = ET.tostring(score, encoding="unicode")
    return xml_decl + doctype + raw


def _find_mscore() -> str | None:
    for cand in [
        shutil.which("mscore"),
        shutil.which("musescore"),
        shutil.which("mscore4"),
        "/usr/local/bin/mscore",
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "/Applications/MuseScore.app/Contents/MacOS/mscore",
    ]:
        if cand and Path(cand).exists():
            return cand
    return None


def render_musicxml_to_png_or_svg(musicxml_path: Path, image_path: Path) -> tuple[bool, str | None]:
    """Try to render MusicXML to PNG via MuseScore. Returns (success, diagnostic)."""
    mscore = _find_mscore()
    if not mscore:
        return False, "MuseScore not found — render unavailable"
    # try mscore -> png directly, else via pdf
    image_path = Path(image_path)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_pdf = image_path.with_suffix(".pdf")
    try:
        # try direct png
        # mscore can write png via -o; try png first then pdf fallback
        cmd_png = [mscore, str(musicxml_path), "-o", str(image_path)]
        res = subprocess.run(cmd_png, capture_output=True, text=True, timeout=30)
        # mscore sometimes writes <name>-1.png for single-page scores instead of <name>.png
        candidate = None
        if image_path.is_file() and image_path.stat().st_size >= 200:
            candidate = image_path
        else:
            # check for -1 variant
            alt = image_path.with_name(image_path.stem + "-1.png")
            if alt.is_file() and alt.stat().st_size >= 200:
                try:
                    # normalize to expected name
                    alt.rename(image_path)
                    candidate = image_path
                except Exception:
                    candidate = alt
                    # update image_path reference for caller? Keep alt as candidate
                    # copy alt to expected path
                    try:
                        shutil.copy(str(alt), str(image_path))
                        candidate = image_path
                    except Exception:
                        pass
            else:
                # glob for any <stem>-*.png
                import glob as _glob2
                pattern = str(image_path.parent / (image_path.stem + "-*.png"))
                matches = sorted(_glob2.glob(pattern))
                if matches and Path(matches[0]).is_file() and Path(matches[0]).stat().st_size >= 200:
                    try:
                        shutil.copy(matches[0], image_path)
                        candidate = image_path
                    except Exception:
                        candidate = Path(matches[0])
        if candidate is not None and candidate.is_file() and candidate.stat().st_size >= 200:
            # ensure standardized path exists
            return True, None
        # fallback pdf then convert
        cmd_pdf = [mscore, str(musicxml_path), "-o", str(tmp_pdf)]
        res2 = subprocess.run(cmd_pdf, capture_output=True, text=True, timeout=30)
        if res2.returncode != 0 or not tmp_pdf.is_file() or tmp_pdf.stat().st_size < 500:
            msg = (res2.stderr or res.stdout or "")[:300]
            return False, f"MuseScore pdf export failed rc={res2.returncode}: {msg}" if msg else "MuseScore export failed"
        # pdf -> png via pdftoppm / gs / convert
        pdftoppm = shutil.which("pdftoppm")
        gs = shutil.which("gs")
        convert = shutil.which("convert")
        import glob as _glob
        import tempfile as _tmp
        import os
        tmpdir = _tmp.mkdtemp()
        base = os.path.join(tmpdir, "page")
        if pdftoppm:
            res3 = subprocess.run([pdftoppm, "-png", "-r", "150", str(tmp_pdf), base], capture_output=True, text=True, timeout=30)
            if res3.returncode != 0:
                return False, f"pdftoppm failed: {res3.stderr[:200]}"
            pngs = sorted(_glob.glob(base + "-*.png"))
            if not pngs and Path(base + ".png").exists():
                pngs = [base + ".png"]
            if not pngs:
                return False, "pdftoppm produced no PNGs"
            shutil.copy(pngs[0], image_path)
            if image_path.stat().st_size >= 200:
                return True, None
            return False, "rendered PNG too small"
        elif gs:
            out_tmp = os.path.join(tmpdir, "gs.png")
            res3 = subprocess.run(["gs","-dSAFER","-dBATCH","-dNOPAUSE","-r150","-sDEVICE=png16m",f"-sOutputFile={out_tmp}", str(tmp_pdf)], capture_output=True, text=True, timeout=30)
            if res3.returncode !=0 or not Path(out_tmp).exists():
                return False, f"Ghostscript failed: {res3.stderr[:200]}"
            shutil.copy(out_tmp, image_path)
            return True, None
        elif convert:
            out_tmp = os.path.join(tmpdir, "conv.png")
            res3 = subprocess.run(["convert","-density","150", f"{tmp_pdf}[0]", out_tmp], capture_output=True, text=True, timeout=30)
            if res3.returncode!=0 or not Path(out_tmp).exists():
                return False, f"convert failed: {res3.stderr[:200]}"
            shutil.copy(out_tmp, image_path)
            return True, None
        else:
            return False, "No PDF→PNG converter (pdftoppm/gs/convert) available"
    except subprocess.TimeoutExpired:
        return False, "MuseScore render timed out"
    except Exception as exc:
        return False, str(exc)[:300]
    finally:
        try:
            if tmp_pdf.exists():
                tmp_pdf.unlink()
        except Exception:
            pass


def _decide_single_staff(events: list) -> bool:
    if not events:
        return True
    staves = {e.staff for e in events if e.staff is not None}
    hands = {e.hand for e in events if e.hand in ("right","left")}
    if len(staves) > 1 or len(hands) > 1:
        return False
    return True


def write_chunk_snippets(chunk, events_by_id: dict, out_dir: Path, *, in_span_events: list | None = None) -> dict:
    """Generate MusicXML snippets for a chunk. Returns artifact dict."""
    snippets_dir = Path(out_dir) / "snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)
    cid_safe = _sanitize_chunk_id(chunk.chunk_id)
    # primary events
    primary_events = [events_by_id[eid] for eid in chunk.primary_event_ids if eid in events_by_id]
    # context events
    context_events = [events_by_id[eid] for eid in chunk.context_event_ids if eid in events_by_id]
    # combined for context-inclusive
    primary_context_events = primary_events + context_events
    # sort combined by onset
    primary_context_events = sorted(primary_context_events, key=lambda e: (e.onset, e.pitch_midi or 0))
    primary_events = sorted(primary_events, key=lambda e: (e.onset, e.pitch_midi or 0))

    artifacts: dict[str, str | None] = {}

    # decide staff handling based on primary vs combined vs full passage
    def _write_one(ev_list, suffix: str, title: str, color_map: dict | None = None):
        if not ev_list:
            return None, None, None
        single = _decide_single_staff(ev_list)
        xml = events_to_musicxml_snippet(ev_list, title=title, single_staff=single, color_by_id=color_map)
        fname = f"chunk_{cid_safe}__{suffix}.musicxml"
        fpath = snippets_dir / fname
        fpath.write_text(xml, encoding="utf-8")
        rel = f"snippets/{fname}"
        # try render
        png_fname = f"chunk_{cid_safe}__{suffix}.png"
        png_path = snippets_dir / png_fname
        ok, diag = render_musicxml_to_png_or_svg(fpath, png_path)
        rel_png = f"snippets/{png_fname}" if ok else None
        if not ok and png_path.exists():
            try:
                png_path.unlink()
            except Exception:
                pass
            rel_png = None
        return rel, rel_png, diag

    # primary
    primary_title = f"{chunk.label} — primary ({chunk.chunk_id})"
    # add measure span and kind for readability
    primary_musicxml, primary_png, primary_diag = _write_one(primary_events, "primary", primary_title)
    artifacts["primary_musicxml"] = primary_musicxml
    artifacts["primary_render"] = primary_png
    if primary_diag and not primary_png:
        artifacts["primary_render_diagnostic"] = primary_diag

    # primary_context if exists
    if context_events:
        # color primary blue, context grey
        color_map = {}
        for eid in chunk.primary_event_ids:
            color_map[eid] = "#1a73e8"
        for eid in chunk.context_event_ids:
            color_map[eid] = "#7a7a7a"
        ctx_title = f"{chunk.label} — primary+context ({chunk.chunk_id})"
        pc_musicxml, pc_png, pc_diag = _write_one(primary_context_events, "primary_context", ctx_title, color_map=color_map)
        artifacts["primary_context_musicxml"] = pc_musicxml
        artifacts["primary_context_render"] = pc_png
        if pc_diag and not pc_png:
            artifacts["primary_context_render_diagnostic"] = pc_diag
    else:
        artifacts["primary_context_musicxml"] = None
        artifacts["primary_context_render"] = None

    # full passage snippet (optional per chunk) — use measure span events if provided
    # We'll let caller handle global full passage; here also generate per-chunk full if in_span_events provided and differs
    if in_span_events is not None:
        # full passage for this chunk's measure span? Use all events whose measure_number in chunk.measure_numbers OR onset window
        # For simplicity check global in_span_events that intersect chunk span
        full_candidates = []
        # if chunk has measure_numbers, filter in_span_events by those numbers
        mnums = set(str(x) for x in chunk.measure_numbers) if chunk.measure_numbers else set()
        if mnums:
            for e in in_span_events:
                if str(e.measure_number or "") in mnums:
                    full_candidates.append(e)
                elif e.measure_number is None and str(e.measure_index or "") in mnums:
                    full_candidates.append(e)
        if not full_candidates:
            # fallback to in_span_events
            full_candidates = list(in_span_events)
        if full_candidates and len(full_candidates) > len(primary_events):
            full_candidates = sorted(full_candidates, key=lambda e: (e.onset, e.pitch_midi or 0))
            full_title = f"{chunk.label} — full passage m.{','.join(chunk.measure_numbers) or '?'}"
            full_musicxml, full_png, full_diag = _write_one(full_candidates, "full", full_title)
            artifacts["full_passage_musicxml"] = full_musicxml
            artifacts["full_passage_render"] = full_png
            if full_diag and not full_png:
                artifacts["full_passage_render_diagnostic"] = full_diag
        else:
            artifacts["full_passage_musicxml"] = None
            artifacts["full_passage_render"] = None
    else:
        artifacts["full_passage_musicxml"] = None
        artifacts["full_passage_render"] = None

    # clean None entries? Keep for explicit
    return artifacts


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Helpers for semantic summary presentation (no semantic logic change)
# ---------------------------------------------------------------------------

def _is_background_fallback(chunk) -> bool:
    """True if this is a generic fallback/background chunk (passage/hand_stream with fallback)."""
    if chunk.kind not in ("hand_stream", "passage"):
        return False
    traits = set(chunk.traits or ())
    caveats = set(chunk.caveats or ())
    if "fallback" in traits or "fallback_chunk" in caveats or "inferred" in traits:
        return True
    # hand_stream / passage that spans whole score is background
    # heuristic: if measure_numbers covers >6 measures and label is generic
    if len(chunk.measure_numbers) > 6:
        return True
    return False

def _chunk_why_line(chunk) -> str:
    """One-line pianist-readable 'why it exists' from kind/traits/payload/caveats."""
    kind = chunk.kind
    traits = list(chunk.traits or ())
    payload = chunk.payload or {}
    caveats = list(chunk.caveats or ())
    parts = []
    # primary why from payload boundary / grouped kinds / dynamics / rolled
    boundary = payload.get("boundary_reason") or payload.get("grouped_kinds") or ""
    if isinstance(boundary, (list, tuple)):
        boundary = ", ".join(str(x) for x in boundary[:3])
    if boundary and boundary != "hand_stream_fallback" and boundary != "hand_streams_parent":
        parts.append(f"Boundary: {boundary}")
    elif kind == "chordal_texture" and boundary == "repeated_chordal_simultaneities":
        parts.append("Repeated chordal simultaneities")
    # traits-derived why
    # filter out background traits
    musical_traits = [t for t in traits if t not in ("fallback","inferred","both_hands","hand_stream","passage","both","left","right","dense","chordal","hand_overlap","slur","phrase_mark","has_dynamics","chord_sequence")]
    # keep order: rolled, decrescendo, scalar etc first
    priority = ["rolled_chord","rolled_chords","decrescendo","crescendo","dynamic_shape","scalar","arpeggiated","repeated_cells","phrase"]
    ordered = sorted(musical_traits, key=lambda t: (0 if t in priority else 1, priority.index(t) if t in priority else 99))
    if ordered:
        # humanize
        human = []
        for t in ordered[:4]:
            if t == "rolled_chord" or t == "rolled_chords":
                human.append("rolled chords")
            elif t == "decrescendo":
                human.append("decrescendo")
            elif t == "crescendo":
                human.append("crescendo")
            elif t == "dynamic_shape":
                human.append("dynamic shape")
            elif t == "scalar":
                human.append("scalar motion")
            elif t == "up":
                human.append("ascending")
            elif t == "fast_run":
                human.append("fast run")
            else:
                human.append(t.replace("_"," "))
        parts.append(", ".join(human))
    # payload specifics
    specifics = []
    if payload.get("dynamics"):
        dyn = payload["dynamics"]
        if isinstance(dyn, list):
            dyn = ", ".join(str(x) for x in dyn[:4])
        specifics.append(f"dynamics: {dyn}")
    if payload.get("dynamic_shape") and payload.get("dynamic_shape") not in str(parts):
        # already covered via traits but keep if not
        pass
    if payload.get("chord_count"):
        specifics.append(f"{payload['chord_count']} chords")
    if payload.get("interval_pattern"):
        specifics.append(f"intervals {payload['interval_pattern']}")
    if payload.get("direction"):
        specifics.append(payload["direction"])
    if specifics:
        parts.append("; ".join(specifics[:2]))
    # fallback note
    if not parts:
        # generic fallback description
        if kind == "hand_stream":
            parts.append("Sustained hand texture (fallback grouping)")
        elif kind == "passage":
            parts.append("General passage grouping")
        elif kind == "phrase":
            gk = payload.get("grouped_kinds")
            if gk:
                parts.append(f"Phrase grouping {', '.join(gk[:3])}")
            else:
                parts.append("Phrase grouping")
        elif kind == "run":
            parts.append("Scalar run")
        elif kind == "chord_shape":
            parts.append("Single chord onset")
        else:
            parts.append(kind.replace("_"," "))
    why = " · ".join(parts)
    # caveat hint subdued
    if "fallback_chunk" in caveats and kind in ("hand_stream","passage"):
        why += " — fallback/inferred"
    return why

def _select_high_signal_chunks(chunks, a: int, b: int):
    """Filter to high-signal chunks for default view.
    - Hide fallback background hand_stream/passage when stronger chunks exist
    - Hide hand_stream children when stronger exist
    - De-emphasize passage unless top parent and no alternative
    Returns (featured, hidden) tuple.
    """
    if not chunks:
        return [], []
    background = {c.chunk_id for c in chunks if _is_background_fallback(c)}
    has_musical = any(c.chunk_id not in background for c in chunks)
    if has_musical:
        featured = [c for c in chunks if c.chunk_id not in background]
    else:
        # only fallbacks exist — show them (most specific fallback)
        # prefer smallest span fallback
        # sort by span length then confidence
        def span_len(c):
            try:
                ints = [int(x) for x in c.measure_numbers if str(x).strip().isdigit()]
                return len(ints) if ints else 999
            except: return 999
        featured = sorted(chunks, key=lambda c: (span_len(c), -float(c.confidence)))
        # limit to top 2 if huge
        # keep at least 1, at most 3 for fallback-only
        featured = featured[:3]
        hidden = [c for c in chunks if c not in featured]
        return featured, hidden
    # has_musical: also de-duplicate overly broad chordal_texture? keep only in-span focused
    # If still many chord_shape children, keep them but limit default to top-level + direct children in span that are not background
    # For now return as sorted by onset
    featured = sorted(featured, key=lambda c: (c.start_onset, c.kind))
    # cap featured to avoid wall of chips: if >8, keep parents first
    if len(featured) > 8:
        # prioritize non-chord_shape first, then chord_shape
        non_chord = [c for c in featured if c.kind != "chord_shape"]
        chord_shapes = [c for c in featured if c.kind == "chord_shape"]
        # keep all non_chord, add up to remaining chord_shapes within limit
        keep = non_chord[:]
        remaining = 8 - len(keep)
        if remaining > 0:
            keep.extend(chord_shapes[:remaining])
            hidden_extra = chord_shapes[remaining:]
        else:
            hidden_extra = chord_shapes
            # need to trim keep if too many non_chord still
            if len(keep) > 8:
                hidden_extra = keep[8:] + hidden_extra
                keep = keep[:8]
        hidden = [c for c in chunks if c not in keep] + hidden_extra if 'hidden_extra' in locals() else [c for c in chunks if c not in featured]
        # ensure hidden includes original background plus excess
        background_list = [c for c in chunks if c.chunk_id in background]
        # merge
        hidden_ids = set(h.chunk_id for h in hidden) | background
        featured_ids = set(f.chunk_id for f in keep)
        hidden = [c for c in chunks if c.chunk_id in hidden_ids and c.chunk_id not in featured_ids]
        featured = keep
    else:
        hidden = [c for c in chunks if c not in featured]
    return featured, hidden

# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Practice Chunk Review — m. {span_label}</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color:#111; line-height:1.5; max-width: 1100px; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-size: 18px; margin-top: 28px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
  h3 {{ font-size: 15px; margin-top: 18px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius: 12px; font-size:12px; background:#eee; margin-right:6px; }}
  .badge-primary {{ background:#1a73e8; color:white; }}
  .badge-context {{ background:#9cc9ff; color:#111; }}
  .badge-grey {{ background:#e9e9e9; color:#444; }}
  .badge-kind {{ background:#eef2ff; color:#1e3a8a; border:1px solid #c7d2fe; text-transform: uppercase; font-size:10px; letter-spacing:0.04em; }}
  .muted {{ color:#666; font-size:13px; }}
  .subdued {{ color:#888; font-size:12px; }}
  .card {{ border:1px solid #ddd; border-radius:10px; padding:14px; background:white; }}
  .card.selected {{ border-color:#1a73e8; box-shadow:0 0 0 2px rgba(26,115,232,0.15); }}
  .diag {{ background:#fff3cd; border:1px solid #ffe69c; padding:10px; border-radius:8px; margin:12px 0; }}
  .diag-error {{ background:#ffe0e0; border-color:#ffb3b3; }}
  table {{ border-collapse: collapse; width:100%; font-size:13px; }}
  th, td {{ border:1px solid #ddd; padding:6px 8px; text-align:left; vertical-align:top; }}
  th {{ background:#f6f6f6; }}
  /* score-first */
  .score-stage {{ border:1px solid #d0d7de; border-radius:12px; background:#fcfcfc; padding:16px; margin:16px 0; }}
  .score-stage h2 {{ margin-top:0; }}
  .score-stage .excerpt-wrap {{ background:white; border:1px solid #ddd; border-radius:8px; padding:8px; text-align:center; }}
  .score-stage .excerpt-wrap img {{ max-width:100%; width:100%; max-width:1100px; height:auto; border:1px solid #e5e5e5; border-radius:6px; display:block; margin:0 auto; }}
  /* chunk map */
  .chunk-map {{ border:1px solid #d0d7de; border-radius:12px; background:#f8fafc; padding:16px; margin:16px 0; }}
  .chunk-map h2 {{ margin-top:0; }}
  .map-tree {{ margin:8px 0; }}
  .map-tree ul {{ margin:4px 0 4px 18px; padding:0; list-style:none; }}
  .map-tree li {{ margin:6px 0; padding:6px 10px; border-radius:8px; border:1px solid #e2e8f0; background:white; cursor:pointer; }}
  .map-tree li:hover {{ background:#eef2ff; border-color:#93c5fd; }}
  .map-tree li.selected {{ background:#1a73e8; color:white; border-color:#1a73e8; }}
  .map-tree li.selected .muted {{ color:#dbeafe; }}
  .map-tree .map-label {{ font-weight:600; }}
  .map-tree .map-meta {{ font-size:12px; }}
  /* featured cards */
  .featured {{ margin:16px 0; }}
  .featured-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:14px; margin-top:12px; }}
  .pc-card {{ border:1px solid #d0d7de; border-radius:12px; padding:14px; background:white; display:flex; flex-direction:column; gap:8px; }}
  .pc-card:hover {{ border-color:#93c5fd; box-shadow:0 1px 4px rgba(0,0,0,0.06); }}
  .pc-card.selected {{ border-color:#1a73e8; box-shadow:0 0 0 2px rgba(26,115,232,0.12); }}
  .pc-title {{ font-weight:700; font-size:15px; display:flex; flex-wrap:wrap; align-items:center; gap:6px; }}
  .pc-meta-line {{ font-size:12px; color:#444; }}
  .pc-why {{ font-size:13px; color:#1f2937; background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; }}
  .pc-practice {{ font-size:12px; }}
  .afford-chip {{ display:inline-block; padding:2px 7px; border-radius:999px; background:#f0fdf4; color:#14532d; border:1px solid #bbf7d0; margin:2px; font-size:11px; }}
  .pc-children {{ font-size:12px; color:#334155; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:6px 10px; }}
  .pc-subdued {{ font-size:11px; color:#888; }}
  /* pills / event grid kept for debug */
  .pill-row {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .pill {{ display:inline-flex; flex-direction:column; align-items:center; border:1px solid #bbb; border-radius:8px; padding:4px 6px; min-width:62px; background:#f2f2f2; font-size:11px; line-height:1.2; }}
  .pill strong {{ font-size:12px; }}
  .pill.is-primary {{ background:#1a73e8; color:white; border-color:#165fcc; }}
  .pill.is-context {{ background:#cfe2ff; color:#111; border-color:#8ab4f8; opacity:0.92; }}
  .pill.is-other {{ background:#ededed; color:#444; }}
  .pill.is-rest {{ background:#fff; border-style:dashed; color:#777; }}
  .hand-row {{ margin-bottom:14px; }}
  .hand-label {{ font-weight:600; font-size:13px; margin-bottom:6px; }}
  .legend span {{ margin-right:8px; }}
  .snippet {{ border:1px solid #d0d7de; border-radius:8px; padding:10px; background:#fcfcfc; margin:10px 0; }}
  .snippet img {{ max-width:100%; height:auto; border:1px solid #ddd; border-radius:4px; background:white; }}
  .snippet-links a {{ margin-right:10px; font-size:13px; }}
  .render-unavailable {{ background:#fff8c5; border:1px solid #eac54d; padding:6px 10px; border-radius:6px; font-size:12px; margin:6px 0; }}
  details.debug {{ border:1px solid #e5e7eb; border-radius:10px; padding:12px 16px; background:#fcfcfc; margin:12px 0; }}
  details.debug > summary {{ cursor:pointer; font-weight:600; font-size:14px; }}
  details.debug[open] {{ background:white; }}
  .chunk-table-wrap {{ overflow:auto; }}
  .no-chunks {{ background:#f0f0f0; border:1px solid #ddd; padding:12px; border-radius:8px; margin:10px 0; }}
  a {{ color:#1a73e8; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .controls {{ margin:10px 0; }}
  .detail-panel {{ border:1px solid #ddd; border-radius:10px; padding:16px; background:white; margin-top:16px; }}
  .detail-panel.selected {{ border-color:#1a73e8; box-shadow:0 0 0 2px rgba(26,115,232,0.12); }}
  .trait-badge {{ display:inline-block; padding:2px 7px; border-radius:999px; background:#eef2ff; color:#1e3a8a; font-size:11px; margin:2px; border:1px solid #c7d2fe; }}
  .afford-badge {{ background:#f0fdf4; color:#14532d; border-color:#bbf7d0; }}
  .caveat-badge {{ background:#fef3c7; color:#78350f; border-color:#fde68a; }}
  .hierarchy ul {{ margin:4px 0 4px 18px; }}
  .evidence-columns {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:10px; font-size:13px; }}
  @media (max-width: 700px) {{ .evidence-columns {{ grid-template-columns:1fr; }} }}
  .snippet-row {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:10px; }}
  @media (max-width: 700px) {{ .snippet-row {{ grid-template-columns:1fr; }} }}
  .snippet-card {{ border:1px solid #e5e7eb; border-radius:8px; padding:8px; background:#fafafa; }}
  .snippet-card img {{ width:100%; height:auto; border:1px solid #ddd; border-radius:4px; background:white; }}
  .json-details pre {{ background:#f7f7f7; padding:10px; border:1px solid #ddd; border-radius:8px; overflow:auto; font-size:11px; max-height:320px; }}
  .summary-strip {{ display:flex; flex-wrap:wrap; gap:16px; font-size:13px; color:#444; margin:8px 0; }}
  .summary-strip strong {{ color:#111; }}
</style>
</head>
<body>
<header>
<h1>Practice Chunk Review — Measures {span_label}</h1>
<div class="muted">Source: {source_label_esc} &middot; Report span {span_label} &middot; Generated via generate_practice_chunk_review.py</div>
<div class="summary-strip">
  <span><strong>Measures:</strong> {span_label} (flagged {flagged_esc})</span>
  <span><strong>Events in span:</strong> {in_span_ev_count}</span>
  <span><strong>Chunks in span:</strong> {in_span_chunk_count} &middot; featured {featured_count}</span>
  <span><strong>Bundle:</strong> {ev_count} events &middot; {chunk_count_all} chunks total</span>
</div>
{no_chunks_banner}
</header>

<section id="score" class="score-stage">
<h2>Score Excerpt</h2>
<div class="muted" style="font-size:13px; margin-bottom:10px;">Primary visual surface for measures {span_label}. Notation below is the excerpt to be understood and practiced.</div>
{score_excerpt_html}
</section>

<section id="chunk-map" class="chunk-map">
<h2>Chunk Map — Parent / Child Grouping</h2>
<div class="muted" style="font-size:13px;">Compact grouping of PracticeChunks detected for this excerpt. Click to highlight. Top-level parents group children for practice.</div>
{chunk_map_html}
<div id="selectedDetail" class="detail-panel">{selected_detail_html}</div>
</section>

<section id="featured" class="featured">
<h2>PracticeChunks — What the system detected</h2>
<div class="muted" style="font-size:13px;">High-signal chunks for this excerpt. Each card shows why it exists and how to practice it. Confidence and caveats are subdued.</div>
<div class="featured-grid" id="featuredGrid">
{featured_cards_html}
</div>
{show_all_toggle_html}
</section>

<details class="debug" id="debug-allchunks">
<summary>Debug: All Chunks Table ({in_span_chunk_count} in span) — includes fallback/background</summary>
<div class="muted" style="font-size:12px; margin:8px 0;">Full table with traits, affordances, hierarchy, evidence counts. Default view filters fallback/hand_stream background.</div>
<div class="chunk-table-wrap">
<table id="chunkTable">
<thead><tr><th>Chunk</th><th>Label / Kind / Hand</th><th>Measures / Onset</th><th>Traits / Affordances / Confidence</th><th>Hierarchy</th><th>Evidence</th></tr></thead>
<tbody>{chunk_rows}</tbody>
</table>
</div>
</details>

<details class="debug" id="debug-events">
<summary>Debug: Raw Event Table &amp; Per-Chunk Evidence</summary>
<div class="muted" style="font-size:12px; margin:8px 0;">All ScoreEvents in measures {span_label}. Selection highlights primary (blue) vs context (soft) via JS. This is forensic evidence, collapsed by default.</div>
<div class="legend" style="margin:8px 0;">
  <span class="badge badge-primary">primary</span>
  <span class="badge badge-context">context</span>
  <span class="badge badge-grey">other</span>
</div>
<div class="controls">
  <label for="chunkSelect">Highlight chunk:</label>
  <select id="chunkSelect" onchange="selectChunk(this.value)">
    <option value="">— none (all grey) —</option>
{select_options}
  </select>
</div>
<div class="event-grid" id="eventGrid">
{event_rows}
</div>
<div style="margin-top:18px;">
<h3>Per-chunk static evidence lists (no JS)</h3>
{per_chunk_event_lists}
</div>
</details>

<details class="debug" id="debug-snippets">
<summary>Debug: Per-Chunk Reconstructed Notation Snippets</summary>
<div class="muted" style="font-size:12px; margin:8px 0;">Isolated MusicXML snippets per chunk (primary / primary+context). Rendering is imperfect and kept as debug evidence.</div>
{snippet_gallery_html}
</details>

<details class="debug" id="debug-objects">
<summary>Debug: Musical Objects &amp; Derived Tokens</summary>
{musical_objects_html}
</details>

<details class="debug" id="debug-diagnostics">
<summary>Debug: Diagnostics &amp; Notation Markings Support</summary>
{diagnostics_banner}
</details>

<details class="debug" id="debug-json">
<summary>Debug: chunks.json Preview &amp; Links</summary>
<p class="muted"><code>chunks.json</code> contains full machine-readable payload. <a href="chunks.json">Open chunks.json</a> &middot; <a href="review.md">Open review.md</a></p>
<pre style="background:#f7f7f7; padding:10px; border:1px solid #ddd; border-radius:8px; overflow:auto; font-size:12px;">{chunks_json_preview}</pre>
</details>

<script>
const chunkMap = {chunk_map_json};
const chunkDetails = {chunk_details_json};

function escHtml(s) {{
  if (s === null || s === undefined) return "—";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}}

function renderDetail(chunkId) {{
  const panel = document.getElementById('selectedDetail');
  if (!panel) return;
  if (!chunkId || !chunkDetails[chunkId]) {{
    panel.innerHTML = '<div class="muted">No chunk selected — click a card or map entry to inspect. Highlights affect the debug event grid (collapsed below).</div>';
    panel.classList.remove('selected');
    return;
  }}
  const d = chunkDetails[chunkId];
  const traits = (d.traits||[]).map(t=>'<span class="trait-badge">'+escHtml(t)+'</span>').join('') || '<span class="muted">—</span>';
  const afford = (d.affordances||[]).map(a=>'<span class="trait-badge afford-badge">'+escHtml(a)+'</span>').join('') || '<span class="muted">—</span>';
  const caveats = (d.caveats||[]).map(c=>'<span class="trait-badge caveat-badge">'+escHtml(c)+'</span>').join('') || '<span class="muted">—</span>';
  const parentHtml = d.parent ? '<a onclick="selectChunk(\''+escHtml(d.parent).replace(/\'/g,"\\'")+'\')">'+escHtml(d.parent)+'</a> <span class="muted">('+escHtml(d.parent_label||"")+' )</span>' : '<span class="muted">— none (top-level)</span>';
  let childrenHtml = '<span class="muted">— none</span>';
  if (d.children && d.children.length) {{
    childrenHtml = d.children.map(cid=> {{
      const lbl = (chunkDetails[cid] && chunkDetails[cid].label) ? chunkDetails[cid].label : "";
      return '<a onclick="selectChunk(\''+escHtml(cid).replace(/\'/g,"\\'")+'\')" style="margin-right:8px;">'+escHtml(cid)+ (lbl? ' <span class="muted">('+escHtml(lbl)+')</span>':'')+'</a>';
    }}).join('<br>');
  }}
  const why = escHtml(d.why || "");
  const snippetPrimary = d.snippet_primary ? '<div class="snippet-card"><div style="font-weight:600; font-size:12px;">Primary snippet</div><a href="'+escHtml(d.snippet_primary)+'" target="_blank">MusicXML</a>'+(d.snippet_primary_png? '<div style="margin-top:6px;"><img src="'+escHtml(d.snippet_primary_png)+'" alt="Primary '+escHtml(chunkId)+'" loading="lazy"></div>' : '<div class="render-unavailable">Render unavailable</div>')+'</div>' : '<div class="snippet-card muted">No primary snippet.</div>';
  const snippetContext = d.snippet_primary_context ? '<div class="snippet-card"><div style="font-weight:600; font-size:12px;">Primary + context</div><a href="'+escHtml(d.snippet_primary_context)+'" target="_blank">MusicXML</a>'+(d.snippet_primary_context_png? '<div style="margin-top:6px;"><img src="'+escHtml(d.snippet_primary_context_png)+'" alt="Primary+context '+escHtml(chunkId)+'" loading="lazy"></div>' : '<div class="render-unavailable">Render unavailable</div>')+'</div>' : '<div class="snippet-card muted">No context snippet</div>';
  const jsonStr = JSON.stringify(d.raw, null, 2);
  panel.innerHTML = ''
    + '<div style="font-weight:700; font-size:15px;">'+escHtml(d.label)+' <span class="badge badge-kind">'+escHtml(d.kind)+'</span> <span class="badge">'+escHtml(d.hand||"both")+'</span></div>'
    + '<div class="muted" style="font-size:12px; margin-top:2px;">'+escHtml(chunkId)+' &middot; m. '+escHtml((d.measures||[]).join(",")||"?")+' &middot; onset '+escHtml(d.onset_start||"?")+' → '+escHtml(d.onset_end||"?")+' &middot; Why: '+why+'</div>'
    + '<div style="margin-top:10px;"><strong>Traits:</strong> '+traits+'</div>'
    + '<div style="margin-top:6px;"><strong>Practice:</strong> '+afford+'</div>'
    + '<div style="margin-top:6px;" class="subdued"><strong>Confidence:</strong> '+escHtml(d.confidence!==undefined? Number(d.confidence).toFixed(2):"—")+' &middot; <strong>Caveats:</strong> '+caveats+'</div>'
    + '<div style="margin-top:10px;" class="hierarchy-nav"><strong>Hierarchy:</strong><br><span><strong>Parent:</strong> '+parentHtml+'</span><br><span><strong>Children ('+(d.children? d.children.length:0)+'):</strong><br>'+childrenHtml+'</span></div>'
    + '<div style="margin-top:10px;" class="muted" style="font-size:12px;">Use the debug event grid below to see primary/context highlights.</div>'
    + '<div class="snippet-row" style="margin-top:12px; display:none;">'+snippetPrimary+snippetContext+'</div>'
    + '<details class="json-details" style="margin-top:12px;"><summary style="cursor:pointer; font-weight:600;">JSON details — '+escHtml(chunkId)+'</summary><pre>'+escHtml(jsonStr)+'</pre></details>';
  panel.classList.add('selected');
}}

function selectChunk(chunkId) {{
  const pills = document.querySelectorAll('.pill[data-event-id]');
  const sel = chunkId ? (chunkMap[chunkId] || null) : null;
  const primarySet = sel ? new Set(sel.primary) : new Set();
  const contextSet = sel ? new Set(sel.context) : new Set();
  pills.forEach(p => {{
    const eid = p.getAttribute('data-event-id');
    p.classList.remove('is-primary','is-context','is-other');
    if (!sel) {{
      p.classList.add('is-other');
    }} else if (primarySet.has(eid)) {{
      p.classList.add('is-primary');
    }} else if (contextSet.has(eid)) {{
      p.classList.add('is-context');
    }} else {{
      p.classList.add('is-other');
    }}
  }});
  document.querySelectorAll('.pc-card').forEach(c => {{
    if (c.dataset.chunkId === chunkId) c.classList.add('selected');
    else c.classList.remove('selected');
  }});
  document.querySelectorAll('#chunkTable tbody tr').forEach(tr => {{
    if (tr.dataset.chunkId === chunkId) tr.style.background = '#e8f0fe';
    else tr.style.background = '';
  }});
  document.querySelectorAll('.map-tree li').forEach(li => {{
    if (li.dataset.chunkId === chunkId) li.classList.add('selected');
    else li.classList.remove('selected');
  }});
  const selEl = document.getElementById('chunkSelect');
  if (selEl && selEl.value !== chunkId) selEl.value = chunkId || '';
  renderDetail(chunkId);
}}
function cardClick(id) {{ selectChunk(id); document.getElementById('selectedDetail').scrollIntoView({{behavior:'smooth', block:'nearest'}}); }}
function mapClick(id) {{ selectChunk(id); document.getElementById('featured').scrollIntoView({{behavior:'smooth', block:'nearest'}}); }}
function toggleHidden() {{
  const el = document.getElementById('hiddenCards');
  const btn = document.getElementById('toggleBtn');
  if (!el) return;
  const isHidden = el.style.display === 'none';
  el.style.display = isHidden ? 'grid' : 'none';
  if (btn) btn.textContent = isHidden ? 'Hide fallback/background chunks' : 'Show all {total_hidden} hidden chunks';
}}
(function() {{
  const first = {first_chunk_json};
  if (first && chunkMap[first]) {{
    selectChunk(first);
  }} else {{
    renderDetail(null);
  }}
}}());</script>
</body>
</html>
"""





def _build_html(
    source: Path,
    source_label: str,
    a: int,
    b: int,
    flagged: tuple[str, ...],
    bundle,
    in_span_events: list,
    in_span_chunks: list,
    diagnostics: tuple[str, ...],
    max_chunks: int | None,
    include_context: bool,
    chunks_json_preview: str,
    chunk_map_json: str,
    first_chunk_id: str | None,
    chunk_snippet_artifacts: dict[str, dict] | None = None,
    full_passage_snippet: dict | None = None,
) -> str:
    span_label = f"{a}-{b}" if a != b else str(a)
    flagged_str = ", ".join(flagged) if flagged else "—"
    ev_sorted = sorted(in_span_events, key=lambda e: (e.onset, e.pitch_midi or 0))
    if ev_sorted:
        onset_bounds = f"{ev_sorted[0].onset} → {ev_sorted[-1].end}"
    else:
        onset_bounds = "—"

    total_chunks = len(bundle.practice_chunks) if hasattr(bundle, "practice_chunks") else 0

    if diagnostics:
        has_error = any("error" in d.lower() or "practice_chunks_error" in d for d in diagnostics)
        cls = "diag diag-error" if has_error else "diag"
        diag_items = "".join(f"<li>{_escape(d)}</li>" for d in diagnostics)
        diagnostics_banner = f'<div class="{cls}"><strong>Diagnostics:</strong><ul style="margin:6px 0 0 18px;">{diag_items}</ul></div>'
        diagnostics_summary = f"{len(diagnostics)} diagnostic(s) — see debug"
    else:
        diagnostics_banner = '<div class="muted">Diagnostics: — none — (chunks built without diagnostics)</div>'
        diagnostics_summary = "— none —"

    if not in_span_chunks:
        no_chunks_banner = '<div class="no-chunks"><strong>No PracticeChunks detected in this span.</strong> Showing event grid (debug) and musical objects so you can judge whether a chunk should be added later.</div>'
    else:
        no_chunks_banner = ""
    try:
        from piano_difficulty.semantic_tokens.notation_markings import marking_support_status
        _mstatus = marking_support_status()
        _mrows = "".join(f"<li><strong>{html.escape(k)}:</strong> {html.escape(v)}</li>" for k,v in _mstatus.items())
        markings_banner = f'<div class="diag" style="background:#f0f7ff; border-color:#c2d6ff;"><strong>Notation markings support (thin layer):</strong><ul style="margin:6px 0 0 18px;">{_mrows}</ul><div class="muted" style="margin-top:6px;">Markings become traits/boundary priors/context/affordances/payload on chunks.</div></div>'
    except Exception:
        markings_banner = '<div class="diag"><strong>Notation markings support:</strong> thin layer unavailable.</div>'
    combined_banner = markings_banner + diagnostics_banner if diagnostics else markings_banner
    # use combined for debug diagnostics section
    diagnostics_banner = combined_banner + diagnostics_banner if diagnostics else combined_banner

    # --- score excerpt ---
    if full_passage_snippet and full_passage_snippet.get("musicxml"):
        fp_xml = html.escape(full_passage_snippet["musicxml"])
        fp_png = full_passage_snippet.get("render")
        fp_diag = full_passage_snippet.get("render_diagnostic")
        if fp_png:
            score_excerpt_html = '<div class="excerpt-wrap"><img src="' + html.escape(fp_png) + '" alt="Full excerpt m.' + html.escape(span_label) + '" loading="lazy"><div class="muted" style="margin-top:6px; font-size:12px;">Full passage excerpt — measures ' + html.escape(span_label) + ' — <a href="' + fp_xml + '">MusicXML</a> &middot; rendered PNG</div></div>'
        elif fp_diag:
            score_excerpt_html = '<div class="excerpt-wrap"><div class="render-unavailable">Excerpt render unavailable: ' + html.escape(str(fp_diag)) + ' — <a href="' + fp_xml + '">MusicXML</a> still available.</div></div>'
        else:
            score_excerpt_html = '<div class="excerpt-wrap"><div class="muted">Excerpt available as MusicXML: <a href="' + fp_xml + '">Download</a> (PNG render unavailable)</div></div>'
    else:
        score_excerpt_html = '<div class="excerpt-wrap"><div class="muted">No full-passage excerpt available — per-chunk debug snippets below show primary/context notation.</div></div>'

    # --- Featured / hidden filtering ---
    # respect max_chunks override? If max_chunks provided, apply after semantic filtering
    featured_raw, hidden_raw = _select_high_signal_chunks(in_span_chunks, a, b)
    # If max_chunks limits total in-span, also truncate featured respecting limit
    # For debug table we always show all, but featured honors max_chunks if set
    if max_chunks is not None and len(featured_raw) > max_chunks:
        featured = featured_raw[:max_chunks]
        # move excess featured to hidden
        hidden = hidden_raw + featured_raw[max_chunks:]
    else:
        featured = featured_raw
        hidden = hidden_raw

    # Build helper maps
    by_id = {c.chunk_id: c for c in in_span_chunks}
    child_map: dict[str, list] = {c.chunk_id: [] for c in in_span_chunks}
    for c in in_span_chunks:
        if c.parent_chunk_id and c.parent_chunk_id in child_map:
            child_map[c.parent_chunk_id].append(c.chunk_id)
    top_level = [c for c in in_span_chunks if not c.parent_chunk_id or c.parent_chunk_id not in by_id]
    if not top_level and in_span_chunks:
        top_level = in_span_chunks

    # --- chunk map html (compact tree) ---
    def _map_label(ch):
        why = _chunk_why_line(ch)
        # truncate why for map
        short_why = why[:80] + ("…" if len(why)>80 else "")
        hand = ch.hand or "both"
        meas = ",".join(ch.measure_numbers) if ch.measure_numbers else "?"
        if len(meas) > 30:
            meas = meas[:27] + "…"
        return short_why, hand, meas
    def _render_map_node(node_id: str, depth: int = 0) -> str:
        ch = by_id.get(node_id)
        if not ch:
            return ""
        why, hand, meas = _map_label(ch)
        children = child_map.get(node_id, [])
        inner = ""
        if children:
            inner = "<ul>" + "".join(_render_map_node(cid, depth+1) for cid in sorted(children, key=lambda cid: by_id[cid].start_onset if cid in by_id else cid)) + "</ul>"
        kind = html.escape(ch.kind)
        label = html.escape(ch.label)
        hand_esc = html.escape(hand)
        meas_esc = html.escape(meas)
        why_esc = html.escape(why)
        is_featured = any(f.chunk_id==node_id for f in featured)
        badge = '<span class="badge badge-kind">'+kind+'</span>' + ('' if is_featured else ' <span class="muted" style="font-size:10px;">(background)</span>')
        return f'<li data-chunk-id="{html.escape(node_id)}" onclick="mapClick(\'{html.escape(node_id)}\')"><div class="map-label">{label} {badge}</div><div class="map-meta muted">{hand_esc} · m.{meas_esc} · Why: {why_esc} · children: {len(children)}</div>{inner}</li>'
    if in_span_chunks:
        # Use set of top-level that are in-span; but also include featured top-level first
        # Sort top_level by featured priority
        def top_sort_key(c):
            is_feat = 0 if any(f.chunk_id==c.chunk_id for f in featured) else 1
            return (is_feat, c.start_onset)
        sorted_tops = sorted(top_level, key=top_sort_key)
        map_items = "".join(_render_map_node(c.chunk_id) for c in sorted_tops)
        chunk_map_html = f'<div class="map-tree"><ul>{map_items}</ul><div class="muted" style="margin-top:8px;">Top-level: {len(top_level)} · Total in span: {len(in_span_chunks)} · Featured: {len(featured)} · Hidden background: {len(hidden)}</div></div>'
    else:
        chunk_map_html = '<div class="muted">No chunks in span — nothing to map.</div>'

    # --- featured cards ---
    def _render_featured_card(ch):
        cid = ch.chunk_id
        why = _chunk_why_line(ch)
        hand = ch.hand or "both"
        meas = ",".join(ch.measure_numbers) if ch.measure_numbers else "?"
        # truncate long measure list for display
        meas_display = meas
        if len(meas) > 40:
            # show range if numeric
            try:
                ints = [int(x) for x in ch.measure_numbers if x.strip().isdigit()]
                if ints:
                    meas_display = f"{min(ints)}–{max(ints)} ({len(ints)} measures)"
                else:
                    meas_display = meas[:37]+"…"
            except:
                meas_display = meas[:37]+"…"
        # affordances
        afford = list(ch.practice_affordances or ())
        afford_html = "".join(f'<span class="afford-chip">{html.escape(a)}</span>' for a in afford) if afford else '<span class="muted">—</span>'
        # children
        children = child_map.get(cid, [])
        # filter children that are in-span
        children_in_span = [by_id[cid2] for cid2 in children if cid2 in by_id]
        if children_in_span:
            child_labels = ", ".join(f"{html.escape(c.label)} ({html.escape(c.kind)})" for c in children_in_span[:4])
            if len(children_in_span) > 4:
                child_labels += f" +{len(children_in_span)-4} more"
            children_html = f'<div class="pc-children"><strong>Children ({len(children_in_span)}):</strong> {child_labels}</div>'
        else:
            # also show count from raw child_chunk_ids if any (outside span but still)
            if ch.child_chunk_ids:
                children_html = f'<div class="pc-children"><strong>Children:</strong> {len(ch.child_chunk_ids)} total (outside span or background)</div>'
            else:
                children_html = '<div class="pc-children muted">No children — leaf for focused practice</div>'
        # confidence subdued
        conf = f"{ch.confidence:.2f}"
        caveat_str = ", ".join(ch.caveats) if ch.caveats else "—"
        parent_note = ""
        if ch.parent_chunk_id and ch.parent_chunk_id in by_id:
            parent_note = f'<div class="subdued">Parent: {html.escape(by_id[ch.parent_chunk_id].label)} ({html.escape(ch.parent_chunk_id[:24])}…)</div>'
        return (
            f'<div class="pc-card" data-chunk-id="{html.escape(cid)}" onclick="cardClick(\'{html.escape(cid)}\')">'
            f'<div class="pc-title">{html.escape(ch.label)} <span class="badge badge-kind">{html.escape(ch.kind)}</span> <span class="badge">{html.escape(hand)}</span></div>'
            f'<div class="pc-meta-line">m. {html.escape(meas_display)} · {html.escape(hand)} · onset {html.escape(str(ch.start_onset))} → {html.escape(str(ch.end_onset))}</div>'
            f'<div class="pc-why"><strong>Why:</strong> {html.escape(why)}</div>'
            f'<div class="pc-practice"><strong>Practice:</strong> {afford_html}</div>'
            f'{children_html}'
            f'<div class="pc-subdued">Confidence {conf} · Caveats: {html.escape(caveat_str)}</div>'
            f'{parent_note}'
            f'</div>'
        )
    if featured:
        featured_cards_html = "".join(_render_featured_card(c) for c in featured)
    else:
        if not in_span_chunks:
            featured_cards_html = '<div class="muted">No chunks detected — see debug sections for raw evidence.</div>'
        else:
            # fallback-only case already filtered, but if hidden then show message
            featured_cards_html = '<div class="muted">All chunks are background/fallback — see "Show all" below for fallback chunks.</div>'

    # show all toggle
    if hidden:
        # render hidden cards (muted) inside collapsible
        hidden_cards_html = "".join(_render_featured_card(c) for c in sorted(hidden, key=lambda x: x.start_onset))
        show_all_toggle_html = (
            f'<div style="margin-top:12px;"><button id="toggleBtn" onclick="toggleHidden()" style="padding:8px 12px; border-radius:8px; border:1px solid #cbd5e1; background:#f8fafc; cursor:pointer;">Show all {len(hidden)} hidden chunks</button>'
            f'<div id="hiddenCards" class="featured-grid" style="display:none; margin-top:12px;">{hidden_cards_html}</div></div>'
        )
        total_hidden = len(hidden)
    else:
        show_all_toggle_html = '<div class="muted" style="margin-top:8px;">All chunks shown — no hidden background.</div>'
        total_hidden = 0

    # --- chunk rows for debug table (all chunks) ---
    displayed_chunks = in_span_chunks
    max_note = ""
    if max_chunks is not None and len(in_span_chunks) > max_chunks:
        # still show all in debug, but note limit
        max_note = f"Note: --max-chunks {max_chunks} applied to featured view; debug table shows all {len(in_span_chunks)}."
    chunk_rows_parts: list[str] = []
    for ch in displayed_chunks:
        cid = ch.chunk_id
        meas = ",".join(ch.measure_numbers) if ch.measure_numbers else f"{ch.measure_start or '?'}–{ch.measure_end or '?'}"
        if len(meas) > 50:
            meas = meas[:47]+"…"
        onset = f"{ch.start_onset} → {ch.end_onset}"
        traits = ", ".join(ch.traits) if ch.traits else "—"
        afford = ", ".join(ch.practice_affordances) if ch.practice_affordances else "—"
        caveats = ", ".join(ch.caveats) if ch.caveats else "—"
        parent = ch.parent_chunk_id or "—"
        children = ", ".join(ch.child_chunk_ids) if ch.child_chunk_ids else "—"
        primary_cnt = len(ch.primary_event_ids)
        context_cnt = len(ch.context_event_ids)
        conf = f"{ch.confidence:.2f}"
        chunk_rows_parts.append(
            f'<tr data-chunk-id="{_escape(cid)}" onclick="cardClick(\'{_escape(cid)}\')" style="cursor:pointer;">'
            f'<td><strong>{_escape(cid)}</strong></td>'
            f'<td>{_escape(ch.label)}<br><span class="muted">{_escape(ch.kind)} &middot; { _escape(ch.hand or "both")}</span></td>'
            f'<td>m. { _escape(meas)}<br><span class="muted">{ _escape(onset)}</span></td>'
            f'<td><span class="muted" title="{html.escape(_chunk_why_line(ch))}">Why: {html.escape(_chunk_why_line(ch))}</span><br>traits: { _escape(traits)}<br>practice: { _escape(afford)}<br>conf: { _escape(conf)} caveats: { _escape(caveats)}</td>'
            f'<td>parent: { _escape(parent)}<br>children: { _escape(children)}</td>'
            f'<td>primary: {primary_cnt}<br>context: {context_cnt}</td></tr>'
        )
    if not displayed_chunks:
        chunk_rows_parts.append('<tr><td colspan="6" class="muted">No chunks in this span — see debug event grid.</td></tr>')
    chunk_rows = "".join(chunk_rows_parts)

    # --- event rows (debug) ---
    groups: dict[str, list] = {"right": [], "left": [], "both": [], "rest": []}
    for e in sorted(in_span_events, key=lambda ev: (ev.onset, ev.pitch_midi or -1)):
        if e.is_rest:
            groups["rest"].append(e)
        elif e.hand == "right":
            groups["right"].append(e)
        elif e.hand == "left":
            groups["left"].append(e)
        else:
            groups["both"].append(e)
    label_map = {"right": "RH (right hand)", "left": "LH (left hand)", "both": "Both / unknown hand", "rest": "Rests"}
    event_rows_parts: list[str] = []
    for key in ["right", "left", "both", "rest"]:
        evs = groups[key]
        if not evs:
            continue
        pills: list[str] = []
        for e in evs:
            pitch_label = e.pitch_name or (str(e.pitch_midi) if e.pitch_midi is not None else "rest")
            beat_str = str(e.beat) if e.beat is not None else "?"
            meas = str(e.measure_number or e.measure_index or "?")
            onset_str = str(e.onset)
            title = f"{pitch_label} m.{meas} beat {beat_str} onset {onset_str} midi {e.pitch_midi or ''} staff {e.staff or ''} {'rest' if e.is_rest else ''} id {e.event_id}"
            cls = "is-rest" if e.is_rest else "is-other"
            pills.append(
                f'<div class="pill {cls}" data-event-id="{_escape(e.event_id)}" title="{_escape(title)}">'
                f'<strong>{_escape(pitch_label)}</strong>'
                f'<span>m.{_escape(meas)} b:{_escape(beat_str)}</span>'
                f'<span style="font-size:10px; color:#555;">{ _escape(e.hand or "")} &middot; { _escape(e.event_id[:8])}</span>'
                f'</div>'
            )
        event_rows_parts.append(
            f'<div class="hand-row"><div class="hand-label">{label_map[key]} — {len(evs)} events</div><div class="pill-row">{"".join(pills)}</div></div>'
        )
    if not in_span_events:
        event_rows_parts.append('<div class="muted">No events in selected span.</div>')
    event_rows = "".join(event_rows_parts)

    # per-chunk evidence lists (debug)
    per_chunk_lists: list[str] = []
    for ch in displayed_chunks:
        prim_ids = ch.primary_event_ids
        ctx_ids = ch.context_event_ids
        ev_by_id = {e.event_id: e for e in in_span_events}
        def _ev_desc(eid: str) -> str:
            ev = ev_by_id.get(eid)
            if ev is None:
                for ev2 in bundle.events:
                    if ev2.event_id == eid:
                        ev = ev2
                        break
            if ev is None:
                return f'{html.escape(eid)} (outside span)'
            pitch = ev.pitch_name or (str(ev.pitch_midi) if ev.pitch_midi is not None else "rest")
            meas = str(ev.measure_number or ev.measure_index or "?")
            beat = str(ev.beat) if ev.beat is not None else "?"
            return f'{html.escape(pitch)} m.{html.escape(meas)} b:{html.escape(beat)} onset {html.escape(str(ev.onset))} [{html.escape(eid[:12])}]'
        prim_list = "<br>".join(f"• {_ev_desc(eid)}" for eid in prim_ids) if prim_ids else "<span class='muted'>— none —</span>"
        ctx_list = "<br>".join(f"• {_ev_desc(eid)}" for eid in ctx_ids) if ctx_ids else "<span class='muted'>— none —</span>"
        per_chunk_lists.append(
            f'<div class="card" style="margin-bottom:12px;">'
            f'<div style="font-weight:600;">{html.escape(ch.chunk_id)} — {html.escape(ch.label)} ({html.escape(ch.kind)}, {html.escape(ch.hand or "both")})</div>'
            f'<div class="muted" style="font-size:12px;">m. {html.escape(",".join(ch.measure_numbers) or "?")} &middot; onset {html.escape(str(ch.start_onset))}→{html.escape(str(ch.end_onset))}</div>'
            f'<div style="margin-top:8px; display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">'
            f'<div><strong>Primary ({len(prim_ids)}):</strong><br>{prim_list}</div>'
            f'<div><strong>Context ({len(ctx_ids)}):</strong><br>{ctx_list}</div>'
            f'</div>'
            f'</div>'
        )
    if not per_chunk_lists:
        per_chunk_lists.append('<div class="muted">No chunks — no per-chunk lists.</div>')
    per_chunk_event_lists = "".join(per_chunk_lists)

    # musical objects in span (debug)
    a_val, b_val = a, b
    objs = list(getattr(bundle, "musical_objects", ()) or ())
    onset_start = None; onset_end = None
    if in_span_events:
        onset_start = min(e.onset for e in in_span_events)
        onset_end = max(e.end for e in in_span_events)
    in_span_objects = []
    for o in objs:
        if _span_intersects_object(o, a_val, b_val) or _in_onset_window(o, onset_start, onset_end):
            in_span_objects.append(o)
    if in_span_objects:
        obj_rows = []
        for o in sorted(in_span_objects, key=lambda x: (x.start_onset, x.object_id)):
            meas = ",".join(o.measure_numbers) if o.measure_numbers else f"{o.measure_start or '?'}"
            obj_rows.append(
                f'<tr><td>{html.escape(o.object_id)}<br><span class="muted">{html.escape(o.label)}</span></td>'
                f'<td>{html.escape(o.hand or "both")}</td>'
                f'<td>m. {html.escape(meas)} &middot; {html.escape(str(o.start_onset))}→{html.escape(str(o.end_onset))}</td>'
                f'<td>{len(o.evidence_event_ids)} events &middot; conf {o.confidence:.2f} &middot; caveats: {html.escape(",".join(o.caveats) or "—")}</td></tr>'
            )
        musical_objects_html = (
            f'<p class="muted">{len(in_span_objects)} musical object(s) in span.</p>'
            f'<table><thead><tr><th>Object</th><th>Hand</th><th>Span</th><th>Evidence</th></tr></thead><tbody>{"".join(obj_rows)}</tbody></table>'
        )
    else:
        musical_objects_html = '<p class="muted">No musical objects in span. Debug event grid above shows raw notes.</p>'

    # snippet gallery (debug)
    snippet_gallery_parts = []
    for ch in displayed_chunks:
        snip = (chunk_snippet_artifacts or {}).get(ch.chunk_id, {})
        primary_xml = snip.get("primary_musicxml")
        primary_png = snip.get("primary_render")
        pc_xml = snip.get("primary_context_musicxml")
        pc_png = snip.get("primary_context_render")
        full_xml = snip.get("full_passage_musicxml")
        full_png = snip.get("full_passage_render")
        if not any([primary_xml, pc_xml, full_xml]):
            continue
        card = f'<div class="card" style="margin-bottom:12px;"><div style="font-weight:600;">{html.escape(ch.chunk_id)} — {html.escape(ch.label)}</div>'
        if primary_xml:
            card += f'<div style="margin-top:8px;"><strong>Primary:</strong> <a href="{html.escape(primary_xml)}">MusicXML</a>'
            if primary_png:
                card += f'<div style="margin-top:6px;"><img src="{html.escape(primary_png)}" alt="Primary {html.escape(ch.chunk_id)}" style="max-width:100%; border:1px solid #ddd; border-radius:4px;" loading="lazy"></div>'
            card += '</div>'
        if pc_xml:
            card += f'<div style="margin-top:8px;"><strong>Primary+context:</strong> <a href="{html.escape(pc_xml)}">MusicXML</a>'
            if pc_png:
                card += f'<div style="margin-top:6px;"><img src="{html.escape(pc_png)}" alt="Primary+context {html.escape(ch.chunk_id)}" style="max-width:100%; border:1px solid #ddd; border-radius:4px;" loading="lazy"></div>'
            card += '</div>'
        if full_xml:
            card += f'<div style="margin-top:8px;"><strong>Full passage:</strong> <a href="{html.escape(full_xml)}">MusicXML</a>'
            if full_png:
                card += f'<div style="margin-top:6px;"><img src="{html.escape(full_png)}" alt="Full {html.escape(ch.chunk_id)}" style="max-width:100%; border:1px solid #ddd; border-radius:4px;" loading="lazy"></div>'
            card += '</div>'
        card += '</div>'
        snippet_gallery_parts.append(card)
    if snippet_gallery_parts:
        snippet_gallery_html = "".join(snippet_gallery_parts)
    else:
        snippet_gallery_html = '<div class="muted">No snippet artifacts for in-span chunks.</div>'

    # select options for debug dropdown
    select_options_parts = []
    for ch in displayed_chunks:
        cid = ch.chunk_id
        select_options_parts.append(f'    <option value="{_escape(cid)}">{_escape(cid)} — {_escape(ch.label)} ({_escape(ch.kind)}, {_escape(ch.hand or "both")})</option>')
    select_options = "\n".join(select_options_parts)

    # first chunk: prefer first featured if exists
    if featured:
        first_id_effective = featured[0].chunk_id
    else:
        first_id_effective = first_chunk_id

    # selected detail initial html (server-rendered)
    if featured and first_id_effective and any(c.chunk_id == first_id_effective for c in featured):
        _first_ch = next((c for c in featured if c.chunk_id == first_id_effective), featured[0])
    elif displayed_chunks and first_id_effective and any(c.chunk_id == first_id_effective for c in displayed_chunks):
        _first_ch = next((c for c in displayed_chunks if c.chunk_id == first_id_effective), displayed_chunks[0])
    elif featured:
        _first_ch = featured[0]
    elif displayed_chunks:
        _first_ch = displayed_chunks[0]
    else:
        _first_ch = None
    if _first_ch is not None:
        _cid = _first_ch.chunk_id
        why_line = _chunk_why_line(_first_ch)
        _traits_html = "".join(f'<span class="trait-badge">{html.escape(t)}</span>' for t in _first_ch.traits) or '<span class="muted">—</span>'
        _afford_html = "".join(f'<span class="trait-badge afford-badge">{html.escape(a)}</span>' for a in _first_ch.practice_affordances) or '<span class="muted">—</span>'
        _caveat_html = "".join(f'<span class="trait-badge caveat-badge">{html.escape(c)}</span>' for c in _first_ch.caveats) or '<span class="muted">—</span>'
        _parent_html = f'<a onclick="selectChunk(\'{html.escape(_first_ch.parent_chunk_id)}\')">{html.escape(_first_ch.parent_chunk_id)}</a>' if _first_ch.parent_chunk_id else '<span class="muted">— none (top-level)</span>'
        _children_html = ', '.join(f'<a onclick="selectChunk(\'{html.escape(cid)}\')">{html.escape(cid)}</a>' for cid in _first_ch.child_chunk_ids) if _first_ch.child_chunk_ids else '<span class="muted">— none</span>'
        selected_detail_html = (
            f'<div style="font-weight:700; font-size:15px;">{html.escape(_first_ch.label)} <span class="badge badge-kind">{html.escape(_first_ch.kind)}</span> <span class="badge">{html.escape(_first_ch.hand or "both")}</span></div>'
            f'<div class="muted" style="font-size:12px; margin-top:2px;">{html.escape(_cid)} &middot; m. {html.escape(",".join(_first_ch.measure_numbers) or "?")} &middot; onset {html.escape(str(_first_ch.start_onset))} → {html.escape(str(_first_ch.end_onset))}</div>'
            f'<div style="margin-top:8px; font-size:13px; background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px;"><strong>Why:</strong> {html.escape(why_line)}</div>'
            f'<div style="margin-top:8px;"><strong>Practice:</strong> {_afford_html}</div>'
            f'<div class="subdued" style="margin-top:6px;"><strong>Confidence:</strong> {_first_ch.confidence:.2f} &middot; <strong>Caveats:</strong> {_caveat_html}</div>'
            f'<div style="margin-top:8px;"><strong>Parent:</strong> {_parent_html} &middot; <strong>Children:</strong> {_children_html}</div>'
            f'<div style="margin-top:6px;"><strong>Traits:</strong> {_traits_html}</div>'
        )
    else:
        selected_detail_html = '<div class="muted">No chunk selected — click a card or map entry to inspect.</div>'

    # chunk details json for JS
    chunk_details_map = {}
    for ch in in_span_chunks:
        cid = ch.chunk_id
        snip = (chunk_snippet_artifacts or {}).get(cid, {})
        parent_label = ""
        if ch.parent_chunk_id:
            for pch in in_span_chunks:
                if pch.chunk_id == ch.parent_chunk_id:
                    parent_label = pch.label
                    break
        chunk_details_map[cid] = {
            "label": ch.label,
            "kind": ch.kind,
            "hand": ch.hand,
            "measures": list(ch.measure_numbers),
            "onset_start": str(ch.start_onset),
            "onset_end": str(ch.end_onset),
            "why": _chunk_why_line(ch),
            "traits": list(ch.traits),
            "affordances": list(ch.practice_affordances),
            "confidence": float(ch.confidence),
            "caveats": list(ch.caveats),
            "parent": ch.parent_chunk_id,
            "parent_label": parent_label,
            "children": list(ch.child_chunk_ids),
            "primary": list(ch.primary_event_ids),
            "context": list(ch.context_event_ids),
            "snippet_primary": snip.get("primary_musicxml"),
            "snippet_primary_png": snip.get("primary_render"),
            "snippet_primary_context": snip.get("primary_context_musicxml"),
            "snippet_primary_context_png": snip.get("primary_context_render"),
            "raw": ch.to_dict(),
        }
    chunk_details_json = json.dumps(chunk_details_map, ensure_ascii=False)
    first_json = json.dumps(first_id_effective) if first_id_effective else "null"

    html_out = HTML_TEMPLATE.format(
        span_label=html.escape(span_label),
        source_label_esc=html.escape(source_label),
        source_path_esc=html.escape(str(source)),
        flagged_esc=html.escape(flagged_str),
        onset_bounds_esc=html.escape(onset_bounds),
        ev_count=len(bundle.events),
        tok_count=len(bundle.derived_tokens),
        gest_count=len(bundle.gestures),
        obj_count=len(getattr(bundle, "musical_objects", ()) or ()),
        comp_count=len(getattr(bundle, "object_components", ()) or ()),
        chunk_count_all=total_chunks,
        in_span_ev_count=len(in_span_events),
        in_span_chunk_count=len(in_span_chunks),
        featured_count=len(featured),
        total_hidden=total_hidden,
        diagnostics_summary=diagnostics_summary,
        diagnostics_banner=diagnostics_banner,
        no_chunks_banner=no_chunks_banner,
        score_excerpt_html=score_excerpt_html,
        chunk_map_html=chunk_map_html,
        selected_detail_html=selected_detail_html,
        featured_cards_html=featured_cards_html,
        show_all_toggle_html=show_all_toggle_html,
        chunk_rows="".join(chunk_rows_parts),
        select_options=select_options,
        event_rows="".join(event_rows_parts),
        per_chunk_event_lists="".join(per_chunk_lists),
        snippet_gallery_html=snippet_gallery_html,
        musical_objects_html=musical_objects_html,
        chunks_json_preview=html.escape(chunks_json_preview[:3000]),
        chunk_map_json=chunk_map_json,
        chunk_details_json=chunk_details_json,
        first_chunk_json=first_json,
    )
    return html_out



# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(
    source: str | Path,
    measures: str,
    output_dir: str | Path,
    flagged: str | None = None,
    source_label: str | None = None,
    max_chunks: int | None = None,
    include_context: bool = False,
) -> Path:
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"source not found: {src}")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    a, b = _parse_measures(measures)
    if a > b:
        a, b = b, a
    if flagged:
        flagged_measures = tuple(s.strip() for s in flagged.split(",") if s.strip())
    else:
        flagged_measures = tuple(str(x) for x in range(a, b + 1))
    label = source_label or str(src.name)

    doc = load_musicxml_document(src)
    score = build_score_ir(doc)
    bundle = build_semantic_bundle(score)

    # onset bounds for span
    onset_start, onset_end = _onset_bounds_for_span(bundle, a, b)
    # Filter events in span
    in_span_events = [e for e in bundle.events if _event_in_span(e, a, b, onset_start, onset_end)]
    # Sort events
    in_span_events = sorted(in_span_events, key=lambda e: (e.onset, e.pitch_midi or -1, e.staff or 99))

    # Filter chunks in span
    in_span_chunks_all = [c for c in (getattr(bundle, "practice_chunks", ()) or ()) if _span_intersects_object(c, a, b) or _in_onset_window(c, onset_start, onset_end)]
    # Sort chunks
    in_span_chunks_all = sorted(in_span_chunks_all, key=lambda c: (c.start_onset, c.kind, c.hand or ""))

    diagnostics = tuple(getattr(bundle, "diagnostics", ()) or ())

    # Build chunks.json payload
    chunk_by_id = {c.chunk_id: c for c in in_span_chunks_all}
    # chunk tree format matching local_inspection: plus extra fields
    practice_chunk_tree = {
        cid: {
            "label": ch.label,
            "kind": ch.kind,
            "hand": ch.hand,
            "child_chunk_ids": list(ch.child_chunk_ids),
            "parent_chunk_id": ch.parent_chunk_id,
            "primary_event_ids": list(ch.primary_event_ids),
            "context_event_ids": list(ch.context_event_ids),
            "traits": list(ch.traits),
            "practice_affordances": list(ch.practice_affordances),
            "measure_numbers": list(ch.measure_numbers),
            "start_onset": str(ch.start_onset),
            "end_onset": str(ch.end_onset),
            "confidence": float(ch.confidence),
            "caveats": list(ch.caveats),
        }
        for cid, ch in chunk_by_id.items()
    }

    # top-level identification
    top_level_ids = [cid for cid, ch in chunk_by_id.items() if not ch.parent_chunk_id or ch.parent_chunk_id not in chunk_by_id]

    chunks_payload: dict = {
        "selected_span": f"{a}-{b}" if a != b else str(a),
        "report_span": [a, b],
        "flagged_measures": list(flagged_measures),
        "source_score": label,
        "source_path": str(src),
        "span_onset_bounds": [str(onset_start) if onset_start is not None else None, str(onset_end) if onset_end is not None else None],
        "bundle_counts": {
            "event_count": len(bundle.events),
            "derived_token_count": len(bundle.derived_tokens),
            "gesture_count": len(bundle.gestures),
            "musical_object_count": len(getattr(bundle, "musical_objects", ()) or ()),
            "object_component_count": len(getattr(bundle, "object_components", ()) or ()),
            "micro_moment_count": len(getattr(bundle, "micro_moments", ()) or ()),
            "practice_chunk_count": len(getattr(bundle, "practice_chunks", ()) or ()),
            "in_span_event_count": len(in_span_events),
            "in_span_practice_chunk_count": len(in_span_chunks_all),
        },
        "diagnostics": list(diagnostics),
        "events": [e.to_dict() for e in in_span_events],
        "practice_chunks": [c.to_dict() for c in in_span_chunks_all],
        "practice_chunk_tree": practice_chunk_tree,
        "chunk_hierarchy": {
            "top_level_chunk_ids": top_level_ids,
            "child_map": {cid: list(ch.child_chunk_ids) for cid, ch in chunk_by_id.items()},
        },
        "events_in_span_ids": [e.event_id for e in in_span_events],
        "musical_objects_in_span": [
            o.to_dict() for o in (getattr(bundle, "musical_objects", ()) or ()) if _span_intersects_object(o, a, b) or _in_onset_window(o, onset_start, onset_end)
        ],
    }

    # --- Snippet generation (MusicXML + optional PNG) ---
    events_by_id = {e.event_id: e for e in bundle.events}
    # also map in_span for quick lookup but use full bundle for correctness (primary may refer outside span? but usually inside)
    chunk_snippet_artifacts: dict[str, dict] = {}
    for ch in in_span_chunks_all:
        try:
            arts = write_chunk_snippets(ch, events_by_id, out_dir, in_span_events=in_span_events)
        except Exception as exc:
            # graceful degradation: record diagnostic
            arts = {
                "primary_musicxml": None,
                "primary_render": None,
                "primary_render_diagnostic": f"snippet generation failed: {exc}",
                "primary_context_musicxml": None,
                "primary_context_render": None,
                "full_passage_musicxml": None,
                "full_passage_render": None,
            }
        chunk_snippet_artifacts[ch.chunk_id] = arts
        # enrich practice_chunk_tree with snippet_artifacts for machine-readable output
        if ch.chunk_id in practice_chunk_tree:
            practice_chunk_tree[ch.chunk_id]["snippet_artifacts"] = {
                "primary_musicxml": arts.get("primary_musicxml"),
                "primary_render": arts.get("primary_render"),
                "primary_context_musicxml": arts.get("primary_context_musicxml"),
                "primary_context_render": arts.get("primary_context_render"),
                "full_passage_musicxml": arts.get("full_passage_musicxml"),
                "full_passage_render": arts.get("full_passage_render"),
            }
            # also include diagnostics if present
            if arts.get("primary_render_diagnostic"):
                practice_chunk_tree[ch.chunk_id]["snippet_artifacts"]["primary_render_diagnostic"] = arts.get("primary_render_diagnostic")
            if arts.get("primary_context_render_diagnostic"):
                practice_chunk_tree[ch.chunk_id]["snippet_artifacts"]["primary_context_render_diagnostic"] = arts.get("primary_context_render_diagnostic")
            if arts.get("full_passage_render_diagnostic"):
                practice_chunk_tree[ch.chunk_id]["snippet_artifacts"]["full_passage_render_diagnostic"] = arts.get("full_passage_render_diagnostic")

    # global full-passage snippet (all events in span)
    full_passage_snippet: dict | None = None
    if in_span_events:
        try:
            snippets_dir = out_dir / "snippets"
            snippets_dir.mkdir(parents=True, exist_ok=True)
            full_title = f"Full passage — measures {a}-{b}" if a != b else f"Full passage — measure {a}"
            single_full = _decide_single_staff(in_span_events)
            full_xml_str = events_to_musicxml_snippet(in_span_events, title=full_title, single_staff=single_full)
            full_fname = f"full_passage__m_{a}-{b}.musicxml" if a != b else f"full_passage__m_{a}.musicxml"
            # sanitize? keep simple
            full_fname = _sanitize_filename(full_fname)
            full_path = snippets_dir / full_fname
            full_path.write_text(full_xml_str, encoding="utf-8")
            rel_full = f"snippets/{full_fname}"
            png_fname = full_fname.replace(".musicxml", ".png")
            png_path = snippets_dir / png_fname
            ok, diag = render_musicxml_to_png_or_svg(full_path, png_path)
            rel_png = f"snippets/{png_fname}" if ok else None
            if not ok and png_path.exists():
                try:
                    png_path.unlink()
                except Exception:
                    pass
            full_passage_snippet = {
                "musicxml": rel_full,
                "render": rel_png,
                "render_diagnostic": diag if not ok else None,
            }
        except Exception as exc:
            full_passage_snippet = {"musicxml": None, "render": None, "render_diagnostic": str(exc)[:300]}

    # enrich top-level payload with snippet artifacts
    chunks_payload["snippet_artifacts"] = chunk_snippet_artifacts
    if full_passage_snippet:
        chunks_payload["full_passage_snippet"] = full_passage_snippet
    # also patch practice_chunks list dicts to include snippet_artifacts for direct access
    # build map for quick patch
    for idx, pc_dict in enumerate(chunks_payload["practice_chunks"]):
        cid = pc_dict.get("chunk_id")
        if cid and cid in chunk_snippet_artifacts:
            arts = chunk_snippet_artifacts[cid]
            pc_dict["snippet_artifacts"] = {
                "primary_musicxml": arts.get("primary_musicxml"),
                "primary_render": arts.get("primary_render"),
                "primary_context_musicxml": arts.get("primary_context_musicxml"),
                "primary_context_render": arts.get("primary_context_render"),
                "full_passage_musicxml": arts.get("full_passage_musicxml"),
                "full_passage_render": arts.get("full_passage_render"),
            }
            if arts.get("primary_render_diagnostic"):
                pc_dict["snippet_artifacts"]["primary_render_diagnostic"] = arts.get("primary_render_diagnostic")
            if arts.get("primary_context_render_diagnostic"):
                pc_dict["snippet_artifacts"]["primary_context_render_diagnostic"] = arts.get("primary_context_render_diagnostic")
            if arts.get("full_passage_render_diagnostic"):
                pc_dict["snippet_artifacts"]["full_passage_render_diagnostic"] = arts.get("full_passage_render_diagnostic")

    # Write chunks.json
    chunks_path = out_dir / "chunks.json"
    chunks_path.write_text(json.dumps(chunks_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Build HTML
    # chunk map for JS
    chunk_map = {c.chunk_id: {"primary": list(c.primary_event_ids), "context": list(c.context_event_ids)} for c in in_span_chunks_all}
    chunk_map_json = json.dumps(chunk_map, ensure_ascii=False)
    first_id = in_span_chunks_all[0].chunk_id if in_span_chunks_all else None
    preview = json.dumps(chunks_payload, indent=2, ensure_ascii=False)
    html_str = _build_html(
        source=src,
        source_label=label,
        a=a, b=b,
        flagged=flagged_measures,
        bundle=bundle,
        in_span_events=in_span_events,
        in_span_chunks=in_span_chunks_all,
        diagnostics=diagnostics,
        max_chunks=max_chunks,
        include_context=include_context,
        chunks_json_preview=preview,
        chunk_map_json=chunk_map_json,
        first_chunk_id=first_id,
        chunk_snippet_artifacts=chunk_snippet_artifacts,
        full_passage_snippet=full_passage_snippet,
    )
    (out_dir / "index.html").write_text(html_str, encoding="utf-8")

    # Optionally review.md (always write a concise markdown)
    review_lines: list[str] = []
    review_lines.append(f"# Practice Chunk Review — Measures {a}-{b}")
    review_lines.append("")
    review_lines.append(f"Source: {label} (`{src}`)")
    review_lines.append(f"Span: {a}-{b}  Flagged: {', '.join(flagged_measures) if flagged_measures else '—'}")
    review_lines.append(f"Bundle counts: events {len(bundle.events)}, tokens {len(bundle.derived_tokens)}, gestures {len(bundle.gestures)}, objects {len(getattr(bundle,'musical_objects',()) or ())}, chunks {len(getattr(bundle,'practice_chunks',()) or ())}")
    review_lines.append(f"In-span events: {len(in_span_events)}  In-span chunks: {len(in_span_chunks_all)}")
    if diagnostics:
        review_lines.append("")
        review_lines.append("Diagnostics:")
        for d in diagnostics:
            review_lines.append(f"- {d}")
    else:
        review_lines.append("")
        review_lines.append("Diagnostics: — none —")
    if not in_span_chunks_all:
        review_lines.append("")
        review_lines.append("**No PracticeChunks detected in this span.** Event grid still shown in HTML.")
    else:
        review_lines.append("")
        review_lines.append(f"Chunks ({len(in_span_chunks_all)}):")
        # respect max_chunks in markdown too?
        displayed = in_span_chunks_all[:max_chunks] if max_chunks is not None else in_span_chunks_all
        for ch in displayed:
            review_lines.append(f"- **{ch.chunk_id}** ({ch.kind}, {ch.hand or 'both'}): {ch.label} — m.{'/'.join(ch.measure_numbers) or '?'} — traits: {', '.join(ch.traits) or '—'} — affordances: {', '.join(ch.practice_affordances) or '—'} — conf {ch.confidence:.2f} — primary {len(ch.primary_event_ids)}, context {len(ch.context_event_ids)} — parent {ch.parent_chunk_id or '—'} — children {', '.join(ch.child_chunk_ids) or '—'}")
        if max_chunks is not None and len(in_span_chunks_all) > max_chunks:
            review_lines.append(f"  (+{len(in_span_chunks_all)-max_chunks} more chunks omitted by --max-chunks)")
    if in_span_events:
        review_lines.append("")
        review_lines.append(f"Events in span ({len(in_span_events)}):")
        for e in in_span_events[:50]:
            pitch = e.pitch_name or (str(e.pitch_midi) if e.pitch_midi is not None else "rest")
            review_lines.append(f"- {pitch} m.{e.measure_number} beat {e.beat} onset {e.onset} hand {e.hand or '?'} {e.event_id}")
        if len(in_span_events) > 50:
            review_lines.append(f"  (+{len(in_span_events)-50} more)")
    # snippet artifacts section
    if in_span_chunks_all:
        review_lines.append("")
        review_lines.append("Snippets:")
        for ch in (in_span_chunks_all[:max_chunks] if max_chunks is not None else in_span_chunks_all):
            arts = chunk_snippet_artifacts.get(ch.chunk_id, {})
            prim = arts.get("primary_musicxml") or "—"
            pc = arts.get("primary_context_musicxml") or "—"
            review_lines.append(f"- {ch.chunk_id}: primary {prim} ; primary+context {pc}")
            if arts.get("primary_render"):
                review_lines.append(f"  - primary render: {arts.get('primary_render')}")
            elif arts.get("primary_render_diagnostic"):
                review_lines.append(f"  - render unavailable: {arts.get('primary_render_diagnostic')}")
            else:
                review_lines.append("  - render unavailable — MusicXML still available")
    if full_passage_snippet and full_passage_snippet.get("musicxml"):
        review_lines.append("")
        review_lines.append(f"Full passage snippet: {full_passage_snippet.get('musicxml')}")
        if full_passage_snippet.get("render"):
            review_lines.append(f"  - render: {full_passage_snippet.get('render')}")
        elif full_passage_snippet.get("render_diagnostic"):
            review_lines.append(f"  - render unavailable: {full_passage_snippet.get('render_diagnostic')}")
    (out_dir / "review.md").write_text("\n".join(review_lines), encoding="utf-8")

    return out_dir


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Practice Chunk review artifact")
    p.add_argument("source", nargs="?", default=None, help="Path to MusicXML/MXL (positional)")
    p.add_argument("--source", dest="source_opt", default=None, help="Path to MusicXML/MXL (flag alias for brief)")
    p.add_argument("--measures", required=True, help="Measure span A-B (e.g., 27-28 or 5)")
    p.add_argument("--output-dir", required=True, help="Output directory for artifact (index.html, chunks.json, review.md)")
    p.add_argument("--flagged", default=None, help="Flagged measures comma-separated (e.g., 27,28) — defaults to report span")
    p.add_argument("--source-label", default=None, help="Source score label for report")
    p.add_argument("--max-chunks", type=int, default=None, help="Max chunks to display in HTML/table (default all)")
    p.add_argument("--include-context", action="store_true", help="Emphasize context notes in visualization (otherwise still shown but muted)")
    ns = p.parse_args(argv)
    # alias handling: --source flag takes precedence if positional missing
    if ns.source_opt is not None:
        if ns.source is None:
            ns.source = ns.source_opt
        elif ns.source != ns.source_opt:
            # prefer explicit --source when both provided (brief style)
            ns.source = ns.source_opt
    if not ns.source:
        p.error("source is required (positional or --source)")
    return ns


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        out = run(args.source, args.measures, args.output_dir, flagged=args.flagged, source_label=args.source_label, max_chunks=args.max_chunks, include_context=args.include_context)
        print(f"Wrote Practice Chunk review to {out}")
        print(f"  - {out / 'index.html'}")
        print(f"  - {out / 'chunks.json'}")
        print(f"  - {out / 'review.md'}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
