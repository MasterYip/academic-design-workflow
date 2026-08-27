"""Safe semantic edit planning for human-agent Visio co-authoring."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .models import ConnectorSpec, EditRequest, Scene, ShapeSpec, semantic_sha256


class SemanticEditError(ValueError):
    """An edit is stale, ambiguous, invalid, or would be a no-op."""


def _apply_patch(element: ShapeSpec | ConnectorSpec, patch: dict[str, Any]):
    current = element.model_dump(mode="python")
    if isinstance(element, ConnectorSpec):
        illegal = sorted(set(patch) - {"style"})
        if illegal:
            raise SemanticEditError(
                f"connector {element.id!r} only supports style edits; received: {', '.join(illegal)}"
            )
    if "style" in patch:
        current["style"] = {**current["style"], **patch.pop("style")}
    current.update(patch)
    model_type = ShapeSpec if isinstance(element, ShapeSpec) else ConnectorSpec
    return model_type.model_validate(current)


def apply_edits(scene: Scene, request: EditRequest) -> tuple[Scene, dict[str, Any]]:
    """Apply a stale-safe edit request and return the revised scene plus change record."""
    base_hash = semantic_sha256(scene)
    if request.scene_id != scene.scene_id:
        raise SemanticEditError(
            f"edit scene_id {request.scene_id!r} does not match {scene.scene_id!r}"
        )
    if request.base_scene_sha256 != base_hash:
        raise SemanticEditError(
            f"stale scene: expected {request.base_scene_sha256}, current {base_hash}"
        )

    revised_data = scene.model_dump(mode="python")
    shape_index = {item["id"]: index for index, item in enumerate(revised_data["shapes"])}
    connector_index = {
        item["id"]: index for index, item in enumerate(revised_data["connectors"])
    }
    changes = []

    for operation in request.edits:
        try:
            before = scene.element(operation.target_id)
        except KeyError as exc:
            raise SemanticEditError(f"missing semantic edit target {operation.target_id!r}") from exc
        actual_element_hash = semantic_sha256(before)
        if operation.expected_element_sha256 != actual_element_hash:
            raise SemanticEditError(
                f"stale element {operation.target_id!r}: expected "
                f"{operation.expected_element_sha256}, current {actual_element_hash}"
            )
        patch = deepcopy(operation.set.model_dump(exclude_none=True))
        after = _apply_patch(before, patch)
        if semantic_sha256(after) == actual_element_hash:
            raise SemanticEditError(f"edit target {operation.target_id!r} is a no-op")
        collection = "shapes" if isinstance(after, ShapeSpec) else "connectors"
        index = shape_index[after.id] if collection == "shapes" else connector_index[after.id]
        revised_data[collection][index] = after.model_dump(mode="python")
        changes.append(
            {
                "target_id": after.id,
                "before_sha256": actual_element_hash,
                "after_sha256": semantic_sha256(after),
                "before": before.model_dump(mode="json"),
                "after": after.model_dump(mode="json"),
            }
        )

    revised_data["revision"] = scene.revision + 1
    revised = Scene.model_validate(revised_data)
    expected_unchanged = scene.semantic_ids() - {change["target_id"] for change in changes}
    changed_unexpectedly = sorted(
        semantic_id
        for semantic_id in expected_unchanged
        if semantic_sha256(scene.element(semantic_id)) != semantic_sha256(revised.element(semantic_id))
    )
    if changed_unexpectedly:
        raise SemanticEditError(
            "unrelated semantic elements changed: " + ", ".join(changed_unexpectedly)
        )
    record = {
        "record_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scene_id": scene.scene_id,
        "base_revision": scene.revision,
        "revised_revision": revised.revision,
        "base_scene_sha256": base_hash,
        "revised_scene_sha256": semantic_sha256(revised),
        "changed_ids": [change["target_id"] for change in changes],
        "preserved_ids": sorted(expected_unchanged),
        "changes": changes,
    }
    return revised, record
