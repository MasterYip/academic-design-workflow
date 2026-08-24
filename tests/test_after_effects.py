from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_design_workflow.after_effects import (
    AEPreflightError,
    AEProject,
    build_aerender_command,
    build_afterfx_script_command,
    file_sha256,
    generate_build_jsx,
    generate_inspect_jsx,
    guard_revision,
    load_project,
    preflight_project,
    semantic_diff,
    validate_jsx_static,
)
from academic_design_workflow.cli import parser


ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "examples" / "after-effects"


def test_example_is_valid_and_covers_academic_metadata() -> None:
    project = load_project(EXAMPLES / "paper-video.json")
    assert project.project_id == "hoffman.paper-video"
    assert project.duration == 4
    assert project.scenes[0].source_anchor.locator == "sec:introduction#motivation"
    assert {layer.kind for layer in project.scenes[0].layers} == {"text", "shape"}


def test_duplicate_stable_ids_are_rejected() -> None:
    raw = json.loads((EXAMPLES / "paper-video.json").read_text(encoding="utf-8"))
    raw["scenes"][0]["layers"][1]["id"] = raw["scenes"][0]["layers"][0]["id"]
    with pytest.raises(ValidationError, match="duplicate stable ID"):
        AEProject.model_validate(raw)


def test_layer_cannot_exceed_scene() -> None:
    raw = json.loads((EXAMPLES / "paper-video.json").read_text(encoding="utf-8"))
    raw["scenes"][0]["layers"][0]["duration"] = 9
    with pytest.raises(ValidationError, match="exceeds scene duration"):
        AEProject.model_validate(raw)


def test_text_style_is_validated_and_emitted_for_ae2020(tmp_path: Path) -> None:
    raw = json.loads((EXAMPLES / "paper-video.json").read_text(encoding="utf-8"))
    title = raw["scenes"][0]["layers"][0]
    title.update(
        {
            "text_font": "Arial-BoldMT",
            "text_size": 72,
            "text_fill": [1, 1, 1],
            "text_justification": "center",
        }
    )
    project = AEProject.model_validate(raw)
    script = generate_build_jsx(
        project,
        EXAMPLES,
        tmp_path / "styled.aep",
        tmp_path / "styled-report.json",
    )
    assert 'textDocument.font = layerSpec.text_font' in script
    assert 'textDocument.fontSize = layerSpec.text_size' in script
    assert 'textDocument.fillColor = layerSpec.text_fill' in script
    assert "ParagraphJustification.CENTER_JUSTIFY" in script
    assert '"ADBE Vector Ellipse Size"' in script
    assert '"ADBE Vector Rect Size"' in script
    assert '"ADBE Vector Shape Size"' not in script

    raw["scenes"][0]["layers"][1]["text_size"] = 20
    with pytest.raises(ValidationError, match="text styling is only valid"):
        AEProject.model_validate(raw)


def test_generated_build_script_is_deterministic_and_es3_guarded(tmp_path: Path) -> None:
    project = load_project(EXAMPLES / "paper-video.json")
    args = (project, EXAMPLES, tmp_path / "video.aep", tmp_path / "report.json")
    first = generate_build_jsx(*args)
    second = generate_build_jsx(*args)
    assert first == second
    assert validate_jsx_static(first) == []
    assert "project.renderQueue.items.add(main)" in first
    assert "ADW_ID=" in first
    assert "new MarkerValue" in first
    assert "Refusing to overwrite existing project" in first
    assert "Builder requires a blank unsaved project" in first
    assert "project.save(projectOutputFile)" in first
    assert "function adwStringify" in first
    assert "JSON.stringify" not in first
    assert '.replace(/\\x08/g, "\\\\b")' in first
    assert "adwPreflightWritableNewFile(REPORT_OUTPUT" in first
    assert "Allow Scripts to Write Files and Access Network" in first
    assert "project.save(projectOutputFile);\n    writeReport(project);" in first


def test_inspector_is_read_only_with_respect_to_project(tmp_path: Path) -> None:
    script = generate_inspect_jsx(tmp_path / "inspection.json")
    assert validate_jsx_static(script) == []
    assert "project.save" not in script
    assert "app.newProject" not in script
    assert "project.revision" in script
    assert "snapshotProperty" in script
    assert "row.value_error=valueError.toString()" in script
    assert "render_queue" in script
    assert "function adwStringify" in script
    assert "JSON.stringify" not in script
    assert "adwWriteNewTextFile(OUTPUT" in script
    assert "Refusing to overwrite existing" in script


