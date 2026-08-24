"""Versioned declarative contract for native, semantically editable Visio scenes."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCENE_SCHEMA_VERSION = "1.0"
EDIT_SCHEMA_VERSION = "1.0"
SEMANTIC_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_-]*$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(StrictModel):
    x: float
    y: float

    @model_validator(mode="after")
    def finite(self) -> Point:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("point coordinates must be finite")
        return self


class PageSpec(StrictModel):
    name: str = Field(min_length=1)
    coordinate_width: float = Field(gt=0)
    coordinate_height: float = Field(gt=0)
    width_in: float = Field(gt=0)
    height_in: float = Field(gt=0)


class ThemeSpec(StrictModel):
    font_family: str = Field(min_length=1)
    colors: dict[str, str]

    @field_validator("colors")
    @classmethod
    def valid_colors(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("theme.colors must define at least one semantic color role")
        invalid = sorted(name for name, color in value.items() if not HEX_PATTERN.fullmatch(color))
        if invalid:
            raise ValueError(f"theme color roles must use #RRGGBB: {', '.join(invalid)}")
        return {name: color.upper() for name, color in value.items()}


class PortSpec(StrictModel):
    name: str = Field(pattern=SEMANTIC_ID_PATTERN)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    direction_x: float = Field(default=0, ge=-1, le=1)
    direction_y: float = Field(default=0, ge=-1, le=1)


class ShapeStyle(StrictModel):
    fill_role: str
    stroke_role: str
    text_role: str
    fill_opacity: float = Field(default=1, ge=0, le=1)
    line_width_pt: float = Field(default=0.75, ge=0)
    line_pattern: Literal["solid", "dashed", "dotted"] = "solid"
    radius: float = Field(default=0.06, ge=0)
    font_size_pt: float = Field(default=8, gt=0)
    font_weight: int = Field(default=400, ge=100, le=900)
    align: Literal["left", "center", "right"] = "center"


class TextRun(StrictModel):
    """A half-open native text range with local size and weight overrides."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    font_size_pt: float = Field(gt=0)
    font_weight: int = Field(default=400, ge=100, le=900)

    @model_validator(mode="after")
    def ordered(self) -> TextRun:
        if self.end <= self.start:
            raise ValueError("text run end must be greater than start")
        return self


class ConnectorStyle(StrictModel):
    stroke_role: str
    line_width_pt: float = Field(default=0.9, gt=0)
    line_pattern: Literal["solid", "dashed", "dotted"] = "solid"
    arrowhead: Literal["none", "standard", "open"] = "standard"


class ShapeSpec(StrictModel):
    id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    role: str = Field(min_length=1)
    kind: Literal["rectangle", "rounded_rectangle", "ellipse", "text"]
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    text: str = ""
    parent: str | None = Field(default=None, pattern=SEMANTIC_ID_PATTERN)
    data: dict[str, str] = Field(default_factory=dict)
    ports: list[PortSpec] = Field(default_factory=list)
    text_runs: list[TextRun] = Field(default_factory=list)
    style: ShapeStyle

    @field_validator("data")
    @classmethod
    def valid_shape_data(cls, value: dict[str, str]) -> dict[str, str]:
        invalid = sorted(key for key in value if re.fullmatch(SEMANTIC_ID_PATTERN, key) is None)
        if invalid:
            raise ValueError(
                "shape data keys must be stable semantic identifiers: " + ", ".join(invalid)
            )
        reserved = sorted(set(value) & {"SemanticID", "Role", "ParentSemanticID", "Source", "Target"})
        if reserved:
            raise ValueError("shape data keys are reserved: " + ", ".join(reserved))
        return value

    @model_validator(mode="after")
    def valid_geometry_and_ports(self) -> ShapeSpec:
        values = (self.x, self.y, self.width, self.height)
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"shape {self.id!r} geometry must be finite")
        names = [port.name for port in self.ports]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"shape {self.id!r} has duplicate ports: {', '.join(duplicates)}")
        ordered_runs = sorted(self.text_runs, key=lambda run: (run.start, run.end))
        for index, run in enumerate(ordered_runs):
            if run.end > len(self.text):
                raise ValueError(f"shape {self.id!r} text run exceeds text length")
            if index and ordered_runs[index - 1].end > run.start:
                raise ValueError(f"shape {self.id!r} has overlapping text runs")
        return self


class Endpoint(StrictModel):
    shape_id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    port: str = Field(pattern=SEMANTIC_ID_PATTERN)


class ConnectorSpec(StrictModel):
    id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    role: str = Field(min_length=1)
    source: Endpoint
    target: Endpoint
    route: list[Point] = Field(default_factory=list)
    style: ConnectorStyle

    @field_validator("route")
    @classmethod
    def route_has_enough_points(cls, value: list[Point]) -> list[Point]:
        if value and len(value) < 2:
            raise ValueError("an explicit connector route needs at least two points")
        return value


