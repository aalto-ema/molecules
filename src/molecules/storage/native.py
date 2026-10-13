"""Strict versioned JSON decoding and atomic document writes."""

import json
import os
import tempfile
from dataclasses import MISSING, asdict, fields
from pathlib import Path
from typing import Any

from molecules.domain.document import Arrow, Atom, Bond, Document, Note, Source

SCHEMA_VERSION = 4
MAX_FILE_BYTES = 10 * 1024 * 1024


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def _fields(value: Any, allowed: set[str], required: set[str]) -> None:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object.")
    if value.keys() - allowed or required - value.keys():
        raise ValueError("Document contains missing or unsupported fields.")


def load_document(path: Path) -> Document:
    with path.open("rb") as stream:
        content = stream.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 10 MiB size limit.")
    return decode_document(content)


def decode_document(content: bytes) -> Document:
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 10 MiB size limit.")
    try:
        data = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(data, dict):
            raise ValueError("Expected a document object.")
        version = data.get("schema_version")
        if type(version) is not int or version not in (1, 2, 3, SCHEMA_VERSION):
            raise ValueError("Unsupported document version; use a compatible app version.")
        allowed = {"schema_version", "title", "atoms", "bonds"}
        if version >= 2:
            allowed.add("sources")
        if version >= 3:
            allowed.update(("arrows", "notes"))
        _fields(data, allowed, {"schema_version", "title", "atoms", "bonds"})
        for name in ("atoms", "bonds", "sources", "arrows", "notes"):
            if not isinstance(data.get(name, []), list):
                raise ValueError(f"{name} must be an array.")
        atom_fields = (
            {f.name for f in fields(Atom)}
            if version >= 2
            else {"id", "element", "x", "y", "charge"}
        )
        bond_fields = (
            {f.name for f in fields(Bond)} if version >= 2 else {"id", "start", "end", "order"}
        )
        for atom in data["atoms"]:
            _fields(atom, atom_fields, {"id", "element", "x", "y"})
        for bond in data["bonds"]:
            _fields(bond, bond_fields, {"id", "start", "end"})
        for source in data.get("sources", []):
            _fields(source, {f.name for f in fields(Source)}, {f.name for f in fields(Source)})
        for name, cls in (("arrows", Arrow), ("notes", Note)):
            for entity in data.get(name, []):
                allowed_fields = {f.name for f in fields(cls)}
                if name == "arrows" and version < 4:
                    allowed_fields -= {
                        "label",
                        "label_side",
                        "label_offset",
                        "start_group",
                        "end_group",
                    }
                _fields(
                    entity,
                    allowed_fields,
                    {
                        f.name
                        for f in fields(cls)
                        if f.default is MISSING and f.default_factory is MISSING
                    },
                )
        document = Document(
            title=data["title"],
            atoms=[Atom(**atom) for atom in data["atoms"]],
            bonds=[Bond(**bond) for bond in data["bonds"]],
            sources=[Source(**source) for source in data.get("sources", [])],
            arrows=[Arrow(**arrow) for arrow in data.get("arrows", [])],
            notes=[Note(**note) for note in data.get("notes", [])],
        )
        document.validate()
        return document
    except (UnicodeError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid document data.") from exc


def save_document(document: Document, path: Path) -> None:
    document.validate()
    data = {"schema_version": SCHEMA_VERSION, **asdict(document)}
    content = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 10 MiB size limit.")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
