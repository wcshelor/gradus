"""S8.2 source provenance fields for pedagogical text.

Distinguishes teacher-authored, learner-authored, literature paraphrase,
and system-generated text. Synthetic-only for thesis phase.

Design refs:
- semantic_music_extraction_tasks.md S8.2 (unsupported source category rejected)
- S8.1 corpus schema (separate human vs generated)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from passage_practice.models.diagnostics import Diagnostic

TEXT_PROVENANCE_SCHEMA_VERSION = "text_provenance.v1"
PEDAGOGICAL_TEXT_SCHEMA_VERSION = "pedagogical_text.v1"


class TextSourceCategory(str, Enum):
    TEACHER_AUTHORED = "teacher_authored"
    LEARNER_AUTHORED = "learner_authored"
    LITERATURE_PARAPHRASE = "literature_paraphrase"
    SYSTEM_GENERATED = "system_generated"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class PedagogicalText:
    """One pedagogical text fragment with source provenance.

    - ``text_id``: stable ID
    - ``content``: text content (synthetic for tests)
    - ``source_category``: one of the four controlled categories
    - ``author_id``: optional author identifier (teacher/learner ID or system version)
    - ``source_ref``: optional literature source identifier (e.g., lit.xxx)
    - ``provenance``: synthetic/human (committed fixtures are synthetic)
    - ``diagnostics``: e.g., synthetic_data
    """

    text_id: str
    content: str
    source_category: TextSourceCategory
    author_id: str | None = None
    source_ref: str | None = None
    provenance: str = "synthetic"
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = PEDAGOGICAL_TEXT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_id(self.text_id, "text_id")
        if not isinstance(self.content, str) or not self.content:
            raise ValueError(f"content must be non-empty str, got {self.content!r}")
        if not isinstance(self.source_category, TextSourceCategory):
            raise TypeError(f"source_category must be TextSourceCategory, got {type(self.source_category).__name__}")
        if self.author_id is not None:
            _check_id(self.author_id, "author_id")
        if self.source_ref is not None:
            _check_id(self.source_ref, "source_ref")
        if self.provenance not in ("synthetic", "human"):
            raise ValueError(f"provenance must be synthetic/human, got {self.provenance!r}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"diagnostics must contain Diagnostic, got {type(d).__name__}")
        if self.schema_version != PEDAGOGICAL_TEXT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {PEDAGOGICAL_TEXT_SCHEMA_VERSION!r}, got {self.schema_version!r}")
        # Category-specific validation: literature paraphrase must have source_ref
        if self.source_category == TextSourceCategory.LITERATURE_PARAPHRASE and not self.source_ref:
            raise ValueError("LITERATURE_PARAPHRASE requires source_ref (resolvable literature source identifier)")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "text_id": self.text_id,
            "content": self.content,
            "source_category": self.source_category.value,
            "provenance": self.provenance,
        }
        if self.author_id is not None:
            payload["author_id"] = self.author_id
        if self.source_ref is not None:
            payload["source_ref"] = self.source_ref
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PedagogicalText":
        if not isinstance(data, dict):
            raise TypeError(f"PedagogicalText requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version != PEDAGOGICAL_TEXT_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version {version!r}; expected {PEDAGOGICAL_TEXT_SCHEMA_VERSION!r}")
        try:
            text_id = data["text_id"]
            content = data["content"]
            source_category_raw = data["source_category"]
            provenance = data["provenance"]
        except KeyError as exc:
            raise ValueError(f"missing PedagogicalText field {exc.args[0]!r}") from exc
        try:
            source_category = TextSourceCategory(source_category_raw)
        except ValueError as exc:
            raise ValueError(f"unknown source_category {source_category_raw!r}") from exc
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("diagnostics must be list")
        return cls(
            text_id=str(text_id),
            content=str(content),
            source_category=source_category,
            author_id=str(data["author_id"]) if "author_id" in data else None,
            source_ref=str(data["source_ref"]) if "source_ref" in data else None,
            provenance=str(provenance),
            diagnostics=tuple(__import__("passage_practice.models.diagnostics", fromlist=["Diagnostic"]).Diagnostic.from_dict(d) for d in raw_diags),
        )


__all__ = ["PedagogicalText", "TextSourceCategory", "PEDAGOGICAL_TEXT_SCHEMA_VERSION", "TEXT_PROVENANCE_SCHEMA_VERSION"]
