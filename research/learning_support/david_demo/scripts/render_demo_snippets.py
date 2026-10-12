#!/usr/bin/env python3
"""Pre-render sheet-music snippet images for any demo piece hotspots.

Reads ``demo_manifest.json`` hotspot measure ranges, extracts those ranges
from the given MusicXML via ``music21``, renders each snippet ahead of time
using MuseScore (or fallback PDF→PNG chain), and updates the manifest in
place with per-hotspot ``snippet_image`` / ``snippet_status``.

Offline/pre-rendered — the web GUI only displays image files; no live
MusicXML rendering happens in the browser. Hotspot IDs / ranks / measure
metadata are preserved.

Usage (from repo root):
    conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_demo_snippets.py \\
        --score research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml \\
        --manifest research/learning_support/david_demo/artifacts/debussy_arabesque_1/demo_manifest.json \\
        --snippets-dir research/learning_support/david_demo/artifacts/debussy_arabesque_1/snippets

Dependencies: music21 (installed in piano-difficulty env), MuseScore 4 (mscore),
pdftoppm (poppler) or Ghostscript, Pillow for multi-page stitching.
If a snippet fails, the hotspot is kept with snippet_image=null,
snippet_status="render_failed", snippet_diagnostic=concise error — the
manifest remains loadable and the frontend shows the failure without breaking.
"""

from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "research" / "piano_difficulty" / "src"
if str(_SRC_ROOT) not in sys.path:
    try:
        import piano_difficulty  # noqa: F401
    except ModuleNotFoundError:
        sys.path.insert(0, str(_SRC_ROOT))


def find_mscore() -> str | None:
    for cand in [
        shutil.which("mscore"),
        shutil.which("musescore"),
        "/usr/local/bin/mscore",
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "/Applications/MuseScore.app/Contents/MacOS/mscore",
    ]:
        if cand and Path(cand).exists():
            return cand
    return None


def _reference_context(score):
    """Collect reference context (first timeSignature, etc.) for snippet prefixing."""
    ctx: dict[str, object] = {}
    try:
        from music21 import meter, key, clef, stream
        for part in score.parts:
            for m in part.getElementsByClass(stream.Measure):
                ts = list(m.getElementsByClass(meter.TimeSignature))
                if ts and "timeSig" not in ctx:
                    try:
                        ctx["timeSig"] = copy.deepcopy(ts[0])
                    except Exception:
                        pass
                ks = list(m.getElementsByClass(key.KeySignature))
                if ks and "keySig" not in ctx:
                    try:
                        ctx["keySig"] = copy.deepcopy(ks[0])
                    except Exception:
                        pass
                # clefs may be inside voices; use recurse
                clefs = [e for e in m.recurse().getElementsByClass(clef.Clef)]
                if clefs and "clef" not in ctx:
                    try:
                        ctx["clef"] = copy.deepcopy(clefs[0])
                    except Exception:
                        pass
                if "timeSig" in ctx:
                    break
            if "timeSig" in ctx:
                break
    except Exception:
        pass
    return ctx


def _remap_voice_ids(measure) -> None:
    """Make voice ids within a measure contiguous (1..N) to avoid makeRests mismatches.

    Music21's export does makeRests/makeTies which expects consistent voice
    ids across consecutive measures.  Clair de Lune has e.g. voices 1,2 in
    measure 65 and 1,5 in measure 66 -> KeyError '2' on write.  Remapping
    per-measure to 1..N fixes the export without altering pitch content.
    """
    try:
        from music21.stream import Voice
        voices = list(measure.getElementsByClass(Voice))
        if len(voices) <= 1:
            return
        # sort by original id for determinism, then rename to 1..N
        voices_sorted = sorted(voices, key=lambda v: str(getattr(v, "id", "")))
        for idx, v in enumerate(voices_sorted, start=1):
            try:
                v.id = str(idx)
            except Exception:
                pass
    except Exception:
        pass


