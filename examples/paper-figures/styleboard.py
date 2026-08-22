"""Render the comprehensive style-board suite for any repository theme."""

from __future__ import annotations

import argparse
from pathlib import Path

from academic_design_workflow.styleboard import render_styleboards
from academic_design_workflow.theme import load_theme


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="rolling-diffusion")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    theme_path = ROOT / "themes" / f"{args.theme}.yaml"
    output = args.output or ROOT / "generated" / "styleboards" / args.theme
    for path in render_styleboards(load_theme(theme_path), output):
        print(path)


if __name__ == "__main__":
    main()
