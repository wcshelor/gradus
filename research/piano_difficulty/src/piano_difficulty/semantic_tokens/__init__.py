"""Semantic score-tokenization layer (native adapter, no external dep).

Architecture:
 MusicXML/MXL -> ScoreIR -> normalized event table -> derived tokens -> gestures
                  -> difficulty subcomponents -> difficulty moments -> explanation
"""

from __future__ import annotations

from fractions import Fraction

from piano_difficulty.normalize.schema import ScoreIR

from .derived_tokens import derive_all
from .event_table import build_event_table, event_table_to_dataframe, event_table_to_dicts
from .gestures import build_gestures
from .models import (
    CATALOG_OBJECT_IDS,
    CHUNK_KINDS,
    CHUNK_LABELS,
    MicroMoment,
    OBJECT_CATALOG,
    OBJECT_DIMENSIONS,
    OBJECT_LABELS,
    ObjectComponent,
    DerivedToken,
    Gesture,
    MusicalObject,
    PracticeChunk,
    ScoreEvent,
    SemanticBundle,
)

try:
    from .musical_objects import build_musical_objects  # noqa: F401
except Exception:  # pragma: no cover
    build_musical_objects = None  # type: ignore[assignment]

try:
    from .narration import MusicalObservation, build_musical_observations  # noqa: F401
except Exception:  # pragma: no cover - narration optional at import time
    MusicalObservation = None  # type: ignore[assignment]
    build_musical_observations = None  # type: ignore[assignment]

try:
    from .local_inspection import (  # noqa: F401
        BroadObjectCard,
        EvidenceSummary,
        InstructionUnit,
        LocalInspection,
        LocalObjectCard,
        build_local_inspection,
        render_markdown as render_local_inspection_markdown,
    )
except Exception:  # pragma: no cover
    LocalInspection = None  # type: ignore[assignment]
    InstructionUnit = None  # type: ignore[assignment]
    LocalObjectCard = None  # type: ignore[assignment]
    BroadObjectCard = None  # type: ignore[assignment]
    EvidenceSummary = None  # type: ignore[assignment]
    build_local_inspection = None  # type: ignore[assignment]
    render_local_inspection_markdown = None  # type: ignore[assignment]

__all__ = [
    "ScoreEvent",
    "DerivedToken",
    "Gesture",
    "SemanticBundle",
    "MusicalObject",
    "ObjectComponent",
    "MicroMoment",
    "PracticeChunk",
    "CATALOG_OBJECT_IDS",
    "CHUNK_KINDS",
    "CHUNK_LABELS",
    "OBJECT_LABELS",
    "OBJECT_DIMENSIONS",
    "OBJECT_CATALOG",
    "MusicalObservation",
    "LocalInspection",
    "InstructionUnit",
    "LocalObjectCard",
    "BroadObjectCard",
    "EvidenceSummary",
    "build_event_table",
    "event_table_to_dicts",
    "event_table_to_dataframe",
    "derive_all",
    "build_gestures",
    "build_musical_objects",
    "build_semantic_bundle",
    "explain_with_semantic_tokens",
    "build_musical_observations",
    "build_local_inspection",
    "render_local_inspection_markdown",
]