def extract_snippet_score(score, measure_numbers: list[int]):
    """Return a new Score containing only the given measure numbers.

    Safer than the original: preserves metadata/partName/instrument where
    possible, reports per-part/per-measure diagnostics, and avoids silent
    gaps that crash MuseScore (missing timeSig etc. handled in normalized fallback).
    """
    from music21 import stream  # lazy import requires music21 installed

    new_score = stream.Score()
    if score.metadata is not None:
        try:
            new_score.metadata = copy.deepcopy(score.metadata)
        except Exception:
            pass
    # preserve score-level info like part count for later grand-staff check
    found_any = False
    per_part_diag: list[str] = []
    for part_idx, part in enumerate(score.parts):
        part_id = getattr(part, "id", f"part_{part_idx}")
        new_part = stream.Part()
        try:
            new_part.id = part.id
        except Exception:
            pass
        try:
            if part.partName:
                new_part.partName = part.partName
        except Exception:
            pass
        # preserve instrument if present
        try:
            from music21 import instrument
            for inst in part.getElementsByClass(instrument.Instrument):
                try:
                    new_part.append(copy.deepcopy(inst))
                except Exception:
                    pass
                break
        except Exception:
            pass
        part_found: list[int] = []
        for m in part.getElementsByClass(stream.Measure):
            if m.measureNumber in measure_numbers:
                try:
                    m_copy = copy.deepcopy(m)
                except Exception as e:
                    raise RuntimeError(
                        f"deepcopy failed for measures {measure_numbers} part {part_id!r} measure {m.measureNumber}: {e}"
                    ) from e
                # keep voice structure but normalize ids to avoid KeyError '2'
                _remap_voice_ids(m_copy)
                new_part.append(m_copy)
                part_found.append(int(m.measureNumber))
        # also handle measures that use alternative numbering (e.g. 0 vs 1) — report gaps
        if part_found:
            found_any = True
        else:
            # no measures for this part in the requested range — keep part empty for now;
            # grand-staff reconstruction happens in normalized fallback
            per_part_diag.append(f"part {part_id!r} has no measures in {measure_numbers} (found none)")
        if len(list(new_part.getElementsByClass(stream.Measure))) > 0:
            new_score.append(new_part)
        else:
            # keep empty part slot for piano grand staff?  Don't append empty now;
            # normalized fallback will recreate empty staves with rest placeholders.
            pass
    if not found_any or len(list(new_score.parts)) == 0:
        detail = "; ".join(per_part_diag) if per_part_diag else "no matching measures"
        raise ValueError(f"No measures found for numbers {measure_numbers}: {detail}")
    return new_score


