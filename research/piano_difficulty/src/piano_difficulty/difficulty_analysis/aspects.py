"""Experimental difficulty aspects profile grouped from existing runtime features.

Primary temporal analysis model: per-aspect windowed series, aspect composite,
and aspect-ranked hotspots with nested feature contributors. Remains relative
symbolic-score evidence — no calibrated grade. Aspects 8 and 9 are explicitly
blocked/caveated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Aspect definitions ordered 1-9 per taxonomy.
# Each entry defines grouping rules and documentation.
_ASPECT_DEFINITIONS = (
    {
        "aspect_id": "rhythmic_demand",
        "label": "Rhythmic demand",
        "readiness": "ready",
        "description": "Temporal precision, subdivision variety, and density as notated.",
        "feature_ids": (
            "rhythm.note_density",
            "rhythm.attack_density",
            "rhythm.shortest_written_duration",
            "rhythm.tuplet_count",
            "rhythm.duration_value_ratio",
            "rhythm.significant_shortest_value",
            "rhythm.asymmetric_tuplet_measure_ratio",
            "rhythm.polyrhythm_measure_ratio",
            "rhythm.polyrhythm_flag",
            "metadata.tempo_change_count",
            "metadata.meter_change_count",
            "metadata.key_change_count",
            "statistics.duration_mean",
            "statistics.duration_std",
            "statistics.duration_variability",
            "metadata.primary_tempo",
            "metadata.length_quarters",
        ),
        "feature_prefixes": ("rhythm.",),
        "missing_features": [
            "Syncopation / off-beat stress beyond polyrhythm/tuplet flags",
            "Nested or changing subdivisions within a measure",
            "Explicit hemiola or cross-rhythm typing",
            "Duration-distribution entropy as distinct descriptor",
        ],
        "limitations": [
            "Written durations only; no performed timing, rubato, or tempo realization.",
            "Tuplet and polyrhythm heuristics depend on MusicXML encoding quality.",
            "attack_density is the reviewed factor; other rhythm descriptors are unweighted traces.",
        ],
    },
    {
        "aspect_id": "pitch_movement_demand",
        "label": "Pitch / movement demand",
        "readiness": "ready",
        "description": "Distance and frequency of relocations between pitch regions between onsets.",
        "feature_ids": (
            "leaps.mean_melodic_leap",
            "leaps.max_melodic_leap",
            "leaps.count_ge_5",
            "leaps.count_ge_8",
            "leaps.count_ge_12",
            "leaps.timed_difficult_displacement_ratio",
            "leaps.max_timed_difficult_displacement",
            "leaps.timed_difficult_displacement_count",
            "metadata.pitch_range",
            "statistics.pitch_mean",
            "statistics.pitch_std",
            "statistics.pitch_entropy",
            "statistics.deviation_from_c4",
            "statistics.pitch_variability",
        ),
        "feature_prefixes": ("leaps.",),
        "missing_features": [
            "Direction-aware leap cost (outward vs return)",
            "Fingering-conditioned movement cost (requires fingering annotation)",
            "Register-specific movement penalty",
        ],
        "limitations": [
            "Closest pitch-set distance is a proxy, not physical hand travel.",
            "Gap-weighted displacement uses onset-gap model, not key-to-key kinematics.",
        ],
    },
    {
        "aspect_id": "hand_shape_span_demand",
        "label": "Hand-shape / span demand",
        "readiness": "partial",
        "description": "Instantaneous hand extension or awkward vertical shaping within a simultaneous onset.",
        "feature_ids": (
            "pitch_geometry.max_simultaneity_span",
            "pitch_geometry.mean_simultaneity_span",
            "pitch_geometry.register_range",
            "statistics.black_key_rate",
            "statistics.triad_count",
            "statistics.seventh_chord_count",
            "statistics.ninth_chord_count",
        ),
        "feature_prefixes": ("pitch_geometry.",),
        "missing_features": [
            "Interval-specific span cost (octave vs ninth vs cluster)",
            "Sustained-span burden (held notes while new notes added)",
            "Ergonomic weighting by hand size (learner-dependent)",
        ],
        "limitations": [
            "Span is hand-local and attack-local; excludes already-sustaining pitches.",
            "Hand inference is staff-based and conservative.",
            "max_simultaneity_span is reviewed; others are descriptive traces.",
        ],
    },
    {
        "aspect_id": "texture_polyphony_demand",
        "label": "Texture / polyphony demand",
        "readiness": "ready",
        "description": "Concurrent voices/notes per unit time and vertical density.",
        "feature_ids": (
            "texture.notes_per_onset",
            "texture.simultaneity_density",
            "texture.vertical_density_proxy",
            "texture.chord_count",
            "texture.chord_ratio",
            "texture.octave_chord_ratio",
            "statistics.polyphony_rate",
            "statistics.triad_count",
            "statistics.seventh_chord_count",
            "statistics.ninth_chord_count",
        ),
        "feature_prefixes": ("texture.",),
        "missing_features": [
            "Voice-count trajectory (2-voice vs 3-voice changes within piece)",
            "Independent voice-leading difficulty (counterpoint vs block chords)",
        ],
        "limitations": [
            "Global onset grouping approximates simultaneity; engraving timing variations can blur it.",
            "Vertical density proxy is duration-based average, not per-window curve.",
            "Excluded from difficulty_overview.v1 to avoid correlated span/density signals; eligible as descriptive bucket here.",
        ],
    },
    {
        "aspect_id": "coordination_demand",
        "label": "Coordination demand",
        "readiness": "ready",
        "description": "Independence of the two hands in time, aligned vs asynchronous attacks and subdivision mismatch.",
        "feature_ids": (
            "coordination.aligned_hand_onset_count",
            "coordination.asynchronous_hand_onset_count",
            "coordination.aligned_hand_onset_ratio",
            "coordination.subdivision_mismatch_proxy",
        ),
        "feature_prefixes": ("coordination.",),
        "missing_features": [
            "Hand-role complexity (melody vs accompaniment independence)",
            "Antiphase or canon-like hand timing typing",
        ],
        "limitations": [
            "subdivision_mismatch_proxy is explicitly a proxy; different onset patterns are not uniformly difficult.",
            "Coordination is only computed on the combined view; hand-filtered profiles exclude it.",
        ],
    },
    {
        "aspect_id": "notation_reading_demand",
        "label": "Notation / reading demand",
        "readiness": "ready",
        "description": "Decoding effort imposed by notation itself: accidentals, clef changes, cross-staff, ledger lines.",
        "feature_ids": (
            "notation.accidental_density",
            "notation.accidental_count",
            "notation.accidental_ratio",
            "notation.clef_change_count",
            "notation.cross_staff_note_count",
            "notation.ledger_line_burden",
            "metadata.key_change_count",
            "statistics.black_key_rate",
            "metadata.key_signature",
        ),
        "feature_prefixes": ("notation.",),
        "missing_features": [
            "Key-signature distance / enharmonic spelling cost",
            "Ornament and grace-note reading load",
            "8va/8vb and other staff-shorthand cost",
        ],
        "limitations": [
            "Accidental density does not model learner reading familiarity.",
            "Cross-staff detection limited to explicit MusicXML conflicts in ScoreIR.",
            "Ledger-line burden assumes standard piano clefs when declarations absent.",
        ],
    },
    {
        "aspect_id": "expression_control_demand",
        "label": "Expression / control demand",
        "readiness": "partial",
        "description": "Fine control of tone, articulation, and dynamics explicitly asked by written instructions.",
        "feature_ids": (
            "expression.articulated_note_ratio",
            "expression.articulation_density",
            "expression.staccato_note_ratio",
            "expression.accent_note_ratio",
            "expression.strong_accent_note_ratio",
            "expression.tenuto_note_ratio",
            "expression.dynamic_marking_count",
            "expression.dynamic_marking_rate",
            "expression.dynamic_change_count",
            "expression.dynamic_range_span",
            "expression.wedge_start_count",
            "expression.crescendo_start_count",
            "expression.diminuendo_start_count",
            "expression.staff_specific_dynamic_ratio",
        ),
        "feature_prefixes": ("expression.",),
        "missing_features": [
            "Pedal demand (sustain/una corda) — MusicXML encoding inconsistent",
            "Phrase-level legato / slur burden beyond single-note flags",
            "Voicing / balance indications (e.g., cantabile over accompaniment)",
        ],
        "limitations": [
            "Only explicitly encoded articulations and dynamics are counted; interpretive nuance beyond score not inferred.",
            "Dynamic ordinals are coarse symbolic ordering, not loudness prediction.",
            "No demand-direction ranking claimed — more markings do not uniformly mean harder.",
        ],
    },
    {
        "aspect_id": "structural_pattern_demand",
        "label": "Structural / pattern demand",
        "readiness": "blocked",
        "description": "Larger organization — repetition, pattern regularity, formal boundaries, predictability.",
        "feature_ids": (
            "metadata.measure_count",
            "metadata.note_count",
            "metadata.page_count",
            "metadata.length_quarters",
        ),
        "feature_prefixes": (),
        "missing_features": [
            "Repetition / recurrence rate (exact or transposed)",
            "Sequence / pattern regularity (n-gram, motivic reuse)",
            "Formal boundary complexity (section counts/irregularity)",
            "Harmonic / pitch predictability (entropy over pitch classes, chord transitions)",
            "Length-normalized novelty (new material per quarter)",
            "Structural pacing (re-scoped playing_speed_variation)",
        ],
        "limitations": [
            "Primary extractor gap: no validated repetition or form extractor is promoted yet.",
            "measure_count and note_count are contextual metadata only, not difficulty ranks.",
            "Any structural descriptor needs operational definition before ranking; repetition may help some learners.",
        ],
    },
    {
        "aspect_id": "performance_interpretive_demand",
        "label": "Performance / interpretive demand",
        "readiness": "caveated",
        "description": "Demands partly encoded in score and heavily learner-dependent: tone, velocity, voicing, timing nuance.",
        "feature_ids": (
            # Proxies only — not quantified performance
            "expression.articulated_note_ratio",
            "expression.articulation_density",
            "expression.staccato_note_ratio",
            "expression.accent_note_ratio",
            "expression.strong_accent_note_ratio",
            "expression.tenuto_note_ratio",
            "expression.dynamic_marking_count",
            "expression.dynamic_marking_rate",
            "expression.dynamic_change_count",
            "expression.dynamic_range_span",
            "expression.wedge_start_count",
            "expression.crescendo_start_count",
            "expression.diminuendo_start_count",
            "expression.staff_specific_dynamic_ratio",
            "metadata.tempo_change_count",
        ),
        "feature_prefixes": (),
        "missing_features": [
            "pressing_velocity_entropy (blocked — likely needs performance/MIDI data)",
            "pressing_velocity_variability (blocked — likely needs performance/MIDI data)",
            "melodic_complexity (blocked — MC family, formula not reconstructed)",
            "melodic_originality (blocked — MC family, formula not reconstructed)",
            "degree_of_melodiousness (blocked — MC family, formula not reconstructed)",
            "Score→performance mappings (timing micro-variation, voicing balance, pedal realization)",
            "Learner-dependent moderators: hand size, experience, practice strategy, reading fluency",
        ],
        "limitations": [
            "Caveated: score alone cannot determine pressing velocity or interpretive nuance.",
            "Partially observable, learner-dependent; needs performance/MIDI or teacher/learner evidence for validation.",
            "Uses only written proxies (dynamics/articulations, tempo changes); not actual performance interpretation.",
            "No cross-aspect weights or calibrated difficulty grade claimed.",
        ],
    },
)

# Temporal feature IDs that are windowable and used for per-aspect series.
# Excludes piece-level metadata except pitch_range which is windowable via measure range.
TEMPORAL_FEATURE_IDS = (
    "rhythm.note_density",
    "rhythm.attack_density",
    "rhythm.shortest_written_duration",
    "rhythm.tuplet_count",
    "rhythm.significant_shortest_value",
    "rhythm.asymmetric_tuplet_measure_ratio",
    "rhythm.polyrhythm_measure_ratio",
    "rhythm.polyrhythm_flag",
    "leaps.mean_melodic_leap",
    "leaps.max_melodic_leap",
    "leaps.count_ge_5",
    "leaps.count_ge_8",
    "leaps.count_ge_12",
    "leaps.timed_difficult_displacement_ratio",
    "leaps.max_timed_difficult_displacement",
    "leaps.timed_difficult_displacement_count",
    "metadata.pitch_range",
    "pitch_geometry.max_simultaneity_span",
    "pitch_geometry.mean_simultaneity_span",
    "pitch_geometry.register_range",
    "texture.notes_per_onset",
    "texture.simultaneity_density",
    "texture.vertical_density_proxy",
    "texture.chord_count",
    "texture.chord_ratio",
    "texture.octave_chord_ratio",
    "coordination.aligned_hand_onset_count",
    "coordination.asynchronous_hand_onset_count",
    "coordination.aligned_hand_onset_ratio",
    "coordination.subdivision_mismatch_proxy",
    "notation.accidental_density",
    "notation.accidental_count",
    "notation.accidental_ratio",
    "notation.clef_change_count",
    "notation.cross_staff_note_count",
    "notation.ledger_line_burden",
    "expression.articulated_note_ratio",
    "expression.articulation_density",
    "expression.staccato_note_ratio",
    "expression.accent_note_ratio",
    "expression.strong_accent_note_ratio",
    "expression.tenuto_note_ratio",
    "expression.dynamic_marking_count",
    "expression.dynamic_marking_rate",
    "expression.dynamic_change_count",
    "expression.dynamic_range_span",
    "expression.wedge_start_count",
    "expression.crescendo_start_count",
    "expression.diminuendo_start_count",
    "expression.staff_specific_dynamic_ratio",
)


def _summarize_feature(record) -> dict:
    """Lightweight summary for one FeatureRecord."""
    return {
        "feature_id": record.feature_id,
        "scope": record.scope,
        "scope_ref": record.scope_ref,
        "value": record.value,
        "units": record.units,
        "reliability": record.reliability,
        "source_span": dict(record.source_span) if isinstance(record.source_span, dict) else record.source_span,
        "diagnostics": list(record.diagnostics) if record.diagnostics else [],
    }


def _matches_aspect(feature_id: str, aspect_def: dict) -> bool:
    if feature_id in aspect_def["feature_ids"]:
        return True
    for prefix in aspect_def.get("feature_prefixes", ()):
        if feature_id.startswith(prefix):
            return True
    return False


@dataclass
class DifficultyAspectsResult:
    payload: dict

    def to_payload(self):
        return self.payload


class DifficultyAspectsProfile:
    profile_id = "difficulty_aspects"
    profile_version = "1"

    def analyze(self, extraction, options=None):
        # Reuse existing runtime FeatureRecords already produced by extract_all
        features = list(extraction.features)

        # Build lookup for deterministic grouping (static)
        aspects_payload = []
        assigned_ids = set()

        for aspect_def in _ASPECT_DEFINITIONS:
            matched = [rec for rec in features if _matches_aspect(rec.feature_id, aspect_def)]
            matched_sorted = sorted(matched, key=lambda r: (r.feature_id, r.scope, r.scope_ref))
            summaries = [_summarize_feature(r) for r in matched_sorted]
            included_ids = sorted({rec.feature_id for rec in matched})
            assigned_ids.update(included_ids)
            readiness = aspect_def["readiness"]
            status = readiness
            if aspect_def["aspect_id"] == "structural_pattern_demand":
                availability = "contextual"
                if readiness not in ("blocked", "missing"):
                    status = "blocked"
            elif aspect_def["aspect_id"] == "performance_interpretive_demand":
                availability = "caveated"
            elif readiness == "partial":
                availability = "partial"
            elif readiness == "ready":
                availability = "available"
            else:
                availability = readiness
            aspect_payload = {
                "aspect_id": aspect_def["aspect_id"],
                "id": aspect_def["aspect_id"],
                "name": aspect_def["label"],
                "label": aspect_def["label"],
                "readiness": readiness,
                "status": status,
                "availability": availability,
                "description": aspect_def["description"],
                "included_feature_ids": included_ids,
                "feature_ids": included_ids,
                "missing_features": list(aspect_def["missing_features"]),
                "missing_feature_notes": list(aspect_def["missing_features"]),
                "future_features": list(aspect_def["missing_features"]),
                "limitations": list(aspect_def["limitations"]),
                "caveats": list(aspect_def["limitations"]),
                "diagnostics": list(aspect_def["limitations"]),
                "features": summaries,
                "feature_summaries": summaries,
            }
            if readiness == "blocked":
                aspect_payload["blocked"] = True
                aspect_payload["is_blocked"] = True
            if readiness == "caveated":
                aspect_payload["caveated"] = True
                aspect_payload["is_caveated"] = True
            aspects_payload.append(aspect_payload)

        # Temporal aspect series, composite and hotspots
        temporal = _build_temporal_aspect_data(extraction, options)

        payload = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "schema_version": "difficulty_aspects.v1",
            "interpretation": "Grouped descriptive traces by difficulty aspect; no cross-aspect weights and no calibrated difficulty grade.",
            "aspect_count": len(aspects_payload),
            "aspects": aspects_payload,
            "diagnostics": [
                "Aspects are descriptive buckets, not a ranked composite.",
                "Aspect 8 (structural/pattern) is blocked: no pattern extractor yet; only contextual counts available.",
                "Aspect 9 (performance/interpretive) is caveated: partially observable from score, learner-dependent.",
                "All feature values reuse existing runtime extraction (extract_all); no new weights or formulas introduced.",
                "Temporal aspect series are mean of feature normalized traces per window; blocked aspects have no temporal signal.",
                "Aspect hotspots are ranked from aspect-composite demand; each hotspot lists aspect contributors with nested feature contributors.",
            ],
            "warnings": [
                "No global weighted composite is computed in this profile.",
                "Do not compare aspects as calibrated grades without external validation.",
                "Aspect composite is descriptive mean of aspect signals excluding blocked; not a validated difficulty grade.",
            ],
        }

        if temporal is not None:
            payload["regions"] = temporal["regions_payload"]
            payload["series"] = temporal["series"]
            payload["aspect_series"] = temporal["series"]
            payload["composite"] = temporal["composite"]
            payload["overall_series"] = temporal["composite"]
            payload["candidate_sections"] = temporal["hotspots"]
            payload["hotspots"] = temporal["hotspots"]
            payload["aspect_hotspots"] = temporal["hotspots"]
            payload["methods"] = temporal["methods"]
            payload["chart"] = {
                "regions": temporal["regions_payload"],
                "series": temporal["series"],
                "composite": temporal["composite"],
                "aspect_ids": temporal["aspect_ids"],
                "factor_ids": temporal["aspect_ids"],
            }
            # Add readiness diagnostics for blocked/caveated
            payload["diagnostics"].append(
                "Blocked aspect (structural_pattern_demand) produces no temporal trace; caveated aspect (performance_interpretive_demand) uses written proxies only."
            )

            # --- Front-facing graph taxonomy layer (additive, presentation layer) ---
            try:
                from piano_difficulty.difficulty_analysis.front_graph_taxonomy import (
                    GRAPH_DIMENSION_IDS,
                    GRAPH_TAXONOMY_VERSION,
                    FEATURE_TO_DIMENSION_WEIGHTS,
                    get_graph_dimensions,
                    compute_graph_series,
                )

                feature_series_for_graph = temporal.get("feature_series") or {}
                regions_for_graph = temporal.get("regions") or []
                hand_mode_for_graph = temporal.get("methods", {}).get("hand_mode", "both")
                try:
                    # Prefer hand_mode from temporal methods
                    hand_mode_for_graph = temporal["methods"].get("hand_mode", hand_mode_for_graph)
                except Exception:
                    pass
                graph_series, per_window_contributors, graph_composite = compute_graph_series(
                    feature_series_for_graph,
                    regions_for_graph,
                    hand_mode=hand_mode_for_graph,
                )

                # Build graph hotspots ranked by graph composite (mirrors aspect hotspots)
                graph_hotspots = []
                try:
                    composite_norm_for_graph = graph_composite.get("normalized_values") or []
                    indexed_g = [(i, v) for i, v in enumerate(composite_norm_for_graph) if v is not None]
                    indexed_g.sort(key=lambda x: x[1], reverse=True)
                    top_n_g = int(temporal.get("methods", {}).get("window", {}).get("size", 5))  # fallback
                    # Use same top_sections as aspect hotspots length
                    top_n_g = len(temporal.get("hotspots") or []) or 5
                    top_g = indexed_g[:top_n_g]
                    # Need region payloads
                    regions_payload_g = temporal.get("regions_payload") or []
                    # For refined metadata helpers
                    score_for_graph = extraction.score
                    for rank_g, (win_idx_g, comp_val_g) in enumerate(sorted(top_g, key=lambda x: x[1], reverse=True), start=1):
                        # Use region payload if available
                        try:
                            region_obj = regions_for_graph[win_idx_g]
                            from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload as _rtp

                            region_payload_g = _rtp(region_obj)
                        except Exception:
                            region_payload_g = regions_payload_g[win_idx_g] if win_idx_g < len(regions_payload_g) else {}
                        # Rank dimensions by their normalized value at this window
                        dim_contribs = []
                        for dim_id, series_g in graph_series.items():
                            v = series_g["normalized_values"][win_idx_g] if win_idx_g < len(series_g["normalized_values"]) else None
                            if v is None:
                                continue
                            dim_contribs.append((dim_id, float(v), series_g.get("label") or dim_id))
                        dim_contribs.sort(key=lambda x: x[1], reverse=True)
                        total_pos_g = sum(v for _, v, _ in dim_contribs if v > 0) or 1.0
                        dim_payloads = []
                        for c_rank, (dim_id, val, label) in enumerate(dim_contribs, start=1):
                            contribs_for_dim = per_window_contributors[win_idx_g].get(dim_id, []) if win_idx_g < len(per_window_contributors) else []
                            share = (max(val, 0) / total_pos_g) if total_pos_g else None
                            dim_payloads.append(
                                {
                                    "dimension_id": dim_id,
                                    "graph_dimension_id": dim_id,
                                    "feature_id": dim_id,
                                    "id": dim_id,
                                    "label": label,
                                    "feature_name": label,
                                    "raw_value": val,
                                    "normalized_value": val,
                                    "smoothed_value": val,
                                    "weighted_value": val,
                                    "contribution_share": share,
                                    "rank": c_rank,
                                    "is_peak_support": c_rank <= 3,
                                    "feature_contributors": contribs_for_dim,
                                    "supporting_feature_contributors": contribs_for_dim,
                                    "graph_contributors": contribs_for_dim,
                                    "units": "normalized_score",
                                }
                            )
                        # Collect distinct local causes across dimensions for this window
                        all_feat_ids = []
                        for d_payload in dim_payloads:
                            for fc in d_payload.get("feature_contributors", []):
                                all_feat_ids.append(fc["feature_id"])
                        distinct_local_causes_g = sorted(set(all_feat_ids))
                        # Build local_causes list (feature-level)
                        local_causes_g = []
                        seen = {}
                        for d_payload in dim_payloads:
                            for fc in d_payload.get("feature_contributors", []):
                                key = fc["feature_id"]
                                # record window_index, feature_id
                                entry = {
                                    "window_index": int(win_idx_g),
                                    "feature_id": fc["feature_id"],
                                    "rank": int(fc.get("rank", 1)),
                                    "contribution_share": fc.get("contribution_share"),
                                    "normalized_value": fc.get("normalized_value"),
                                    "raw_value": fc.get("raw_value"),
                                    "graph_dimension_id": d_payload["dimension_id"],
                                }
                                local_causes_g.append(entry)
                                if key not in seen:
                                    seen[key] = []
                                seen[key].append(win_idx_g)

                        # Refined section metadata enrichment (explanatory, optional)
                        setup_indices_g: list[int] = []
                        continuation_indices_g: list[int] = []
                        is_single_hand_window_g = False
                        hand_tempering_g = None
                        has_mosso_tempo_g = False
                        tempo_texts_g: list[str] = []
                        tempo_influence_g = None
                        try:
                            # single-hand check via coordination proxy
                            from piano_difficulty.features.coordination import is_single_hand_active

                            region_obj_for_meta = regions_for_graph[win_idx_g] if win_idx_g < len(regions_for_graph) else None
                            if region_obj_for_meta is not None and hasattr(region_obj_for_meta, "start_offset"):
                                is_single_hand_window_g = is_single_hand_active(
                                    score_for_graph, region_obj_for_meta.start_offset, region_obj_for_meta.end_offset
                                )
                            if is_single_hand_window_g:
                                hand_tempering_g = {"applied": True, "tempered_factor": "rhythm.attack_density", "factor": 0.6, "note": "rhythm tempered (single-hand active, factor 0.6)"}
                        except Exception:
                            pass
                        try:
                            from piano_difficulty.features.expression import collect_mosso_texts_for_region, has_mosso_in_region

                            region_obj_for_meta = regions_for_graph[win_idx_g] if win_idx_g < len(regions_for_graph) else None
                            if region_obj_for_meta is not None:
                                has_mosso_tempo_g = has_mosso_in_region(
                                    score_for_graph,
                                    getattr(region_obj_for_meta, "start_offset", None),
                                    getattr(region_obj_for_meta, "end_offset", None),
                                    measure_start=getattr(region_obj_for_meta, "measure_start", None),
                                    measure_end=getattr(region_obj_for_meta, "measure_end", None),
                                )
                                if has_mosso_tempo_g:
                                    tempo_texts_g = collect_mosso_texts_for_region(
                                        score_for_graph,
                                        getattr(region_obj_for_meta, "start_offset", None),
                                        getattr(region_obj_for_meta, "end_offset", None),
                                        measure_start=getattr(region_obj_for_meta, "measure_start", None),
                                        measure_end=getattr(region_obj_for_meta, "measure_end", None),
                                    )
                                    tempo_influence_g = "mosso-style tempo text in region; local explanation includes tempo context"
                        except Exception:
                            pass

                        # snippet fields for graph hotspot (reuse region's snippet logic)
                        _snippet_measure_numbers_g = list(region_payload_g.get("measure_numbers", [])) if isinstance(region_payload_g, dict) else []
                        _snippet_range_g = region_payload_g.get("measure_index_range") or region_payload_g.get("measure_range") or ""
                        hotspot_g = {
                            "hotspot_id": f"graph:{score_for_graph.source_path or 'score'}:{win_idx_g}",
                            "id": f"graph_section:both:{region_payload_g.get('start_offset')}:{region_payload_g.get('end_offset')}",
                            "section_id": f"graph_section:both:{region_payload_g.get('start_offset')}:{region_payload_g.get('end_offset')}",
                            "rank": rank_g,
                            "window_index": win_idx_g,
                            "measure_start": region_payload_g.get("measure_start"),
                            "measure_end": region_payload_g.get("measure_end"),
                            "measure_numbers": list(region_payload_g.get("measure_numbers", [])),
                            "measure_range": region_payload_g.get("measure_numbers", ["unknown"])[-1] if False else (f"{region_payload_g.get('measure_numbers', ['unknown'])[0]}-{region_payload_g.get('measure_numbers', ['unknown'])[-1]}" if len(region_payload_g.get("measure_numbers", [])) >= 2 else (region_payload_g.get("measure_numbers", ["unknown"])[0] if region_payload_g.get("measure_numbers") else "unknown")),
                            "label": region_payload_g.get("label") or f"Measures {'-'.join(region_payload_g.get('measure_numbers', [])) if region_payload_g.get('measure_numbers') else 'unknown'}",
                            "region": region_payload_g,
                            "representative_region": region_payload_g,
                            "score_value": comp_val_g,
                            "score": comp_val_g,
                            "method": "graph_composite_top_n.v1",
                            "supporting_dimension_ids": [c["dimension_id"] for c in dim_payloads],
                            "supporting_window_indices": [win_idx_g],
                            "supporting_feature_ids": distinct_local_causes_g,
                            "dimension_contributors": dim_payloads,
                            "graph_dimension_contributors": dim_payloads,
                            "top_contributors": dim_payloads,
                            "contributions": dim_payloads,
                            "feature_contributions": dim_payloads,
                            "start_offset": region_payload_g.get("start_offset"),
                            "end_offset": region_payload_g.get("end_offset"),
                            "score_position": region_payload_g.get("position"),
                            "snippet_image": None,
                            "snippet_status": "not_requested",
                            "snippet_diagnostic": "Snippet not pre-rendered; run pre-render script to generate snippets/window_<index>__measures_<range>.png.",
                            "snippet_measure_numbers": _snippet_measure_numbers_g,
                            "snippet_measure_index_range": _snippet_range_g,
                            "snippet_window_index": win_idx_g,
                            # refined explanatory metadata
                            "local_causes": local_causes_g,
                            "distinct_local_causes": distinct_local_causes_g,
                            "distinct_local_cause_count": len(distinct_local_causes_g),
                            "setup_window_indices": setup_indices_g,
                            "continuation_window_indices": continuation_indices_g,
                            "is_single_hand_window": is_single_hand_window_g,
                            "has_mosso_tempo": has_mosso_tempo_g,
                            "tempo_texts": tempo_texts_g,
                        }
                        if hand_tempering_g is not None:
                            hotspot_g["hand_tempering"] = hand_tempering_g
                        if tempo_influence_g is not None:
                            hotspot_g["tempo_influence"] = tempo_influence_g
                        graph_hotspots.append(hotspot_g)
                except Exception:
                    graph_hotspots = []

                front_graph_payload = {
                    "version": GRAPH_TAXONOMY_VERSION,
                    "taxonomy_version": GRAPH_TAXONOMY_VERSION,
                    "schema_version": GRAPH_TAXONOMY_VERSION,
                    "graph_taxonomy_version": GRAPH_TAXONOMY_VERSION,
                    "dimensions": get_graph_dimensions(),
                    "graph_dimensions": get_graph_dimensions(),
                    "dimension_ids": list(GRAPH_DIMENSION_IDS),
                    "graph_dimension_ids": list(GRAPH_DIMENSION_IDS),
                    "dimension_count": len(GRAPH_DIMENSION_IDS),
                    "weight_table": {fid: dict(w) for fid, w in FEATURE_TO_DIMENSION_WEIGHTS.items()},
                    "feature_to_dimension_weights": {fid: dict(w) for fid, w in FEATURE_TO_DIMENSION_WEIGHTS.items()},
                    "series": graph_series,
                    "graph_series": graph_series,
                    "series_by_dimension": graph_series,
                    "composite": graph_composite,
                    "graph_composite": graph_composite,
                    "overall_series": graph_composite,
                    "contributors_per_window": per_window_contributors,
                    "graph_contributors": per_window_contributors,
                    "graph_contributors_per_window": per_window_contributors,
                    "hotspots": graph_hotspots,
                    "graph_hotspots": graph_hotspots,
                    "candidate_sections": graph_hotspots,
                    "methods": {
                        "aggregation": "weighted_mean_of_feature_normalized_per_graph_dimension_then_mean_of_dimensions",
                        "composite": "graph_composite",
                        "hotspot_method": "graph_composite_top_n.v1",
                        "hand_mode": hand_mode_for_graph,
                        "weight_table_version": GRAPH_TAXONOMY_VERSION,
                        "explanation_note": "Local causes and section-refinement metadata (local_causes, distinct_local_causes, supporting_window_indices, setup_window_indices, continuation_window_indices, hand_tempering/is_single_hand_window, has_mosso_tempo/tempo_texts/tempo_influence) can support graph explanations/tooltips; they are explanation/detail metadata and not required for graph computation.",
                    },
                    "explanation_note": "Graph dimensions are composite signals over normalized raw feature traces; hover/click explanations retain raw contributing feature IDs and refined section metadata where available.",
                    "caveats": "Do not replace 9-aspect backend taxonomy; Notation / Reading remains its own dimension with deeper semantics deferred; context-only features (metadata.length_quarters, measure_count, note_count, page_count) are excluded from scoring.",
                }
                payload["front_graph_taxonomy"] = front_graph_payload
                payload["graph_taxonomy"] = front_graph_payload
                payload["graph_dimensions"] = get_graph_dimensions()
                payload["graph_series"] = graph_series
                payload["graph_composite"] = graph_composite
                payload["graph_taxonomy_version"] = GRAPH_TAXONOMY_VERSION
                payload["graph_hotspots"] = graph_hotspots
                # Enrich chart with graph series for report surfaces
                if isinstance(payload.get("chart"), dict):
                    payload["chart"]["graph_series"] = graph_series
                    payload["chart"]["graph_composite"] = graph_composite
                    payload["chart"]["graph_dimension_ids"] = list(GRAPH_DIMENSION_IDS)
                    payload["chart"]["front_graph_taxonomy_version"] = GRAPH_TAXONOMY_VERSION
                # Diagnostics
                payload["diagnostics"].append(
                    "Front-facing graph taxonomy (gradus.front_graph_taxonomy.v2) provides six learner-facing graph dimensions as a presentation layer over raw feature traces; raw feature extraction formulas unchanged; difficulty_overview.v1 remains compatible."
                )
            except Exception as _graph_exc:
                # Graph layer is additive; do not fail primary profile if it errors
                payload["front_graph_taxonomy_error"] = str(_graph_exc)
                payload["graph_taxonomy_error"] = str(_graph_exc)

        return DifficultyAspectsResult(payload)


def _build_temporal_aspect_data(extraction, options=None):
    """Build per-aspect temporal series, composite and aspect-ranked hotspots.

    Returns dict with regions, series, composite, hotspots or None if no measures.
    """
    score = extraction.score
    if not score.measures:
        return None
    # Resolve window options
    try:
        from piano_difficulty.difficulty_analysis.overview import OverviewOptions
        if options is not None and isinstance(options, OverviewOptions):
            opts = options
        else:
            opts = OverviewOptions()
    except Exception:
        # Fallback defaults
        class _FallbackOpts:
            window = "measure"
            window_size = 2
            stride = 1
            hand = "both"
            top_sections = 5
        opts = _FallbackOpts()

    # Build feature series via difficulty dynamics core
    try:
        from piano_difficulty.difficulty_analysis.dynamics.core import build_difficulty_profile
        from piano_difficulty.difficulty_analysis.dynamics.models import (
            CompositeConfig,
            DifficultyDynamicsConfig,
            NormalizationConfig,
            PeakDetectionConfig,
            WindowStrategyConfig,
            region_to_payload,
        )
    except Exception:
        return None

    union_ids = tuple(sorted(set(TEMPORAL_FEATURE_IDS)))

    config = DifficultyDynamicsConfig(
        experiment_name="difficulty_aspects",
        score_path=score.source_path or Path("score.musicxml"),
        feature_ids=union_ids,
        hand_mode=getattr(opts, "hand", "both"),
        window=WindowStrategyConfig(
            kind=getattr(opts, "window", "measure"),
            size=int(getattr(opts, "window_size", 2)),
            step=int(getattr(opts, "stride", 1)),
            beat_size=getattr(opts, "window_size", 2),
            beat_step=getattr(opts, "stride", 1),
        ),
        normalization=NormalizationConfig(method="min_max"),
        composite=CompositeConfig(enabled=False),
        peaks=PeakDetectionConfig(top_n=int(getattr(opts, "top_sections", 5))),
        overview_mode=True,
    )
    try:
        profile = build_difficulty_profile(score, config)
    except Exception:
        return None

    feature_series = profile.series
    regions = list(profile.regions)
    if not regions:
        return None

    regions_payload = [region_to_payload(r) for r in regions]

    # Per-aspect series: mean of feature normalized values per window
    aspect_series: dict[str, dict] = {}
    aspect_ids = []
    for aspect_def in _ASPECT_DEFINITIONS:
        aid = aspect_def["aspect_id"]
        readiness = aspect_def["readiness"]
        label = aspect_def["label"]
        aspect_ids.append(aid)
        contributing_fids = [fid for fid in union_ids if _matches_aspect(fid, aspect_def)]
        # For performance_interpretive_demand, contributing_fids already includes expression proxies
        if readiness == "blocked":
            raw_vals = [None] * len(regions)
            norm_vals = [None] * len(regions)
            smoothed = [None] * len(regions)
            units = None
            availability_notes = (
                "Aspect blocked: no validated temporal extractor; contextual metadata only",
            )
            provenance = "blocked"
        else:
            raw_vals = []
            norm_vals = []
            smoothed = []
            for idx in range(len(regions)):
                vals = []
                for fid in contributing_fids:
                    series = feature_series.get(fid)
                    if series is None:
                        continue
                    v = series.normalized_values[idx] if idx < len(series.normalized_values) else None
                    if v is not None:
                        vals.append(float(v))
                if vals:
                    mean = sum(vals) / len(vals)
                    raw_vals.append(mean)
                    norm_vals.append(mean)
                    smoothed.append(mean)
                else:
                    raw_vals.append(None)
                    norm_vals.append(None)
                    smoothed.append(None)
            units = "normalized_score"
            availability_notes = ()
            provenance = "aspect_aggregation"

        availability = aspect_def["readiness"]
        if aid == "structural_pattern_demand":
            availability = "contextual"
        elif aid == "performance_interpretive_demand":
            availability = "caveated"
        elif readiness == "partial":
            availability = "partial"
        elif readiness == "ready":
            availability = "available"

        series_payload = {
            "feature_id": aid,
            "aspect_id": aid,
            "feature_name": label,
            "label": label,
            "name": label,
            "provenance": provenance,
            "readiness": readiness,
            "status": readiness,
            "availability": availability,
            "description": aspect_def["description"],
            "temporal_adaptation": "aspect_mean_of_feature_normalized",
            "hand_mode": getattr(opts, "hand", "both"),
            "extractor_name": "aspect_aggregation",
            "extractor_config": {"contributing_feature_ids": sorted(contributing_fids)},
            "units": units,
            "source_scope": "aspect",
            "source_scope_ref": aid,
            "regions": regions_payload,
            "raw_values": raw_vals,
            "normalized_values": norm_vals,
            "smoothed_values": smoothed,
            "missing_region_indices": [i for i, v in enumerate(norm_vals) if v is None],
            "transformation_metadata": {
                "aggregation": "mean_of_feature_normalized",
                "contributing_feature_ids": sorted(contributing_fids),
                "contributing_feature_count": len(contributing_fids),
                "readiness": readiness,
                "blocked": readiness == "blocked",
                "caveated": readiness == "caveated",
            },
            "availability_notes": list(availability_notes),
            "missing_features": list(aspect_def["missing_features"]),
            "limitations": list(aspect_def["limitations"]),
        }
        if readiness == "blocked":
            series_payload["blocked"] = True
            series_payload["is_blocked"] = True
        if readiness == "caveated":
            series_payload["caveated"] = True
            series_payload["is_caveated"] = True
        aspect_series[aid] = series_payload

    # Composite overall: mean of aspect normalized values excluding blocked
    composite_aspect_ids = [aid for aid, s in aspect_series.items() if s.get("readiness") != "blocked"]
    composite_raw = []
    composite_norm = []
    composite_smooth = []
    for idx in range(len(regions)):
        vals = []
        for aid in composite_aspect_ids:
            v = aspect_series[aid]["normalized_values"][idx]
            if v is not None:
                vals.append(float(v))
        if vals:
            mean = sum(vals) / len(vals)
            composite_raw.append(mean)
            composite_norm.append(mean)
            composite_smooth.append(mean)
        else:
            composite_raw.append(None)
            composite_norm.append(None)
            composite_smooth.append(None)

    composite_payload = {
        "feature_id": "composite.aspect_demand",
        "aspect_id": "composite.aspect_demand",
        "feature_name": "Overall aspect demand",
        "label": "Overall aspect demand",
        "provenance": "aspect_composite",
        "units": "normalized_score",
        "regions": regions_payload,
        "raw_values": composite_raw,
        "normalized_values": composite_norm,
        "smoothed_values": composite_smooth,
        "missing_region_indices": [i for i, v in enumerate(composite_norm) if v is None],
        "transformation_metadata": {
            "aggregation": "mean_of_aspect_normalized_excluding_blocked",
            "included_aspect_ids": sorted(composite_aspect_ids),
            "excluded_blocked": ["structural_pattern_demand"],
            "included_count": len(composite_aspect_ids),
        },
        "availability_notes": ["Composite is descriptive mean of aspect signals, not a calibrated grade"],
    }

    # Hotspots: top windows by composite value
    indexed = [(i, v) for i, v in enumerate(composite_norm) if v is not None]
    indexed.sort(key=lambda x: x[1], reverse=True)
    top_n = int(getattr(opts, "top_sections", 5))
    top = indexed[:top_n]

    hotspots = []
    # Precompute aspect_defs map
    aspect_def_map = {a["aspect_id"]: a for a in _ASPECT_DEFINITIONS}
    for rank, (win_idx, comp_val) in enumerate(sorted(top, key=lambda x: x[1], reverse=True), start=1):
        region = regions[win_idx]
        # Rank aspects by their normalized value at this window
        aspect_contribs_with_vals = []
        for aid, series in aspect_series.items():
            if series.get("readiness") == "blocked":
                continue
            v = series["normalized_values"][win_idx]
            if v is None:
                continue
            aspect_contribs_with_vals.append((aid, float(v), series.get("label") or aid))
        aspect_contribs_with_vals.sort(key=lambda x: x[1], reverse=True)
        total_positive = sum(v for _, v, _ in aspect_contribs_with_vals if v > 0) or 1.0

        contrib_payloads = []
        for c_rank, (aid, val, label) in enumerate(aspect_contribs_with_vals, start=1):
            aspect_def = aspect_def_map[aid]
            contributing_fids = [fid for fid in union_ids if _matches_aspect(fid, aspect_def)]
            feat_vals = []
            for fid in contributing_fids:
                fseries = feature_series.get(fid)
                if fseries is None:
                    continue
                fv = fseries.normalized_values[win_idx] if win_idx < len(fseries.normalized_values) else None
                if fv is None:
                    continue
                raw_val = fseries.raw_values[win_idx] if win_idx < len(fseries.raw_values) else None
                feat_vals.append((fid, float(fv), raw_val, fseries))
            feat_vals.sort(key=lambda x: x[1], reverse=True)
            feat_total = sum(v for _, v, _, _ in feat_vals if v > 0) or 1.0
            feat_contribs = []
            for f_rank, (fid, fv, raw_val, fseries) in enumerate(feat_vals, start=1):
                share = (max(fv, 0) / feat_total) if feat_total else None
                feat_contribs.append(
                    {
                        "feature_id": fid,
                        "label": fseries.feature_name or fid,
                        "feature_name": fseries.feature_name,
                        "raw_value": raw_val,
                        "normalized_value": fv,
                        "smoothed_value": fseries.smoothed_values[win_idx] if win_idx < len(fseries.smoothed_values) else None,
                        "weighted_value": fv,
                        "contribution_share": share,
                        "rank": f_rank,
                        "units": fseries.units,
                    }
                )
            # Keep at most top 5 feature contributors per aspect for brevity
            feat_contribs_sorted = sorted(feat_contribs, key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))[:5]
            share = (max(val, 0) / total_positive) if total_positive else None
            is_peak = c_rank <= 3
            contrib_payloads.append(
                {
                    "aspect_id": aid,
                    "feature_id": aid,
                    "id": aid,
                    "label": label,
                    "feature_name": label,
                    "aspect_label": label,
                    "readiness": aspect_series[aid].get("readiness"),
                    "availability": aspect_series[aid].get("availability"),
                    "raw_value": val,
                    "normalized_value": val,
                    "smoothed_value": val,
                    "weighted_value": val,
                    "contribution_share": share,
                    "rank": c_rank,
                    "is_peak_support": is_peak,
                    "feature_contributors": feat_contribs_sorted,
                    "supporting_feature_contributors": feat_contribs_sorted,
                    "feature_summaries": feat_contribs_sorted,
                    "units": "normalized_score",
                }
            )

        # Stable snippet fields (demo-friendly, no live render required)
        # snippet_image/status/diagnostic enriched later via snippet_resolver;
        # defaults are not_requested with explainable diagnostic.
        _snippet_measure_numbers = list(region.measure_numbers)
        _snippet_range = f"{region.measure_start}-{region.measure_end}" if region.measure_start != region.measure_end else str(region.measure_start)
        if len(region.measure_numbers) >= 2:
            try:
                _ints = sorted(int(str(x)) for x in region.measure_numbers)
                _snippet_range = f"{_ints[0]}-{_ints[-1]}"
                _snippet_measure_numbers = [str(i) for i in _ints]
            except ValueError:
                _snippet_range = f"{region.measure_numbers[0]}-{region.measure_numbers[-1]}"
        elif region.measure_numbers:
            _snippet_range = str(region.measure_numbers[0])

        hotspot = {
            "hotspot_id": f"{score.source_path or 'score'}:{win_idx}",
            "id": f"aspect_section:both:{region.start_offset}:{region.end_offset}",
            "section_id": f"aspect_section:both:{region.start_offset}:{region.end_offset}",
            "rank": rank,
            "window_index": win_idx,
            "measure_start": region.measure_start,
            "measure_end": region.measure_end,
            "measure_index_start": region.measure_start,
            "measure_index_end": region.measure_end,
            "measure_index_range": _snippet_range,
            "measure_numbers": list(region.measure_numbers),
            "measure_range": f"{region.measure_numbers[0]}-{region.measure_numbers[-1]}" if len(region.measure_numbers) >= 2 else (region.measure_numbers[0] if region.measure_numbers else "unknown"),
            "label": region.label or f"Measures {'-'.join(region.measure_numbers) if region.measure_numbers else 'unknown'}",
            "region": region_to_payload(region),
            "representative_region": region_to_payload(region),
            "score_value": comp_val,
            "score": comp_val,
            "method": "aspect_composite_top_n.v1",
            "supporting_aspect_ids": [c["aspect_id"] for c in contrib_payloads],
            "supporting_window_indices": [win_idx],
            "supporting_feature_ids": [fid for c in contrib_payloads for fid in [f["feature_id"] for f in c.get("feature_contributors", [])]],
            "aspect_contributors": contrib_payloads,
            "top_contributors": contrib_payloads,
            "contributions": contrib_payloads,
            "feature_contributions": contrib_payloads,
            "start_offset": str(region.start_offset) if region.start_offset is not None else None,
            "end_offset": str(region.end_offset) if region.end_offset is not None else None,
            "score_position": region.position,
            "snippet_image": None,
            "snippet_status": "not_requested",
            "snippet_diagnostic": "Snippet not pre-rendered; run pre-render script to generate snippets/window_<index>__measures_<range>.png.",
            "snippet_measure_numbers": _snippet_measure_numbers,
            "snippet_measure_index_range": _snippet_range,
            "snippet_window_index": win_idx,
        }
        hotspots.append(hotspot)

    methods = {
        "window": {
            "kind": getattr(opts, "window", "measure"),
            "size": int(getattr(opts, "window_size", 2)),
            "step": int(getattr(opts, "stride", 1)),
        },
        "hand_mode": getattr(opts, "hand", "both"),
        "aggregation": "mean_of_feature_normalized_per_aspect_then_mean_of_aspects_excluding_blocked",
        "composite": "aspect_composite",
        "hotspot_method": "aspect_composite_top_n.v1",
        "temporal_feature_ids": list(union_ids),
    }

    return {
        "regions": regions,
        "regions_payload": regions_payload,
        "series": aspect_series,
        "composite": composite_payload,
        "hotspots": hotspots,
        "aspect_ids": aspect_ids,
        "methods": methods,
        "feature_series": feature_series,
    }
