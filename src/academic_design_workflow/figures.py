"""Theme-bound vector primitives for plots and scientific schematics."""

from __future__ import annotations

from collections.abc import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

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
    common = dict(facecolor=face, edgecolor=edge, linewidth=token.stroke.width_pt,
                  alpha=token.fill_opacity, zorder=zorder)
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
    elif token.geometry == "cylinder":
        patch = Rectangle((x, y + height * 0.12), width, height * 0.76, **common)
        ax.add_patch(patch)
        ax.add_patch(Ellipse((x + width / 2, y + height * 0.88), width, height * 0.24, **common))
        ax.add_patch(Ellipse((x + width / 2, y + height * 0.12), width, height * 0.24, **common))
    elif token.geometry == "circle":
        patch = Ellipse((x + width / 2, y + height / 2), width, height, **common)
    else:
        patch = Rectangle((x, y), width, height, **common)
    ax.add_patch(patch)
    if title:
        text_color = "text_inverse" if fill_role == "surface_strong" else "text_primary"
        ax.text(x + width / 2, y + height / 2, title, ha="center", va="center",
                fontsize=theme.typography.roles_pt["caption"], fontweight="bold",
                color=theme.color_value(text_color), zorder=zorder + 2)
    return patch


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
    styled_shape(ax, theme, bounds, style="field", zorder=0)
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
    role: str = "connector",
    style: str = "flow",
    zorder: int = 3,
) -> FancyArrowPatch:
    stroke = theme.shape.strokes[style]
    head = theme.shape.arrowheads["standard"]
    patch = FancyArrowPatch(
        start, end,
        arrowstyle=str(head["style"]),
        mutation_scale=float(head["scale"]),
        color=theme.color_value(role if role else stroke.color),
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