def build_normalized_snippet_score(score, measure_numbers: list[int]):
    """Build a safer snippet Score for MuseScore.

    - Renumbers measures sequentially 1..N (MuseScore stumbles on gaps like 35,36 without context).
    - Inserts a reference timeSignature into the first measure of each part if missing.
    - Remaps voice ids to 1..N per measure (avoids KeyError '2' on makeRests/makeTies).
    - Preserves metadata and part identity; recreates empty piano staves so the
      grand staff is not collapsed to a single staff.
    - Handles per-measure deepcopy failures with detailed context.
    """
    from music21 import stream, meter

    ctx = _reference_context(score)
    ref_ts = ctx.get("timeSig")

    new_score = stream.Score()
    if score.metadata is not None:
        try:
            new_score.metadata = copy.deepcopy(score.metadata)
        except Exception:
            pass

    # Determine expected part count (piano = 2)
    expected_parts = len(list(score.parts))
    parts_with_measures = 0

    for part_idx, part in enumerate(score.parts):
        part_id = getattr(part, "id", f"part_{part_idx}")
        new_part = stream.Part()
        try:
            new_part.id = part.id
        except Exception:
            pass
        try:
            if part.partName:
                new_part.partName = part.partName
        except Exception:
            pass
        # preserve instrument
        try:
            from music21 import instrument
            for inst in part.getElementsByClass(instrument.Instrument):
                try:
                    new_part.append(copy.deepcopy(inst))
                except Exception:
                    pass
                break
        except Exception:
            pass

        seq = 0
        for m in part.getElementsByClass(stream.Measure):
            if m.measureNumber not in measure_numbers:
                continue
            try:
                m_copy = copy.deepcopy(m)
            except Exception as e:
                raise RuntimeError(
                    f"deepcopy failed for measures {measure_numbers} part {part_id!r} measure {m.measureNumber}: {e}"
                ) from e
            seq += 1
            # renumber sequentially for MuseScore
            try:
                m_copy.number = seq
            except Exception:
                pass
            # avoid malformed attributes that can crash musicxml export
            _remap_voice_ids(m_copy)
            # insert timeSig if first measure lacks it
            if seq == 1 and ref_ts is not None:
                try:
                    has_ts = bool(list(m_copy.getElementsByClass(meter.TimeSignature)))
                except Exception:
                    has_ts = False
                if not has_ts:
                    try:
                        m_copy.insert(0, copy.deepcopy(ref_ts))
                    except Exception:
                        pass
            new_part.append(m_copy)

        if seq > 0:
            parts_with_measures += 1
            new_score.append(new_part)
        else:
            # keep empty part for piano grand staff: synthesize a placeholder measure
            # with the same count as sibling parts so MuseScore still renders two staves
            if expected_parts == 2:
                try:
                    placeholder = stream.Measure(number=1)
                    if ref_ts is not None:
                        try:
                            placeholder.insert(0, copy.deepcopy(ref_ts))
                        except Exception:
                            pass
                    # add a whole rest spanning the reference timeSig or 9/8 fallback
                    try:
                        from music21.note import Rest
                        # use duration from ref_ts if available
                        r = Rest()
                        # fill measure with rest if possible; music21 will handle
                        placeholder.append(r)
                    except Exception:
                        pass
                    new_part.append(placeholder)
                    new_score.append(new_part)
                except Exception:
                    # if placeholder fails, still ensure we have at least one part
                    new_score.append(new_part)
            else:
                # for non-piano, just don't add empty part
                pass

    if len(list(new_score.parts)) == 0:
        raise ValueError(f"No measures found for numbers {measure_numbers} (normalized)")
    # ensure we preserved at least the same staff count for piano
    if expected_parts == 2 and len(list(new_score.parts)) == 1:
        # duplicate: already handled per-part, but guard
        pass
    return new_score


def _write_snippet_score(snippet_score, fp: str, measure_numbers: list[int] | None = None) -> None:
    """Write snippet Score to MusicXML, with improved diagnostics."""
    try:
        snippet_score.write("musicxml", fp=fp)
    except Exception as e:
        ctx = f" measures {measure_numbers}" if measure_numbers is not None else ""
        # Surface voice-mismatch and duration issues more clearly
        msg = f"MusicXML write failed{ctx}: {e}"
        # provide hint for the classic KeyError '2'
        if "'2'" in str(e) or "KeyError" in type(e).__name__:
            msg += " (voice id mismatch between measures; try normalized fallback)"
        raise RuntimeError(msg) from e


def _mscore_diagnostic(res) -> str:
    raw = (res.stderr or res.stdout or "").strip().replace("\n", " ")
    # surface a concise snippet; keep QML noise trimmed but preserve real error
    if not raw:
        return f"rc={res.returncode}"
    # truncate but keep first meaningful part (QML warnings are repetitive)
    snippet = raw[:500]
    # if QML noise dominates, try to find a non-QML line
    if "Invalid QML" in snippet and len(snippet) > 300:
        # keep first 300 chars of QML + hint
        snippet = snippet[:300] + " …"
    return f"rc={res.returncode}: {snippet}"[:400]


