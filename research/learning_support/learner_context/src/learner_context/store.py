"""Optional context operations and provenance — LS-04.

In-memory `ContextStore` over the LS-03b contracts with an explicit local
persistence boundary (JSON file, synthetic data only). No habit inference,
no external model processing, no network.

Design refs:
- three-area plan, sections 4 (records) and LS-04 (operations/provenance)
- research/learning_support/first_slice.md (S4, S5, section 5 outputs)
- learner_context/README.md (boundary)

Semantics:
- Create is session-only unless `saved=True` is explicitly chosen. Export and
  file save include explicitly saved entries only; session-only notes are
  never persisted implicitly.
- Journal text is immutable; correction appends a new revision linked by
  `supersedes`. Superseded entries stay readable (dated, not authoritative)
  but are never selected.
- Deletion removes the entry and its permission and cascades to dependent
  summaries: deleted content leaves no hidden memory.
- Exclusion replaces the permission (use flags off); excluded entries are
  never selected and invalidate dependent summaries.
- A summary is current iff every source entry resolves, none is superseded,
  and none is excluded. Corrections stale dependents; deletions remove them.
- Selection follows the request's `context_scope` over permitted, active
  entries: NONE selects nothing; REFERENCED selects entries linked by piece
  identity or overlapping exact region; PERMITTED selects all permitted
  active entries. Only current summaries whose sources were all selected are
  attached. Piece/region entries used under a versioned request carry a
  `score_version_unverified` warning (S7: never attach across editions
  silently). Empty history selects empty context without error.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity

from .models import (
    SUPPORTED_JOURNAL_VERSIONS,
    SUPPORTED_PERMISSION_VERSIONS,
    SUPPORTED_REQUEST_VERSIONS,
    SUPPORTED_RESULT_VERSIONS,
    SUPPORTED_SUMMARY_VERSIONS,
    AssistanceRequest,
    ContextPermission,
    ContextScope,
    ContextSummary,
    EntryScope,
    JournalEntry,
)

STORE_SCHEMA_VERSION = "context_store.v1"
SELECTED_CONTEXT_SCHEMA_VERSION = "selected_context.v1"

SUPPORTED_STORE_VERSIONS = {STORE_SCHEMA_VERSION}
SUPPORTED_SELECTION_VERSIONS = {SELECTED_CONTEXT_SCHEMA_VERSION}


@dataclass(frozen=True, slots=True)
class SelectedContext:
    """Deterministic result of selecting context for one request."""

    request_id: str
    entries: tuple[JournalEntry, ...] = ()
    summaries: tuple[ContextSummary, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id:
            raise ValueError(f"request_id must be non-empty str, got {self.request_id!r}")
        for name in ("entries", "summaries", "diagnostics"):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be tuple")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SELECTED_CONTEXT_SCHEMA_VERSION,
            "request_id": self.request_id,
        }
        if self.entries:
            payload["entries"] = [e.to_dict() for e in self.entries]
        if self.summaries:
            payload["summaries"] = [s.to_dict() for s in self.summaries]
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectedContext":
        if not isinstance(data, dict):
            raise TypeError(f"SelectedContext requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_SELECTION_VERSIONS:
            raise ValueError(
                f"unsupported SelectedContext schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SELECTION_VERSIONS)}"
            )
        try:
            request_id = data["request_id"]
        except KeyError as exc:
            raise ValueError(f"missing SelectedContext field {exc.args[0]!r}") from exc

        def _items(key: str, factory):
            raw = data.get(key, [])
            if not isinstance(raw, list):
                raise ValueError(f"SelectedContext {key} must be list")
            return tuple(factory(item) for item in raw)

        return cls(
            request_id=request_id,
            entries=_items("entries", JournalEntry.from_dict),
            summaries=_items("summaries", ContextSummary.from_dict),
            diagnostics=_items("diagnostics", Diagnostic.from_dict),
        )


class ContextStore:
    """Mutable in-memory holder for entries, permissions, and summaries."""

    def __init__(self) -> None:
        self._entries: dict[str, JournalEntry] = {}
        self._permissions: dict[str, ContextPermission] = {}
        self._summaries: dict[str, ContextSummary] = {}

    # -- entries ---------------------------------------------------------

    def add_entry(self, entry: JournalEntry, saved: bool = False) -> ContextPermission:
        if not isinstance(entry, JournalEntry):
            raise TypeError(f"entry must be JournalEntry, got {type(entry).__name__}")
        if not isinstance(saved, bool):
            raise TypeError(f"saved must be bool, got {saved!r}")
        if entry.entry_id in self._entries:
            raise ValueError(f"duplicate entry_id {entry.entry_id!r}")
        self._entries[entry.entry_id] = entry
        permission = ContextPermission(entry_id=entry.entry_id, saved=saved)
        self._permissions[entry.entry_id] = permission
        return permission

    def get_entry(self, entry_id: str) -> JournalEntry:
        try:
            return self._entries[entry_id]
        except KeyError as exc:
            raise KeyError(f"unknown entry_id {entry_id!r}") from exc

    def list_entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries.values())

    def correct_entry(
        self,
        entry_id: str,
        *,
        new_id: str,
        text: str,
        recorded_at: str,
        practice_note: str | None = None,
        tags: tuple[str, ...] = (),
        fields: dict[str, str] | None = None,
        saved: bool | None = None,
    ) -> JournalEntry:
        old = self.get_entry(entry_id)
        old_permission = self.get_permission(entry_id)
        correction = JournalEntry(
            entry_id=new_id,
            text=text,
            author=old.author,
            recorded_at=recorded_at,
            scope=old.scope,
            piece_id=old.piece_id,
            region=old.region,
            practice_note=practice_note,
            tags=tags,
            fields=fields,
            revision=old.revision + 1,
            supersedes=old.entry_id,
        )
        self.add_entry(
            correction, saved=old_permission.saved if saved is None else saved
        )
        return correction

    def delete_entry(self, entry_id: str) -> None:
        self.get_entry(entry_id)
        del self._entries[entry_id]
        self._permissions.pop(entry_id, None)
        stale = [
            sid
            for sid, summary in self._summaries.items()
            if entry_id in summary.source_entry_ids
        ]
        for sid in stale:
            del self._summaries[sid]

    # -- permissions -----------------------------------------------------

    def get_permission(self, entry_id: str) -> ContextPermission:
        try:
            return self._permissions[entry_id]
        except KeyError as exc:
            raise KeyError(f"unknown entry_id {entry_id!r}") from exc

    def set_permission(self, permission: ContextPermission) -> None:
        if not isinstance(permission, ContextPermission):
            raise TypeError(
                "permission must be ContextPermission, "
                f"got {type(permission).__name__}"
            )
        self.get_entry(permission.entry_id)
        self._permissions[permission.entry_id] = permission

    def set_excluded(self, entry_id: str, excluded: bool = True) -> ContextPermission:
        if not isinstance(excluded, bool):
            raise TypeError(f"excluded must be bool, got {excluded!r}")
        current = self.get_permission(entry_id)
        if excluded:
            updated = ContextPermission(
                entry_id=entry_id, saved=current.saved, use_current=False,
                use_future=False, excluded=True,
            )
        else:
            updated = ContextPermission(
                entry_id=entry_id, saved=current.saved, use_current=True,
                use_future=current.use_future, excluded=False,
            )
        self._permissions[entry_id] = updated
        return updated

    # -- summaries -------------------------------------------------------

    def add_summary(self, summary: ContextSummary) -> None:
        if not isinstance(summary, ContextSummary):
            raise TypeError(
                f"summary must be ContextSummary, got {type(summary).__name__}"
            )
        if summary.summary_id in self._summaries:
            raise ValueError(f"duplicate summary_id {summary.summary_id!r}")
        for source_id in summary.source_entry_ids:
            self.get_entry(source_id)
        self._summaries[summary.summary_id] = summary

    def get_summary(self, summary_id: str) -> ContextSummary:
        try:
            return self._summaries[summary_id]
        except KeyError as exc:
            raise KeyError(f"unknown summary_id {summary_id!r}") from exc

    def is_summary_current(self, summary_id: str) -> bool:
        summary = self.get_summary(summary_id)
        superseded = self._superseded_ids()
        for source_id in summary.source_entry_ids:
            if source_id not in self._entries or source_id in superseded:
                return False
            permission = self._permissions.get(source_id)
            if permission is None or permission.excluded:
                return False
        return True

    def current_summaries(self) -> tuple[ContextSummary, ...]:
        return tuple(
            s for s in self._summaries.values() if self.is_summary_current(s.summary_id)
        )

    def _superseded_ids(self) -> set[str]:
        return {
            entry.supersedes for entry in self._entries.values()
            if entry.supersedes is not None
        }

    def _active_permitted(self) -> list[JournalEntry]:
        superseded = self._superseded_ids()
        selected = []
        for entry in self._entries.values():
            if entry.entry_id in superseded:
                continue
            permission = self._permissions.get(entry.entry_id)
            if permission is None or permission.excluded or not permission.use_current:
                continue
            selected.append(entry)
        return selected

    # -- selection -------------------------------------------------------

    def select_context(self, request: AssistanceRequest) -> SelectedContext:
        if not isinstance(request, AssistanceRequest):
            raise TypeError(
                f"request must be AssistanceRequest, got {type(request).__name__}"
            )
        if request.context_scope == ContextScope.NONE:
            return SelectedContext(request_id=request.request_id)
        candidates = self._active_permitted()
        if request.context_scope == ContextScope.REFERENCED:
            candidates = [e for e in candidates if self._linked(e, request)]
        selected_ids = {e.entry_id for e in candidates}
        summaries = tuple(
            s for s in self.current_summaries()
            if set(s.source_entry_ids) <= selected_ids
        )
        diagnostics = tuple(self._version_warnings(e, request) for e in candidates
                             if self._needs_version_warning(e, request))
        return SelectedContext(
            request_id=request.request_id,
            entries=tuple(candidates),
            summaries=summaries,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _linked(entry: JournalEntry, request: AssistanceRequest) -> bool:
        if request.piece_id is not None:
            if entry.piece_id != request.piece_id:
                return False
            return True
        if request.region is not None and entry.region is not None:
            return entry.region.overlaps(request.region)
        return False

    @staticmethod
    def _needs_version_warning(entry: JournalEntry, request: AssistanceRequest) -> bool:
        return (
            request.score_version is not None
            and entry.scope in (EntryScope.PIECE, EntryScope.REGION)
            and entry.piece_id is not None
            and entry.piece_id == request.piece_id
        )

    @staticmethod
    def _version_warnings(entry: JournalEntry, request: AssistanceRequest) -> Diagnostic:
        return Diagnostic(
            code="score_version_unverified",
            severity=Severity.WARNING,
            message=(
                f"entry {entry.entry_id!r} carries no edition identity; confirm it "
                f"matches score version {request.score_version!r} before treating "
                "it as local evidence"
            ),
        )

    # -- persistence boundary --------------------------------------------

    def export(self) -> dict[str, Any]:
        saved_ids = {
            eid for eid, perm in self._permissions.items() if perm.saved
        }
        entries = [self._entries[eid].to_dict() for eid in self._entries if eid in saved_ids]
        permissions = [
            self._permissions[eid].to_dict() for eid in self._entries if eid in saved_ids
        ]
        summaries = [
            s.to_dict() for s in self._summaries.values()
            if set(s.source_entry_ids) <= saved_ids and self.is_summary_current(s.summary_id)
        ]
        return {
            "schema_version": STORE_SCHEMA_VERSION,
            "entries": entries,
            "permissions": permissions,
            "summaries": summaries,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.export(), sort_keys=True, indent=2) + "\n")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextStore":
        if not isinstance(data, dict):
            raise TypeError(f"ContextStore requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_STORE_VERSIONS:
            raise ValueError(
                f"unsupported ContextStore schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_STORE_VERSIONS)}"
            )
        store = cls()
        for key, factory, adder in (
            ("entries", JournalEntry.from_dict, store._insert_entry),
            ("permissions", ContextPermission.from_dict, store._insert_permission),
            ("summaries", ContextSummary.from_dict, store.add_summary),
        ):
            raw = data.get(key, [])
            if not isinstance(raw, list):
                raise ValueError(f"ContextStore {key} must be list")
            for item in raw:
                adder(factory(item))
        for eid in store._permissions:
            if eid not in store._entries:
                raise ValueError(f"permission references unknown entry {eid!r}")
        return store

    def _insert_entry(self, entry: JournalEntry) -> None:
        if entry.entry_id in self._entries:
            raise ValueError(f"duplicate entry_id {entry.entry_id!r}")
        self._entries[entry.entry_id] = entry

    def _insert_permission(self, permission: ContextPermission) -> None:
        if permission.entry_id in self._permissions:
            raise ValueError(
                f"duplicate permission for {permission.entry_id!r}"
            )
        self._permissions[permission.entry_id] = permission

    @classmethod
    def load(cls, path: str | Path) -> "ContextStore":
        return cls.from_dict(json.loads(Path(path).read_text()))


__all__ = [
    "SELECTED_CONTEXT_SCHEMA_VERSION",
    "STORE_SCHEMA_VERSION",
    "ContextStore",
    "SelectedContext",
]

# Re-exported so contract-version coverage stays visible at this boundary.
__all__ += [
    "SUPPORTED_JOURNAL_VERSIONS",
    "SUPPORTED_PERMISSION_VERSIONS",
    "SUPPORTED_REQUEST_VERSIONS",
    "SUPPORTED_RESULT_VERSIONS",
    "SUPPORTED_SUMMARY_VERSIONS",
]
