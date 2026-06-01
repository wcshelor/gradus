"""MusicXML and MXL loading helpers.

This module is intended to be the primary input boundary for the repository.
MusicXML should be the first-class source format because it preserves the score
structure needed for notation, coordination, articulation, and control-related
descriptors.

Planned responsibilities:

- open `.musicxml`, `.xml`, and `.mxl` files,
- resolve the primary score document inside an MXL archive,
- call the selected parser library,
- return a parser-native object plus source metadata,
- emit diagnostics for unsupported or ambiguous score structures.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

MUSICXML_PARSER_BACKEND = "partitura"
_SUPPORTED_SUFFIXES = {".musicxml", ".xml", ".mxl"}


@dataclass(slots=True)
class MusicXMLDocument:
    """Raw MusicXML payload and parsed XML root used by normalization."""

    source_path: Path
    root: ElementTree.Element
    xml_payload: bytes
    rootfile_path: str | None = None
    compressed: bool = False


def _coerce_score_path(path: str | Path) -> Path:
    score_path = Path(path).expanduser()
    suffix = score_path.suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(_SUPPORTED_SUFFIXES))
        raise ValueError(
            f"Unsupported MusicXML-family file '{score_path}'. "
            f"Expected one of: {supported}."
        )
    if not score_path.is_file():
        raise FileNotFoundError(score_path)
    return score_path


def _iter_parts(parsed_score: Any) -> list[Any]:
    parts = getattr(parsed_score, "parts", None)
    if parts is not None:
        return list(parts)

    if hasattr(parsed_score, "measures") and hasattr(parsed_score, "notes_tied"):
        return [parsed_score]

    if isinstance(parsed_score, Iterable) and not isinstance(
        parsed_score, (str, bytes, bytearray)
    ):
        return list(parsed_score)

    return []


def _read_mxl_archive_payload(path: str | Path) -> tuple[bytes, str]:
    """Return the main MusicXML payload and rootfile path from an MXL archive."""
    archive_path = _coerce_score_path(path)
    if archive_path.suffix.lower() != ".mxl":
        raise ValueError(f"Expected an .mxl file, got '{archive_path.name}'.")

    try:
        with ZipFile(archive_path) as archive:
            try:
                container_xml = archive.read("META-INF/container.xml")
            except KeyError as exc:
                raise ValueError(
                    f"MXL archive '{archive_path}' is missing META-INF/container.xml."
                ) from exc

            try:
                container_root = ElementTree.fromstring(container_xml)
            except ElementTree.ParseError as exc:
                raise ValueError(
                    f"MXL archive '{archive_path}' has a malformed container.xml."
                ) from exc

            rootfile_path = None
            for element in container_root.iter():
                if element.tag.endswith("rootfile"):
                    rootfile_path = element.get("full-path")
                    if rootfile_path:
                        break

            if not rootfile_path:
                raise ValueError(
                    f"MXL archive '{archive_path}' does not declare a primary score file."
                )

            try:
                return archive.read(rootfile_path), rootfile_path
            except KeyError as exc:
                raise ValueError(
                    f"MXL archive '{archive_path}' references missing score payload "
                    f"'{rootfile_path}'."
                ) from exc
    except BadZipFile as exc:
        raise ValueError(f"File '{archive_path}' is not a valid MXL archive.") from exc


def read_mxl_archive(path: str | Path) -> bytes:
    """Return the main MusicXML document payload from an MXL archive.

    The final implementation should read `META-INF/container.xml` rather than
    guessing the location of the score payload.
    """
    payload, _rootfile_path = _read_mxl_archive_payload(path)
    return payload


def load_musicxml_document(path: str | Path) -> MusicXMLDocument:
    """Load a MusicXML-family file as raw XML for normalization."""
    score_path = _coerce_score_path(path)

    if score_path.suffix.lower() == ".mxl":
        xml_payload, rootfile_path = _read_mxl_archive_payload(score_path)
        compressed = True
    else:
        xml_payload = score_path.read_bytes()
        rootfile_path = None
        compressed = False

    try:
        root = ElementTree.fromstring(xml_payload)
    except ElementTree.ParseError as exc:
        raise ValueError(f"MusicXML file '{score_path}' is malformed.") from exc

    return MusicXMLDocument(
        source_path=score_path,
        root=root,
        xml_payload=xml_payload,
        rootfile_path=rootfile_path,
        compressed=compressed,
    )


def load_musicxml(path: str | Path) -> Any:
    """Load a MusicXML-family score with the chosen parser backend.

    The return type is intentionally parser-native here. Downstream code should
    immediately hand the parser object to the normalization layer rather than
    using it directly.
    """
    try:
        from partitura.io.importmusicxml import (
            load_musicxml as _partitura_load_musicxml,
        )
    except ImportError as exc:
        raise ImportError(
            "partitura is required for load_musicxml(...). Use "
            "load_musicxml_document(...) for raw XML normalization without "
            "partitura."
        ) from exc

    score_path = _coerce_score_path(path)

    if score_path.suffix.lower() == ".mxl":
        xml_payload = read_mxl_archive(score_path)
        with TemporaryDirectory(prefix="piano-difficulty-mxl-") as tmpdir:
            extracted_path = Path(tmpdir) / f"{score_path.stem}.musicxml"
            extracted_path.write_bytes(xml_payload)
            return _partitura_load_musicxml(
                str(extracted_path),
                validate=False,
                force_note_ids="keep",
            )

    return _partitura_load_musicxml(
        str(score_path),
        validate=False,
        force_note_ids="keep",
    )


def validate_supported_score(parsed_score: Any) -> list[str]:
    """Perform lightweight parser-level checks before normalization.

    This validation step should identify cases such as:

    - clearly non-piano scores,
    - missing measure structure,
    - unsupported multi-part layouts,
    - malformed or incomplete parser output.
    """
    diagnostics: list[str] = []
    parts = _iter_parts(parsed_score)

    if not parts:
        return ["Parsed score contains no parts."]

    if len(parts) > 1:
        diagnostics.append(
            f"Parsed score contains {len(parts)} parts; current support is aimed at "
            "single-score piano layouts and may reject ensemble-style scores later."
        )

    total_measures = 0
    total_notes = 0
    has_grand_staff = False
    part_names: list[str] = []

    for part in parts:
        part_name = str(getattr(part, "part_name", "") or "").strip()
        if part_name:
            part_names.append(part_name.lower())

        measures = list(getattr(part, "measures", []))
        notes = list(getattr(part, "notes_tied", []))
        total_measures += len(measures)
        total_notes += len(notes)

        staff_count = getattr(part, "number_of_staves", None) or 0
        has_grand_staff = has_grand_staff or staff_count >= 2

    if total_measures == 0:
        diagnostics.append("Parsed score contains no measures.")

    if total_notes == 0:
        diagnostics.append("Parsed score contains no notes.")

    piano_name_tokens = ("piano", "pno", "pf", "klavier")
    looks_like_piano = has_grand_staff or any(
        any(token in name for token in piano_name_tokens) for name in part_names
    )

    if not looks_like_piano:
        diagnostics.append(
            "Parsed score does not advertise a piano part or grand-staff layout."
        )

    return diagnostics