def render_via_mscore_to_png(tmp_xml: str, out_png: Path, dpi: int = 150) -> None:
    """Render MusicXML to PNG via MuseScore PDF + pdftoppm/GS + Pillow stitching.

    Raises on failure with concise message.
    """
    mscore = find_mscore()
    if not mscore:
        raise RuntimeError("MuseScore executable not found (mscore)")

    tmp_pdf = tempfile.mktemp(suffix=".pdf")
    try:
        cmd = [mscore, tmp_xml, "-o", tmp_pdf]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0 or not Path(tmp_pdf).exists():
            raise RuntimeError(f"MuseScore PDF export failed ({_mscore_diagnostic(res)})")
        if Path(tmp_pdf).stat().st_size < 1000:
            raise RuntimeError("MuseScore produced empty PDF")

        pdftoppm = shutil.which("pdftoppm")
        gs = shutil.which("gs")
        convert = shutil.which("convert")

        tmpdir = tempfile.mkdtemp()
        base = os.path.join(tmpdir, "page")

        rendered_pngs: list[str] = []
        if pdftoppm:
            res2 = subprocess.run([pdftoppm, "-png", "-r", str(dpi), tmp_pdf, base], capture_output=True, text=True, timeout=30)
            if res2.returncode != 0:
                raise RuntimeError(f"pdftoppm failed: {res2.stderr[:300]}")
            rendered_pngs = sorted(glob.glob(base + "-*.png"))
            if not rendered_pngs and Path(base + ".png").exists():
                rendered_pngs = [base + ".png"]
            if not rendered_pngs:
                raise RuntimeError("pdftoppm produced no PNGs")
        elif gs:
            out_tmp = os.path.join(tmpdir, "gs.png")
            res2 = subprocess.run(
                ["gs", "-dSAFER", "-dBATCH", "-dNOPAUSE", f"-r{dpi}", "-sDEVICE=png16m", f"-sOutputFile={out_tmp}", tmp_pdf],
                capture_output=True, text=True, timeout=30,
            )
            if res2.returncode != 0 or not Path(out_tmp).exists():
                raise RuntimeError(f"Ghostscript failed: {res2.stderr[:300]}")
            rendered_pngs = [out_tmp]
        elif convert:
            out_tmp = os.path.join(tmpdir, "convert.png")
            res2 = subprocess.run(["convert", "-density", str(dpi), f"{tmp_pdf}[0]", out_tmp], capture_output=True, text=True, timeout=30)
            if res2.returncode != 0 or not Path(out_tmp).exists():
                raise RuntimeError(f"ImageMagick convert failed: {res2.stderr[:300]}")
            rendered_pngs = [out_tmp]
        else:
            raise RuntimeError("No PDF→PNG converter found (pdftoppm/gs/convert)")

        if len(rendered_pngs) == 1:
            shutil.copy(rendered_pngs[0], out_png)
        else:
            try:
                from PIL import Image
            except Exception:
                shutil.copy(rendered_pngs[0], out_png)
                return
            imgs = [Image.open(p).convert("RGB") for p in rendered_pngs]
            max_w = max(im.size[0] for im in imgs)
            gap = 12
            total_h = sum(im.size[1] for im in imgs) + gap * (len(imgs) - 1)
            combined = Image.new("RGB", (max_w, total_h), (255, 255, 255))
            y = 0
            for im in imgs:
                x = (max_w - im.size[0]) // 2
                combined.paste(im, (x, y))
                y += im.size[1] + gap
                im.close()
            out_png.parent.mkdir(parents=True, exist_ok=True)
            combined.save(out_png, dpi=(dpi, dpi))
            combined.close()
    finally:
        try:
            if Path(tmp_pdf).exists():
                Path(tmp_pdf).unlink()
        except Exception:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render hotspot snippets for any demo piece (offline, generic)")
    p.add_argument("--score", type=Path, required=True, help="Path to the source MusicXML score")
    p.add_argument("--manifest", type=Path, required=True, help="Path to demo_manifest.json")
    p.add_argument("--snippets-dir", type=Path, required=True, help="Output directory for snippet PNGs")
    p.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150)")
    p.add_argument("--overwrite", action="store_true", help="Force re-render even if PNG exists")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    score_path = Path(args.score).expanduser()
    manifest_path = Path(args.manifest).expanduser()
    snippets_dir = Path(args.snippets_dir).expanduser()
    dpi = int(args.dpi)

    if not score_path.is_file():
        print(f"[error] Score not found: {score_path}", file=sys.stderr)
        return 2
    if not manifest_path.is_file():
        print(f"[error] Manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[error] Failed to parse manifest JSON: {e}", file=sys.stderr)
        return 2

    hotspots = manifest.get("hotspots")
    if not isinstance(hotspots, list) or not hotspots:
        print("[error] Manifest has no hotspots", file=sys.stderr)
        return 2

    try:
        hotspots_sorted = sorted(hotspots, key=lambda h: (h.get("rank") if isinstance(h.get("rank"), int) else 999, str(h.get("id") or "")))
    except Exception:
        hotspots_sorted = hotspots

    snippets_dir.mkdir(parents=True, exist_ok=True)

    try:
        from music21 import converter  # noqa: F401
    except ModuleNotFoundError as e:
        print(f"[error] music21 not available in this env: {e}. Install in piano-difficulty env.", file=sys.stderr)
        return 2

    try:
        from music21 import converter as m21conv
        score = m21conv.parse(str(score_path))
    except Exception as e:
        print(f"[error] Failed to parse MusicXML via music21: {e}", file=sys.stderr)
        return 2

    rendered = 0
    failed = 0

    for idx, h in enumerate(hotspots_sorted, start=1):
        rank = h.get("rank")
        if isinstance(rank, int) and 1 <= rank <= 999:
            fname = f"hotspot_{rank:03d}.png"
        else:
            fname = f"hotspot_{idx:03d}.png"
        rel_path = f"snippets/{fname}"
        abs_path = snippets_dir / fname

        measure_numbers_raw = h.get("measure_numbers") or []
        try:
            measure_numbers = sorted(set(int(str(m).strip()) for m in measure_numbers_raw if str(m).strip() != ""))
        except Exception as e:
            h["snippet_image"] = None
            h["snippet_status"] = "render_failed"
            h["snippet_diagnostic"] = f"Invalid measure_numbers: {e}"[:200]
            failed += 1
            print(f"[warn] hotspot {h.get('id')} invalid measures -> render_failed")
            continue

        if not measure_numbers:
            h["snippet_image"] = None
            h["snippet_status"] = "render_failed"
            h["snippet_diagnostic"] = "No measures in hotspot"[:200]
            failed += 1
            continue

        if abs_path.is_file() and not args.overwrite:
            if abs_path.stat().st_size > 1000:
                h["snippet_image"] = rel_path
                h["snippet_status"] = "rendered"
                h["snippet_diagnostic"] = None
                rendered += 1
                print(f"[ok] hotspot {h.get('id')} rank={rank} already exists -> {rel_path}")
                continue

        tmp_xml = tempfile.mktemp(suffix=".musicxml")
        tmp_xml_norm: str | None = None
        try:
            # --- extract/write with diagnostics + normalized fallback ---
            snippet_score = None
            write_err: Exception | None = None
            try:
                snippet_score = extract_snippet_score(score, measure_numbers)
                _write_snippet_score(snippet_score, tmp_xml, measure_numbers)
            except Exception as e:
                write_err = e
                # try normalized rebuild
                try:
                    snippet_score = build_normalized_snippet_score(score, measure_numbers)
                    tmp_xml_norm = tempfile.mktemp(suffix=".musicxml")
                    _write_snippet_score(snippet_score, tmp_xml_norm, measure_numbers)
                    # use normalized as primary tmp_xml for rendering
                    tmp_xml = tmp_xml_norm
                    write_err = None
                except Exception as e2:
                    raise RuntimeError(
                        f"extract/write failed for measures {measure_numbers}: {e2} (initial: {write_err})"
                    ) from e2
            else:
                # raw write succeeded; keep tmp_xml as is
                pass

            # --- render with fallback via normalized score ---
            try:
                render_via_mscore_to_png(tmp_xml, abs_path, dpi=dpi)
            except Exception as e:
                # fallback: rebuild normalized snippet and retry via temp normalized file
                norm_tmp = tempfile.mktemp(suffix=".musicxml")
                norm_pdf_tried = False
                try:
                    norm_score = build_normalized_snippet_score(score, measure_numbers)
                    _write_snippet_score(norm_score, norm_tmp, measure_numbers)
                    # optionally try MusicXML export through temp normalized file before PDF export is already done;
                    # now retry MuseScore on normalized file
                    render_via_mscore_to_png(norm_tmp, abs_path, dpi=dpi)
                    norm_pdf_tried = True
                except Exception as e2:
                    # keep concise diagnostic, include both errors but truncated
                    base = str(e).strip().replace("\n", " ")[:140]
                    fallback = str(e2).strip().replace("\n", " ")[:140]
                    if norm_pdf_tried:
                        msg = f"MuseScore PDF export failed for measures {measure_numbers}: {base} ; normalized retry: {fallback}"
                    else:
                        msg = f"render failed for measures {measure_numbers}: {base} ; normalized write/render: {fallback}"
                    raise RuntimeError(msg) from e2
                finally:
                    try:
                        if Path(norm_tmp).exists():
                            Path(norm_tmp).unlink()
                    except Exception:
                        pass
                # if fallback succeeded, continue to verification
                if not norm_pdf_tried:
                    # shouldn't happen, but guard
                    pass

            if not abs_path.is_file() or abs_path.stat().st_size < 1000:
                raise RuntimeError(f"Output PNG missing or too small for measures {measure_numbers}")

            h["snippet_image"] = rel_path
            h["snippet_status"] = "rendered"
            h["snippet_diagnostic"] = None
            rendered += 1
            print(f"[ok] hotspot {h.get('id')} rank={rank} measures {measure_numbers} -> {rel_path} ({abs_path.stat().st_size} bytes)")

        except Exception as e:
            diag = str(e).strip().replace("\n", " ")[:200]
            if not diag:
                diag = f"{type(e).__name__}"
            # ensure concise but informative
            if "measures" not in diag and measure_numbers:
                diag = f"measures {measure_numbers}: {diag}"
                diag = diag[:200]
            h["snippet_image"] = None
            h["snippet_status"] = "render_failed"
            h["snippet_diagnostic"] = diag
            failed += 1
            print(f"[fail] hotspot {h.get('id')} rank={rank} measures {measure_numbers} -> {diag}", file=sys.stderr)
            try:
                if abs_path.is_file():
                    abs_path.unlink()
            except Exception:
                pass
        finally:
            try:
                if Path(tmp_xml).exists():
                    Path(tmp_xml).unlink()
            except Exception:
                pass
            try:
                if tmp_xml_norm and Path(tmp_xml_norm).exists() and Path(tmp_xml_norm) != Path(tmp_xml):
                    Path(tmp_xml_norm).unlink()
            except Exception:
                pass

    total = len(hotspots_sorted)
    if failed == 0:
        manifest["snippet_status"] = "rendered"
        manifest["snippet_diagnostic"] = f"All {rendered}/{total} hotspots rendered to snippets/ via music21 + MuseScore (PDF→PNG {dpi}dpi)."
    elif rendered == 0:
        manifest["snippet_status"] = "render_failed"
        manifest["snippet_diagnostic"] = f"All {total} hotspots failed to render; see per-hotspot snippet_diagnostic."
    else:
        manifest["snippet_status"] = "partial"
        manifest["snippet_diagnostic"] = f"{rendered}/{total} hotspots rendered; {failed} failed. See per-hotspot diagnostics."

    tmp_manifest = manifest_path.with_suffix(".tmp.json")
    try:
        tmp_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        json.loads(tmp_manifest.read_text(encoding="utf-8"))
        tmp_manifest.replace(manifest_path)
    except Exception as e:
        print(f"[error] Failed to write manifest: {e}", file=sys.stderr)
        return 2
    finally:
        try:
            if tmp_manifest.exists():
                tmp_manifest.unlink()
        except Exception:
            pass

    print(f"[done] rendered={rendered} failed={failed} total={total} snippets_dir={snippets_dir}")
    print(f"[done] manifest updated: {manifest_path}")
    return 0 if failed == 0 else (1 if rendered > 0 else 2)


if __name__ == "__main__":
    raise SystemExit(main())
