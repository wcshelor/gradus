"""Shared diagnostics and provenance containers — T01.3.

Provides immutable, deterministically serializable diagnostics that carry
source references. No layer-specific catalogs; callers use generic codes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .source import SourceRef

DIAGNOSTIC_SCHEMA_VERSION = "diagnostic.v1"
SUPPORTED_DIAGNOSTIC_VERSIONS = {DIAGNOSTIC_SCHEMA_VERSION}


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Immutable diagnostic with optional source evidence.

    - code: stable snake_case identifier (required)
    - severity: info/warning/error (required)
    - message: human-readable, not for parsing (required)
    - context: optional free-form dict for location/detail (e.g., measure_index)
              Must be JSON-serializable when present; keys sorted on serialize.
    - source_refs: optional tuple of SourceRef that evidence the diagnostic.
    """

    code: str
    severity: Severity
    message: str
    context: dict[str, Any] | None = None
    source_refs: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError(f"Diagnostic code must be non-empty str, got {self.code!r}")
        if not isinstance(self.severity, Severity):
            raise TypeError(f"Diagnostic severity must be Severity, got {type(self.severity).__name__}")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError(f"Diagnostic message must be non-empty str, got {self.message!r}")
        if self.context is not None and not isinstance(self.context, dict):
            raise TypeError("Diagnostic context must be dict or None")
        if not isinstance(self.source_refs, tuple):
            raise TypeError("Diagnostic source_refs must be tuple")
        for r in self.source_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(f"Diagnostic source_refs must contain SourceRef, got {type(r).__name__}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.context is not None:
            # deterministic: sort keys
            payload["context"] = {k: self.context[k] for k in sorted(self.context)}
        if self.source_refs:
            payload["source_refs"] = [r.to_dict() for r in self.source_refs]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Diagnostic":
        if not isinstance(data, dict):
            raise TypeError(f"Diagnostic requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_DIAGNOSTIC_VERSIONS:
            raise ValueError(
                f"unsupported Diagnostic schema_version {version!r}; supported: {sorted(SUPPORTED_DIAGNOSTIC_VERSIONS)}"
            )
        try:
            code = data["code"]
            severity_raw = data["severity"]
            message = data["message"]
        except KeyError as exc:
            raise ValueError(f"missing Diagnostic field {exc.args[0]!r}") from exc
        try:
            severity = Severity(severity_raw)
        except ValueError as exc:
            raise ValueError(f"unknown Severity {severity_raw!r}") from exc
        context = data.get("context")
        if context is not None and not isinstance(context, dict):
            raise ValueError(f"Diagnostic context must be dict, got {type(context).__name__}")
        raw_refs = data.get("source_refs", [])
        if not isinstance(raw_refs, list):
            raise ValueError("Diagnostic source_refs must be list")
        source_refs = tuple(SourceRef.from_dict(r) for r in raw_refs)
        return cls(code=code, severity=severity, message=message, context=context, source_refs=source_refs)
