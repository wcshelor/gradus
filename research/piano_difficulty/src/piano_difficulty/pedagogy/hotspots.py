"""Hotspot generator v0.

Converts analysis_profiles[*].notable_measures, measure_summaries, and
high-value feature records into candidate PracticeHotspots with evidence.

Priority order:
  1. candidate_sections (merged peaks) — richest evidence
  2. factor_peaks / composite_peaks grouped by window_index
  3. fallback: top measure_summaries by feature count / density features
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from piano_difficulty.pedagogy.factors import factors_for_contributions, guess_factors_for_features
from piano_difficulty.pedagogy.models import DifficultyFactor, EvidenceRef, PracticeHotspot, HotspotOrigin, HotspotStatus


def _piece_id_from_result(analysis_result: Any) -> tuple[str | None, str | None]:
    score = getattr(getattr(analysis_result, "extraction", None), "score", None)
    if score is not None:
        path = str(score.source_path) if getattr(score, "source_path", None) is not None else None
        # piece_id is stable hash of source_path or title
        if path:
            return path, path
        title = getattr(score, "title", None)
        if title:
            return str(title), None
    # also try dict payload style
    if isinstance(analysis_result, dict):
        src = analysis_result.get("source", {})
        path = src.get("path") if isinstance(src, dict) else None
        return path, path
    return None, None


def _stable_hotspot_id(piece_id: str | None, measure_start: int, measure_end: int, window_index: int | None, extra: str = "") -> str:
    base = f"{piece_id or 'piece'}:m{measure_start}-{measure_end}:w{window_index if window_index is not None else 'x'}:{extra}"
    digest = hashlib.sha1(base.encode()).hexdigest()[:8]
    return f"hs:{measure_start}-{measure_end}:{digest}"


def _confidence_from_score(score: Any, max_score: float | None) -> float | None:
    if score is None or not isinstance(score, (int, float)):
        return None
    if max_score is None or max_score == 0:
        return max(0.0, min(1.0, float(score)))
    # normalize 0..1, clamp
    return max(0.0, min(1.0, float(score) / float(max_score)))


def generate_hotspots(
    analysis_result: Any,
    *,
    max_hotspots: int = 5,
    include_measure_fallback: bool = True,
) -> list[PracticeHotspot]:
    """Generate candidate hotspots from an AnalysisResult or payload dict.

    Works without learner history. Always returns list (possibly empty) and
    never mutates the input.
    """
    piece_id, source_path = _piece_id_from_result(analysis_result)

    # Extract analysis_profiles payload
    profiles: list[dict[str, Any]] = []
    if hasattr(analysis_result, "to_json_payload"):
        payload = analysis_result.to_json_payload()
        profiles = payload.get("analysis_profiles", []) if isinstance(payload, dict) else []
        measure_summaries = payload.get("measure_summaries", []) if isinstance(payload, dict) else []
        # also try to get source path from payload if missing
        if piece_id is None and isinstance(payload, dict):
            piece_id = payload.get("source", {}).get("path") if isinstance(payload.get("source"), dict) else None
            source_path = piece_id
    elif isinstance(analysis_result, dict):
        payload = analysis_result
        profiles = payload.get("analysis_profiles", [])
        measure_summaries = payload.get("measure_summaries", [])
    else:
        # raw ExtractionResult style: try attributes
        profiles = []
        measure_summaries = getattr(getattr(analysis_result, "extraction", None), "measure_summaries", []) or []
        if not isinstance(measure_summaries, list):
            measure_summaries = []

    # Find difficulty_overview profile if present
    overview: dict[str, Any] | None = None
    for prof in profiles:
        if isinstance(prof, dict) and prof.get("profile_id") == "difficulty_overview":
            overview = prof
            break
    if overview is None and profiles:
        # fallback to first profile that looks like overview
        for prof in profiles:
            if isinstance(prof, dict) and "candidate_sections" in prof:
                overview = prof
                break

    created_at = datetime.now(timezone.utc).isoformat()
    hotspots: list[PracticeHotspot] = []

    if overview is not None:
        candidate_sections: list[dict[str, Any]] = overview.get("candidate_sections", []) or []
        if candidate_sections:
            max_score = max((s.get("score", 0) for s in candidate_sections if isinstance(s.get("score"), (int, float))), default=None)
            for section in candidate_sections[:max_hotspots]:
                region = section.get("region", {}) if isinstance(section.get("region"), dict) else {}
                ms = region.get("measure_start")
                me = region.get("measure_end")
                if not isinstance(ms, int) or not isinstance(me, int):
                    continue
                measure_numbers = tuple(str(x) for x in region.get("measure_numbers", []) if isinstance(x, str) or isinstance(x, (int, float)))
                # fallback if measure_numbers empty
                if not measure_numbers:
                    measure_numbers = tuple(str(i) for i in range(ms, me + 1))
                window_index = region.get("window_index") if isinstance(region.get("window_index"), int) else None
                supporting_indices = section.get("supporting_window_indices", [])
                score = section.get("score")
                confidence = _confidence_from_score(score, max_score)
                # evidence: supporting windows + contributions
                evidence_refs: list[EvidenceRef] = []
                contributions: list[dict[str, Any]] = section.get("contributions", []) or []
                region_evidence: list[dict[str, Any]] = overview.get("region_evidence", []) or []
                # map window_index -> note_ids
                region_evidence_by_idx = {r.get("window_index"): r for r in region_evidence if isinstance(r, dict) and isinstance(r.get("window_index"), int)}
                for widx in supporting_indices:
                    if not isinstance(widx, int):
                        continue
                    rev = region_evidence_by_idx.get(widx, {})
                    note_ids = rev.get("logical_note_ids", []) if isinstance(rev, dict) else []
                    if not isinstance(note_ids, list):
                        note_ids = []
                    evidence_refs.append(EvidenceRef(evidence_id=f"region:{widx}", kind="region", window_index=widx, note_ids=tuple(str(x) for x in note_ids[:8])))
                for contrib in contributions[:4]:
                    fid = contrib.get("feature_id")
                    if isinstance(fid, str):
                        evidence_refs.append(EvidenceRef(evidence_id=f"contrib:{fid}:{window_index}", kind="feature_record", feature_id=fid, window_index=window_index))
                # deduplicate
                seen = set()
                deduped: list[EvidenceRef] = []
                for e in evidence_refs:
                    if e.evidence_id not in seen:
                        seen.add(e.evidence_id)
                        deduped.append(e)
                # suggested factors from contributions
                suggested = factors_for_contributions(contributions, top_n=3)
                # ensure evidence_ids linked
                enriched: list[DifficultyFactor] = []
                for factor in suggested:
                    # link evidence ids
                    ev_ids = tuple(e.evidence_id for e in deduped if e.feature_id in factor.source_feature_ids) or tuple(e.evidence_id for e in deduped[:2])
                    enriched.append(DifficultyFactor(factor_id=factor.factor_id, confidence=factor.confidence, evidence_ids=ev_ids, source_feature_ids=factor.source_feature_ids))
                if not enriched:
                    # fallback mapping from supporting_factor_ids
                    sup_fids = section.get("supporting_factor_ids", []) or []
                    if isinstance(sup_fids, list) and sup_fids:
                        enriched = guess_factors_for_features([str(x) for x in sup_fids if isinstance(x, str)])

                hid = _stable_hotspot_id(piece_id, ms, me, window_index, extra=str(score))
                hotspots.append(PracticeHotspot(
                    hotspot_id=hid,
                    piece_id=piece_id,
                    source_path=source_path,
                    measure_start=ms,
                    measure_end=me,
                    measure_numbers=measure_numbers,
                    window_index=window_index,
                    score_position=region.get("position") if isinstance(region.get("position"), (int, float)) else None,
                    confidence=confidence,
                    evidence=tuple(deduped),
                    suggested_factors=tuple(enriched),
                    status=HotspotStatus.candidate,
                    origin=HotspotOrigin.auto,
                    created_at=created_at,
                    diagnostics=(),
                ))
            if hotspots:
                return hotspots[:max_hotspots]

        # fallback: peaks grouped by window
        factor_peaks: list[dict[str, Any]] = overview.get("factor_peaks", []) or []
        composite_peaks: list[dict[str, Any]] = overview.get("composite_peaks", []) or []
        all_peaks = factor_peaks + composite_peaks
        if all_peaks:
            # group by window_index via region.window_index
            from collections import defaultdict
            peaks_by_window: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for peak in all_peaks:
                region = peak.get("region", {}) if isinstance(peak.get("region"), dict) else {}
                widx = region.get("window_index")
                if isinstance(widx, int):
                    peaks_by_window[widx].append(peak)
            # sort windows by best value desc
            def best_val(peaks: list[dict[str, Any]]) -> float:
                vals = [p.get("value", 0) for p in peaks if isinstance(p.get("value"), (int, float))]
                return max(vals) if vals else 0.0
            sorted_windows = sorted(peaks_by_window.items(), key=lambda kv: -best_val(kv[1]))
            region_by_widx: dict[int, dict[str, Any]] = {}
            for r in overview.get("regions", []) or []:
                if isinstance(r, dict) and isinstance(r.get("window_index"), int):
                    region_by_widx[r["window_index"]] = r
            region_evidence_by_idx = {r.get("window_index"): r for r in (overview.get("region_evidence", []) or []) if isinstance(r, dict) and isinstance(r.get("window_index"), int)}
            max_val = max((best_val(p) for _, p in sorted_windows), default=None)
            for widx, peaks in sorted_windows[:max_hotspots]:
                region = region_by_widx.get(widx, {})
                ms = region.get("measure_start")
                me = region.get("measure_end")
                if not isinstance(ms, int) or not isinstance(me, int):
                    # try peak region
                    if peaks:
                        pr = peaks[0].get("region", {}) if isinstance(peaks[0].get("region"), dict) else {}
                        ms = pr.get("measure_start")
                        me = pr.get("measure_end")
                    if not isinstance(ms, int) or not isinstance(me, int):
                        continue
                measure_numbers = tuple(str(x) for x in region.get("measure_numbers", []) ) if isinstance(region.get("measure_numbers"), list) else tuple(str(i) for i in range(ms, me+1))
                if not measure_numbers:
                    measure_numbers = tuple(str(i) for i in range(ms, me+1))
                confidence = _confidence_from_score(best_val(peaks), max_val)
                feature_ids = [p.get("contributing_feature_id") for p in peaks if isinstance(p.get("contributing_feature_id"), str)]
                evidence_refs = []
                rev = region_evidence_by_idx.get(widx, {})
                note_ids = rev.get("logical_note_ids", []) if isinstance(rev, dict) else []
                if isinstance(note_ids, list) and note_ids:
                    evidence_refs.append(EvidenceRef(evidence_id=f"region:{widx}", kind="region", window_index=widx, note_ids=tuple(str(x) for x in note_ids[:8])))
                for fid in feature_ids[:3]:
                    evidence_refs.append(EvidenceRef(evidence_id=f"peak:{fid}:{widx}", kind="feature_record", feature_id=fid, window_index=widx))
                suggested = guess_factors_for_features([str(x) for x in feature_ids if isinstance(x, str)])
                hid = _stable_hotspot_id(piece_id, ms, me, widx, extra="peak")
                hotspots.append(PracticeHotspot(
                    hotspot_id=hid,
                    piece_id=piece_id,
                    source_path=source_path,
                    measure_start=ms,
                    measure_end=me,
                    measure_numbers=measure_numbers,
                    window_index=widx,
                    score_position=region.get("position") if isinstance(region.get("position"), (int, float)) else None,
                    confidence=confidence,
                    evidence=tuple(evidence_refs),
                    suggested_factors=tuple(suggested),
                    status=HotspotStatus.candidate,
                    origin=HotspotOrigin.auto,
                    created_at=created_at,
                    diagnostics=(),
                ))
            if hotspots:
                return hotspots[:max_hotspots]

    # final fallback: measure_summaries
    if include_measure_fallback and measure_summaries:
        # rank measures by feature count or density-like values
        def measure_score(msumm: dict[str, Any]) -> float:
            feats = msumm.get("features", [])
            if not isinstance(feats, list):
                return 0.0
            # boost if texture/density features high? simplified: count + max numeric value
            count = len(feats)
            max_val = 0.0
            for f in feats:
                if isinstance(f, dict):
                    v = f.get("value")
                    if isinstance(v, (int, float)):
                        max_val = max(max_val, float(v))
            return count * 0.1 + max_val * 0.01

        ranked = sorted(measure_summaries, key=lambda m: -measure_score(m) if isinstance(m, dict) else 0)
        # take top unique measure indices
        for msumm in ranked[:max_hotspots]:
            if not isinstance(msumm, dict):
                continue
            midx = msumm.get("measure_index")
            if not isinstance(midx, int):
                continue
            ms = midx
            me = midx
            feature_ids = []
            for feat in msumm.get("features", []) or []:
                if isinstance(feat, dict) and isinstance(feat.get("feature_id"), str):
                    feature_ids.append(feat["feature_id"])
            # use 1-based measure numbers (printed numbers often 1-based; fallback to index+1)
            measure_numbers = (str(midx),)
            evidence_refs = [EvidenceRef(evidence_id=f"measure:{midx}", kind="measure_summary", feature_id=fid) for fid in feature_ids[:3]]
            suggested = guess_factors_for_features(feature_ids[:3])
            hid = _stable_hotspot_id(piece_id, ms, me, None, extra=f"ms:{midx}")
            confidence = 0.4  # fallback low confidence
            hotspots.append(PracticeHotspot(
                hotspot_id=hid,
                piece_id=piece_id,
                source_path=source_path,
                measure_start=ms,
                measure_end=me,
                measure_numbers=measure_numbers,
                window_index=None,
                score_position=None,
                confidence=confidence,
                evidence=tuple(evidence_refs),
                suggested_factors=tuple(suggested),
                status=HotspotStatus.candidate,
                origin=HotspotOrigin.auto,
                created_at=created_at,
                diagnostics=("fallback: measure_summary",),
            ))
        return hotspots[:max_hotspots]

    return hotspots
