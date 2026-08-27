"""CLI wiring for native Visio scene validation, editing, generation, and audit."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from .bridge import run_bridge
from .edits import apply_edits
from .models import EditRequest, Scene, semantic_sha256
from .package import audit_vsdx, diff_audits


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _require_outputs_absent(*paths: Path | None) -> None:
    for path in paths:
        if path is not None and path.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {path}")


def _load_scene(path: Path) -> Scene:
    return Scene.model_validate(_read_json(path))


def configure_parser(commands: argparse._SubParsersAction) -> None:
    visio = commands.add_parser("visio", help="native Visio human-agent co-authoring")
    subcommands = visio.add_subparsers(dest="visio_command", required=True)

    validate = subcommands.add_parser("validate", help="validate a versioned Visio scene")
    validate.add_argument("scene", type=Path)
    validate.add_argument("--json", action="store_true", dest="as_json")

    schema = subcommands.add_parser("schema", help="emit the current Visio scene JSON Schema")
    schema.add_argument("--output", type=Path)

    apply_command = subcommands.add_parser(
        "apply-edits", help="apply stale-safe semantic edits to a scene without Visio"
    )
    apply_command.add_argument("scene", type=Path)
    apply_command.add_argument("edits", type=Path)
    apply_command.add_argument("--output-scene", type=Path, required=True)
    apply_command.add_argument("--change-record", type=Path, required=True)

    generate = subcommands.add_parser("generate", help="generate a native VSDX using Visio COM")
    generate.add_argument("scene", type=Path)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--preview", type=Path)
    generate.add_argument("--audit", type=Path)
    generate.add_argument("--bridge-record", type=Path)
    generate.add_argument("--bridge", type=Path)

    edit = subcommands.add_parser("edit", help="apply semantic edits to a native VSDX")
    edit.add_argument("input_vsdx", type=Path)
    edit.add_argument("base_scene", type=Path)
    edit.add_argument("edits", type=Path)
    edit.add_argument("--output-scene", type=Path, required=True)
    edit.add_argument("--output-vsdx", type=Path, required=True)
    edit.add_argument("--change-record", type=Path, required=True)
    edit.add_argument("--preview", type=Path)
    edit.add_argument("--audit", type=Path)
    edit.add_argument("--bridge-record", type=Path)
    edit.add_argument("--bridge", type=Path)

    audit = subcommands.add_parser("audit", help="inspect VSDX package structure read-only")
    audit.add_argument("vsdx", type=Path)
    audit.add_argument("--output", type=Path)

    diff = subcommands.add_parser("diff", help="diff two VSDX packages by semantic ID")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", type=Path)


def _emit(value: Any, output: Path | None = None) -> None:
    if output is not None:
        _write_json(output, value)
    # Windows consoles may still use a legacy code page; escaped JSON remains portable.
    print(json.dumps(value, indent=2, ensure_ascii=True))


def run(args: argparse.Namespace) -> None:
    if args.visio_command == "validate":
        scene = _load_scene(args.scene)
        result = {
            "valid": True,
            "schema_version": scene.schema_version,
            "scene_id": scene.scene_id,
            "revision": scene.revision,
            "scene_sha256": semantic_sha256(scene),
            "shape_count": len(scene.shapes),
            "connector_count": len(scene.connectors),
        }
        if args.as_json:
            _emit(result)
        else:
            print(
                f"valid Visio scene: {scene.scene_id} r{scene.revision} "
                f"({result['scene_sha256']})"
            )
        return

    if args.visio_command == "schema":
        value = Scene.model_json_schema()
        _emit(value, args.output)
        return

    if args.visio_command == "apply-edits":
        scene = _load_scene(args.scene)
        request = EditRequest.model_validate(_read_json(args.edits))
        revised, record = apply_edits(scene, request)
        _require_outputs_absent(args.output_scene, args.change_record)
        _write_json(args.output_scene, revised.model_dump(mode="json"))
        _write_json(args.change_record, record)
        _emit(record)
        return

    if args.visio_command == "generate":
        scene = _load_scene(args.scene)
        _require_outputs_absent(args.output, args.preview, args.audit, args.bridge_record)
        with tempfile.TemporaryDirectory(prefix="adw-visio-scene-") as directory:
            normalized_scene = Path(directory) / "scene.json"
            normalized_scene.write_text(
                json.dumps(scene.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
            )
            result = run_bridge(
                mode="generate",
                scene=normalized_scene,
                output=args.output,
                scene_hash=semantic_sha256(scene),
                bridge=args.bridge,
                preview=args.preview,
            )
        if args.bridge_record:
            _write_json(args.bridge_record, result)
        if args.audit:
            _write_json(args.audit, audit_vsdx(args.output))
        _emit(result)
        return

    if args.visio_command == "edit":
        scene = _load_scene(args.base_scene)
        request = EditRequest.model_validate(_read_json(args.edits))
        revised, record = apply_edits(scene, request)
        _require_outputs_absent(
            args.output_scene,
            args.output_vsdx,
            args.change_record,
            args.preview,
            args.audit,
            args.bridge_record,
        )
        args.output_scene.parent.mkdir(parents=True, exist_ok=True)
        args.output_scene.write_text(
            json.dumps(revised.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            result = run_bridge(
                mode="edit",
                scene=args.output_scene,
                output=args.output_vsdx,
                scene_hash=semantic_sha256(revised),
                bridge=args.bridge,
                input_vsdx=args.input_vsdx,
                edits=args.edits,
                base_scene_hash=semantic_sha256(scene),
                preview=args.preview,
            )
        except Exception:
            args.output_scene.unlink(missing_ok=True)
            raise
        _write_json(args.change_record, record)
        if args.bridge_record:
            _write_json(args.bridge_record, result)
        if args.audit:
            _write_json(args.audit, audit_vsdx(args.output_vsdx))
        _emit({"bridge": result, "change_record": record})
        return

    if args.visio_command == "audit":
        _emit(audit_vsdx(args.vsdx), args.output)
        return

    if args.visio_command == "diff":
        _emit(diff_audits(audit_vsdx(args.before), audit_vsdx(args.after)), args.output)
        return

    raise ValueError(f"unknown Visio command: {args.visio_command}")
