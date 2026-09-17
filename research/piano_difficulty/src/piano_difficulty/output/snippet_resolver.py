"""Snippet resolver for demo-friendly score PNGs.

Stable layout: artifacts/<demo_id>/snippets/window_<index>__measures_<range>.png
or relative `snippets/window_...png` inside a piece dir.

The resolver prefers existing PNGs, falls back to on-demand rendering when a
source score and renderer are available, and never raises for missing assets —
it returns structured status.

Statuses:
  available      — pre-rendered PNG already on disk
  rendered       — successfully rendered and cached on this call
  missing_source — source MusicXML/MXL not found
  render_failed  — renderer missing or raised
  not_requested  — snippets disabled / hotspot has no location
  not_rendered   — legacy alias for not_requested (kept for compat)

All hotspots remain usable; failures degrade to snippet_diagnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


VALID_STATUSES = (
    "available",
    "rendered",
    "missing_source",
    "render_failed",
    "not_requested",
    # legacy compat
    "not_rendered",
)

SNIPPET_DIR_NAME = "snippets"
MIN_PNG_BYTES = 200


# ---------------------------------------------------------------------------
# helpers: filename & extraction
# ---------------------------------------------------------------------------

def _coerce_measure_numbers(raw) -> list[str]:
    """Normalize measure_numbers to sorted unique str list."""
    if raw is None:
        return []
    if isinstance(raw, str):
        # e.g. "1-2" or "3" — treat as single range token
        return [raw] if raw.strip() else []
    if not isinstance(raw, Iterable):
        return []
    out: list[str] = []
    for v in raw:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out.append(s)
    # dedupe, try numeric sort when all numeric
    try:
        ints = sorted(set(int(x) for x in out))
        return [str(i) for i in ints]
    except ValueError:
        return sorted(set(out))


def _extract_measure_numbers(hotspot: dict) -> list[str]:
    # explicit snippet fields first
    for key in ("snippet_measure_numbers", "measure_numbers", "measure_number_list"):
        if hotspot.get(key):
            nums = _coerce_measure_numbers(hotspot.get(key))
            if nums:
                return nums
    # region fallback
    region = hotspot.get("region")
    if isinstance(region, dict) and region.get("measure_numbers"):
        nums = _coerce_measure_numbers(region.get("measure_numbers"))
        if nums:
            return nums
    rep = hotspot.get("representative_region")
    if isinstance(rep, dict) and rep.get("measure_numbers"):
        nums = _coerce_measure_numbers(rep.get("measure_numbers"))
        if nums:
            return nums
    # measure_range string: "5-7" or "3"
    for key in ("measure_range", "snippet_measure_index_range", "measure_index_range"):
        raw = hotspot.get(key)
        if isinstance(raw, str) and raw.strip():
            # parse "5-7" or "5"
            parts = raw.strip().split("-")
            nums: list[str] = []
            try:
                if len(parts) == 2:
                    a, b = int(parts[0].strip()), int(parts[1].strip())
                    lo, hi = min(a, b), max(a, b)
                    nums = [str(i) for i in range(lo, hi + 1)]
                else:
                    int(parts[0].strip())
                    nums = [parts[0].strip()]
                if nums:
                    return nums
            except ValueError:
                pass
    # numeric start/end
    ms, me = hotspot.get("measure_start"), hotspot.get("measure_end")
    if isinstance(ms, int) and isinstance(me, int):
        if ms == me:
            return [str(ms)]
        lo, hi = min(ms, me), max(ms, me)
        return [str(i) for i in range(lo, hi + 1)]
    # also measure_index_start/end
    ms, me = hotspot.get("measure_index_start"), hotspot.get("measure_index_end")
    if isinstance(ms, int) and isinstance(me, int):
        if ms == me:
            return [str(ms)]
        lo, hi = min(ms, me), max(ms, me)
        return [str(i) for i in range(lo, hi + 1)]
    return []


def _extract_window_index(hotspot: dict) -> int | None:
    for key in ("window_index", "snippet_window_index", "windowIndex"):
        v = hotspot.get(key)
        if isinstance(v, int):
            return v
    region = hotspot.get("region")
    if isinstance(region, dict) and isinstance(region.get("window_index"), int):
        return region["window_index"]
    return None


def _range_token(measure_numbers: list[str]) -> str:
    if not measure_numbers:
        return "unknown"
    if len(measure_numbers) == 1:
        return measure_numbers[0]
    # measure_numbers sorted — use first-last to match window_...__measures_5-6 pattern
    # If non-contiguous, still first-last is stable; alternative could be "5_7" but spec says range.
    try:
        ints = [int(x) for x in measure_numbers]
        return f"{min(ints)}-{max(ints)}"
    except ValueError:
        return f"{measure_numbers[0]}-{measure_numbers[-1]}"


def snippet_filename(window_index: int | None, measure_numbers: list[str]) -> str:
    """Return stable filename e.g. window_002__measures_5-6.png."""
    idx = int(window_index) if isinstance(window_index, int) else 0
    # clamp negative?
    if idx < 0:
        idx = 0
    rng = _range_token(measure_numbers)
    # sanitize range token: only allow alnum + '-' + '_' + '.'; replace others
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", rng)
    return f"window_{idx:03d}__measures_{safe}.png"


def snippet_relative_path(window_index: int | None, measure_numbers: list[str]) -> str:
    return f"{SNIPPET_DIR_NAME}/{snippet_filename(window_index, measure_numbers)}"


def _existing_png(snippets_dir: Path, rel: str) -> Path | None:
    abs_path = snippets_dir / Path(rel).name
    # also support subdir-aware check (snippets/window_...png)
    candidate = snippets_dir / Path(rel).name
    # for compat with hotspot_*.png naming from learning_support, also check alternate?
    # Primary is window_*.png
    if candidate.is_file() and candidate.stat().st_size >= MIN_PNG_BYTES:
        return candidate
    # also check exact relative path if snippets_dir already includes snippets/
    alt = snippets_dir.parent / rel
    if alt.is_file() and alt.stat().st_size >= MIN_PNG_BYTES:
        return alt
    # direct snippets_dir/rel
    direct = snippets_dir / Path(rel).name
    # fallback glob for same window_index (if measure range differs but window same)
    # not needed for strict match
    return None


# ---------------------------------------------------------------------------
# result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SnippetResult:
    snippet_image: str | None
    snippet_status: str
    snippet_diagnostic: str | None
    snippet_measure_numbers: list[str]
    snippet_measure_index_range: str
    snippet_window_index: int | None
    absolute_path: Path | None = None

    def to_hotspot_patch(self) -> dict:
        return {
            "snippet_image": self.snippet_image,
            "snippet_status": self.snippet_status,
            "snippet_diagnostic": self.snippet_diagnostic,
            "snippet_measure_numbers": list(self.snippet_measure_numbers),
            "snippet_measure_index_range": self.snippet_measure_index_range,
            "snippet_window_index": self.snippet_window_index,
        }


# ---------------------------------------------------------------------------
# core resolver
# ---------------------------------------------------------------------------

Renderer = Callable[[Path, Path, dict], None]


def resolve_snippet_for_hotspot(
    hotspot: dict,
    snippets_dir: str | Path,
    source_score: str | Path | None = None,
    renderer: Renderer | None = None,
    *,
    allow_render: bool = True,
    overwrite: bool = False,
    min_bytes: int = MIN_PNG_BYTES,
) -> SnippetResult:
    """Resolve snippet for one hotspot.

    Never raises for expected missing/renderer failures; returns status.
    """
    measure_numbers = _extract_measure_numbers(hotspot)
    window_index = _extract_window_index(hotspot)

    # helpers to build result
    def _range_str(nums: list[str]) -> str:
        if not nums:
            return ""
        return _range_token(nums)

    measure_range = _range_str(measure_numbers)

    # snippet_image relative path (stable even when not yet rendered)
    rel = snippet_relative_path(window_index, measure_numbers) if measure_numbers else None

    snippets_dir_p = Path(snippets_dir).expanduser()

    # no location at all
    if not measure_numbers and window_index is None:
        return SnippetResult(
            snippet_image=None,
            snippet_status="not_requested",
            snippet_diagnostic="Hotspot has no window_index or measure_numbers; snippet not requested.",
            snippet_measure_numbers=[],
            snippet_measure_index_range="",
            snippet_window_index=None,
            absolute_path=None,
        )

    # check existing PNG
    if rel is not None:
        # ensure snippets_dir exists for check — but don't create yet
        # check both possible locations
        candidate = snippets_dir_p / Path(rel).name
        if candidate.is_file() and candidate.stat().st_size >= min_bytes and not overwrite:
            return SnippetResult(
                snippet_image=rel,
                snippet_status="available",
                snippet_diagnostic=f"Reused pre-rendered snippet {rel}.",
                snippet_measure_numbers=measure_numbers,
                snippet_measure_index_range=measure_range,
                snippet_window_index=window_index,
                absolute_path=candidate,
            )
        # also check legacy hotspot_*.png naming for compat? Only window pattern required,
        # but we allow fallback search for existing file matching window index
        # not needed per spec; keep strict.

    if not allow_render:
        return SnippetResult(
            snippet_image=None,
            snippet_status="not_requested",
            snippet_diagnostic="Snippet not rendered; pre-render required or enable allow_render.",
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    # need source
    if source_score is None:
        return SnippetResult(
            snippet_image=None,
            snippet_status="missing_source",
            snippet_diagnostic="Source score not available; snippet cannot be rendered.",
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )
    src = Path(source_score).expanduser()
    if not src.is_file():
        return SnippetResult(
            snippet_image=None,
            snippet_status="missing_source",
            snippet_diagnostic=f"Source score not found: {src}.",
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    if renderer is None:
        return SnippetResult(
            snippet_image=None,
            snippet_status="render_failed",
            snippet_diagnostic="No renderer configured; install MuseScore/music21 or pre-render snippets.",
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    if rel is None:
        return SnippetResult(
            snippet_image=None,
            snippet_status="render_failed",
            snippet_diagnostic="Cannot determine snippet filename; missing measure_numbers.",
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    # attempt render
    dest = snippets_dir_p / Path(rel).name
    # ensure parent
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        renderer(src, dest, hotspot)
    except Exception as exc:  # noqa: BLE001
        # remove partial
        try:
            if dest.is_file():
                dest.unlink()
        except Exception:
            pass
        diag = str(exc).strip().replace("\n", " ")
        if not diag:
            diag = type(exc).__name__
        diag = diag[:200]
        return SnippetResult(
            snippet_image=None,
            snippet_status="render_failed",
            snippet_diagnostic=diag,
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    # validate output
    try:
        if not dest.is_file() or dest.stat().st_size < min_bytes:
            try:
                if dest.is_file():
                    dest.unlink()
            except Exception:
                pass
            return SnippetResult(
                snippet_image=None,
                snippet_status="render_failed",
                snippet_diagnostic="Renderer produced no PNG or file too small.",
                snippet_measure_numbers=measure_numbers,
                snippet_measure_index_range=measure_range,
                snippet_window_index=window_index,
                absolute_path=None,
            )
    except Exception as exc:  # noqa: BLE001
        return SnippetResult(
            snippet_image=None,
            snippet_status="render_failed",
            snippet_diagnostic=str(exc)[:200],
            snippet_measure_numbers=measure_numbers,
            snippet_measure_index_range=measure_range,
            snippet_window_index=window_index,
            absolute_path=None,
        )

    return SnippetResult(
        snippet_image=rel,
        snippet_status="rendered",
        snippet_diagnostic=None,
        snippet_measure_numbers=measure_numbers,
        snippet_measure_index_range=measure_range,
        snippet_window_index=window_index,
        absolute_path=dest,
    )


def enrich_hotspot_with_snippet(
    hotspot: dict,
    snippets_dir: str | Path,
    source_score: str | Path | None = None,
    renderer: Renderer | None = None,
    *,
    allow_render: bool = True,
    overwrite: bool = False,
) -> dict:
    """Mutate hotspot in place with snippet_* fields (graceful). Returns hotspot."""
    result = resolve_snippet_for_hotspot(
        hotspot, snippets_dir, source_score, renderer,
        allow_render=allow_render, overwrite=overwrite,
    )
    hotspot["snippet_image"] = result.snippet_image
    hotspot["snippet_status"] = result.snippet_status
    hotspot["snippet_diagnostic"] = result.snippet_diagnostic
    hotspot["snippet_measure_numbers"] = list(result.snippet_measure_numbers)
    hotspot["snippet_measure_index_range"] = result.snippet_measure_index_range
    hotspot["snippet_window_index"] = result.snippet_window_index
    # also ensure measure_index_range alias for older readers
    if "measure_index_range" not in hotspot or not hotspot.get("measure_index_range"):
        hotspot["measure_index_range"] = result.snippet_measure_index_range
    return hotspot


def enrich_hotspots(
    hotspots: list[dict],
    snippets_dir: str | Path,
    source_score: str | Path | None = None,
    renderer: Renderer | None = None,
    *,
    allow_render: bool = True,
    overwrite: bool = False,
) -> list[dict]:
    for hs in hotspots:
        if isinstance(hs, dict):
            enrich_hotspot_with_snippet(hs, snippets_dir, source_score, renderer, allow_render=allow_render, overwrite=overwrite)
    return hotspots


def default_snippet_fields_for_hotspot(hotspot: dict) -> dict:
    """Build snippet_* fields without requiring renderer/source (for analysis phase).

    Prefers `not_requested` / `available` check only if snippets_dir can be inferred.
    Callers that have a piece_dir should prefer resolve_snippet_for_hotspot with
    snippets_dir to get `available` detection.
    """
    measure_numbers = _extract_measure_numbers(hotspot)
    window_index = _extract_window_index(hotspot)
    rng = _range_token(measure_numbers) if measure_numbers else ""
    return {
        "snippet_image": None,
        "snippet_status": "not_requested",
        "snippet_diagnostic": "Snippet not pre-rendered; run pre-render script or provide snippets/window_*.png.",
        "snippet_measure_numbers": measure_numbers,
        "snippet_measure_index_range": rng,
        "snippet_window_index": window_index,
    }


def enrich_payload_with_snippets(
    payload: dict,
    snippets_dir: str | Path,
    source_score: str | Path | None = None,
    renderer: Renderer | None = None,
    *,
    allow_render: bool = True,
    overwrite: bool = False,
) -> dict:
    """Enrich all hotspot candidate_sections in payload with snippet_* fields.

    Walks both difficulty_overview and difficulty_aspects profiles. Mutates
    payload in place and returns it. Never raises for snippet failures.
    """
    if not isinstance(payload, dict):
        return payload
    profiles = payload.get("analysis_profiles")
    if not isinstance(profiles, list):
        return payload
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        # difficulty_overview: candidate_sections
        for key in ("candidate_sections", "hotspots", "aspect_hotspots"):
            sections = profile.get(key)
            if isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict):
                        enrich_hotspot_with_snippet(
                            sec, snippets_dir, source_score, renderer,
                            allow_render=allow_render, overwrite=overwrite,
                        )
            # also difficulty_aspects hotspots
        # also handle hand_views for overview
        hand_views = profile.get("hand_views")
        if isinstance(hand_views, dict):
            for view in hand_views.values():
                if isinstance(view, dict):
                    cs = view.get("candidate_sections")
                    if isinstance(cs, list):
                        for sec in cs:
                            if isinstance(sec, dict):
                                enrich_hotspot_with_snippet(
                                    sec, snippets_dir, source_score, renderer,
                                    allow_render=allow_render, overwrite=overwrite,
                                )
    return payload


def try_default_mscore_renderer(source: str | Path, dest: str | Path, hotspot: dict) -> None:
    """Best-effort MuseScore-backed renderer (music21 + mscore). Raises on failure."""
    # Lazy imports — may not be installed
    try:
        from music21 import converter as m21conv
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"music21 not available: {exc}") from exc

    import copy
    import glob
    import os
    import shutil
    import subprocess
    import tempfile

    # find mscore
    def _find_mscore() -> str | None:
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

    mscore = _find_mscore()
    if not mscore:
        raise RuntimeError("MuseScore executable not found (mscore)")

    # parse source and extract requested measures
    measure_numbers = _extract_measure_numbers(hotspot)
    if not measure_numbers:
        raise RuntimeError("Hotspot has no measure_numbers")
    try:
        ints = [int(x) for x in measure_numbers]
    except ValueError:
        ints = []
        for x in measure_numbers:
            try:
                ints.append(int(x))
            except ValueError:
                pass
        if not ints:
            raise RuntimeError(f"Invalid measure_numbers {measure_numbers}")
    score = m21conv.parse(str(source))
    # build snippet score
    from music21 import stream

    new_score = stream.Score()
    if score.metadata is not None:
        try:
            new_score.metadata = copy.deepcopy(score.metadata)
        except Exception:
            pass
    for part in score.parts:
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
        for m in part.getElementsByClass(stream.Measure):
            if m.measureNumber in ints:
                try:
                    m_copy = copy.deepcopy(m)
                except Exception as e:
                    raise RuntimeError(f"deepcopy measure {m.measureNumber} failed: {e}") from e
                new_part.append(m_copy)
        if len(list(new_part.getElementsByClass(stream.Measure))) > 0:
            new_score.append(new_part)
    if len(list(new_score.parts)) == 0:
        raise RuntimeError(f"No measures found for numbers {ints}")

    tmp_xml = tempfile.mktemp(suffix=".musicxml")
    tmp_pdf = tempfile.mktemp(suffix=".pdf")
    try:
        new_score.write("musicxml", fp=tmp_xml)
        cmd = [mscore, tmp_xml, "-o", tmp_pdf]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0 or not Path(tmp_pdf).exists():
            raise RuntimeError(f"MuseScore PDF export failed (rc={res.returncode}): {(res.stderr or res.stdout)[:300]}")
        if Path(tmp_pdf).stat().st_size < 1000:
            raise RuntimeError("MuseScore produced empty PDF")
        # pdf -> png
        pdftoppm = shutil.which("pdftoppm")
        gs = shutil.which("gs")
        convert = shutil.which("convert")
        tmpdir = tempfile.mkdtemp()
        base = os.path.join(tmpdir, "page")
        rendered_pngs: list[str] = []
        if pdftoppm:
            res2 = subprocess.run([pdftoppm, "-png", "-r", "150", tmp_pdf, base], capture_output=True, text=True, timeout=30)
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
                ["gs", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-r150", "-sDEVICE=png16m", f"-sOutputFile={out_tmp}", tmp_pdf],
                capture_output=True, text=True, timeout=30,
            )
            if res2.returncode != 0 or not Path(out_tmp).exists():
                raise RuntimeError(f"Ghostscript failed: {res2.stderr[:300]}")
            rendered_pngs = [out_tmp]
        elif convert:
            out_tmp = os.path.join(tmpdir, "convert.png")
            res2 = subprocess.run(["convert", "-density", "150", f"{tmp_pdf}[0]", out_tmp], capture_output=True, text=True, timeout=30)
            if res2.returncode != 0 or not Path(out_tmp).exists():
                raise RuntimeError(f"ImageMagick convert failed: {res2.stderr[:300]}")
            rendered_pngs = [out_tmp]
        else:
            raise RuntimeError("No PDF→PNG converter found (pdftoppm/gs/convert)")
        dest_p = Path(dest)
        if len(rendered_pngs) == 1:
            shutil.copy(rendered_pngs[0], dest_p)
        else:
            try:
                from PIL import Image  # type: ignore

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
                dest_p.parent.mkdir(parents=True, exist_ok=True)
                combined.save(dest_p, dpi=(150, 150))
                combined.close()
            except Exception:
                shutil.copy(rendered_pngs[0], dest_p)
    finally:
        for p in (tmp_xml, tmp_pdf):
            try:
                if Path(p).exists():
                    Path(p).unlink()
            except Exception:
                pass

