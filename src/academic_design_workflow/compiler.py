"""Compile one validated theme for Python, CSS, and TypeScript consumers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .theme import Theme


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _flatten(value: Any, prefix: tuple[str, ...] = ()) -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result.update(_flatten(child, (*prefix, str(key))))
        return result
    if isinstance(value, list):
        return {"-".join(prefix): ", ".join(str(item) for item in value)}
    return {"-".join(prefix): value}


def matplotlib_rc(theme: Theme) -> dict[str, Any]:
    """Return rcParams-compatible values for publication figures."""
    sans = theme.typography.sans
    roles = theme.typography.roles_pt
    chart = theme.chart
    return {
        "font.family": "sans-serif",
        "font.sans-serif": sans.family,
        "font.size": roles["body"],
        "axes.titlesize": roles["section_title"],
        "axes.labelsize": roles["axis_label"],
        "axes.labelcolor": theme.color_value("text_primary"),
        "axes.edgecolor": theme.color_value(str(chart.axes["color"])),
        "axes.linewidth": chart.axes["width_pt"],
        "axes.facecolor": theme.color_value("surface"),
        "figure.facecolor": theme.color_value("canvas"),
        "xtick.labelsize": roles["caption"],
        "ytick.labelsize": roles["caption"],
        "xtick.color": theme.color_value("text_secondary"),
        "ytick.color": theme.color_value("text_secondary"),
        "grid.color": theme.color_value(str(chart.grid["color"])),
        "grid.alpha": chart.grid["opacity"],
        "grid.linewidth": chart.grid["width_pt"],
        "lines.linewidth": chart.lines["width_pt"],
        "lines.markersize": chart.markers["size_pt"],
        "legend.frameon": chart.legend["frame"],
        "legend.fontsize": roles["caption"],
        "savefig.bbox": "tight",
        "savefig.facecolor": theme.color_value("canvas"),
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }


def css_variables(theme: Theme) -> str:
    """Compile stable CSS custom properties from the entire theme."""
    raw = theme.model_dump(mode="json")
    flattened = _flatten(raw)
    lines = [":root {"]
    for key, value in sorted(flattened.items()):
        if key.startswith("meta-") or key.endswith("-usage"):
            continue
        css_value = str(value).lower() if isinstance(value, bool) else value
        lines.append(f"  --adw-{_slug(key)}: {css_value};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def compile_theme(theme: Theme, output_dir: str | Path) -> list[Path]:
    """Write cross-media token artifacts and return their paths."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "theme.json": json.dumps(theme.model_dump(mode="json"), indent=2) + "\n",
        "theme.css": css_variables(theme),
        "matplotlib.json": json.dumps(matplotlib_rc(theme), indent=2) + "\n",
    }
    written = []
    for name, content in files.items():
        path = output / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written

