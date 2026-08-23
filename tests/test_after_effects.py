from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_design_workflow.after_effects import (
    AEProject,
    generate_build_jsx,
    generate_inspect_jsx,
    load_project,
    semantic_diff,
    validate_jsx_static,
)


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


def test_inspector_is_read_only_with_respect_to_project(tmp_path: Path) -> None:
    script = generate_inspect_jsx(tmp_path / "inspection.json")
    assert validate_jsx_static(script) == []
    assert "project.save" not in script
    assert "app.newProject" not in script
    assert "project.revision" in script
    assert "snapshotProperty" in script
    assert "render_queue" in script


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
