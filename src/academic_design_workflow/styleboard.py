"""Comprehensive cross-media style-board renderer."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from .compiler import matplotlib_rc
from .figures import arrow, box, panel, styled_shape, token_row
from .theme import Theme


BOARD_SIZE = (16, 9)


def _setup(theme: Theme, title: str, number: str):
    mpl.rcParams.update(matplotlib_rc(theme))
    fig = plt.figure(figsize=BOARD_SIZE)
    fig.subplots_adjust(left=0.045, right=0.965, top=0.86, bottom=0.07)
    fig.text(0.045, 0.94, title, fontsize=22, fontweight="bold",
             color=theme.color_value("text_primary"), va="top")
    fig.text(0.955, 0.94, f"{theme.meta.name} · {number}", ha="right", va="top",
             fontsize=9, color=theme.color_value("text_secondary"))
    fig.add_artist(plt.Line2D([0.045, 0.965], [0.885, 0.885], transform=fig.transFigure,
                              color=theme.color_value("border"), linewidth=0.7))
    return fig


def _label(ax, theme: Theme, text: str, x=0.0, y=1.03):
    ax.text(x, y, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=10, fontweight="bold", color=theme.color_value("text_primary"))


def foundations(theme: Theme):
    fig = _setup(theme, "Foundations & component grammar", "01")
    grid = fig.add_gridspec(2, 3, height_ratios=[0.88, 1.12], hspace=0.33, wspace=0.24)
    colors = fig.add_subplot(grid[0, :2]); colors.axis("off"); _label(colors, theme, "Semantic color system")
    roles = list(theme.color.roles)
    for i, role in enumerate(roles):
        col, row = i % 9, i // 9
        x, y = col / 9, 0.68 - row * 0.39
        colors.add_patch(Rectangle((x, y), 0.094, 0.18, transform=colors.transAxes,
                                   color=theme.color_value(role), clip_on=False))
        colors.text(x, y - 0.045, role.replace("data_", ""), transform=colors.transAxes,
                    fontsize=6.6, va="top", color=theme.color_value("text_primary"))
    for i, (name, alpha) in enumerate(theme.color.opacity.items()):
        colors.add_patch(Rectangle((0.01 + i * 0.137, -0.07), 0.118, 0.105,
                                   transform=colors.transAxes,
                                   color=theme.color_value("data_primary"), alpha=alpha, clip_on=False))
        colors.text(0.01 + i * 0.137, -0.10, f"{name} {alpha:.2g}",
                    transform=colors.transAxes, fontsize=6.2, va="top")

    typography = fig.add_subplot(grid[0, 2]); typography.axis("off"); _label(typography, theme, "Typography")
    if theme.meta.name == "intact":
        samples = [("figure_title", "Isomorphic Intent-to-Action"), ("section_title", "Shared world representation"),
                   ("body", "One predictor maps intent directly to action."),
                   ("label", "Task-specific head pair"), ("caption", "Blue: world · coral: direct control"),
                   ("micro", "4 domains · 0 search · 3.8 ms")]
    else:
        samples = [("figure_title", "Semantic Rolling Control"), ("section_title", "System overview"),
                   ("body", "Conditioned policy predicts coherent motion."),
                   ("label", "Latent state"), ("caption", "Mean ± 95% confidence interval"),
                   ("micro", "H = 20 · d = 256 · 30 FPS")]
    for i, (role, text) in enumerate(samples):
        typography.text(0, 0.90 - i * 0.155, text, transform=typography.transAxes,
                        fontsize=theme.typography.roles_pt[role] * 1.55,
                        fontweight="bold" if i < 2 else "normal",
                        color=theme.color_value("text_primary" if i < 4 else "text_secondary"))
        typography.text(1, 0.90 - i * 0.155, role, transform=typography.transAxes,
                        ha="right", fontsize=6, color=theme.color_value("text_secondary"))

    shapes = fig.add_subplot(grid[1, 0]); shapes.set(xlim=(0, 10), ylim=(0, 7)); shapes.axis("off")
    _label(shapes, theme, "Shape vocabulary")
    specimens = [("module", "Module"), ("focal_module", "Focal"), ("tag", "TAG"),
                 ("encoder", "Encoder"), ("dataset", "Dataset")]
    for i, (style, name) in enumerate(specimens):
        if style in theme.shape.vocabulary:
            x, y = (0.3 + (i % 2) * 4.8, 4.7 - (i // 2) * 2.0)
            styled_shape(shapes, theme, (x, y, 3.8, 1.15), style=style, title=name)
    arrow(shapes, theme, (0.5, 0.65), (3.2, 0.65), role="connector")
    arrow(shapes, theme, (4.0, 0.65), (6.7, 0.65), role="data_secondary", style="optional_flow")
    shapes.text(7.2, 0.65, "solid / guide", va="center", fontsize=7,
                color=theme.color_value("text_secondary"))

    widgets = fig.add_subplot(grid[1, 1]); widgets.set(xlim=(0, 10), ylim=(0, 7)); widgets.axis("off")
    _label(widgets, theme, "Widgets & panel patterns")
    panel(widgets, theme, (0.1, 0.3, 9.7, 6.2), "Experiment summary", label="a")
    box(widgets, theme, (0.7, 3.7, 3.7, 1.4), title="Policy checkpoint", detail="best validation score")
    styled_shape(widgets, theme, (5.0, 4.0, 1.7, 0.65), style="tag", title="SELECTED")
    for i, role in enumerate(("data_primary", "data_secondary", "data_tertiary")):
        styled_shape(widgets, theme, (0.8, 2.55 - i * 0.72, 0.38, 0.38), style="token", role=role)
        widgets.text(1.45, 2.74 - i * 0.72, ("Primary result", "Condition", "Task family")[i], va="center", fontsize=7.2)
    styled_shape(widgets, theme, (5.0, 1.2, 3.3, 0.85), style="focal_module", title="Primary action")

    rules = fig.add_subplot(grid[1, 2]); rules.axis("off"); _label(rules, theme, "Cross-media rules")
    if theme.meta.name == "intact":
        rule_text = ["1  Blue is shared/world structure", "2  Coral is intent/action activation",
                     "3  Domain chips remain stable everywhere", "4  Pale blue and blush separate systems",
                     "5  Math capsules sit inside strong enclosures", "6  Dark media trade density for atmosphere",
                     "7  Orbit means rollout; arrows mean control", "8  Metrics anchor the presentation identity"]
    elif theme.meta.name == "rolling-diffusion":
        rule_text = ["1  Gray occupies most visual area", "2  Orange marks focal events and paths",
                     "3  Muted blue supports state structure", "4  Burgundy is reserved for action history",
                     "5  No purple or saturated cyan", "6  Dotted lines are guides or provenance",
                     "7  Panels establish chapters and order", "8  Motion follows established connectors"]
    else:
        rule_text = ["1  Neutral machinery; vivid semantic signals", "2  One focal accent per reading step",
                     "3  Shape + label + color for important meaning", "4  Dotted lines are guides or provenance",
                     "5  Panels establish chapters and order", "6  Opacity describes context—not weak text",
                     "7  Motion follows established connectors", "8  All media share semantic role names"]
    for i, text in enumerate(rule_text):
        rules.text(0, 0.95 - i * 0.115, text, fontsize=8.3, va="top",
                   color=theme.color_value("text_primary" if i < 3 else "text_secondary"))
    return fig


def charts(theme: Theme):
    fig = _setup(theme, "Scientific chart gallery", "02")
    grid = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.34)
    rng = np.random.default_rng(7); roles = ("data_primary", "data_secondary", "data_tertiary")
    ax = fig.add_subplot(grid[0, 0]); _label(ax, theme, "Learning curves + uncertainty")
    x = np.arange(0, 11)
    for i, role in enumerate(roles):
        mean = 0.15 * i + 0.82 * (1 - np.exp(-x / (2.4 + i * 0.55))); err = 0.08 - x * 0.003
        color = theme.color_value(role); ax.plot(x, mean, marker=("o", "s", "^")[i], color=color, label=("Ours", "Base A", "Base B")[i]); ax.fill_between(x, mean - err, mean + err, color=color, alpha=theme.chart.uncertainty["opacity"])
    ax.set(xlabel="Training steps (k)", ylabel="Success", ylim=(0, 1.2)); ax.grid(axis="y"); ax.legend(ncol=3, loc="lower right")
    ax = fig.add_subplot(grid[0, 1]); _label(ax, theme, "Grouped comparison")
    categories = ["Walk", "Run", "Turn", "Stairs"]; values = np.array([[82, 76, 71, 66], [75, 68, 65, 54], [69, 64, 59, 48]]); xx = np.arange(4); width = 0.24
    for i, role in enumerate(roles): ax.bar(xx + (i - 1) * width, values[i], width, color=theme.color_value(role), label=("Ours", "A", "B")[i])
    ax.set_xticks(xx, categories); ax.set(ylabel="Score (%)", ylim=(0, 100)); ax.grid(axis="y"); ax.legend(ncol=3)
    ax = fig.add_subplot(grid[0, 2]); _label(ax, theme, "Scatter + semantic classes")
    for i, role in enumerate(roles):
        points = rng.normal((i * 0.9, i * 0.45), (0.42, 0.30), size=(24, 2)); ax.scatter(points[:, 0], points[:, 1], s=28, marker=("o", "s", "^")[i], facecolor=theme.color_value(role), edgecolor="white", linewidth=0.4, alpha=0.82, label=("Walk", "Run", "Jump")[i])
    ax.set(xlabel="Latent dimension 1", ylabel="Latent dimension 2"); ax.grid(alpha=0.25); ax.legend()
    ax = fig.add_subplot(grid[1, 0]); _label(ax, theme, "Distribution / uncertainty")
    distributions = [rng.normal(0.72, 0.08, 80), rng.normal(0.61, 0.09, 80), rng.normal(0.52, 0.11, 80)]
    bp = ax.boxplot(distributions, patch_artist=True, labels=["Ours", "A", "B"], widths=0.55)
    for patch, role in zip(bp["boxes"], roles): patch.set_facecolor(theme.color_value(role)); patch.set_alpha(0.65)
    ax.set(ylabel="Normalized return"); ax.grid(axis="y")
    ax = fig.add_subplot(grid[1, 1]); _label(ax, theme, "Matrix / attention map")
    matrix = np.array([[.9, .5, .2, .1, .05], [.55, .85, .42, .18, .08], [.2, .48, .92, .5, .22], [.08, .18, .55, .88, .52], [.03, .08, .24, .5, .94]])
    cmap = mpl.colors.LinearSegmentedColormap.from_list("theme_seq", theme.color.sequential); image = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(5), [r"$t{-}2$", r"$t{-}1$", r"$t$", r"$t{+}1$", r"$t{+}2$"]); ax.set_yticks(range(5), ["State", "Action", "Task", "Latent", "Context"]); fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax = fig.add_subplot(grid[1, 2]); _label(ax, theme, "Temporal state/action sequence")
    t = np.arange(12); state = np.array([2, 3, 4, 5, 4, 3, 4, 6, 7, 6, 5, 4]); action = -np.array([1, 2, 3, 5, 6, 5, 3, 2, 4, 3, 2, 1])
    ax.bar(t, state, color=theme.color_value("data_primary"), label="State"); ax.bar(t, action, color=theme.color_value("negative"), label="Action"); ax.axvline(6.5, color=theme.color_value("connector"), linestyle=":", linewidth=1)
    ax.text(3, 7.3, "PAST", ha="center", color=theme.color_value("text_secondary"), fontsize=7); ax.text(9, 7.3, "FUTURE", ha="center", color=theme.color_value("text_secondary"), fontsize=7)
    ax.set(xlabel="Horizon", ylabel="Token magnitude", yticks=[]); ax.legend(ncol=2)
    return fig


def framework(theme: Theme):
    fig = _setup(theme, "Paper framework language", "03")
    ax = fig.add_axes([0.045, 0.08, 0.92, 0.78]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off")
    panel(ax, theme, (0.0, 4.7, 4.6, 4.0), "Task & observation encoding", label="a"); panel(ax, theme, (4.9, 4.7, 5.2, 4.0), "Semantic latent learning", label="b"); panel(ax, theme, (10.4, 4.7, 5.6, 4.0), "Rolling diffusion", label="c")
    for i, (label, role) in enumerate((("Task", "data_tertiary"), ("State", "data_primary"), ("Privileged", "data_quaternary"), ("Action", "warning"))):
        styled_shape(ax, theme, (0.45, 7.4 - i * 0.68, 0.42, 0.42), style="token", role=role); box(ax, theme, (1.05, 7.28 - i * 0.68, 2.05, 0.58), title=label)
    styled_shape(ax, theme, (3.35, 5.55, 0.82, 2.5), style="encoder", title="Compose"); arrow(ax, theme, (3.1, 6.65), (3.32, 6.65))
    styled_shape(ax, theme, (5.35, 6.15, 1.05, 1.65), style="encoder", title="Encode"); token_row(ax, theme, (6.75, 7.15), [r"$z_1$", r"$z_2$", r"$z_3$", r"$z_H$"], roles=("data_secondary", "positive"), width=0.48, height=0.42); arrow(ax, theme, (6.45, 6.95), (6.72, 6.95), role="data_secondary")
    styled_shape(ax, theme, (7.2, 5.2, 1.6, 1.15), style="dataset", title="Dataset"); arrow(ax, theme, (7.95, 6.95), (7.95, 6.4)); box(ax, theme, (8.75, 6.55, 0.9, 0.7), title="Loss")
    box(ax, theme, (10.85, 6.25, 3.1, 1.35), style="focal_module", title="Conditioned denoiser", detail="semantic rolling planner")
    for i in range(7): styled_shape(ax, theme, (11.0 + i * 0.57, 5.35, 0.42, 0.55 + i * 0.10), style="token", role="negative" if i < 4 else "data_quaternary")
    styled_shape(ax, theme, (0.1, 3.7, 15.6, 0.55), style="panel_header"); ax.text(0.35, 3.98, "SEMANTIC ROLLING CONTROL", color=theme.color_value("text_inverse"), fontsize=8, fontweight="bold", va="center")
    token_row(ax, theme, (3.0, 2.72), ["S"] * 8, roles=("data_primary",), width=0.62, height=0.55, gap=0.12); token_row(ax, theme, (3.0, 1.92), ["A"] * 8, roles=("negative",), width=0.62, height=0.55, gap=0.12)
    ax.axvline(8.6, ymin=0.14, ymax=0.44, color=theme.color_value("connector"), linestyle=":"); ax.text(6.1, 3.42, "PAST", ha="center", fontsize=7, color=theme.color_value("text_secondary")); ax.text(11.2, 3.42, "FUTURE", ha="center", fontsize=7, color=theme.color_value("text_secondary"))
    box(ax, theme, (10.2, 1.45, 3.5, 1.8), title="Deployment policy", detail="condition → denoise → action"); arrow(ax, theme, (8.95, 2.55), (10.12, 2.55), role="data_secondary"); arrow(ax, theme, (13.75, 2.35), (15.1, 2.35), role="data_primary"); styled_shape(ax, theme, (15.05, 1.8, 0.55, 1.1), style="token", role="surface_strong", title="ACT")
    return fig


def framework_intact(theme: Theme):
    """Original INTACT-inspired scientific framework specimen."""
    fig = _setup(theme, "Paper framework language", "03")
    ax = fig.add_axes([0.045, 0.08, 0.92, 0.78]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off")
    panel(ax, theme, (0.0, 0.6, 4.0, 7.9), "Multi-domain trajectories", label="a")
    domain_data = (("Manipulation", "data_quaternary"), ("Navigation", "data_tertiary"),
                   ("Tracking", "data_primary"), ("Interaction", "data_secondary"))
    for i, (name, role) in enumerate(domain_data):
        x = 0.35 + (i % 2) * 1.8; y = 5.35 - (i // 2) * 2.35
        styled_shape(ax, theme, (x, y, 1.55, 1.75), style="module")
        ax.add_patch(Rectangle((x, y + 1.57), 1.55, 0.18, color=theme.color_value(role)))
        ax.text(x + 0.15, y + 1.25, name, fontsize=7.2, fontweight="bold")
        styled_shape(ax, theme, (x + 0.16, y + 0.35, 0.52, 0.62), style="token", role=role)
        styled_shape(ax, theme, (x + 0.86, y + 0.35, 0.52, 0.62), style="token", role=role)
        ax.text(x + 0.77, y + 0.12, r"$o_t \rightarrow o_g$", ha="center", fontsize=6.4,
                color=theme.color_value("text_secondary"))

    panel(ax, theme, (4.25, 0.6, 3.0, 7.9), "Shared visual encoder", label="b")
    ax.text(5.75, 6.65, r"$E_\theta$", ha="center", va="center", fontsize=32,
            color=theme.color_value("data_primary"))
    ax.text(5.75, 5.75, "one latent space", ha="center", fontsize=8,
            color=theme.color_value("text_secondary"))
    token_row(ax, theme, (4.72, 4.7), ["1", "2", "3", "4"],
              roles=("data_quaternary", "data_tertiary", "data_primary", "data_secondary"),
              width=0.45, height=0.5, gap=0.18)
    box(ax, theme, (4.65, 2.65, 2.2, 1.1), title="Indexed latent batch", detail=r"$\{z_t^k,\,z_g^k\}_{k=1}^{4}$")
    arrow(ax, theme, (4.02, 4.5), (4.22, 4.5), role="data_primary")

    panel(ax, theme, (7.5, 0.6, 5.5, 7.9), "Intent-conditioned head pair", label="c")
    box(ax, theme, (7.95, 6.35, 2.0, 0.85), style="focal_module", title="Local intent", detail=r"$m_t=z_{t+1}-z_t$")
    box(ax, theme, (10.25, 6.35, 2.0, 0.85), title="Goal intent", detail=r"$m_t=\mathrm{sg}(z_g)-z_t$")
    ax.text(8.95, 5.95, "PHYSICAL · ATTACHED", ha="center", fontsize=6.4,
            color=theme.color_value("warning"), fontweight="bold")
    ax.text(11.25, 5.95, "DEPLOYABLE · DETACHED", ha="center", fontsize=6.4,
            color=theme.color_value("data_secondary"), fontweight="bold")
    box(ax, theme, (9.25, 4.1, 2.0, 1.25), style="focal_module", title="INTENT predictor", detail=r"$G_\eta^k$")
    arrow(ax, theme, (8.95, 6.25), (9.75, 5.42), role="highlight")
    arrow(ax, theme, (11.25, 6.25), (10.75, 5.42), role="data_secondary")
    box(ax, theme, (7.95, 1.35, 2.2, 1.25), title="Forward model", detail=r"$F_\psi^k(z_t,a_t)$")
    box(ax, theme, (10.65, 1.55, 1.55, 0.85), title="Prediction", detail=r"$\hat z_{t+1}$")
    arrow(ax, theme, (10.2, 1.98), (10.58, 1.98), role="data_primary")
    styled_shape(ax, theme, (11.0, 3.05, 0.82, 0.62), style="token", role="highlight", title="ACTION")
    arrow(ax, theme, (10.75, 4.05), (11.35, 3.72), role="highlight")

    panel(ax, theme, (13.25, 0.6, 2.75, 7.9), "Inference", label="d")
    box(ax, theme, (13.62, 5.5, 2.0, 1.45), style="focal_module", title="Direct control", detail="one action chunk")
    arrow(ax, theme, (12.3, 3.37), (13.55, 6.1), role="highlight")
    box(ax, theme, (13.62, 2.25, 2.0, 1.55), title="World rollout", detail="optional verify · replan")
    for i in range(4):
        styled_shape(ax, theme, (13.85 + i * 0.42, 1.35, 0.25, 0.25), style="token",
                     role="data_primary" if i in (0, 3) else "surface_subtle")
        if i < 3: arrow(ax, theme, (14.11 + i * 0.42, 1.48), (14.24 + i * 0.42, 1.48), role="data_primary")
    return fig


def website(theme: Theme):
    fig = _setup(theme, "Project website UI language", "04")
    ax = fig.add_axes([0.045, 0.08, 0.92, 0.78]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off"); styled_shape(ax, theme, (0.2, 0.2, 15.6, 8.5), style="field")
    ax.text(0.65, 8.15, "ROLLING / LAB", fontweight="bold", fontsize=10)
    for i, item in enumerate(("Method", "Results", "Video", "Paper")): ax.text(10.2 + i * 1.15, 8.15, item, fontsize=7, color=theme.color_value("text_secondary"))
    styled_shape(ax, theme, (14.6, 7.82, 0.75, 0.55), style="tag", title="CODE")
    ax.text(0.75, 6.85, "Semantic control,\nrolled into the future.", fontsize=24, fontweight="bold", va="top", linespacing=0.96, color=theme.color_value("text_primary"))
    ax.text(0.78, 4.85, "A project-site composition that shares the paper's semantic colors,\ntechnical modules, clipped rails, and temporal flow.", fontsize=8.5, color=theme.color_value("text_secondary"), linespacing=1.4)
    styled_shape(ax, theme, (0.8, 3.85, 2.05, 0.72), style="focal_module", title="Read the paper"); styled_shape(ax, theme, (3.05, 3.85, 1.65, 0.72), style="module", title="Watch video")
    panel(ax, theme, (7.25, 3.55, 7.7, 3.95), "Interactive method overview"); box(ax, theme, (7.85, 5.25, 1.7, 0.85), title="Task"); styled_shape(ax, theme, (10.25, 4.8, 1.2, 1.7), style="encoder", title="Policy"); box(ax, theme, (12.2, 5.25, 1.9, 0.85), title="Action"); arrow(ax, theme, (9.6, 5.65), (10.18, 5.65), role="data_tertiary"); arrow(ax, theme, (11.5, 5.65), (12.12, 5.65), role="data_primary"); token_row(ax, theme, (8.2, 4.05), ["t−2", "t−1", "t", "t+1", "t+2"], roles=("negative", "negative", "highlight", "positive", "positive"), width=0.68, height=0.48, gap=0.15)
    for i, (metric, value, role) in enumerate((("Success", "92%", "data_secondary"), ("Latency", "18 ms", "data_primary"), ("Tasks", "12", "data_tertiary"))):
        x = 0.8 + i * 2.05; styled_shape(ax, theme, (x, 1.0, 1.75, 1.7), style="module"); ax.text(x + 0.18, 2.25, metric, fontsize=6.5, color=theme.color_value("text_secondary")); ax.text(x + 0.18, 1.45, value, fontsize=18, fontweight="bold", color=theme.color_value(role))
    panel(ax, theme, (7.25, 0.75, 7.7, 2.25), "Results are evidence, not decoration")
    for i, value in enumerate([0.42, 0.57, 0.68, 0.81, 0.92]): ax.add_patch(Rectangle((8.0 + i * 1.15, 1.15), 0.7, value * 1.1, color=theme.color_value("data_primary"), alpha=0.35 + i * 0.12))
    return fig


def _particles(ax, theme: Theme, seed: int, count: int = 650) -> None:
    rng = np.random.default_rng(seed)
    angle = rng.uniform(0, 2 * np.pi, count); radius = np.clip(rng.normal(2.6, 1.05, count), 0.2, 5.0)
    x = 8 + np.cos(angle) * radius * 1.35; y = 5.25 + np.sin(angle) * radius * 0.70
    colors = np.where(rng.random(count) > 0.52, theme.color_value("data_primary"), theme.color_value("highlight"))
    ax.scatter(x, y, s=rng.uniform(1, 9, count), c=colors, alpha=rng.uniform(0.05, 0.38, count), linewidths=0, zorder=0)


def website_intact(theme: Theme):
    """Dark editorial project-site specimen for INTACT."""
    fig = _setup(theme, "Project website UI language", "04")
    ax = fig.add_axes([0.045, 0.08, 0.92, 0.78]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 16, 9, color=theme.color_value("canvas"), zorder=-3)); _particles(ax, theme, 22)
    ax.text(0.55, 8.35, "INTENT / ACTION LAB", color=theme.color_value("text_primary"), fontsize=8, fontweight="bold")
    for i, item in enumerate(("Method", "World model", "Results", "Paper")):
        ax.text(10.1 + i * 1.25, 8.35, item, fontsize=6.8, color=theme.color_value("text_secondary"))
    ax.plot([0.6, 5.8], [7.82, 7.82], color=theme.color_value("data_primary"), linewidth=0.8)
    ax.plot([10.2, 15.4], [7.82, 7.82], color=theme.color_value("highlight"), linewidth=0.8)
    # Orbit mark and segmented display identity.
    theta = np.linspace(0.45, 5.8, 100)
    ax.plot(4.7 + np.cos(theta) * 1.25, 5.3 + np.sin(theta) * 1.25,
            color=theme.color_value("text_primary"), linewidth=5, solid_capstyle="round")
    arrow(ax, theme, (4.2, 5.15), (5.45, 5.75), role="highlight")
    styled_shape(ax, theme, (3.85, 4.62, 0.52, 0.52), style="token", role="data_primary", title="m")
    styled_shape(ax, theme, (5.55, 5.65, 0.52, 0.52), style="token", role="highlight", title="a")
    ax.text(6.35, 6.1, "IN", fontsize=34, fontweight="bold", color=theme.color_value("data_primary"))
    ax.text(8.05, 6.1, "T", fontsize=34, fontweight="bold", color=theme.color_value("text_primary"))
    ax.text(8.82, 6.1, "ACT", fontsize=34, fontweight="bold", color=theme.color_value("highlight"))
    ax.text(8.6, 4.92, "INTENT", fontsize=9, fontweight="bold", color=theme.color_value("data_primary"), ha="right")
    arrow(ax, theme, (8.75, 5.0), (9.45, 5.0), role="text_primary")
    ax.text(9.65, 4.92, "ACTION", fontsize=9, fontweight="bold", color=theme.color_value("highlight"))
    ax.text(8.0, 3.62, "ISOMORPHIC INTENT-TO-ACTION LEARNING", ha="center", fontsize=14,
            fontweight="bold", color=theme.color_value("text_primary"))
    ax.text(8.0, 3.1, "Search-free control from a learned world model", ha="center", fontsize=8,
            color=theme.color_value("text_secondary"))
    ax.plot([3.2, 12.8], [2.72, 2.72], color=theme.color_value("border"), linewidth=0.7)
    metrics = (("1", "FULL-DATA EPOCH", "text_primary"), ("95.3%", "DIRECT SUCCESS", "highlight"),
               ("0", "ONLINE SEARCH", "text_primary"), ("3.8 ms", "INFERENCE", "data_primary"))
    for i, (value, label, role) in enumerate(metrics):
        x = 2.0 + i * 4.0; ax.text(x, 1.72, value, ha="center", fontsize=14, fontweight="bold", color=theme.color_value(role)); ax.text(x, 1.30, label, ha="center", fontsize=5.8, color=theme.color_value("text_secondary"))
        if i < 3: ax.plot([x + 2, x + 2], [1.05, 2.12], color=theme.color_value("border"), linewidth=0.6)
    return fig


def video(theme: Theme):
    fig = _setup(theme, "Video composition & motion language", "05")
    grid = fig.add_gridspec(2, 3, height_ratios=[1, 0.44], hspace=0.32, wspace=0.22); scene_titles = ("01 · PROBLEM", "02 · MECHANISM", "03 · EVIDENCE")
    for index in range(3):
        ax = fig.add_subplot(grid[0, index]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off"); ax.add_patch(Rectangle((0, 0), 16, 9, facecolor=theme.color_value("surface"), edgecolor=theme.color_value("border"), linewidth=0.8)); safe = theme.video.safe_area_percent / 100; ax.add_patch(Rectangle((16 * safe, 9 * safe), 16 * (1 - 2 * safe), 9 * (1 - 2 * safe), fill=False, edgecolor=theme.color_value("border"), linestyle=":", linewidth=0.7)); styled_shape(ax, theme, (0.8, 7.55, 5.0, 0.65), style="panel_header"); ax.text(1.1, 7.87, scene_titles[index], color=theme.color_value("text_inverse"), fontsize=7.5, fontweight="bold", va="center")
        if index == 0:
            ax.text(1.2, 5.8, "Long-horizon control\nbreaks coherence.", fontsize=16, fontweight="bold", va="top")
            for i in range(7): styled_shape(ax, theme, (1.2 + i * 1.55, 2.7, 0.8, 0.7 + i * 0.32), style="token", role="negative" if i > 3 else "surface_subtle")
        elif index == 1:
            box(ax, theme, (1.2, 4.1, 4.0, 1.35), title="Condition history"); box(ax, theme, (7.0, 3.65, 4.2, 2.2), style="focal_module", title="Rolling denoiser", detail="phase-aligned update"); arrow(ax, theme, (5.3, 4.78), (6.9, 4.78), role="data_secondary"); token_row(ax, theme, (3.4, 2.2), ["S", "A", "S", "A", "S"], roles=("data_primary", "negative"), width=0.75, height=0.62, gap=0.2)
        else:
            for i, value in enumerate([3.3, 4.6, 5.2, 6.8, 7.6]): ax.add_patch(Rectangle((1.4 + i * 2.2, 2.0), 1.2, value * 0.62, color=theme.color_value("data_primary"), alpha=0.42 + i * 0.12))
            ax.axhline(6.6, xmin=0.08, xmax=0.82, color=theme.color_value("data_secondary"), linewidth=2); ax.text(1.4, 7.0, "+18% success across tasks", fontsize=13, fontweight="bold")
        ax.add_patch(Rectangle((1.1, 0.55), 13.8, 0.82, color=theme.color_value("surface_strong"), alpha=0.9)); ax.text(8, 0.96, ("Motivation remains readable without audio.", "Signals activate along stable connectors.", "Claims resolve into quantitative evidence.")[index], ha="center", va="center", color=theme.color_value("text_inverse"), fontsize=7.2)
    timeline = fig.add_subplot(grid[1, :]); timeline.set(xlim=(0, 30), ylim=(0, 4)); timeline.axis("off"); _label(timeline, theme, "Beat sheet, transition, and caption rhythm")
    for start, end, label, role in [(0, 4, "TITLE", "surface_strong"), (4, 10, "PROBLEM", "negative"), (10, 20, "MECHANISM", "data_secondary"), (20, 27, "EVIDENCE", "data_primary"), (27, 30, "END", "data_tertiary")]:
        timeline.add_patch(Rectangle((start, 1.8), end - start - 0.12, 0.95, color=theme.color_value(role), alpha=0.88)); timeline.text((start + end) / 2, 2.28, label, ha="center", va="center", fontsize=7, fontweight="bold", color=theme.color_value("text_inverse"))
    for second in range(0, 31, 2): timeline.plot([second, second], [1.25, 1.48], color=theme.color_value("border"), linewidth=0.7); timeline.text(second, 0.95, f"{second}s", ha="center", fontsize=6, color=theme.color_value("text_secondary"))
    return fig


def video_intact(theme: Theme):
    """Dark INTACT motion specimen with orbit, direct path, and metrics."""
    fig = _setup(theme, "Video composition & motion language", "05")
    grid = fig.add_gridspec(2, 3, height_ratios=[1, 0.44], hspace=0.32, wspace=0.22)
    titles = ("01 · INTENT", "02 · ISOMORPHISM", "03 · DIRECT CONTROL")
    for index in range(3):
        ax = fig.add_subplot(grid[0, index]); ax.set(xlim=(0, 16), ylim=(0, 9)); ax.axis("off")
        ax.add_patch(Rectangle((0, 0), 16, 9, color=theme.color_value("canvas"), zorder=-3)); _particles(ax, theme, 40 + index, 260)
        safe = theme.video.safe_area_percent / 100; ax.add_patch(Rectangle((16 * safe, 9 * safe), 16 * (1 - 2 * safe), 9 * (1 - 2 * safe), fill=False, edgecolor=theme.color_value("border"), linestyle=":", linewidth=0.7))
        ax.text(1.1, 7.85, titles[index], color=theme.color_value("text_secondary"), fontsize=7, fontweight="bold")
        if index == 0:
            theta = np.linspace(0.5, 5.8, 100); ax.plot(8 + np.cos(theta) * 2.3, 4.6 + np.sin(theta) * 2.3, color=theme.color_value("text_primary"), linewidth=5, solid_capstyle="round")
            styled_shape(ax, theme, (5.5, 3.95, 0.8, 0.8), style="token", role="data_primary", title="m")
            arrow(ax, theme, (6.4, 4.4), (9.4, 5.6), role="highlight"); styled_shape(ax, theme, (9.55, 5.25, 0.8, 0.8), style="token", role="highlight", title="a")
        elif index == 1:
            ax.text(2.0, 5.2, "IN", fontsize=26, fontweight="bold", color=theme.color_value("data_primary")); arrow(ax, theme, (5.2, 5.5), (7.1, 5.5), role="text_primary"); ax.text(7.6, 5.2, "ACT", fontsize=26, fontweight="bold", color=theme.color_value("highlight")); ax.text(8, 3.4, "same geometry · different semantics", ha="center", fontsize=8, color=theme.color_value("text_secondary"))
        else:
            box(ax, theme, (1.5, 4.1, 4.1, 1.4), title="Goal intent", detail=r"$m_t^{goal}$"); arrow(ax, theme, (5.75, 4.8), (7.2, 4.8), role="highlight"); box(ax, theme, (7.4, 3.85, 4.6, 1.9), style="focal_module", title="One action chunk", detail="search-free · 3.8 ms"); arrow(ax, theme, (12.2, 4.8), (14.2, 4.8), role="highlight")
        ax.add_patch(Rectangle((1.1, 0.55), 13.8, 0.82, color=theme.color_value("surface_strong"), alpha=0.92)); ax.text(8, 0.96, ("Intent forms a geometric object in latent space.", "A shared predictor maps intent directly to action.", "World rollout remains optional, not mandatory.")[index], ha="center", va="center", color=theme.color_value("text_primary"), fontsize=7.2)
    timeline = fig.add_subplot(grid[1, :]); timeline.set(xlim=(0, 24), ylim=(0, 4)); timeline.axis("off"); _label(timeline, theme, "Blue world structure → coral direct-control activation")
    beats = [(0, 4, "IDENTITY", "surface_strong"), (4, 10, "INTENT", "data_primary"), (10, 16, "MAP", "text_primary"), (16, 22, "ACT", "highlight"), (22, 24, "METRICS", "surface_strong")]
    for start, end, label, role in beats:
        timeline.add_patch(Rectangle((start, 1.75), end - start - 0.1, 0.95, color=theme.color_value(role), alpha=0.92)); timeline.text((start + end) / 2, 2.22, label, ha="center", va="center", fontsize=7, fontweight="bold", color=theme.color_value("text_inverse") if role != "text_primary" else theme.color_value("canvas"))
    return fig


def render_styleboards(theme: Theme, output_dir: str | Path) -> list[Path]:
    """Render five SVG/PDF/PNG boards and a PNG contact sheet."""
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    paper_theme = theme.for_variant("paper"); web_theme = theme.for_variant("web"); video_theme = theme.for_variant("video")
    if theme.meta.name == "intact":
        builders = (("01-foundations", foundations, paper_theme), ("02-charts", charts, paper_theme),
                    ("03-framework", framework_intact, paper_theme), ("04-website", website_intact, web_theme),
                    ("05-video", video_intact, video_theme))
    else:
        builders = (("01-foundations", foundations, paper_theme), ("02-charts", charts, paper_theme),
                    ("03-framework", framework, paper_theme), ("04-website", website, web_theme),
                    ("05-video", video, video_theme))
    written: list[Path] = []; previews: list[np.ndarray] = []
    for name, builder, board_theme in builders:
        fig = builder(board_theme)
        for suffix, dpi in (("svg", None), ("pdf", None), ("png", 150)):
            path = output / f"{name}.{suffix}"; fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.04); written.append(path)
        previews.append(plt.imread(output / f"{name}.png")); plt.close(fig)
    contact_theme = web_theme
    contact = plt.figure(figsize=(16, 9), facecolor=contact_theme.color_value("canvas")); contact.suptitle(f"{theme.meta.name} · comprehensive cross-media style system", x=0.04, y=0.97, ha="left", fontsize=20, fontweight="bold", color=contact_theme.color_value("text_primary")); grid = contact.add_gridspec(2, 3, left=0.04, right=0.97, top=0.90, bottom=0.05, wspace=0.06, hspace=0.12)
    names = ("FOUNDATIONS", "CHARTS", "PAPER FRAMEWORK", "WEBSITE UI", "VIDEO", "DESIGN CONTRACT")
    for i in range(5):
        ax = contact.add_subplot(grid[i // 3, i % 3]); ax.imshow(previews[i]); ax.axis("off"); ax.set_title(names[i], loc="left", fontsize=8, fontweight="bold", pad=4, color=contact_theme.color_value("text_primary"))
    ax = contact.add_subplot(grid[1, 2]); ax.axis("off"); ax.set_title(names[-1], loc="left", fontsize=8, fontweight="bold", color=contact_theme.color_value("text_primary"))
    for i, item in enumerate(["ONE THEME", "SEMANTIC TOKENS", "VECTOR FIRST", "AUDITABLE DATA", "RESPONSIVE LAYOUT", "PURPOSEFUL MOTION", "ACCESSIBLE ENCODING"]):
        styled_shape(ax, contact_theme, (0.05, 0.80 - i * 0.105, 0.72, 0.07), style="tag"); ax.text(0.09, 0.835 - i * 0.105, item, transform=ax.transAxes, va="center", fontsize=8, fontweight="bold", color=contact_theme.color_value("text_inverse"))
    overview = output / "00-overview.png"; contact.savefig(overview, dpi=170, bbox_inches="tight", pad_inches=0.04); plt.close(contact); written.insert(0, overview)
    return written
