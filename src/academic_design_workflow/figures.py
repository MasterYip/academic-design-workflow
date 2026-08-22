"""Theme-bound vector primitives for plots and scientific schematics."""

from __future__ import annotations

from collections.abc import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import (
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    PathPatch,
    Polygon,
    Rectangle,
)
from matplotlib.path import Path

from .compiler import matplotlib_rc
from .theme import ShapeStyle, Theme


def apply_theme(theme: Theme) -> None:
    mpl.rcParams.update(matplotlib_rc(theme))


def canvas(
    theme: Theme,
    *,
    width: str = "double_column",
    aspect: str = "wide",
    xlim: tuple[float, float] = (0, 12),
    ylim: tuple[float, float] = (0, 7),
) -> tuple[Figure, Axes]:
    apply_theme(theme)
    figure_width = theme.layout.figure_width_in[width]
    ratio = theme.layout.aspect_ratios[aspect]
    fig, ax = plt.subplots(figsize=(figure_width, figure_width / ratio))
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis("off")
    return fig, ax


def _shape(theme: Theme, name: str) -> ShapeStyle:
    try:
        return theme.shape.vocabulary[name]
    except KeyError as exc:
        raise KeyError(f"unknown shape token: {name}") from exc


def box(
    ax: Axes,
    theme: Theme,
    bounds: tuple[float, float, float, float],
    *,
    style: str = "module",
    title: str = "",
    detail: str = "",
    zorder: int = 2,
) -> FancyBboxPatch:
    x, y, width, height = bounds
    token = _shape(theme, style)
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle=f"round,pad=0,rounding_size={token.radius}",
        facecolor=theme.color_value(token.fill),
        alpha=token.fill_opacity,
        edgecolor=theme.color_value(token.stroke.color),
        linewidth=token.stroke.width_pt,
        linestyle=token.stroke.style,
        joinstyle=token.stroke.join,
        zorder=zorder,
    )
    ax.add_patch(patch)
    if title:
        ax.text(
            x + width / 2, y + height * (0.58 if detail else 0.5), title,
            ha="center", va="center", fontweight="bold",
            fontsize=theme.typography.roles_pt["label"],
            color=theme.color_value("text_primary"), zorder=zorder + 2,
        )
    if detail:
        ax.text(
            x + width / 2, y + height * 0.28, detail,
            ha="center", va="center",
            fontsize=theme.typography.roles_pt["caption"],
            color=theme.color_value("text_secondary"), zorder=zorder + 2,
        )
    return patch


def styled_shape(
    ax: Axes,
    theme: Theme,
    bounds: tuple[float, float, float, float],
    *,
    style: str,
    title: str = "",
    role: str | None = None,
    zorder: int = 2,
):
    """Draw the theme's shape vocabulary, including technical diagram motifs."""
    x, y, width, height = bounds
    token = _shape(theme, style)
    fill_role = role or token.fill
    face = theme.color_value(fill_role)
    edge = theme.color_value(token.stroke.color)
    common = {
        "facecolor": face,
        "edgecolor": edge,
        "linewidth": token.stroke.width_pt,
        "linestyle": token.stroke.style,
        "joinstyle": token.stroke.join,
        "alpha": token.fill_opacity,
        "zorder": zorder,
    }
    if token.geometry in {"rounded_rectangle", "capsule"}:
        radius = height / 2 if token.geometry == "capsule" else token.radius
        patch = FancyBboxPatch((x, y), width, height,
                               boxstyle=f"round,pad=0,rounding_size={radius}", **common)
    elif token.geometry == "trapezoid":
        inset = min(width * 0.22, height * 0.28)
        patch = Polygon([(x, y), (x + width, y + inset), (x + width, y + height - inset),
                         (x, y + height)], closed=True, **common)
    elif token.geometry == "clipped_header":
        clip = min(width * 0.10, height * 0.55)
        patch = Polygon([(x, y), (x + width, y), (x + width - clip, y + height),
                         (x, y + height)], closed=True, **common)
    elif token.geometry == "rounded_top_rectangle":
        radius = min(token.radius, width / 2, height)
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + height - radius),
            (x + width, y + height),
            (x + width - radius, y + height),
            (x + radius, y + height),
            (x, y + height),
            (x, y + height - radius),
            (x, y),
        ]
        codes = [
            Path.MOVETO,
            Path.LINETO,
            Path.LINETO,
            Path.CURVE3,
            Path.CURVE3,
            Path.LINETO,
            Path.CURVE3,
            Path.CURVE3,
            Path.CLOSEPOLY,
        ]
        patch = PathPatch(Path(vertices, codes), **common)
    elif token.geometry in {"cylinder", "layered_cylinder"}:
        ring_height = height * 0.20
        lower_center = y + height * 0.14
        body_top = y + height * (0.84 if token.geometry == "cylinder" else 0.78)
        body = Rectangle((x, lower_center), width, body_top - lower_center, **common)
        ax.add_patch(body)
        ax.add_patch(Ellipse((x + width / 2, lower_center), width, ring_height, **common))
        if token.geometry == "layered_cylinder":
            ring_centers = [y + height * value for value in (0.78, 0.85, 0.92)]
            for center in ring_centers[:-1]:
                ax.add_patch(Ellipse((x + width / 2, center), width, ring_height, **common))
            patch = Ellipse(
                (x + width / 2, ring_centers[-1]), width, ring_height, **common
            )
        else:
            patch = Ellipse(
                (x + width / 2, y + height * 0.88), width, height * 0.24, **common
            )
    elif token.geometry == "circle":
        patch = Ellipse((x + width / 2, y + height / 2), width, height, **common)
    else:
        patch = Rectangle((x, y), width, height, **common)
    ax.add_patch(patch)
    if title:
        text_color = theme.color.roles[fill_role].on_color or "text_primary"
        ax.text(x + width / 2, y + height / 2, title, ha="center", va="center",
                fontsize=theme.typography.roles_pt["caption"], fontweight="bold",
                color=theme.color_value(text_color), zorder=zorder + 2)
    return patch


