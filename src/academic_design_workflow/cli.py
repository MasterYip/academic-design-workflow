"""Command-line interface for theme validation and compilation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .after_effects import (
    generate_build_jsx,
    generate_inspect_jsx,
    load_project,
    semantic_diff,
    validate_jsx_static,
    write_canonical,
)
from .compiler import compile_theme
from .styleboard import render_styleboards
from .theme import load_theme


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="adw")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a YAML theme")
    validate.add_argument("theme", type=Path)
    compile_command = commands.add_parser("compile", help="compile cross-media tokens")
    compile_command.add_argument("theme", type=Path)
    compile_command.add_argument("--output", type=Path, required=True)
    styleboard = commands.add_parser("styleboard", help="render the comprehensive style-board suite")
    styleboard.add_argument("theme", type=Path)
    styleboard.add_argument("--output", type=Path, required=True)
    ae = commands.add_parser("ae", help="source-first After Effects co-authoring tools")
    ae_commands = ae.add_subparsers(dest="ae_command", required=True)
    ae_validate = ae_commands.add_parser("validate", help="validate an AE semantic manifest")
    ae_validate.add_argument("manifest", type=Path)
    ae_normalize = ae_commands.add_parser("normalize", help="write canonical manifest JSON")
    ae_normalize.add_argument("manifest", type=Path)
    ae_normalize.add_argument("--output", type=Path, required=True)
    ae_generate = ae_commands.add_parser("generate", help="generate an AE project-builder JSX")
    ae_generate.add_argument("manifest", type=Path)
    ae_generate.add_argument("--output", type=Path, required=True)
    ae_generate.add_argument("--project-output", type=Path, required=True)
    ae_generate.add_argument("--report-output", type=Path, required=True)
    ae_inspect = ae_commands.add_parser("inspect-script", help="generate read-only AE inspector JSX")
    ae_inspect.add_argument("--output", type=Path, required=True)
    ae_inspect.add_argument("--report-output", type=Path, required=True)
    ae_diff = ae_commands.add_parser("diff", help="semantic diff of two stable-ID manifests")
    ae_diff.add_argument("before", type=Path)
    ae_diff.add_argument("after", type=Path)
    ae_diff.add_argument("--output", type=Path, required=True)
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "ae":
        if args.ae_command == "validate":
            project = load_project(args.manifest)
            print(
                f"valid AE manifest: {project.project_id}; "
                f"{len(project.scenes)} scenes; {project.duration:g}s"
            )
        elif args.ae_command == "normalize":
            print(write_canonical(load_project(args.manifest), args.output))
        elif args.ae_command == "generate":
            project = load_project(args.manifest)
            script = generate_build_jsx(
                project,
                args.manifest.parent,
                args.project_output,
                args.report_output,
            )
            errors = validate_jsx_static(script)
            if errors:
                raise SystemExit("invalid generated JSX: " + "; ".join(errors))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(script, encoding="utf-8")
            print(args.output)
        elif args.ae_command == "inspect-script":
            script = generate_inspect_jsx(args.report_output)
            errors = validate_jsx_static(script)
            if errors:
                raise SystemExit("invalid generated JSX: " + "; ".join(errors))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(script, encoding="utf-8")
            print(args.output)
        elif args.ae_command == "diff":
            report = semantic_diff(load_project(args.before), load_project(args.after))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(args.output)
        return
    theme = load_theme(args.theme)
    if args.command == "validate":
        print(f"valid theme: {theme.meta.name} v{theme.meta.version}")
    elif args.command == "compile":
        for path in compile_theme(theme, args.output):
            print(path)
    elif args.command == "styleboard":
        for path in render_styleboards(theme, args.output):
            print(path)


if __name__ == "__main__":
    main()
