import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_design_workflow.visio.edits import SemanticEditError, apply_edits
from academic_design_workflow.visio.models import EditRequest, Scene, semantic_sha256

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "visio" / "hoffman_policy.scene.json"
EXAMPLE_EDIT = ROOT / "examples" / "visio" / "hoffman_policy.resize.edit.json"


def scene_data():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def scene():
    return Scene.model_validate(scene_data())


def request_for(scene_object, target_id, patch, *, scene_hash=None, element_hash=None):
    return EditRequest.model_validate(
        {
            "schema_version": "1.0",
            "scene_id": scene_object.scene_id,
            "base_scene_sha256": scene_hash or semantic_sha256(scene_object),
            "edits": [
                {
                    "target_id": target_id,
                    "expected_element_sha256": element_hash
                    or semantic_sha256(scene_object.element(target_id)),
                    "set": patch,
                }
            ],
        }
    )


def test_representative_scene_and_checked_in_edit_are_current():
    current = scene()
    request = EditRequest.model_validate(json.loads(EXAMPLE_EDIT.read_text(encoding="utf-8")))
    assert semantic_sha256(current) == request.base_scene_sha256
    revised, record = apply_edits(current, request)
    assert revised.revision == 2
    assert record["changed_ids"] == ["condition_encoder"]


def test_scene_rejects_duplicate_ids():
    data = scene_data()
    duplicate = deepcopy(data["shapes"][0])
    data["shapes"].append(duplicate)
    with pytest.raises(ValidationError, match="duplicate semantic IDs"):
        Scene.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("shape_id", "missing_block", "dangling target shape"),
        ("port", "missing_port", "references missing target port"),
    ],
)
def test_scene_rejects_dangling_connector_endpoints(field, value, message):
    data = scene_data()
    data["connectors"][0]["target"][field] = value
    with pytest.raises(ValidationError, match=message):
        Scene.model_validate(data)


def test_scene_rejects_unknown_style_role():
    data = scene_data()
    data["shapes"][0]["style"]["fill_role"] = "not_a_role"
    with pytest.raises(ValidationError, match="unknown color roles"):
        Scene.model_validate(data)


def test_scene_accepts_auditable_metadata_and_rejects_reserved_or_invalid_keys():
    data = scene_data()
    data["metadata"] = {"SourceScript": "fig.py", "SourceSHA256": "abc"}
    data["shapes"][1]["data"] = {"SourceText": r"$x_0$", "SourceLine": "42"}
    current = Scene.model_validate(data)
    assert current.metadata["SourceScript"] == "fig.py"
    assert current.shapes[1].data["SourceText"] == r"$x_0$"

    invalid = deepcopy(data)
    invalid["shapes"][1]["data"] = {"bad key": "value"}
    with pytest.raises(ValidationError, match="shape data keys"):
        Scene.model_validate(invalid)

    reserved = deepcopy(data)
    reserved["metadata"] = {"SceneHash": "shadow"}
    with pytest.raises(ValidationError, match="scene metadata keys are reserved"):
        Scene.model_validate(reserved)


def test_empty_provenance_fields_preserve_schema_1_0_hashes():
    current = scene()
    request = EditRequest.model_validate(json.loads(EXAMPLE_EDIT.read_text(encoding="utf-8")))
    assert current.metadata == {}
    assert all(shape.data == {} for shape in current.shapes)
    assert semantic_sha256(current) == request.base_scene_sha256


def test_edit_rejects_stale_scene_and_stale_element():
    current = scene()
    stale_scene = request_for(current, "condition_encoder", {"x": 3.0}, scene_hash="0" * 64)
    with pytest.raises(SemanticEditError, match="stale scene"):
        apply_edits(current, stale_scene)
    stale_element = request_for(
        current, "condition_encoder", {"x": 3.0}, element_hash="0" * 64
    )
    with pytest.raises(SemanticEditError, match="stale element"):
        apply_edits(current, stale_element)


def test_edit_request_rejects_ambiguous_duplicate_targets():
    current = scene()
    operation = {
        "target_id": "condition_encoder",
        "expected_element_sha256": semantic_sha256(current.element("condition_encoder")),
        "set": {"x": 3.0},
    }
    with pytest.raises(ValidationError, match="ambiguous edits repeat targets"):
        EditRequest.model_validate(
            {
                "schema_version": "1.0",
                "scene_id": current.scene_id,
                "base_scene_sha256": semantic_sha256(current),
                "edits": [operation, operation],
            }
        )


def test_edit_rejects_missing_target_and_noop():
    current = scene()
    missing = EditRequest.model_validate(
        {
            "schema_version": "1.0",
            "scene_id": current.scene_id,
            "base_scene_sha256": semantic_sha256(current),
            "edits": [
                {
                    "target_id": "missing_block",
                    "expected_element_sha256": "0" * 64,
                    "set": {"x": 1.0},
                }
            ],
        }
    )
    with pytest.raises(SemanticEditError, match="missing semantic edit target"):
        apply_edits(current, missing)
    encoder = current.element("condition_encoder")
    noop = request_for(current, "condition_encoder", {"x": encoder.x})
    with pytest.raises(SemanticEditError, match="no-op"):
        apply_edits(current, noop)


def test_shape_edit_changes_only_target_and_records_preserved_ids():
    current = scene()
    before_action = semantic_sha256(current.element("noisy_action"))
    request = request_for(
        current,
        "condition_encoder",
        {"x": 3.05, "width": 2.5, "text": "Reviewed encoder"},
    )
    revised, record = apply_edits(current, request)
    encoder = revised.element("condition_encoder")
    assert (encoder.x, encoder.width, encoder.text) == (3.05, 2.5, "Reviewed encoder")
    assert semantic_sha256(revised.element("noisy_action")) == before_action
    assert "noisy_action" in record["preserved_ids"]
    assert record["base_scene_sha256"] == semantic_sha256(current)
    assert record["revised_scene_sha256"] == semantic_sha256(revised)


def test_connector_rejects_geometry_edit_but_allows_style_edit():
    current = scene()
    illegal = request_for(current, "condition_to_encoder", {"x": 1.0})
    with pytest.raises(SemanticEditError, match="only supports style edits"):
        apply_edits(current, illegal)
    legal = request_for(
        current, "condition_to_encoder", {"style": {"line_width_pt": 1.4}}
    )
    revised, _ = apply_edits(current, legal)
    assert revised.element("condition_to_encoder").style.line_width_pt == 1.4