def semantic_row(
    ax: Axes,
    theme: Theme,
    bounds: tuple[float, float, float, float],
    labels: Iterable[str],
    *,
    active_index: int = 0,
    zorder: int = 2,
) -> list:
    """Draw a compact segmented widget with one semantically active segment."""
    items = tuple(labels)
    if not items:
        raise ValueError("semantic rows require at least one segment")
    if not 0 <= active_index < len(items):
        raise ValueError("active segment index is outside the semantic row")
    x, y, width, height = bounds
    outer = styled_shape(ax, theme, bounds, style="widget_row", zorder=zorder)
    gap = min(width * 0.012, 0.06)
    inset = min(height * 0.10, 0.07)
    segment_width = (width - inset * 2 - gap * (len(items) - 1)) / len(items)
    patches = [outer]
    for index, label in enumerate(items):
        segment_x = x + inset + index * (segment_width + gap)
        style = "widget_segment_active" if index == active_index else "widget_segment"
        segment = styled_shape(
            ax,
            theme,
            (segment_x, y + inset, segment_width, height - inset * 2),
            style=style,
            zorder=zorder + 1,
        )
        patches.append(segment)
        text_role = "text_inverse" if index == active_index else "text_primary"
        ax.text(
            segment_x + segment_width / 2,
            y + height / 2,
            label,
            ha="center",
            va="center",
            fontsize=theme.typography.roles_pt["caption"],
            color=theme.color_value(text_role),
            zorder=zorder + 3,
        )
    return patches


