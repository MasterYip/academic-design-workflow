"""Command-line interface for theme validation and compilation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import compile_theme
from .theme import load_theme


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="adw")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a YAML theme")
    validate.add_argument("theme", type=Path)
    compile_command = commands.add_parser("compile", help="compile cross-media tokens")
    compile_command.add_argument("theme", type=Path)
    compile_command.add_argument("--output", type=Path, required=True)
    return root


def main() -> None:
    args = parser().parse_args()
    theme = load_theme(args.theme)
    if args.command == "validate":
        print(f"valid theme: {theme.meta.name} v{theme.meta.version}")
    elif args.command == "compile":
        for path in compile_theme(theme, args.output):
            print(path)


if __name__ == "__main__":
    main()

