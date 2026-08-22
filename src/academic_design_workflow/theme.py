"""Typed schema for the complete cross-media visual language."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ThemeMeta(StrictModel):
    name: str
    version: int = Field(ge=1)
    description: str
    intent: list[str]
    avoid: list[str] = Field(default_factory=list)


class ColorToken(StrictModel):
    value: str
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    on_color: str | None = None
    usage: str

    @field_validator("value")
    @classmethod
    def valid_hex(cls, value: str) -> str:
        value = value.upper()
        if len(value) not in (4, 7, 9) or not value.startswith("#"):
            raise ValueError("colors must use #RGB, #RRGGBB, or #RRGGBBAA")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ValueError("invalid hexadecimal color") from exc
        return value


class ColorSystem(StrictModel):
    roles: dict[str, ColorToken]
    categorical: list[str]
    sequential: list[str]
    diverging: list[str]
    opacity: dict[str, float]

    @field_validator("opacity")
    @classmethod
    def valid_opacities(cls, values: dict[str, float]) -> dict[str, float]:
        if any(value < 0 or value > 1 for value in values.values()):
            raise ValueError("opacity tokens must be between 0 and 1")
        return values


class FontStack(StrictModel):
    family: list[str]
    weight: int = Field(ge=100, le=900)
    style: Literal["normal", "italic"] = "normal"
    letter_spacing_em: float = 0


class TypographySystem(StrictModel):
    sans: FontStack
    serif: FontStack
    mono: FontStack
    math: str
    roles_pt: dict[str, float]
    line_height: dict[str, float]
    casing: dict[str, Literal["none", "uppercase", "lowercase", "title"]]


class StrokeStyle(StrictModel):
    color: str
    width_pt: float = Field(ge=0)
    style: Literal["solid", "dashed", "dotted", "dashdot"] = "solid"
    cap: Literal["butt", "round", "projecting"] = "round"
    join: Literal["miter", "round", "bevel"] = "round"


class ShadowStyle(StrictModel):
    color: str
    opacity: float = Field(ge=0, le=1)
    blur: float = Field(ge=0)
    offset_x: float = 0
    offset_y: float = 0


class ShapeStyle(StrictModel):
    geometry: Literal["rectangle", "rounded_rectangle", "capsule", "circle", "line"]
    fill: str
    fill_opacity: float = Field(default=1, ge=0, le=1)
    stroke: StrokeStyle
    radius: float = Field(default=0, ge=0)
    padding: list[float] = Field(min_length=2, max_length=4)
    shadow: str = "none"
    emphasis: Literal["quiet", "normal", "strong"] = "normal"


class ShapeSystem(StrictModel):
    strokes: dict[str, StrokeStyle]
    shadows: dict[str, ShadowStyle]
    vocabulary: dict[str, ShapeStyle]
    arrowheads: dict[str, dict[str, float | str]]
    icon: dict[str, float | str]


class SpacingSystem(StrictModel):
    base: float = Field(gt=0)
    scale: list[float]
    density: Literal["compact", "balanced", "open"]


class LayoutSystem(StrictModel):
    figure_width_in: dict[str, float]
    aspect_ratios: dict[str, float]
    grid_columns: int = Field(ge=1)
    gutter: float = Field(ge=0)
    outer_margin: float = Field(ge=0)
    alignment: Literal["optical", "geometric"]
    reading_order: Literal["left_to_right", "top_to_bottom", "radial"]


class ChartSystem(StrictModel):
    axes: dict[str, float | str | bool]
    lines: dict[str, float | str]
    markers: dict[str, float | str]
    grid: dict[str, float | str | bool]
    legend: dict[str, float | str | bool]
    uncertainty: dict[str, float | str]
    rules: list[str]


class WebSystem(StrictModel):
    content_width_px: int = Field(gt=0)
    breakpoints_px: dict[str, int]
    radius_scale_px: dict[str, float]
    focus_ring: dict[str, float | str]
    transitions_ms: dict[str, int]


class MotionCurve(StrictModel):
    duration_ms: int = Field(ge=0)
    easing: str
    distance_px: float = Field(ge=0)
    opacity_from: float = Field(ge=0, le=1)


class MotionSystem(StrictModel):
    principles: list[str]
    curves: dict[str, MotionCurve]
    reduced_motion: Literal["remove", "crossfade", "shorten"]


class VideoSystem(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    safe_area_percent: float = Field(ge=0, le=25)
    title_duration_s: float = Field(gt=0)
    transition: str
    caption: dict[str, float | str]


class Theme(StrictModel):
    meta: ThemeMeta
    color: ColorSystem
    typography: TypographySystem
    shape: ShapeSystem
    spacing: SpacingSystem
    layout: LayoutSystem
    chart: ChartSystem
    web: WebSystem
    motion: MotionSystem
    video: VideoSystem

    @model_validator(mode="after")
    def references_exist(self) -> "Theme":
        roles = set(self.color.roles)
        referenced = []
        for stroke in self.shape.strokes.values():
            referenced.append(stroke.color)
        for shape in self.shape.vocabulary.values():
            referenced.extend((shape.fill, shape.stroke.color))
            if shape.shadow != "none" and shape.shadow not in self.shape.shadows:
                raise ValueError(f"unknown shadow token: {shape.shadow}")
        missing = sorted({name for name in referenced if name not in roles and name != "none"})
        if missing:
            raise ValueError(f"unknown semantic color roles: {', '.join(missing)}")
        return self

    def color_value(self, role: str) -> str:
        try:
            return self.color.roles[role].value
        except KeyError as exc:
            raise KeyError(f"unknown theme color role: {role}") from exc


def load_theme(path: str | Path) -> Theme:
    """Load and validate a YAML theme."""
    with Path(path).open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return Theme.model_validate(raw)