def compound_node(
    ax: Axes,
    theme: Theme,
    bounds: tuple[float, float, float, float],
    *,
    title: str,
    detail: str,
    badge: str = "",
    focal: bool = False,
    port_labels: tuple[str, str] = ("in", "out"),
    zorder: int = 3,
) -> dict[str, object]:
    """Draw a hierarchical graph node with a title band, badge, and explicit ports."""
    x, y, width, height = bounds
    style = "graph_node_focal" if focal else "graph_node"
    node = styled_shape(ax, theme, bounds, style=style, zorder=zorder)
    inset = min(width * 0.045, 0.10)
    header_height = height * 0.30
    header = styled_shape(
        ax,
        theme,
        (x + inset, y + height - header_height - inset, width - inset * 2, header_height),
        style="graph_node_header",
        zorder=zorder + 1,
    )
    ax.text(
        x + inset * 2,
        y + height - header_height / 2 - inset,
        title,
        ha="left",
        va="center",
        fontsize=theme.typography.roles_pt["label"],
        fontweight="bold",
        color=theme.color_value("text_primary"),
        zorder=zorder + 3,
    )
    ax.text(
        x + inset * 2,
        y + height * 0.34,
        detail,
        ha="left",
        va="center",
        fontsize=theme.typography.roles_pt["micro"],
        color=theme.color_value("text_secondary"),
        zorder=zorder + 3,
    )
    port_size = min(height * 0.18, width * 0.10)
    port_y = y + height * 0.42 - port_size / 2
    input_port = styled_shape(
        ax,
        theme,
        (x - port_size / 2, port_y, port_size, port_size),
        style="graph_port",
        zorder=zorder + 3,
    )
    output_style = "graph_port_focal" if focal else "graph_port"
    output_port = styled_shape(
        ax,
        theme,
        (x + width - port_size / 2, port_y, port_size, port_size),
        style=output_style,
        zorder=zorder + 3,
    )
    for port_x, label, alignment in (
        (x + port_size * 0.75, port_labels[0], "left"),
        (x + width - port_size * 0.75, port_labels[1], "right"),
    ):
        ax.text(
            port_x,
            y + height * 0.14,
            label,
            ha=alignment,
            va="center",
            fontsize=theme.typography.roles_pt["micro"],
            color=theme.color_value("text_secondary"),
            zorder=zorder + 3,
        )
    badge_patch = None
    if badge:
        badge_width = min(width * 0.38, max(width * 0.22, len(badge) * width * 0.035))
        badge_patch = styled_shape(
            ax,
            theme,
            (x + width - badge_width - inset, y + inset, badge_width, height * 0.20),
            style="semantic_badge",
            title=badge,
            zorder=zorder + 2,
        )
    return {
        "node": node,
        "header": header,
        "input_port": input_port,
        "output_port": output_port,
        "badge": badge_patch,
    }


def panel(
    ax: Axes,
    theme: Theme,
    bounds: tuple[float, float, float, float],
    title: str,
    *,
    label: str = "",
) -> None:
    """Draw a technical panel with a theme-specific header rail."""
    x, y, width, height = bounds
    container_style = (
        "panel_container" if "panel_container" in theme.shape.vocabulary else "field"
    )
    styled_shape(ax, theme, bounds, style=container_style, zorder=0)
    header_height = min(0.55, height * 0.17)
    header_style = "panel_header" if "panel_header" in theme.shape.vocabulary else "tag"
    styled_shape(ax, theme, (x, y + height - header_height, width, header_height),
                 style=header_style, zorder=1)
    prefix = f"({label}) " if label else ""
    ax.text(x + 0.16, y + height - header_height / 2, prefix + title,
            ha="left", va="center", color=theme.color_value("text_inverse"),
            fontsize=theme.typography.roles_pt["section_title"], fontweight="bold", zorder=3)


def arrow(
    ax: Axes,
    theme: Theme,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    role: str | None = None,
    style: str = "flow",
    zorder: int = 3,
) -> FancyArrowPatch:
    stroke = theme.shape.strokes[style]
    head = theme.shape.arrowheads["standard"]
    patch = FancyArrowPatch(
        start, end,
        arrowstyle=str(head["style"]),
        mutation_scale=float(head["scale"]),
        color=theme.color_value(role or stroke.color),
        linewidth=stroke.width_pt,
        linestyle=stroke.style,
        shrinkA=1.5, shrinkB=1.5,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def token_row(
    ax: Axes,
    theme: Theme,
    origin: tuple[float, float],
    labels: Iterable[str],
    *,
    roles: tuple[str, ...] = ("data_primary",),
    width: float = 0.48,
    height: float = 0.40,
    gap: float = 0.09,
) -> None:
    x, y = origin
    for index, label in enumerate(labels):
        role = roles[index % len(roles)]
        token = _shape(theme, "token")
        patch = FancyBboxPatch(
            (x + index * (width + gap), y), width, height,
            boxstyle=f"round,pad=0,rounding_size={token.radius}",
            facecolor=theme.color_value(role), alpha=theme.color.opacity["subtle"],
            edgecolor=theme.color_value(role), linewidth=token.stroke.width_pt,
        )
        ax.add_patch(patch)
        ax.text(
            x + index * (width + gap) + width / 2, y + height / 2, label,
            ha="center", va="center", fontsize=theme.typography.roles_pt["caption"],
            color=theme.color_value("text_primary"),
        )


def save_vector_bundle(fig: Figure, stem: str) -> list[str]:
    outputs = []
    for suffix, dpi in (("svg", None), ("pdf", None), ("png", 220)):
        path = f"{stem}.{suffix}"
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.02)
        outputs.append(path)
    return outputs
