from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch

from academic_design_workflow.figures import panel
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
