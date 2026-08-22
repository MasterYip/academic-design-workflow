from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse, FancyBboxPatch, PathPatch, Rectangle

from academic_design_workflow.figures import (
    arrow,
    compound_node,
    panel,
    semantic_row,
    styled_shape,
)
from academic_design_workflow.theme import load_theme

ROOT = Path(__file__).resolve().parents[1]


def test_hoffman_panel_header_is_full_width_with_only_top_corners_rounded():
    theme = load_theme(ROOT / "themes" / "hoffman.yaml")
    fig = Figure()
    ax = fig.subplots()

    panel(ax, theme, (1.0, 2.0, 6.0, 4.0), "Integrated title")

    assert len(ax.patches) == 2
    header = ax.patches[1]
    assert isinstance(header, PathPatch)
    vertices = header.get_path().vertices
    assert np.isclose(vertices[:, 0].min(), 1.0)
    assert np.isclose(vertices[:, 0].max(), 7.0)
    assert tuple(vertices[0]) == (1.0, 5.45)
    assert tuple(vertices[1]) == (7.0, 5.45)
    assert np.count_nonzero(header.get_path().codes == header.get_path().CURVE3) == 4
    assert np.allclose(header.get_facecolor(), matplotlib.colors.to_rgba("#5A5A57"))
    fig.clear()


def test_hoffman_dataset_uses_layered_cylinder_contours_and_process_bar():
    theme = load_theme(ROOT / "themes" / "hoffman.yaml")
    fig = Figure()
    ax = fig.subplots()

    styled_shape(ax, theme, (1.0, 1.0, 3.0, 2.0), style="dataset", title="DATA")
    process_bar = styled_shape(
        ax, theme, (0.5, 3.8, 6.0, 0.6), style="process_bar", title="PROCESS"
    )

    ellipses = [patch for patch in ax.patches if isinstance(patch, Ellipse)]
    rectangles = [patch for patch in ax.patches if isinstance(patch, Rectangle)]
    assert len(ellipses) == 4
    assert len(rectangles) == 1
    assert [ellipse.center[1] for ellipse in ellipses] == sorted(
        ellipse.center[1] for ellipse in ellipses
    )
    assert isinstance(process_bar, FancyBboxPatch)
    assert np.allclose(process_bar.get_facecolor(), matplotlib.colors.to_rgba("#5A5A57"))
    assert ax.texts[-1].get_color() == "#FFFFFF"
    fig.clear()


def test_compound_widgets_and_nodes_expose_hierarchy_and_ports():
    theme = load_theme(ROOT / "themes" / "hoffman.yaml")
    fig = Figure()
    ax = fig.subplots()

    row = semantic_row(ax, theme, (0.5, 0.5, 4.0, 0.8), ("Observation", "Noise"))
    node = compound_node(
        ax,
        theme,
        (5.5, 0.4, 3.0, 1.8),
        title="Predict",
        detail="condition · update",
        badge="FOCAL",
        focal=True,
    )

    assert len(row) == 3
    assert np.allclose(row[1].get_facecolor(), matplotlib.colors.to_rgba("#5A5A57"))
    assert isinstance(node["node"], FancyBboxPatch)
    assert isinstance(node["header"], PathPatch)
    assert isinstance(node["input_port"], Ellipse)
    assert isinstance(node["output_port"], Ellipse)
    assert isinstance(node["badge"], FancyBboxPatch)
    assert {text.get_text() for text in ax.texts} >= {
        "Observation",
        "Noise",
        "Predict",
        "condition · update",
        "FOCAL",
    }
    guide = arrow(ax, theme, (0.0, 3.0), (2.0, 3.0), style="graph_guide")
    assert np.allclose(guide.get_edgecolor(), matplotlib.colors.to_rgba("#B7B8B4"))
    fig.clear()