class Scene(StrictModel):
    schema_version: Literal[SCENE_SCHEMA_VERSION]
    scene_id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    revision: int = Field(ge=1)
    page: PageSpec
    theme: ThemeSpec
    metadata: dict[str, str] = Field(default_factory=dict)
    shapes: list[ShapeSpec]
    connectors: list[ConnectorSpec] = Field(default_factory=list)

    @field_validator("metadata")
    @classmethod
    def valid_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        invalid = sorted(key for key in value if re.fullmatch(SEMANTIC_ID_PATTERN, key) is None)
        if invalid:
            raise ValueError(
                "scene metadata keys must be stable semantic identifiers: " + ", ".join(invalid)
            )
        reserved = sorted(set(value) & {"SceneID", "SceneSchema", "SceneHash"})
        if reserved:
            raise ValueError("scene metadata keys are reserved: " + ", ".join(reserved))
        return value

    @model_validator(mode="after")
    def semantic_integrity(self) -> Scene:
        identifiers = [item.id for item in [*self.shapes, *self.connectors]]
        duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
        if duplicates:
            raise ValueError(f"duplicate semantic IDs: {', '.join(duplicates)}")

        shapes = {shape.id: shape for shape in self.shapes}
        color_roles = set(self.theme.colors)
        for shape in self.shapes:
            if shape.x < 0 or shape.y < 0:
                raise ValueError(f"shape {shape.id!r} starts outside the coordinate space")
            if shape.x + shape.width > self.page.coordinate_width:
                raise ValueError(f"shape {shape.id!r} exceeds page coordinate width")
            if shape.y + shape.height > self.page.coordinate_height:
                raise ValueError(f"shape {shape.id!r} exceeds page coordinate height")
            used_roles = {
                shape.style.fill_role,
                shape.style.stroke_role,
                shape.style.text_role,
            }
            missing = sorted(used_roles - color_roles)
            if missing:
                raise ValueError(f"shape {shape.id!r} uses unknown color roles: {', '.join(missing)}")
            if shape.parent is not None and shape.parent not in shapes:
                raise ValueError(f"shape {shape.id!r} has dangling parent {shape.parent!r}")
            if shape.parent == shape.id:
                raise ValueError(f"shape {shape.id!r} cannot parent itself")

        for shape in self.shapes:
            seen = {shape.id}
            parent = shape.parent
            while parent is not None:
                if parent in seen:
                    raise ValueError(f"shape hierarchy contains a cycle through {shape.id!r}")
                seen.add(parent)
                parent = shapes[parent].parent

        for connector in self.connectors:
            if connector.style.stroke_role not in color_roles:
                raise ValueError(
                    f"connector {connector.id!r} uses unknown color role "
                    f"{connector.style.stroke_role!r}"
                )
            for point in connector.route:
                if not (0 <= point.x <= self.page.coordinate_width):
                    raise ValueError(f"connector {connector.id!r} route exceeds page width")
                if not (0 <= point.y <= self.page.coordinate_height):
                    raise ValueError(f"connector {connector.id!r} route exceeds page height")
            for side, endpoint in (("source", connector.source), ("target", connector.target)):
                shape = shapes.get(endpoint.shape_id)
                if shape is None:
                    raise ValueError(
                        f"connector {connector.id!r} has dangling {side} shape "
                        f"{endpoint.shape_id!r}"
                    )
                ports = {port.name for port in shape.ports}
                if endpoint.port not in ports:
                    raise ValueError(
                        f"connector {connector.id!r} references missing {side} port "
                        f"{endpoint.shape_id}.{endpoint.port}"
                    )
        return self

    def semantic_ids(self) -> set[str]:
        return {item.id for item in [*self.shapes, *self.connectors]}

    def element(self, semantic_id: str) -> ShapeSpec | ConnectorSpec:
        matches = [item for item in [*self.shapes, *self.connectors] if item.id == semantic_id]
        if len(matches) != 1:
            raise KeyError(f"expected exactly one element for semantic ID {semantic_id!r}")
        return matches[0]


class ElementPatch(StrictModel):
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    text: str | None = None
    style: dict[str, Any] | None = None

    @model_validator(mode="after")
    def not_empty(self) -> ElementPatch:
        if not self.model_fields_set or all(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("edit patch must set at least one field")
        return self


class EditOperation(StrictModel):
    target_id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    expected_element_sha256: str = Field(pattern=SHA256_PATTERN)
    set: ElementPatch


class EditRequest(StrictModel):
    schema_version: Literal[EDIT_SCHEMA_VERSION]
    scene_id: str = Field(pattern=SEMANTIC_ID_PATTERN)
    base_scene_sha256: str = Field(pattern=SHA256_PATTERN)
    edits: list[EditOperation] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_targets(self) -> EditRequest:
        targets = [edit.target_id for edit in self.edits]
        duplicates = sorted({target for target in targets if targets.count(target) > 1})
        if duplicates:
            raise ValueError(f"ambiguous edits repeat targets: {', '.join(duplicates)}")
        return self


def canonical_data(model: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(model, BaseModel):
        data = model.model_dump(mode="json", exclude_none=True)
        # Optional provenance was added after schema 1.0 shipped. Empty values are
        # omitted from canonical hashes so existing scenes and stale-bound edit
        # requests retain their original identity.
        if isinstance(model, Scene):
            if not data.get("metadata"):
                data.pop("metadata", None)
            for shape in data.get("shapes", []):
                if not shape.get("data"):
                    shape.pop("data", None)
                if not shape.get("text_runs"):
                    shape.pop("text_runs", None)
        elif isinstance(model, ShapeSpec):
            if not data.get("data"):
                data.pop("data", None)
            if not data.get("text_runs"):
                data.pop("text_runs", None)
        return data
    return model


def canonical_json(model: BaseModel | dict[str, Any]) -> str:
    return json.dumps(canonical_data(model), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def semantic_sha256(model: BaseModel | dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(model).encode("utf-8")).hexdigest()


def load_scene_data(data: Any) -> Scene:
    return Scene.model_validate(data)


def load_edit_data(data: Any) -> EditRequest:
    return EditRequest.model_validate(data)