def build_semantic_bundle(score: ScoreIR, *, include_rests: bool = True) -> SemanticBundle:
    events = build_event_table(score, include_rests=include_rests)
    tokens = derive_all(events)
    gestures = build_gestures(events, tokens)
    diagnostics: tuple[str, ...] = ()
    try:
        from .musical_objects import build_musical_objects as _build_objs

        musical_objects = _build_objs(events, tokens, gestures, score)
    except Exception as exc:
        musical_objects = []
        diagnostics = (f"musical_objects_error: {type(exc).__name__}: {exc}",)
    score_id = str(score.source_path) if score.source_path is not None else score.title
    bundle = SemanticBundle(
        events=tuple(events),
        derived_tokens=tuple(tokens),
        gestures=tuple(gestures),
        musical_objects=tuple(musical_objects),
        score_id=score_id,
        diagnostics=diagnostics,
    )
    # Build object components and micro-moments (additive, backward-compatible)
    try:
        from .object_components import build_micro_moments, build_object_components

        object_components = build_object_components(bundle)
        micro_moments = build_micro_moments(bundle, object_components)
        # recreate bundle with new layers
        bundle = SemanticBundle(
            events=bundle.events,
            derived_tokens=bundle.derived_tokens,
            gestures=bundle.gestures,
            musical_objects=bundle.musical_objects,
            object_components=object_components,
            micro_moments=micro_moments,
            score_id=bundle.score_id,
            diagnostics=bundle.diagnostics,
        )
    except Exception as exc:
        # conservative: keep bundle without components but add diagnostic
        bundle = SemanticBundle(
            events=bundle.events,
            derived_tokens=bundle.derived_tokens,
            gestures=bundle.gestures,
            musical_objects=bundle.musical_objects,
            score_id=bundle.score_id,
            diagnostics=bundle.diagnostics + (f"object_components_error: {type(exc).__name__}: {exc}",),
        )
    # Build PracticeChunks (additive, backward-compatible)
    try:
        from .practice_chunks import build_practice_chunks

        practice_chunks = build_practice_chunks(bundle)
        bundle = SemanticBundle(
            events=bundle.events,
            derived_tokens=bundle.derived_tokens,
            gestures=bundle.gestures,
            musical_objects=bundle.musical_objects,
            object_components=bundle.object_components,
            micro_moments=bundle.micro_moments,
            practice_chunks=practice_chunks,
            score_id=bundle.score_id,
            diagnostics=bundle.diagnostics,
        )
    except Exception as exc:
        bundle = SemanticBundle(
            events=bundle.events,
            derived_tokens=bundle.derived_tokens,
            gestures=bundle.gestures,
            musical_objects=bundle.musical_objects,
            object_components=bundle.object_components,
            micro_moments=bundle.micro_moments,
            score_id=bundle.score_id,
            diagnostics=bundle.diagnostics + (f"practice_chunks_error: {type(exc).__name__}: {exc}",),
        )
    return bundle


def explain_with_semantic_tokens(bundle: SemanticBundle) -> list[str]:
    """Plain-language explanations grounded in concrete evidence."""
    explanations: list[str] = []
    for g in bundle.gestures:
        meas = "-".join(g.measure_numbers) if g.measure_numbers else f"{g.measure_start}-{g.measure_end}"
        hand = g.hand or "both"
        if g.kind == "bass_to_chord":
            explanations.append(f"Bass-to-chord motion ({hand}, measures {meas}) spans {g.payload.get('movement')} semitones into {g.payload.get('chord_shape')}.")
        elif g.kind == "melody_with_accompaniment":
            explanations.append(f"Melody with accompaniment ({meas}): right-hand melodic motion over aligned left-hand support.")
        elif g.kind == "block_chord_landing":
            explanations.append(f"Block-chord landing ({hand}, {meas}) {g.payload.get('note_count')} notes spanning {g.payload.get('span_semitones')} semitones.")
        elif g.kind == "arpeggio":
            explanations.append(f"Arpeggio/broken chord ({hand}, {meas}) {g.payload.get('type')} pattern {g.payload.get('interval_pattern')}.")
        elif g.kind == "scalar_run":
            explanations.append(f"Scalar run {g.payload.get('direction')} ({hand}, {meas}) {g.payload.get('steps')} notes.")
        elif g.kind == "repeated_note_figure":
            explanations.append(f"Repeated-note figure pitch {g.payload.get('pitch')} ({hand}, {meas}) repeated {g.payload.get('repeat_count')} times.")
        elif g.kind == "cadence_like_arrival":
            explanations.append(f"Cadence-like arrival ({hand}, {meas}) wide span {g.payload.get('span_semitones')} semitones.")
        elif g.kind == "accompaniment_pattern":
            explanations.append(f"Accompaniment pattern ({hand}, {meas}) intervals {g.payload.get('pattern_intervals')}.")
        else:
            explanations.append(f"{g.kind} ({meas})")
    # Also summarize derived tokens if no gestures
    if not explanations:
        for t in bundle.derived_tokens[:5]:
            meas = "-".join(t.measure_numbers) if t.measure_numbers else str(t.measure_start)
            explanations.append(f"{t.kind} ({t.hand or 'both'}, {meas}) evidence {len(t.evidence_event_ids)} events.")
    return explanations
