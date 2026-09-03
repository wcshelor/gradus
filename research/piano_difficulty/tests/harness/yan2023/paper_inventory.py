"""Frozen paper-facing 73-slot inventory for the Yan 2023 lane.

This module keeps the implementation-friendly 78-slot working inventory intact,
but also records a paper-facing 73-slot inventory driven by Figure 6 and
Table 3 evidence from Yan et al. (2023).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tests.harness.yan2023.slot_inventory import (
    FeatureStatus,
    ScopeCode,
    SourceKind,
    WORKING_FEATURE_SLOTS,
)

PaperScopeEvidence = Literal[
    "working_global",
    "working_scoped",
    "figure6_unsuffixed",
    "table3_global_formula",
]

PAPER_73_INVENTORY_LOCKED = True
PAPER_73_INVENTORY_SIZE = 73
EXPECTED_PAPER_73_SCOPE_OVERRIDES: dict[str, tuple[ScopeCode, ...]] = {
    "hand_stretch": ("global",),
    "playing_speed": ("global",),
    "pressing_velocity_entropy": ("global",),
}
EXPECTED_PAPER_73_SCOPE_COUNTS: dict[ScopeCode, int] = {
    "es": 21,
    "bs": 21,
    "ts": 21,
    "global": 10,
}
EXPECTED_PAPER_73_STATUS_COUNTS: dict[FeatureStatus, int] = {
    "implemented": 52,
    "proxyable": 14,
    "blocked": 7,
}


@dataclass(frozen=True, slots=True)
class Yan2023PaperSlot:
    """One slot in the paper-facing 73-slot inventory."""

    slot_id: str
    base_feature: str
    family: str
    scope_code: ScopeCode
    status: FeatureStatus
    source_kinds: tuple[SourceKind, ...]
    scope_evidence: PaperScopeEvidence
    notes: str


_PAPER_SCOPE_OVERRIDES: dict[str, tuple[ScopeCode, ...]] = {
    "hand_stretch": ("global",),
    "playing_speed": ("global",),
    "pressing_velocity_entropy": ("global",),
}

_PAPER_SCOPE_EVIDENCE: dict[str, PaperScopeEvidence] = {
    "hand_stretch": "figure6_unsuffixed",
    "playing_speed": "figure6_unsuffixed",
    "pressing_velocity_entropy": "table3_global_formula",
}

_PAPER_SCOPE_NOTES: dict[str, str] = {
    "hand_stretch": (
        "Figure 6 shows an unsuffixed `hand stretch` label, so the paper-73 "
        "inventory collapses staff variants to one paper-facing slot."
    ),
    "playing_speed": (
        "Figure 6 shows an unsuffixed `playing speed` label, so the paper-73 "
        "inventory collapses staff variants to one paper-facing slot."
    ),
    "pressing_velocity_entropy": (
        "Table 3 defines pressing-velocity entropy on the whole-score "
        "probability distribution, so the paper-73 inventory keeps one "
        "paper-facing slot."
    ),
}


def paper_scope_override_map() -> dict[str, tuple[ScopeCode, ...]]:
    """Return the scope overrides used to collapse the working inventory."""

    return dict(_PAPER_SCOPE_OVERRIDES)


def build_paper_73_slot_inventory() -> tuple[Yan2023PaperSlot, ...]:
    """Return the locked paper-facing 73-slot inventory."""

    grouped: dict[str, list] = {}
    for slot in WORKING_FEATURE_SLOTS:
        grouped.setdefault(slot.base_feature, []).append(slot)

    slots: list[Yan2023PaperSlot] = []
    for base_feature in sorted(grouped):
        working_slots = grouped[base_feature]
        exemplar = working_slots[0]
        scopes = _PAPER_SCOPE_OVERRIDES.get(
            base_feature,
            tuple(slot.scope_code for slot in working_slots),
        )
        scope_evidence = _PAPER_SCOPE_EVIDENCE.get(
            base_feature,
            "working_global" if scopes == ("global",) else "working_scoped",
        )
        note_suffix = _PAPER_SCOPE_NOTES.get(base_feature)
        notes = exemplar.notes
        if note_suffix is not None:
            notes = f"{notes} {note_suffix}"
        for scope in scopes:
            slot_id = base_feature if scope == "global" else f"{base_feature}_{scope}"
            slots.append(
                Yan2023PaperSlot(
                    slot_id=slot_id,
                    base_feature=base_feature,
                    family=exemplar.family,
                    scope_code=scope,
                    status=exemplar.status,
                    source_kinds=exemplar.source_kinds,
                    scope_evidence=scope_evidence,
                    notes=notes,
                )
            )
    return tuple(slots)


PAPER_73_FEATURE_SLOTS = build_paper_73_slot_inventory()


def validate_paper_73_inventory_lock() -> None:
    """Fail fast if the frozen paper-facing slot contract drifts."""

    if not PAPER_73_INVENTORY_LOCKED:
        raise RuntimeError("PAPER_73_INVENTORY_LOCKED must remain True.")
    if len(PAPER_73_FEATURE_SLOTS) != PAPER_73_INVENTORY_SIZE:
        raise RuntimeError(
            "Frozen Yan paper-facing inventory must stay at "
            f"{PAPER_73_INVENTORY_SIZE} slots, got {len(PAPER_73_FEATURE_SLOTS)}."
        )
    if paper_scope_override_map() != EXPECTED_PAPER_73_SCOPE_OVERRIDES:
        raise RuntimeError(
            "Frozen Yan paper-facing scope overrides drifted from the locked "
            "73-slot contract."
        )
    if paper_slot_scope_counts() != EXPECTED_PAPER_73_SCOPE_COUNTS:
        raise RuntimeError(
            "Frozen Yan paper-facing scope counts drifted from the locked "
            "73-slot contract."
        )
    if paper_slot_status_counts() != EXPECTED_PAPER_73_STATUS_COUNTS:
        raise RuntimeError(
            "Frozen Yan paper-facing status counts drifted from the locked "
            "73-slot contract."
        )


def paper_slot_status_counts() -> dict[FeatureStatus, int]:
    counts: dict[FeatureStatus, int] = {
        "implemented": 0,
        "proxyable": 0,
        "blocked": 0,
    }
    for slot in PAPER_73_FEATURE_SLOTS:
        counts[slot.status] += 1
    return counts


def paper_slot_scope_counts() -> dict[ScopeCode, int]:
    counts: dict[ScopeCode, int] = {
        "es": 0,
        "bs": 0,
        "ts": 0,
        "global": 0,
    }
    for slot in PAPER_73_FEATURE_SLOTS:
        counts[slot.scope_code] += 1
    return counts


def paper_slot_source_counts() -> dict[SourceKind, int]:
    counts: dict[SourceKind, int] = {
        "paper_text": 0,
        "table3": 0,
        "figure6_visible": 0,
        "paper_scope_expansion": 0,
    }
    for slot in PAPER_73_FEATURE_SLOTS:
        for source_kind in slot.source_kinds:
            counts[source_kind] += 1
    return counts


def paper_scope_evidence_counts() -> dict[PaperScopeEvidence, int]:
    counts: dict[PaperScopeEvidence, int] = {
        "working_global": 0,
        "working_scoped": 0,
        "figure6_unsuffixed": 0,
        "table3_global_formula": 0,
    }
    for slot in PAPER_73_FEATURE_SLOTS:
        counts[slot.scope_evidence] += 1
    return counts


__all__ = [
    "PAPER_73_FEATURE_SLOTS",
    "PAPER_73_INVENTORY_LOCKED",
    "PAPER_73_INVENTORY_SIZE",
    "EXPECTED_PAPER_73_SCOPE_COUNTS",
    "EXPECTED_PAPER_73_SCOPE_OVERRIDES",
    "EXPECTED_PAPER_73_STATUS_COUNTS",
    "PaperScopeEvidence",
    "Yan2023PaperSlot",
    "build_paper_73_slot_inventory",
    "paper_scope_evidence_counts",
    "paper_scope_override_map",
    "paper_slot_scope_counts",
    "paper_slot_source_counts",
    "paper_slot_status_counts",
    "validate_paper_73_inventory_lock",
]


validate_paper_73_inventory_lock()
