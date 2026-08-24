"""Read-only structural audit and semantic diff for VSDX OPC packages."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cell_value(shape: ET.Element, name: str) -> str | None:
    for child in shape:
        if _local(child.tag) == "Cell" and child.attrib.get("N") == name:
            return child.attrib.get("V", child.attrib.get("F"))
    return None


def _shape_data(shape: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for section in shape:
        if _local(section.tag) != "Section" or section.attrib.get("N") != "Property":
            continue
        for row in section:
            if _local(row.tag) != "Row":
                continue
            row_name = row.attrib.get("N")
            if not row_name:
                continue
            for cell in row:
                if _local(cell.tag) == "Cell" and cell.attrib.get("N") == "Value":
                    raw = cell.attrib.get("V", cell.attrib.get("F", ""))
                    if raw.startswith('"') and raw.endswith('"'):
                        raw = raw[1:-1].replace('""', '"')
                    result[row_name] = raw
    return result


def _shape_inventory(root: ET.Element) -> list[dict[str, Any]]:
    inventory = []
    for shape in root.iter():
        if _local(shape.tag) != "Shape":
            continue
        data = _shape_data(shape)
        text = ""
        for child in shape:
            if _local(child.tag) == "Text":
                text = "".join(child.itertext()).strip()
                break
        inventory.append(
            {
                "sheet_id": shape.attrib.get("ID"),
                "name_u": shape.attrib.get("NameU"),
                "type": shape.attrib.get("Type", "Shape"),
                "one_d": _cell_value(shape, "OneD") == "1",
                "semantic_id": data.get("SemanticID"),
                "role": data.get("Role"),
                "parent_semantic_id": data.get("ParentSemanticID"),
                "source": data.get("Source"),
                "target": data.get("Target"),
                "shape_data": data,
                "text": text,
                "geometry": {
                    name: _cell_value(shape, name)
                    for name in ("PinX", "PinY", "Width", "Height", "BeginX", "BeginY", "EndX", "EndY")
                    if _cell_value(shape, name) is not None
                },
                "style": {
                    name: _cell_value(shape, name)
                    for name in (
                        "FillForegnd",
                        "FillForegndTrans",
                        "FillPattern",
                        "LineColor",
                        "LineWeight",
                        "LinePattern",
                        "EndArrow",
                    )
                    if _cell_value(shape, name) is not None
                },
            }
        )
    return inventory


def audit_vsdx(path: str | Path) -> dict[str, Any]:
    """Audit VSDX structure without opening Visio or mutating the package."""
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    with zipfile.ZipFile(candidate) as package:
        names = sorted(package.namelist())
        page_parts = [
            name
            for name in names
            if name.startswith("visio/pages/page")
            and name.endswith(".xml")
            and Path(name).name != "pages.xml"
        ]
        shapes: list[dict[str, Any]] = []
        connects: list[dict[str, str]] = []
        page_shape_data: dict[str, str] = {}
        foreign_data_records = 0
        for part in page_parts:
            root = ET.fromstring(package.read(part))
            shapes.extend(_shape_inventory(root))
            for element in root:
                if _local(element.tag) == "PageSheet":
                    page_shape_data.update(_shape_data(element))
            for element in root.iter():
                name = _local(element.tag)
                if name == "Connect":
                    connects.append(dict(sorted(element.attrib.items())))
                elif name == "ForeignData":
                    foreign_data_records += 1
        pages_index = "visio/pages/pages.xml"
        if pages_index in names:
            pages_root = ET.fromstring(package.read(pages_index))
            for element in pages_root.iter():
                if _local(element.tag) == "PageSheet":
                    page_shape_data.update(_shape_data(element))

    semantic_ids = [shape["semantic_id"] for shape in shapes if shape["semantic_id"]]
    duplicate_semantic_ids = sorted(
        {semantic_id for semantic_id in semantic_ids if semantic_ids.count(semantic_id) > 1}
    )
    media_parts = [name for name in names if name.startswith("visio/media/")]
    import_named_parts = [
        name for name in names if any(token in name.lower() for token in ("foreign", "image"))
    ]
    groups = [shape for shape in shapes if shape["type"] == "Group"]
    foreign_shapes = [shape for shape in shapes if shape["type"] == "Foreign"]
    connectors = [shape for shape in shapes if shape["one_d"] or shape["source"]]
    native_shapes = [shape for shape in shapes if shape["type"] not in {"Group", "Foreign"}]
    violations = []
    if groups:
        violations.append(f"contains {len(groups)} group records")
    if foreign_shapes or foreign_data_records:
        violations.append("contains foreign shapes or ForeignData")
    if media_parts or import_named_parts:
        violations.append("contains media or import/image-named package parts")
    if duplicate_semantic_ids:
        violations.append("contains duplicate semantic IDs")
    if len(semantic_ids) != len(shapes):
        violations.append("not every shape has a semantic ID")
    if len(connects) != 2 * len(connectors):
        violations.append("connector glue count is not exactly two per connector")
    return {
        "audit_version": "1.0",
        "path": str(candidate.resolve()),
        "sha256": _sha256(candidate),
        "size_bytes": candidate.stat().st_size,
        "package_parts": len(names),
        "page_parts": page_parts,
        "shape_records": len(shapes),
        "native_shape_records": len(native_shapes),
        "group_records": len(groups),
        "foreign_shape_records": len(foreign_shapes),
        "foreign_data_records": foreign_data_records,
        "media_parts": media_parts,
        "import_or_image_named_parts": import_named_parts,
        "semantic_shape_records": len(semantic_ids),
        "duplicate_semantic_ids": duplicate_semantic_ids,
        "page_shape_data": page_shape_data,
        "connector_records": len(connectors),
        "connect_records": len(connects),
        "native_semantic_pass": not violations,
        "native_semantic_violations": violations,
        "shapes": shapes,
        "connects": sorted(connects, key=json.dumps),
    }


def _semantic_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for shape in audit.get("shapes", []):
        semantic_id = shape.get("semantic_id")
        if semantic_id:
            if semantic_id in result:
                raise ValueError(f"audit contains ambiguous semantic ID {semantic_id!r}")
            result[semantic_id] = shape
    return result


def diff_audits(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return a machine-readable semantic and connector-relationship diff."""
    before_map = _semantic_map(before)
    after_map = _semantic_map(after)
    before_ids = set(before_map)
    after_ids = set(after_map)
    changed = []
    for semantic_id in sorted(before_ids & after_ids):
        left = before_map[semantic_id]
        right = after_map[semantic_id]
        fields = {
            field: {"before": left.get(field), "after": right.get(field)}
            for field in (
                "name_u",
                "type",
                "one_d",
                "role",
                "parent_semantic_id",
                "shape_data",
                "text",
                "geometry",
                "style",
            )
            if left.get(field) != right.get(field)
        }
        if fields:
            changed.append({"semantic_id": semantic_id, "fields": fields})
    before_connects = {json.dumps(item, sort_keys=True) for item in before.get("connects", [])}
    after_connects = {json.dumps(item, sort_keys=True) for item in after.get("connects", [])}
    return {
        "diff_version": "1.0",
        "before_sha256": before.get("sha256"),
        "after_sha256": after.get("sha256"),
        "added_semantic_ids": sorted(after_ids - before_ids),
        "removed_semantic_ids": sorted(before_ids - after_ids),
        "changed": changed,
        "connects_added": [json.loads(item) for item in sorted(after_connects - before_connects)],
        "connects_removed": [json.loads(item) for item in sorted(before_connects - after_connects)],
    }
