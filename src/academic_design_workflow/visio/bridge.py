"""Optional Windows PowerShell/COM bridge for native Visio generation and editing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class VisioBridgeError(RuntimeError):
    """The optional native Visio bridge is unavailable or failed safely."""


def default_bridge_path() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts" / "visio" / "native_bridge.ps1"


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise VisioBridgeError("PowerShell is required for native Visio COM operations")
    return executable


def run_bridge(
    *,
    mode: str,
    scene: Path,
    output: Path,
    scene_hash: str,
    bridge: Path | None = None,
    input_vsdx: Path | None = None,
    edits: Path | None = None,
    base_scene_hash: str | None = None,
    preview: Path | None = None,
) -> dict[str, Any]:
    """Run the task-owned COM bridge and parse its single JSON result."""
    if os.name != "nt":
        raise VisioBridgeError("native Visio generation is supported only on Windows")
    script = (bridge or default_bridge_path()).resolve()
    if not script.is_file():
        raise VisioBridgeError(f"Visio bridge script not found: {script}")
    command = [
        _powershell(),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Mode",
        mode,
        "-Scene",
        str(scene.resolve()),
        "-Output",
        str(output.resolve()),
        "-SceneHash",
        scene_hash,
    ]
    optional = {
        "-InputVsdx": input_vsdx,
        "-Edits": edits,
        "-BaseSceneHash": base_scene_hash,
        "-Preview": preview,
    }
    for flag, value in optional.items():
        if value is not None:
            command.extend((flag, str(value.resolve()) if isinstance(value, Path) else value))
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown bridge failure"
        raise VisioBridgeError(message)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise VisioBridgeError("Visio bridge returned no audit result")
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise VisioBridgeError("Visio bridge did not return valid JSON") from exc