def test_semantic_diff_respects_nested_and_record_ownership() -> None:
    before = load_project(EXAMPLES / "paper-video.json")
    after = load_project(EXAMPLES / "paper-video-human-edit.json")
    report = semantic_diff(before, after)
    assert report["change_count"] >= 4
    dispositions = {change["disposition"] for change in report["changes"]}
    assert "preserve_human_edit" in dispositions
    assert "conflict_requires_review" in dispositions
    assert report["safe_to_auto_apply"] is False
    position = next(change for change in report["changes"] if "ADBE Position/value" in change["path"])
    assert position["ownership"] == "human"
    assert position["disposition"] == "preserve_human_edit"


def test_static_validator_rejects_modern_javascript() -> None:
    errors = validate_jsx_static("const x = () => ({value: 1});")
    assert len(errors) == 2


def test_preflight_verifies_assets_outputs_and_source_revision(tmp_path: Path) -> None:
    asset = tmp_path / "figure.png"
    asset.write_bytes(b"paper-figure")
    source = tmp_path / "agent-r001.aep"
    source.write_bytes(b"native-aep")
    raw = json.loads((EXAMPLES / "paper-video.json").read_text(encoding="utf-8"))
    raw["assets"] = [
        {
            "id": "asset.figure",
            "kind": "image",
            "path": asset.name,
            "sha256": file_sha256(asset),
        }
    ]
    project = AEProject.model_validate(raw)
    report = preflight_project(
        project,
        tmp_path,
        tmp_path / "human-r002.aep",
        tmp_path / "human-r002.report.json",
        source_project=source,
        expected_source_sha256=file_sha256(source),
    )
    assert report["status"] == "pass"
    assert report["assets"][0]["status"] == "verified"
    assert report["source_revision"]["source_sha256"] == file_sha256(source)


def test_preflight_fails_closed_on_asset_output_and_stale_revision(tmp_path: Path) -> None:
    raw = json.loads((EXAMPLES / "paper-video.json").read_text(encoding="utf-8"))
    raw["assets"] = [
        {
            "id": "asset.figure",
            "kind": "image",
            "path": "missing.png",
            "sha256": "0" * 64,
        }
    ]
    project = AEProject.model_validate(raw)
    with pytest.raises(AEPreflightError, match="missing asset"):
        preflight_project(project, tmp_path, tmp_path / "new.aep", tmp_path / "new.json")

    (tmp_path / "missing.png").write_bytes(b"different-content")
    with pytest.raises(AEPreflightError, match="asset hash mismatch"):
        preflight_project(project, tmp_path, tmp_path / "new.aep", tmp_path / "new.json")

    source = tmp_path / "agent-r001.aep"
    source.write_bytes(b"native-aep")
    output = tmp_path / "human-r002.aep"
    output.write_bytes(b"already-here")
    with pytest.raises(AEPreflightError, match="overwrite existing revision"):
        guard_revision(source, file_sha256(source), output)
    output.unlink()
    with pytest.raises(AEPreflightError, match="stale source revision hash"):
        guard_revision(source, "0" * 64, output)


def test_native_commands_are_shell_free_and_refuse_render_overwrite(tmp_path: Path) -> None:
    afterfx = tmp_path / "AfterFX.exe"
    aerender = tmp_path / "aerender.exe"
    script = tmp_path / "build.jsx"
    project = tmp_path / "agent-r001.aep"
    for path in (afterfx, aerender, script, project):
        path.write_bytes(b"fixture")

    assert build_afterfx_script_command(afterfx, script) == [
        str(afterfx.resolve()),
        "-r",
        str(script.resolve()),
    ]
    output = tmp_path / "preview.avi"
    command = build_aerender_command(
        aerender,
        project,
        output,
        comp="Paper demo",
        render_settings="Draft Settings",
        output_module="AVI review",
    )
    assert command == [
        str(aerender.resolve()),
        "-project",
        str(project.resolve()),
        "-comp",
        "Paper demo",
        "-RStemplate",
        "Draft Settings",
        "-OMtemplate",
        "AVI review",
        "-output",
        str(output.resolve()),
    ]
    assert "-continueOnMissingFootage" not in command
    output.write_bytes(b"durable-preview")
    with pytest.raises(AEPreflightError, match="overwrite existing render"):
        build_aerender_command(aerender, project, output)


def test_cli_exposes_native_preflight_and_command_planners() -> None:
    parsed = parser().parse_args(
        [
            "ae",
            "preflight",
            "manifest.json",
            "--project-output",
            "agent-r001.aep",
            "--report-output",
            "agent-r001.json",
            "--source-project",
            "human-r000.aep",
            "--source-sha256",
            "0" * 64,
        ]
    )
    assert parsed.ae_command == "preflight"
    assert parsed.source_sha256 == "0" * 64
    render = parser().parse_args(
        [
            "ae",
            "render-command",
            "agent-r001.aep",
            "--aerender",
            "aerender.exe",
            "--output",
            "preview.avi",
        ]
    )
    assert render.ae_command == "render-command"
