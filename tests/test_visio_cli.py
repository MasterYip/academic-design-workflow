from pathlib import Path

from academic_design_workflow.cli import parser
from academic_design_workflow.visio.bridge import default_bridge_path
from academic_design_workflow.visio.cli import _emit, _write_json

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_theme_commands_and_nested_visio_commands_coexist():
    root = parser()
    assert root.parse_args(["validate", "theme.yaml"]).command == "validate"
    args = root.parse_args(["visio", "validate", "scene.json"])
    assert (args.command, args.visio_command) == ("visio", "validate")
    assert root.parse_args(["visio", "audit", "chart.vsdx"]).visio_command == "audit"


def test_default_bridge_is_repository_local_and_contains_no_import_pipeline():
    bridge = default_bridge_path()
    assert bridge == ROOT / "scripts" / "visio" / "native_bridge.ps1"
    source = bridge.read_text(encoding="utf-8").lower()
    forbidden = ("page.import", "addpicture", "foreignobject", ".svg", ".pdf", ".emf")
    assert not any(token in source for token in forbidden)


def test_console_json_is_ascii_safe_on_legacy_windows_code_pages(capsys):
    _emit({"label": "H = 20 • N = 4"})
    assert "\\u2022" in capsys.readouterr().out


def test_json_outputs_are_never_silently_overwritten(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("original", encoding="utf-8")
    try:
        _write_json(output, {"replacement": True})
    except FileExistsError as error:
        assert "refusing to overwrite" in str(error)
    else:
        raise AssertionError("existing output was not rejected")
    assert output.read_text(encoding="utf-8") == "original"
