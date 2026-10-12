#!/usr/bin/env python3
"""Pre-render sheet-music snippet images for existing hotspots.

Reads ``demo_manifest.json`` hotspot measure ranges, extracts those ranges
from the canonical Debussy MusicXML via ``music21``, renders each snippet
ahead of time using MuseScore (or fallback PDF→PNG chain), and updates the
manifest in place with per-hotspot ``snippet_image`` / ``snippet_status``.

This script is intentionally Debussy-only and offline/pre-rendered. The web
GUI only displays image files; no live MusicXML rendering happens in the
browser. Hotspot IDs / ranks / measure metadata are preserved.

Usage (from repo root):
    conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_debussy_snippets.py
    conda run -n piano-difficulty python research/learning_support/david_demo/scripts/render_debussy_snippets.py --score <path> --manifest <path> --snippets-dir <dir>

Dependencies: music21 (installed in piano-difficulty env), MuseScore 4 (mscore),
pdftoppm (poppler) or Ghostscript, Pillow for multi-page stitching.
If a snippet fails, the hotspot is kept with snippet_image=null,
snippet_status="render_failed", snippet_diagnostic=concise error.
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

CANONICAL_SCORE_REL = Path("research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml")
CANONICAL_SCORE_ABS = _REPO_ROOT / CANONICAL_SCORE_REL
MANIFEST_REL = Path("research/learning_support/david_demo/artifacts/debussy_arabesque_1/demo_manifest.json")
MANIFEST_ABS = _REPO_ROOT / MANIFEST_REL
SNIPPETS_DIR_REL = Path("research/learning_support/david_demo/artifacts/debussy_arabesque_1/snippets")
SNIPPETS_DIR_ABS = _REPO_ROOT / SNIPPETS_DIR_REL


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


def extract_snippet_score(score, measure_numbers: list[int]):
    """Return a new Score containing only the given measure numbers."""
    from music21 import stream  # lazy import requires music21 installed

    new_score = stream.Score()
    # Preserve metadata if present
    if score.metadata is not None:
        try:
            new_score.metadata = copy.deepcopy(score.metadata)
        except Exception:
            pass
    for part in score.parts:
        new_part = stream.Part()
        # copy part id/name
        try:
            new_part.id = part.id
        except Exception:
            pass
        try:
            if part.partName:
                new_part.partName = part.partName
        except Exception:
            pass
        # Copy relevant measures
        for m in part.getElementsByClass(stream.Measure):
            if m.measureNumber in measure_numbers:
                try:
                    m_copy = copy.deepcopy(m)
                except Exception as e:
                    raise RuntimeError(f"deepcopy measure {m.measureNumber} failed: {e}") from e
                new_part.append(m_copy)
        # Only append non-empty parts; but keep both staves even if one empty?
        # If a part has no measures in range (unlikely for piano), skip.
        if len(list(new_part.getElementsByClass(stream.Measure))) > 0:
            new_score.append(new_part)
    # Fallback: if nothing appended, fail
    if len(list(new_score.parts)) == 0:
        raise ValueError(f"No measures found for numbers {measure_numbers}")
    return new_score


def render_via_mscore_to_png(tmp_xml: str, out_png: Path, dpi: int = 150) -> None:
    """Render MusicXML to PNG via MuseScore PDF + pdftoppm/GS + Pillow stitching.

    Raises on failure with concise message.
    """
    mscore = find_mscore()
    if not mscore:
        raise RuntimeError("MuseScore executable not found (mscore)")

    tmp_pdf = tempfile.mktemp(suffix=".pdf")
    try:
        # Use MuseScore to export PDF (more reliable than direct PNG)
        cmd = [mscore, tmp_xml, "-o", tmp_pdf]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0 or not Path(tmp_pdf).exists():
            raise RuntimeError(f"MuseScore PDF export failed (rc={res.returncode}): {(res.stderr or res.stdout)[:300]}")
        # Check that PDF has content
        if Path(tmp_pdf).stat().st_size < 1000:
            raise RuntimeError("MuseScore produced empty PDF")

        # Try pdftoppm first (poppler)
        pdftoppm = shutil.which("pdftoppm")
        gs = shutil.which("gs")
        convert = shutil.which("convert")

        tmpdir = tempfile.mkdtemp()
        base = os.path.join(tmpdir, "page")

        rendered_pngs: list[str] = []
        if pdftoppm:
            # Render all pages
            res2 = subprocess.run([pdftoppm, "-png", "-r", str(dpi), tmp_pdf, base], capture_output=True, text=True, timeout=30)
            if res2.returncode != 0:
                raise RuntimeError(f"pdftoppm failed: {res2.stderr[:300]}")
            rendered_pngs = sorted(glob.glob(base + "-*.png"))
            if not rendered_pngs and Path(base + ".png").exists():
                rendered_pngs = [base + ".png"]
            if not rendered_pngs:
                raise RuntimeError("pdftoppm produced no PNGs")
        elif gs:
            # Ghostscript fallback: render first page only
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

        # Stitch if multi-page
        if len(rendered_pngs) == 1:
            shutil.copy(rendered_pngs[0], out_png)
        else:
            # Vertically stack with Pillow
            try:
                from PIL import Image
            except Exception as e:
                # Fallback: copy first page
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
            # Ensure parent exists
            out_png.parent.mkdir(parents=True, exist_ok=True)
            combined.save(out_png, dpi=(dpi, dpi))
            combined.close()
    finally:
        # Cleanup temp PDF
        try:
            if Path(tmp_pdf).exists():
                Path(tmp_pdf).unlink()
        except Exception:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render Debussy hotspot snippets (Pass 2, offline)")
    p.add_argument("--score", type=Path, default=CANONICAL_SCORE_ABS, help=f"Canonical MusicXML (default: {CANONICAL_SCORE_REL})")
    p.add_argument("--manifest", type=Path, default=MANIFEST_ABS, help=f"Manifest JSON (default: {MANIFEST_REL})")
    p.add_argument("--snippets-dir", type=Path, default=SNIPPETS_DIR_ABS, help=f"Snippets output dir (default: {SNIPPETS_DIR_REL})")
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

    # Load manifest
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[error] Failed to parse manifest JSON: {e}", file=sys.stderr)
        return 2

    hotspots = manifest.get("hotspots")
    if not isinstance(hotspots, list) or not hotspots:
        print("[error] Manifest has no hotspots", file=sys.stderr)
        return 2

    # Sort hotspots by rank for stable filenames
    try:
        hotspots_sorted = sorted(hotspots, key=lambda h: (h.get("rank") if isinstance(h.get("rank"), int) else 999, str(h.get("id") or "")))
    except Exception:
        hotspots_sorted = hotspots

    # Map rank -> filename stability: hotspot_001.png for rank 1 etc.
    # If rank missing, fallback to sorted index
    snippets_dir.mkdir(parents=True, exist_ok=True)

    # Load score once via music21
    try:
        from music21 import converter  # noqa: F401
    except ModuleNotFoundError as e:
        print(f"[error] music21 not available in this env: {e}. Install in piano-difficulty env.", file=sys.stderr)
        return 2

    # music21 parsing may emit warnings; allow
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
        # Stable filename: hotspot_001.png based on rank
        if isinstance(rank, int) and 1 <= rank <= 999:
            fname = f"hotspot_{rank:03d}.png"
        else:
            fname = f"hotspot_{idx:03d}.png"
        rel_path = f"snippets/{fname}"
        abs_path = snippets_dir / fname

        measure_numbers_raw = h.get("measure_numbers") or []
        # Parse to ints; manifest stores strings like "62"
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

        # If file exists and not overwrite, still verify it is readable via Pillow
        if abs_path.is_file() and not args.overwrite:
            # Quick validation: exists and non-empty
            if abs_path.stat().st_size > 1000:
                h["snippet_image"] = rel_path
                h["snippet_status"] = "rendered"
                h["snippet_diagnostic"] = None
                rendered += 1
                print(f"[ok] hotspot {h.get('id')} rank={rank} already exists -> {rel_path}")
                continue

        # Attempt render
        tmp_xml = tempfile.mktemp(suffix=".musicxml")
        try:
            # Extract
            try:
                snippet_score = extract_snippet_score(score, measure_numbers)
                snippet_score.write("musicxml", fp=tmp_xml)
            except Exception as e:
                raise RuntimeError(f"extract/write failed: {e}") from e

            # Render to PNG
            render_via_mscore_to_png(tmp_xml, abs_path, dpi=dpi)

            # Verify output
            if not abs_path.is_file() or abs_path.stat().st_size < 1000:
                raise RuntimeError("Output PNG missing or too small")

            h["snippet_image"] = rel_path
            h["snippet_status"] = "rendered"
            h["snippet_diagnostic"] = None
            rendered += 1
            print(f"[ok] hotspot {h.get('id')} rank={rank} measures {measure_numbers} -> {rel_path} ({abs_path.stat().st_size} bytes)")

        except Exception as e:
            # concise diagnostic
            diag = str(e).strip().replace("\n", " ")[:200]
            if not diag:
                diag = f"{type(e).__name__}"
            h["snippet_image"] = None
            h["snippet_status"] = "render_failed"
            h["snippet_diagnostic"] = diag
            failed += 1
            print(f"[fail] hotspot {h.get('id')} rank={rank} -> {diag}", file=sys.stderr)
            # Remove partial file if created
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

    # Update top-level snippet_status
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

    # Write manifest atomically
    tmp_manifest = manifest_path.with_suffix(".tmp.json")
    try:
        tmp_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        # Validate JSON
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
