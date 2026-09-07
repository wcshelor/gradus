"""Tests for LS-04 optional context operations and provenance."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from learner_context.models import (
    AssistanceRequest,
    ContextPermission,
    ContextScope,
    ContextSummary,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from learner_context.store import (
    SELECTED_CONTEXT_SCHEMA_VERSION,
    STORE_SCHEMA_VERSION,
    ContextStore,
    SelectedContext,
)
from passage_practice.models.time import ScoreInterval, ScorePosition


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, offset_in_measure=Fraction(0, 1))


def _region(start: int, end: int) -> ScoreInterval:
    return ScoreInterval(start=_pos(Fraction(start, 1)), end=_pos(Fraction(end, 1)))


def _note(entry_id="entry.1", **overrides) -> JournalEntry:
    base = dict(
        entry_id=entry_id,
        text="The join still feels uncertain.",
        author="learner",
        recorded_at="2026-09-05T10:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _request(request_id="req.1", **overrides) -> AssistanceRequest:
    base = dict(request_id=request_id, intent=RequestIntent.UNDERSTAND)
    base.update(overrides)
    return AssistanceRequest(**base)


def _summary(summary_id="sum.1", sources=("entry.1",), **overrides) -> ContextSummary:
    base = dict(
        summary_id=summary_id,
        source_entry_ids=tuple(sources),
        method_id="recurrence_heuristic",
        method_version="v1",
        created_at="2026-09-05T11:00:00",
        interpretation="Join difficulty recurs; unconfirmed.",
    )
    base.update(overrides)
    return ContextSummary(**base)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


# Create / read ---------------------------------------------------------------


def test_create_is_session_only_unless_explicitly_saved():
    store = ContextStore()
    session_perm = store.add_entry(_note())
    saved_perm = store.add_entry(_note("entry.2"), saved=True)
    assert session_perm.saved is False
    assert saved_perm.saved is True
    assert store.get_entry("entry.1").text.startswith("The join")


def test_rejects_duplicates_unknown_and_wrong_types():
    store = ContextStore()
    store.add_entry(_note())
    with pytest.raises(ValueError):
        store.add_entry(_note())
    with pytest.raises(KeyError):
        store.get_entry("missing")
    with pytest.raises(KeyError):
        store.delete_entry("missing")
    with pytest.raises(TypeError):
        store.add_entry("not-an-entry")  # type: ignore
    with pytest.raises(TypeError):
        store.add_entry(_note("entry.2"), saved="yes")  # type: ignore


# Save boundary ---------------------------------------------------------------


def test_session_only_notes_are_not_persisted(tmp_path):
    store = ContextStore()
    store.add_entry(_note())
    store.add_entry(_note("entry.2"), saved=True)
    exported = store.export()
    assert exported["schema_version"] == STORE_SCHEMA_VERSION
    assert [e["entry_id"] for e in exported["entries"]] == ["entry.2"]
    assert [p["entry_id"] for p in exported["permissions"]] == ["entry.2"]
    assert _dump(exported) == _dump(ContextStore.from_dict(exported).export())

    path = tmp_path / "context.json"
    store.save(path)
    on_disk = json.loads(path.read_text())
    assert [e["entry_id"] for e in on_disk["entries"]] == ["entry.2"]
    reloaded = ContextStore.load(path)
    assert [e.entry_id for e in reloaded.list_entries()] == ["entry.2"]
    assert reloaded.get_permission("entry.2").saved is True
    with pytest.raises(KeyError):
        reloaded.get_entry("entry.1")


def test_rejects_unsupported_store_version_and_dangling_permission():
    store = ContextStore()
    store.add_entry(_note("entry.1"), saved=True)
    data = store.export()
    data["schema_version"] = "context_store.v99"
    with pytest.raises(ValueError):
        ContextStore.from_dict(data)
    data = store.export()
    data["permissions"].append(
        ContextPermission(entry_id="ghost").to_dict()
    )
    with pytest.raises(ValueError):
        ContextStore.from_dict(data)


# Correct / delete / exclude ---------------------------------------------------


def test_correction_appends_revision_and_keeps_original():
    store = ContextStore()
    store.add_entry(_note(), saved=True)
    revised = store.correct_entry(
        "entry.1",
        new_id="entry.2",
        text="The join feels better; position change still slips.",
        recorded_at="2026-09-06T10:00:00",
    )
    assert revised.revision == 2
    assert revised.supersedes == "entry.1"
    assert revised.scope == EntryScope.GENERAL
    assert store.get_entry("entry.1").revision == 1  # dated, retained
    assert store.get_permission("entry.2").saved is True  # inherited


def test_selection_uses_latest_revision_only():
    store = ContextStore()
    store.add_entry(_note())
    store.correct_entry(
        "entry.1", new_id="entry.2", text="Updated.",
        recorded_at="2026-09-06T10:00:00",
    )
    selected = store.select_context(
        _request(context_scope=ContextScope.PERMITTED)
    )
    assert [e.entry_id for e in selected.entries] == ["entry.2"]


def test_delete_removes_entry_permission_and_dependent_summaries():
    store = ContextStore()
    store.add_entry(_note(), saved=True)
    store.add_entry(_note("entry.2"), saved=True)
    store.add_summary(_summary(sources=("entry.1", "entry.2")))
    store.add_summary(_summary("sum.2", sources=("entry.2",)))
    store.delete_entry("entry.1")
    with pytest.raises(KeyError):
        store.get_entry("entry.1")
    with pytest.raises(KeyError):
        store.get_permission("entry.1")
    with pytest.raises(KeyError):
        store.get_summary("sum.1")  # cascaded: no hidden memory
    assert store.get_summary("sum.2").summary_id == "sum.2"
    selected = store.select_context(
        _request(context_scope=ContextScope.PERMITTED)
    )
    assert [e.entry_id for e in selected.entries] == ["entry.2"]


def test_excluded_entries_never_selected_and_stale_summaries():
    store = ContextStore()
    store.add_entry(_note(), saved=True)
    store.add_summary(_summary())
    assert store.is_summary_current("sum.1") is True
    store.set_excluded("entry.1")
    selected = store.select_context(
        _request(context_scope=ContextScope.PERMITTED)
    )
    assert selected.entries == ()
    assert selected.summaries == ()
    assert store.is_summary_current("sum.1") is False
    store.set_excluded("entry.1", excluded=False)
    assert store.is_summary_current("sum.1") is True


def test_set_permission_replaces_and_validates():
    store = ContextStore()
    store.add_entry(_note())
    store.set_permission(
        ContextPermission(entry_id="entry.1", saved=True, use_future=True)
    )
    assert store.get_permission("entry.1").use_future is True
    with pytest.raises(KeyError):
        store.set_permission(ContextPermission(entry_id="ghost"))
    with pytest.raises(TypeError):
        store.set_permission("nope")  # type: ignore


# Summaries --------------------------------------------------------------------


def test_summary_requires_resolvable_sources_and_unique_id():
    store = ContextStore()
    with pytest.raises(KeyError):
        store.add_summary(_summary())
    store.add_entry(_note())
    store.add_summary(_summary())
    with pytest.raises(ValueError):
        store.add_summary(_summary())
    with pytest.raises(KeyError):
        store.get_summary("missing")
    with pytest.raises(KeyError):
        store.is_summary_current("missing")


def test_correction_stales_dependent_summary():
    store = ContextStore()
    store.add_entry(_note())
    store.add_summary(_summary())
    store.correct_entry(
        "entry.1", new_id="entry.2", text="Updated.",
        recorded_at="2026-09-06T10:00:00",
    )
    assert store.is_summary_current("sum.1") is False
    assert store.current_summaries() == ()


# Selection --------------------------------------------------------------------


def test_none_scope_selects_nothing_and_empty_history_is_valid():
    store = ContextStore()
    store.add_entry(_note(), saved=True)
    selected = store.select_context(_request())
    assert selected.entries == ()
    assert selected.summaries == ()
    empty = ContextStore().select_context(
        _request("req.2", context_scope=ContextScope.PERMITTED)
    )
    assert empty.entries == () and empty.summaries == ()


def test_referenced_scope_links_by_piece_and_region():
    store = ContextStore()
    store.add_entry(_note("entry.1", piece_id="piece.a"))
    store.add_entry(
        _note("entry.2", scope=EntryScope.REGION, piece_id="piece.b",
              region=_region(4, 8))
    )
    store.add_entry(_note("entry.3", piece_id="piece.b"))
    store.add_entry(
        _note("entry.4", scope=EntryScope.REGION, piece_id="piece.z",
              region=_region(6, 10))
    )
    request = _request(
        context_scope=ContextScope.REFERENCED,
        piece_id="piece.b",
        region=_region(6, 12),
    )
    selected = store.select_context(request)
    assert [e.entry_id for e in selected.entries] == ["entry.2", "entry.3"]
    unrelated = store.select_context(
        _request("req.2", context_scope=ContextScope.REFERENCED,
                 piece_id="piece.q", region=_region(6, 12))
    )
    assert unrelated.entries == ()


def test_summaries_attach_only_when_current_and_selected():
    store = ContextStore()
    store.add_entry(_note("entry.1", piece_id="piece.a"))
    store.add_entry(_note("entry.2", piece_id="piece.b"))
    store.add_summary(_summary())
    request = _request(context_scope=ContextScope.REFERENCED, piece_id="piece.a")
    selected = store.select_context(request)
    assert [s.summary_id for s in selected.summaries] == ["sum.1"]
    partial = _request(
        "req.2", context_scope=ContextScope.REFERENCED, piece_id="piece.b"
    )
    assert store.select_context(partial).summaries == ()


def test_score_version_mismatch_is_surfaced():
    store = ContextStore()
    store.add_entry(
        _note("entry.1", scope=EntryScope.PIECE, piece_id="piece.a")
    )
    store.add_entry(_note("entry.2"))  # general scope: no warning
    versioned = _request(
        context_scope=ContextScope.PERMITTED,
        piece_id="piece.a",
        score_version="edition.b",
    )
    selected = store.select_context(versioned)
    assert len(selected.entries) == 2
    (warning,) = selected.diagnostics
    assert warning.code == "score_version_unverified"
    assert "edition.b" in warning.message
    unversioned = _request(context_scope=ContextScope.PERMITTED, piece_id="piece.a")
    assert store.select_context(unversioned).diagnostics == ()


def test_selection_is_deterministic_and_versioned():
    store = ContextStore()
    store.add_entry(_note("entry.1", piece_id="piece.a"), saved=True)
    store.add_summary(_summary())
    request = _request(context_scope=ContextScope.PERMITTED, piece_id="piece.a")
    first = store.select_context(request)
    second = store.select_context(request)
    assert _dump(first.to_dict()) == _dump(second.to_dict())
    assert first.to_dict()["schema_version"] == SELECTED_CONTEXT_SCHEMA_VERSION
    assert SelectedContext.from_dict(first.to_dict()) == first
    broken = first.to_dict()
    broken["schema_version"] = "selected_context.v99"
    with pytest.raises(ValueError):
        SelectedContext.from_dict(broken)
