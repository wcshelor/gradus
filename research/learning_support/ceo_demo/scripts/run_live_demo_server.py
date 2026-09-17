#!/usr/bin/env python3
"""Local live-demo server for CEO demo: search CIPI/Oktav and run on-demand analysis.

Serves existing static web files and exposes JSON API:
  GET  /api/datasets
  GET  /api/pieces?dataset=<cipi|oktav>&q=<query>
  POST /api/analyze
  GET  /api/jobs/<job_id>

Live analysis writes under research/learning_support/ceo_demo/artifacts/live/<safe_piece_id>/
with at least analysis.json/.md/.html/.csv and demo_manifest.json.

Usage:
  python research/learning_support/ceo_demo/scripts/run_live_demo_server.py
  python research/learning_support/ceo_demo/scripts/run_live_demo_server.py --port 8000 --host 127.0.0.1

Claim boundaries:
  labels are provenance only, output is symbolic-score evidence,
  no calibrated learner grade, Oktav labels are not Gradus grades.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

REPO_ROOT = Path(__file__).resolve().parents[4]
CIPI_MANIFEST_CSV = REPO_ROOT / "research/piano_difficulty/evaluation_scores/manifests/cipi/cipi_movement_manifest.csv"
OKTAV_LOAD_REPORT = REPO_ROOT / "research/piano_difficulty/tests/artifacts/oktav_dataset/python_analysis/full_run/load_report.json"
OKTAV_LABEL_CSV = REPO_ROOT / "research/piano_difficulty/tests/artifacts/oktav_dataset/python_analysis/full_run/oktav_labeled_feature_matrix.csv"
CIPI_ROOT = Path("/Users/campshelor/Desktop/oktav-thesis/datasets/cipi")
OKTAV_ROOT = Path("/Users/campshelor/Desktop/oktav-thesis/datasets/oktav-starting-dataset")
ARTIFACTS_BASE = REPO_ROOT / "research/learning_support/ceo_demo/artifacts"
LIVE_BASE = ARTIFACTS_BASE / "live"
BUILD_SCRIPT = REPO_ROOT / "research/learning_support/ceo_demo/scripts/build_demo_piece.py"
DEMO_SOURCE_DIR = REPO_ROOT / "research/learning_support/ceo_demo/data/source_scores"

# Curated catalog -> canonical filename mapping (stable, see data/source_scores/README.md)
CURATED_FILE_MAP = {
    "beethoven_fur_elise": "beethoven_fur-elise.musicxml",
    "beethoven_bagatelle_119_10": "beethoven_bagatelle-a-major-op-119-no-10.musicxml",
    "mozart_k545": "mozart_k545_mvt1.musicxml",
    "chopin_waltz_a_minor_kk_ivb_11": "chopin_waltz-a-minor-kk-ivb-11.musicxml",
    "chopin_prelude_e_minor_28_4": "chopin_prelude-e-minor-op-28-no-4.musicxml",
    "chopin_prelude_a_major_28_7": "chopin_prelude-a-major-op-28-no-7.musicxml",
    "debussy_arabesque_1": "debussy_arabesque-no-1.musicxml",
    "satie_gymnopedie_1": "satie_gymnopedie-no-1.musicxml",
    "oktav_le_onde": "oktav_le-onde_OK00027.xml",
    "oktav_a_thousand_miles": "oktav_a-thousand-miles_OK00016.xml",
    "oktav_viva_la_vida": "oktav_viva-la-vida_OK00009.xml",
}

# In-memory indexes
_cipi_index: list[dict] | None = None
_oktav_index: list[dict] | None = None
_index_lock = threading.Lock()

# Jobs store
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def slugify(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(text or "")).strip("_").lower()
    if not s:
        s = "piece"
    return s[:max_len].strip("_") or "piece"


def safe_piece_id(dataset: str, piece_uid: str | None, dataset_relative_path: str | None, piece_id: str | None = None) -> str:
    base = piece_uid or dataset_relative_path or piece_id or "unknown"
    # for CIPI prefer piece_uid which is already filesystem safe-ish but slug anyway
    slug = slugify(base)
    # ensure uniqueness-ish by including dataset prefix
    return f"live_{dataset}_{slug}"


def load_cipi_index() -> list[dict]:
    global _cipi_index
    with _index_lock:
        if _cipi_index is not None:
            return _cipi_index
        results: list[dict] = []
        if not CIPI_MANIFEST_CSV.is_file():
            print(f"[warn] CIPI manifest not found: {CIPI_MANIFEST_CSV}", file=sys.stderr)
            _cipi_index = results
            return results
        try:
            with CIPI_MANIFEST_CSV.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cipi_id = (row.get("cipi_id") or "").strip()
                    piece_id = (row.get("piece_id") or "").strip()
                    piece_uid = (row.get("piece_uid") or "").strip()
                    composer = (row.get("composer") or "").strip()
                    work_name = (row.get("work_name") or "").strip()
                    henle = (row.get("henle") or "").strip()
                    dataset_rel = (row.get("dataset_relative_path") or "").strip()
                    # Some rows have empty dataset_relative_path? fallback to legacy
                    if not dataset_rel:
                        dataset_rel = (row.get("legacy_dataset_relative_path") or "").strip()
                    title = work_name or piece_id
                    # normalized search blob
                    search_blob = " ".join([composer, work_name, title, piece_id, piece_uid, cipi_id, dataset_rel, henle]).lower()
                    # resolve absolute path
                    source_path = CIPI_ROOT / dataset_rel if dataset_rel else None
                    exists = source_path.is_file() if source_path else False
                    results.append({
                        "dataset": "cipi",
                        "cipi_id": cipi_id,
                        "piece_id": piece_id,
                        "piece_uid": piece_uid,
                        "composer": composer,
                        "title": title,
                        "work_name": work_name,
                        "henle": henle,
                        "difficulty_label": f"Henle {henle}" if henle else "",
                        "dataset_id": cipi_id,
                        "dataset_relative_path": dataset_rel,
                        "source_path": str(source_path.resolve()) if source_path else "",
                        "exists": exists,
                        "_search_blob": search_blob,
                    })
        except Exception as e:
            print(f"[error] Failed to load CIPI index: {e}", file=sys.stderr)
        _cipi_index = results
        print(f"[info] CIPI index loaded: {len(results)} entries (CIPI_ROOT={CIPI_ROOT} exists={CIPI_ROOT.is_dir()})")
        return results


def load_oktav_index() -> list[dict]:
    global _oktav_index
    with _index_lock:
        if _oktav_index is not None:
            return _oktav_index
        results: list[dict] = []
        if OKTAV_LOAD_REPORT.is_file():
            try:
                data = json.loads(OKTAV_LOAD_REPORT.read_text(encoding="utf-8"))
                records = data.get("records") or []
                for rec in records:
                    dataset_rel = rec.get("dataset_relative_path") or rec.get("filename") or ""
                    piece_id = rec.get("piece_id") or ""
                    piece_uid = rec.get("piece_uid") or ""
                    title = rec.get("title") or rec.get("filename") or piece_uid
                    composer = rec.get("composer") or ""
                    # Try to extract composer from filename heuristic? Keep empty
                    source_path = rec.get("source_path") or rec.get("provenance", {}).get("source_path") or ""
                    # fallback to OKTAV_ROOT / dataset_rel
                    if not source_path:
                        source_path = str((OKTAV_ROOT / dataset_rel).resolve()) if dataset_rel else ""
                    exists = Path(source_path).is_file() if source_path else False
                    # difficulty label provenance only
                    labels = rec.get("labels") or {}
                    diff_num = labels.get("difficulty_numeric")
                    diff_label = ""
                    if diff_num not in (None, ""):
                        diff_label = f"Oktav {diff_num} (original dataset label; not a Gradus grade)"
                    search_blob = " ".join([composer, title, piece_id, piece_uid, dataset_rel, diff_label]).lower()
                    results.append({
                        "dataset": "oktav",
                        "piece_id": piece_id,
                        "piece_uid": piece_uid,
                        "composer": composer,
                        "title": title,
                        "work_name": title,
                        "henle": "",
                        "difficulty_label": diff_label,
                        "difficulty_numeric": diff_num if diff_num not in (None, "") else None,
                        "dataset_id": piece_id,
                        "dataset_relative_path": dataset_rel,
                        "source_path": source_path,
                        "exists": exists,
                        "arrangement": rec.get("adapter_metadata", {}).get("arrangement_raw") or "",
                        "_search_blob": search_blob,
                    })
                _oktav_index = results
                print(f"[info] Oktav index loaded from load_report: {len(results)} entries (OKTAV_ROOT={OKTAV_ROOT} exists={OKTAV_ROOT.is_dir()})")
                return results
            except Exception as e:
                print(f"[error] Failed to load Oktav load_report: {e}", file=sys.stderr)
        # Fallback: scan directory
        if OKTAV_ROOT.is_dir():
            try:
                for p in sorted(OKTAV_ROOT.iterdir(), key=lambda x: x.name.lower()):
                    if not p.is_file() or p.name == ".DS_Store":
                        continue
                    if p.suffix.lower() not in {".xml", ".musicxml", ".mxl"}:
                        continue
                    dataset_rel = p.name
                    piece_uid = re.sub(r"[^a-z0-9]+", "_", dataset_rel.lower()).strip("_")
                    # parse OK id
                    m = re.search(r"OK\d{5}", dataset_rel, re.IGNORECASE)
                    ok_id = m.group(0).upper() if m else piece_uid
                    search_blob = " ".join([p.stem, dataset_rel, ok_id]).lower()
                    results.append({
                        "dataset": "oktav",
                        "piece_id": ok_id,
                        "piece_uid": piece_uid,
                        "composer": "",
                        "title": p.stem,
                        "work_name": p.stem,
                        "henle": "",
                        "difficulty_label": "",
                        "dataset_id": ok_id,
                        "dataset_relative_path": dataset_rel,
                        "source_path": str(p.resolve()),
                        "exists": True,
                        "_search_blob": search_blob,
                    })
                print(f"[info] Oktav index loaded from directory scan: {len(results)} entries")
            except Exception as e:
                print(f"[error] Failed to scan Oktav dir: {e}", file=sys.stderr)
        _oktav_index = results
        return results


def ensure_indexes():
    load_cipi_index()
    load_oktav_index()


def search_pieces(dataset: str, query: str, limit: int = 50) -> list[dict]:
    ensure_indexes()
    q = (query or "").strip().lower()
    if dataset == "cipi":
        pool = load_cipi_index()
    elif dataset == "oktav":
        pool = load_oktav_index()
    else:
        pool = load_cipi_index() + load_oktav_index()
    if not q:
        # return first N sorted by composer/title
        sliced = sorted(pool, key=lambda x: (x.get("composer") or "", x.get("title") or ""))[:limit]
        # strip _search_blob
        return [{k: v for k, v in item.items() if k != "_search_blob"} for item in sliced]
    filtered = []
    for item in pool:
        blob = item.get("_search_blob") or ""
        # also check individual fields explicitly for substring
        if q in blob:
            filtered.append(item)
            if len(filtered) >= limit:
                break
    # if too few, try case-insensitive substring without blob (already)
    return [{k: v for k, v in item.items() if k != "_search_blob"} for item in filtered]


def find_piece_for_analyze(dataset: str, payload: dict) -> dict | None:
    """Find index entry matching analyze payload."""
    # payload may contain piece_id, piece_uid, dataset_relative_path, cipi_id, etc.
    ensure_indexes()
    pool = load_cipi_index() if dataset == "cipi" else load_oktav_index() if dataset == "oktav" else []
    # Prefer exact dataset_relative_path match
    target_rel = payload.get("dataset_relative_path") or payload.get("datasetRelativePath") or ""
    target_pid = payload.get("piece_id") or payload.get("pieceId") or payload.get("dataset_id") or payload.get("cipi_id") or ""
    target_uid = payload.get("piece_uid") or payload.get("pieceUid") or ""
    # Try exact match on dataset_relative_path first
    if target_rel:
        for item in pool:
            if item.get("dataset_relative_path") == target_rel:
                return item
        # also try normalized case-insensitive
        for item in pool:
            if item.get("dataset_relative_path", "").lower() == target_rel.lower():
                return item
    if target_uid:
        for item in pool:
            if item.get("piece_uid") == target_uid:
                return item
    if target_pid:
        # For Oktav piece_id may have duplicates; need also dataset_rel to disambiguate
        candidates = [x for x in pool if x.get("piece_id") == target_pid or x.get("dataset_id") == target_pid or x.get("cipi_id") == target_pid]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1 and target_rel:
            for c in candidates:
                if c.get("dataset_relative_path") == target_rel:
                    return c
            return candidates[0]
        if candidates:
            return candidates[0]
    # Fallback: try to match by title? Use first result of search with piece_id as query
    if target_pid:
        for item in pool:
            if target_pid.lower() in item.get("_search_blob", ""):
                return item
    return None


# ── Open-score helpers (local-demo convenience, not a production viewer) ─────

def _find_mscore() -> str | None:
    import shutil as _shutil
    for cand in [
        _shutil.which("mscore"),
        _shutil.which("musescore"),
        "/usr/local/bin/mscore",
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "/Applications/MuseScore.app/Contents/MacOS/mscore",
    ]:
        if cand and Path(cand).exists():
            return cand
    return None


def _is_allowed_path(p: Path) -> bool:
    """Return True iff p resolves inside DEMO_SOURCE_DIR or matches a known job source_path."""
    try:
        rp = p.resolve()
    except Exception:
        return False
    # Allowed base: curated demo scores dir
    try:
        demo_root = DEMO_SOURCE_DIR.resolve()
        if rp == demo_root or demo_root in rp.parents:
            return True
    except Exception:
        pass
    # Allowed: any known live job source_path (external CIPI/Oktav file already validated)
    with _jobs_lock:
        for job in _jobs.values():
            piece = job.get("piece") or {}
            sp = piece.get("source_path")
            if sp:
                try:
                    if Path(sp).resolve() == rp:
                        return True
                except Exception:
                    continue
    # Also allow files under LIVE_BASE? Not source scores, so deny.
    return False


def _resolve_curated_path(piece_id: str) -> Path | None:
    """Resolve curated piece_id to its canonical source file under DEMO_SOURCE_DIR."""
    fname = CURATED_FILE_MAP.get(piece_id)
    if fname:
        cand = DEMO_SOURCE_DIR / fname
        if cand.is_file():
            return cand
    # Fallback: try artifacts/<piece_id>/demo_manifest.json piece.source_score_path
    try:
        manifest = ARTIFACTS_BASE / piece_id / "demo_manifest.json"
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            piece = data.get("piece") or {}
            rel = piece.get("source_score_path") or piece.get("canonical_filename") or ""
            if rel:
                # rel may be relative to repo root or filename
                cand = (REPO_ROOT / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
                # If rel was just filename, the above will be repo_root/filename which won't exist; try DEMO_SOURCE_DIR
                if cand.is_file():
                    return cand
                cand2 = DEMO_SOURCE_DIR / Path(rel).name
                if cand2.is_file():
                    return cand2
    except Exception:
        pass
    # Live jobs: search by safe_piece_id or piece_id
    with _jobs_lock:
        for job in _jobs.values():
            if job.get("safe_piece_id") == piece_id:
                sp = (job.get("piece") or {}).get("source_path")
                if sp and Path(sp).is_file():
                    return Path(sp)
            piece = job.get("piece") or {}
            if piece.get("piece_id") == piece_id or piece.get("piece_uid") == piece_id or piece.get("dataset_id") == piece_id:
                sp = piece.get("source_path")
                if sp and Path(sp).is_file():
                    return Path(sp)
    return None


def _resolve_source_score_path_raw(raw: str) -> Path | None:
    """Resolve raw source_score_path string and ensure file exists (no allow check yet)."""
    raw = raw.strip()
    if not raw:
        return None
    # Reject URLs or control chars
    if "://" in raw or "\n" in raw or "\r" in raw:
        return None
    p = Path(raw)
    # If relative, treat as repo-relative first
    candidates = []
    if not p.is_absolute():
        candidates.append((REPO_ROOT / raw).resolve())
        candidates.append((DEMO_SOURCE_DIR / Path(raw).name).resolve())
        candidates.append(Path(raw).resolve())
    else:
        candidates.append(p.resolve())
    for cand in candidates:
        if cand.is_file():
            return cand
    # Also try literal resolve even if not exists (to check allow deny)
    try:
        return p.resolve()
    except Exception:
        return None


def _launch_musescore(path: Path) -> None:
    """Attempt to open path in MuseScore; raises on failure."""
    path_str = str(path)
    # macOS primary: open -a MuseScore
    for app_name in ["MuseScore 4", "MuseScore"]:
        try:
            proc = subprocess.Popen(
                ["open", "-a", app_name, path_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Give it a moment to report immediate failure? Not needed.
            return
        except FileNotFoundError:
            # 'open' not found (non-macOS)
            break
        except Exception:
            continue
    # Fallback: direct executable
    mscore = _find_mscore()
    if mscore:
        try:
            subprocess.Popen([mscore, path_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception as e:
            raise RuntimeError(f"MuseScore launch failed ({mscore}): {e}") from e
    # If open failed and no fallback, raise.
    # Check if 'open' exists but app not found, try xdg-open fallback for linux
    try:
        import shutil as _shutil
        if _shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", path_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    except Exception:
        pass
    raise RuntimeError("MuseScore not found — tried open -a MuseScore and fallback executables")


def run_analysis_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        dataset = job["dataset"]
        piece = job["piece"]
        if not piece:
            raise FileNotFoundError("Piece not found in index")
        source_path = Path(piece["source_path"])
        if not source_path.is_file():
            # try alternative resolution
            alt = None
            if dataset == "cipi":
                alt = CIPI_ROOT / piece.get("dataset_relative_path", "")
            elif dataset == "oktav":
                alt = OKTAV_ROOT / piece.get("dataset_relative_path", "")
            if alt and alt.is_file():
                source_path = alt
            else:
                raise FileNotFoundError(f"Source file not found: {source_path} (alt {alt})")
        # Build safe id and out dir
        safe = safe_piece_id(dataset, piece.get("piece_uid"), piece.get("dataset_relative_path"), piece.get("piece_id"))
        # Ensure slug stability: if job already has safe_piece_id use it
        if job.get("safe_piece_id"):
            safe = job["safe_piece_id"]
        else:
            job["safe_piece_id"] = safe
        out_dir = LIVE_BASE / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        # Prepare build args
        title = piece.get("title") or piece.get("work_name") or safe
        composer = piece.get("composer") or "Unknown"
        dataset_id = piece.get("dataset_id") or piece.get("cipi_id") or piece.get("piece_id") or ""
        dataset_rel = piece.get("dataset_relative_path") or ""
        # For Oktav title/composer may be empty; use filename stem
        # Run build_demo_piece.py as subprocess for determinism.
        # Prefer conda env piano-difficulty if available (server may be launched with system python).
        import shutil as _shutil
        conda_exe = _shutil.which("conda")
        use_conda = False
        if conda_exe:
            # probe if env exists
            try:
                probe = subprocess.run([conda_exe, "run", "-n", "piano-difficulty", "python", "-c", "import sys; print(sys.version)"], capture_output=True, text=True, timeout=10)
                if probe.returncode == 0:
                    use_conda = True
            except Exception:
                use_conda = False
        if use_conda:
            cmd = [
                conda_exe, "run", "-n", "piano-difficulty", "python",
                str(BUILD_SCRIPT),
                "--piece-id", safe,
                "--score", str(source_path),
                "--title", title,
                "--composer", composer,
                "--dataset", dataset,
                "--out-dir", str(out_dir),
            ]
        else:
            cmd = [
                sys.executable,
                str(BUILD_SCRIPT),
                "--piece-id", safe,
                "--score", str(source_path),
                "--title", title,
                "--composer", composer,
                "--dataset", dataset,
                "--out-dir", str(out_dir),
            ]
        if dataset_id:
            cmd += ["--dataset-id", str(dataset_id)]
        if dataset_rel:
            cmd += ["--dataset-relative-path", dataset_rel]
        print(f"[job {job_id}] Running: {' '.join(cmd)}", flush=True)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        raw_log = (proc.stdout or "") + "\n" + (proc.stderr or "")

        def _sanitize_log(s: str) -> str:
            # Replace control chars 0x00-0x1F except \n \r \t with space; also strip surrogates
            out = []
            for ch in s:
                o = ord(ch)
                if o < 32 and ch not in ("\n", "\r", "\t"):
                    out.append(" ")
                elif 0xD800 <= o <= 0xDFFF:  # surrogates
                    out.append("?")
                else:
                    out.append(ch)
            sanitized = "".join(out)
            # also ensure valid utf-8 roundtrip
            return sanitized[:12000]

        job["log"] = _sanitize_log(raw_log)
        if proc.returncode != 0:
            raise RuntimeError(f"build_demo_piece failed (exit {proc.returncode}): {proc.stderr[:2000]}")
        # Validate outputs
        required = ["analysis.json", "analysis.md", "analysis.html", "analysis.csv", "demo_manifest.json"]
        missing = [n for n in required if not (out_dir / n).is_file()]
        if missing:
            raise RuntimeError(f"Missing generated artifacts: {missing}")
        # Validate manifest has 9 aspects etc. Quick check
        manifest = json.loads((out_dir / "demo_manifest.json").read_text(encoding="utf-8"))
        chart = manifest.get("chart") or {}
        series = chart.get("series") or {}
        if len(series) != 9:
            print(f"[warn] job {job_id} manifest series count {len(series)} !=9", file=sys.stderr)
        hotspots = manifest.get("hotspots") or []
        if not hotspots:
            print(f"[warn] job {job_id} manifest has no hotspots", file=sys.stderr)
        manifest_url = f"/research/learning_support/ceo_demo/artifacts/live/{safe}/demo_manifest.json"
        # Also provide relative URL for web/ context
        manifest_url_rel = f"../artifacts/live/{safe}/demo_manifest.json"
        with _jobs_lock:
            job["status"] = "succeeded"
            job["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            job["manifest_url"] = manifest_url
            job["manifest_url_rel"] = manifest_url_rel
            job["artifact_dir"] = str(out_dir)
            job["safe_piece_id"] = safe
            # include manifest snippet for convenience
            job["piece_title"] = title
            job["piece_composer"] = composer
        print(f"[job {job_id}] Succeeded -> {manifest_url}", flush=True)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()

        def _sanitize_err(s: str) -> str:
            out = []
            for ch in s:
                o = ord(ch)
                if o < 32 and ch not in ("\n", "\r", "\t"):
                    out.append(" ")
                elif 0xD800 <= o <= 0xDFFF:
                    out.append("?")
                else:
                    out.append(ch)
            return "".join(out)[:4000]

        print(f"[job {job_id}] Failed: {e}\n{tb}", file=sys.stderr)
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                job["error"] = _sanitize_err(str(e))
                tb_s = _sanitize_err(tb)
                if "log" not in job or not job["log"]:
                    job["log"] = tb_s
                else:
                    job["log"] = _sanitize_err(job["log"] + "\n" + tb_s)


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):
        # concise logging
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def end_headers(self):
        # CORS for local demo
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/api/datasets" or path == "/api/datasets/":
            self.handle_datasets()
            return
        if path.startswith("/api/pieces"):
            self.handle_pieces(qs)
            return
        if path.startswith("/api/jobs/"):
            job_id = path.split("/api/jobs/")[-1].strip("/")
            job_id = unquote(job_id)
            self.handle_job_get(job_id)
            return
        if path == "/api/jobs" or path == "/api/jobs/":
            self.handle_jobs_list()
            return
        if path == "/api/health":
            self.send_json({"ok": True, "cipi_root_exists": CIPI_ROOT.is_dir(), "oktav_root_exists": OKTAV_ROOT.is_dir()})
            return
        if path in ("/api/open-score", "/api/open-score/"):
            self.send_json({"error": "Method not allowed — use POST /api/open-score", "method": "GET"}, status=405)
            return
        # Serve static files (default)
        # Ensure / redirects to web/
        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/research/learning_support/ceo_demo/web/")
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/api/analyze", "/api/analyze/"):
            self.handle_analyze()
            return
        if path in ("/api/open-score", "/api/open-score/"):
            self.handle_open_score()
            return
        self.send_error(404, "Not found")

    # API handlers
    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_datasets(self):
        ensure_indexes()
        cipi_count = len(load_cipi_index())
        oktav_count = len(load_oktav_index())
        self.send_json({
            "datasets": [
                {
                    "id": "cipi",
                    "label": "CIPI",
                    "count": cipi_count,
                    "root": str(CIPI_ROOT),
                    "exists": CIPI_ROOT.is_dir(),
                    "description": "CIPI piano corpus (Henle-graded, MusicXML)",
                },
                {
                    "id": "oktav",
                    "label": "Oktav",
                    "count": oktav_count,
                    "root": str(OKTAV_ROOT),
                    "exists": OKTAV_ROOT.is_dir(),
                    "description": "Oktav corpus (original dataset labels only; not Gradus grades)",
                },
            ],
            "claim_boundaries": "labels are provenance only; output is symbolic-score evidence; no calibrated learner grade; Oktav labels are not Gradus grades",
        })

    def handle_pieces(self, qs):
        dataset = (qs.get("dataset") or qs.get("dataset[]") or ["cipi"])[0]
        dataset = dataset.lower().strip()
        if dataset not in ("cipi", "oktav"):
            # support "all"
            if dataset in ("all", "both", ""):
                dataset = "all"
            else:
                dataset = "cipi"
        q = (qs.get("q") or qs.get("query") or [""])[0]
        limit_str = (qs.get("limit") or ["50"])[0]
        try:
            limit = max(1, min(100, int(limit_str)))
        except:
            limit = 50
        # normalize query (parse_qs already decodes)
        q = q or ""
        # Use "all" if requested
        if dataset == "all":
            results = search_pieces("all", q, limit=limit)
        else:
            results = search_pieces(dataset, q, limit=limit)
        self.send_json({
            "dataset": dataset,
            "query": q,
            "count": len(results),
            "results": results,
            "claim_boundaries": "labels are provenance only; output is symbolic-score evidence; no calibrated learner grade",
        })

    def handle_analyze(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_json({"error": f"Invalid JSON: {e}"}, status=400)
            return
        dataset = (payload.get("dataset") or "").lower().strip()
        if dataset not in ("cipi", "oktav"):
            self.send_json({"error": "dataset must be 'cipi' or 'oktav'"}, status=400)
            return
        # Find piece in index
        piece = find_piece_for_analyze(dataset, payload)
        if not piece:
            # Try to construct piece from payload directly if source_path provided
            # Allow direct source_path fallback for debugging
            direct_path = payload.get("source_path") or payload.get("sourcePath")
            if direct_path and Path(direct_path).is_file():
                piece = {
                    "dataset": dataset,
                    "piece_id": payload.get("piece_id") or payload.get("dataset_id") or Path(direct_path).stem,
                    "piece_uid": slugify(Path(direct_path).stem),
                    "composer": payload.get("composer") or "Unknown",
                    "title": payload.get("title") or Path(direct_path).stem,
                    "dataset_id": payload.get("dataset_id") or payload.get("piece_id") or "",
                    "dataset_relative_path": payload.get("dataset_relative_path") or Path(direct_path).name,
                    "source_path": direct_path,
                    "exists": True,
                }
            else:
                self.send_json({"error": "Piece not found. Check dataset, piece_id, dataset_relative_path. Use /api/pieces to discover.", "payload": payload}, status=404)
                return
        # Create job
        job_id = uuid.uuid4().hex[:12]
        safe = safe_piece_id(dataset, piece.get("piece_uid"), piece.get("dataset_relative_path"), piece.get("piece_id"))
        job = {
            "job_id": job_id,
            "jobId": job_id,
            "status": "queued",
            "dataset": dataset,
            "piece": piece,
            "safe_piece_id": safe,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "manifest_url": None,
            "artifact_dir": str(LIVE_BASE / safe),
            "error": None,
            "log": "",
        }
        with _jobs_lock:
            _jobs[job_id] = job
        # Start worker thread
        t = threading.Thread(target=run_analysis_job, args=(job_id,), daemon=True)
        t.start()
        self.send_json({
            "job_id": job_id,
            "jobId": job_id,
            "status": "queued",
            "safe_piece_id": safe,
            "dataset": dataset,
            "piece": {k: v for k, v in piece.items() if not k.startswith("_")},
            "poll_url": f"/api/jobs/{job_id}",
        }, status=202)

    def handle_job_get(self, job_id: str):
        with _jobs_lock:
            job = _jobs.get(job_id)
            if not job:
                self.send_json({"error": f"Job not found: {job_id}"}, status=404)
                return
            # copy for response
            resp = dict(job)
        # sanitize log length and ensure no control chars leak
        if len(resp.get("log") or "") > 8000:
            resp["log"] = resp["log"][-8000:]
        # final sanitize for any remaining piece fields that may contain control chars
        def _sanitize_val(v):
            if isinstance(v, str):
                return "".join(" " if (ord(c) < 32 and c not in ("\n", "\r", "\t")) else c for c in v)
            return v
        # sanitize piece strings if needed (light)
        if isinstance(resp.get("piece"), dict):
            resp["piece"] = {k: _sanitize_val(v) if isinstance(v, str) else v for k, v in resp["piece"].items()}
        self.send_json(resp)

    def handle_jobs_list(self):
        with _jobs_lock:
            jobs = list(_jobs.values())
        # return minimal
        self.send_json({"jobs": [{"job_id": j["job_id"], "status": j["status"], "dataset": j["dataset"], "safe_piece_id": j.get("safe_piece_id")} for j in jobs]})

    def handle_open_score(self):
        """POST /api/open-score — local-demo convenience: open canonical score in MuseScore.

        Body: { piece_id: str, source_score_path?: str }
        Validates that target resolves under DEMO_SOURCE_DIR or matches a known live job source_path.
        Launches MuseScore via `open -a MuseScore` (macOS) with fallback to known executables.
        """
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_json({"error": f"Invalid JSON: {e}"}, status=400)
            return
        if not isinstance(payload, dict):
            self.send_json({"error": "JSON body must be an object"}, status=400)
            return
        piece_id = str(payload.get("piece_id") or payload.get("pieceId") or "").strip()
        source_raw = str(payload.get("source_score_path") or payload.get("sourceScorePath") or payload.get("canonical_filename") or "").strip()

        target: Path | None = None

        # Prefer resolving via piece_id (server is source of truth)
        if piece_id:
            cand = _resolve_curated_path(piece_id)
            if cand is not None:
                target = cand
            else:
                # piece_id not in curated/live → if source_raw supplied, try that as fallback but still validate
                if source_raw:
                    cand2 = _resolve_source_score_path_raw(source_raw)
                    if cand2 and cand2.is_file() and _is_allowed_path(cand2):
                        # Only allow raw if it matches allowed location; do not trust arbitrary external path
                        target = cand2
                if target is None:
                    self.send_json({"error": f"Unknown piece_id '{piece_id}' — not in curated catalog or live jobs. Provide a valid curated piece_id or a live-analyzed piece_id.", "piece_id": piece_id}, status=404)
                    return
            # If both piece_id and source_raw supplied, ensure they agree when both resolve inside demo
            if source_raw and target is not None:
                cand_raw = _resolve_source_score_path_raw(source_raw)
                if cand_raw and cand_raw.is_file():
                    try:
                        if cand_raw.resolve() != target.resolve():
                            # If raw is allowed and target is also allowed but they differ → reject mismatch
                            # Allow if raw points to same file via different relative form? Already checked exact resolve equality.
                            self.send_json({"error": "source_score_path does not match canonical score for piece_id", "piece_id": piece_id, "canonical": str(target)}, status=400)
                            return
                    except Exception:
                        pass
        elif source_raw:
            cand = _resolve_source_score_path_raw(source_raw)
            if cand is None or not cand.is_file():
                self.send_json({"error": f"Could not resolve source_score_path '{source_raw}' to an existing file"}, status=404)
                return
            if not _is_allowed_path(cand):
                self.send_json({"error": "Path not in allowed demo score locations — must be under research/learning_support/ceo_demo/data/source_scores/ or a known live-analyzed score", "path": str(cand)}, status=403)
                return
            target = cand
        else:
            self.send_json({"error": "Missing piece_id or source_score_path — provide at least piece_id"}, status=400)
            return

        if target is None or not target.is_file():
            self.send_json({"error": f"Score file not found: {target}", "piece_id": piece_id}, status=404)
            return
        if not _is_allowed_path(target):
            self.send_json({"error": "Path not in allowed demo score locations — must be under research/learning_support/ceo_demo/data/source_scores/ or a known live-analyzed score", "path": str(target)}, status=403)
            return

        # Security: ensure path is not traversing outside allowed tree via raw param bypass (already checked)
        try:
            _launch_musescore(target)
        except Exception as e:
            self.send_json({"error": f"Failed to launch MuseScore: {e}", "path": str(target)}, status=500)
            return

        self.send_json({"ok": True, "opened": str(target), "piece_id": piece_id or None, "source_score_path": str(target)}, status=200)


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Run CEO demo live server (static + live analysis)")
    p.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8000, help="Port to bind (default 8000)")
    p.add_argument("--no-open", action="store_true", help="Do not try to open browser")
    return p.parse_args()


def main():
    args = parse_args()
    # ensure indexes eagerly if possible
    try:
        ensure_indexes()
    except Exception as e:
        print(f"[warn] Index preload failed: {e}", file=sys.stderr)
    LIVE_BASE.mkdir(parents=True, exist_ok=True)
    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, DemoHandler)
    url = f"http://{args.host}:{args.port}/research/learning_support/ceo_demo/web/"
    print(f"[ok] CEO demo live server serving repo root: {REPO_ROOT}")
    print(f"[ok] Static demo: {url}")
    print(f"[ok] API: http://{args.host}:{args.port}/api/datasets")
    print(f"[ok] CIPI root: {CIPI_ROOT} (exists={CIPI_ROOT.is_dir()})")
    print(f"[ok] Oktav root: {OKTAV_ROOT} (exists={OKTAV_ROOT.is_dir()})")
    print(f"[ok] Live artifacts: {LIVE_BASE}")
    print(f"[info] Claim boundaries: labels are provenance only; output is symbolic-score evidence; no calibrated learner grade; Oktav labels are not Gradus grades")
    if not args.no_open:
        # best-effort open
        try:
            import webbrowser
            webbrowser.open(url)
        except:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[info] Shutting down")
        httpd.shutdown()


if __name__ == "__main__":
    main()
