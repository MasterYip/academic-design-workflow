"""Render a compact proof that one theme controls plots and schematic elements."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from academic_design_workflow.figures import arrow, box, save_vector_bundle, token_row
from academic_design_workflow.theme import load_theme
from academic_design_workflow.compiler import matplotlib_rc
import matplotlib as mpl


ROOT = Path(__file__).resolve().parents[2]
THEME = load_theme(ROOT / "themes" / "academic-clean.yaml")
OUTPUT = ROOT / "generated" / "styleboard"


def build() -> list[str]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(matplotlib_rc(THEME))
    fig = plt.figure(figsize=(THEME.layout.figure_width_in["double_column"], 4.35))
    grid = fig.add_gridspec(2, 2, height_ratios=[0.34, 0.66], hspace=0.36, wspace=0.30)

    palette = fig.add_subplot(grid[0, :])
    palette.axis("off")
    palette.text(0, 1.10, "Academic Clean — total style proof", transform=palette.transAxes,
                 fontsize=THEME.typography.roles_pt["figure_title"], fontweight="bold")
    selected = ["data_primary", "data_secondary", "data_tertiary", "data_quaternary",
                "positive", "warning", "negative"]
    for index, role in enumerate(selected):
        x = index / len(selected)
        palette.add_patch(plt.Rectangle((x, 0.25), 0.11, 0.38, transform=palette.transAxes,
                                        color=THEME.color_value(role), clip_on=False))
        palette.text(x, 0.12, role.replace("data_", ""), transform=palette.transAxes,
                     fontsize=THEME.typography.roles_pt["micro"], va="top")

    plot = fig.add_subplot(grid[1, 0])
    x = np.linspace(0, 10, 9)
    for index, role in enumerate(("data_primary", "data_secondary", "data_tertiary")):
        y = 0.22 * index + (1 - np.exp(-x / (2.0 + index * 0.5)))
        plot.plot(x, y, marker=("o", "s", "^")[index], color=THEME.color_value(role),
                  label=("Proposed", "Baseline A", "Baseline B")[index])
    plot.set(title="Data-plot language", xlabel="Training steps (k)", ylabel="Success rate")
    plot.grid(axis="y")
    plot.spines[["top", "right"]].set_visible(False)
    plot.legend()

    diagram = fig.add_subplot(grid[1, 1])
    diagram.set(xlim=(0, 10), ylim=(0, 6))
    diagram.axis("off")
    box(diagram, THEME, (0.2, 3.6, 2.2, 1.25), title="Observation", detail="history\ntokens")
    box(diagram, THEME, (3.35, 3.25, 2.9, 1.95), style="focal_module",
        title="Policy", detail="shared latent\nmodel")
    box(diagram, THEME, (7.45, 3.6, 2.25, 1.25), title="Action", detail="joint\ncommand")
    arrow(diagram, THEME, (2.45, 4.22), (3.27, 4.22), role="data_secondary")
    arrow(diagram, THEME, (6.33, 4.22), (7.37, 4.22), role="data_tertiary")
    token_row(diagram, THEME, (2.6, 1.25), [r"$z_1$", r"$z_2$", r"$\cdots$", r"$z_H$"],
              roles=("data_primary", "data_secondary"))
    diagram.text(0.2, 5.55, "Schematic shape grammar", fontweight="bold",
                 fontsize=THEME.typography.roles_pt["section_title"])
    diagram.text(0.2, 0.35, "Quiet surfaces · semantic accents · rounded technical geometry",
                 color=THEME.color_value("text_secondary"),
                 fontsize=THEME.typography.roles_pt["caption"])

    return save_vector_bundle(fig, str(OUTPUT / "academic-clean-styleboard"))


if __name__ == "__main__":
    for output in build():
        print(output)
