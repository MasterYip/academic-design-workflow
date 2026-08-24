"""Source-first After Effects co-authoring manifests and ExtendScript bridges.

The module deliberately does not parse or patch binary AEP files.  It keeps a
small semantic source of truth, emits reviewable JSX, and compares stable-ID
snapshots produced before and after a human editing pass.
"""

from __future__ import annotations

import json
import math
import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ID_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{2,79}$")


class Ownership(str, Enum):
    AGENT = "agent"
    HUMAN = "human"
    SHARED = "shared"


class Anchor(BaseModel):
    """Trace an edit back to a paper, narration, figure, or citation source."""

    source: str
    locator: str
    revision: str | None = None


class Marker(BaseModel):
    id: str
    time: float = Field(ge=0)
    duration: float = Field(default=0, ge=0)
    comment: str
    ownership: Ownership = Ownership.SHARED


class Keyframe(BaseModel):
    time: float = Field(ge=0)
    value: float | str | list[float]


class AnimatedProperty(BaseModel):
    match_name: str
    value: float | str | list[float] | None = None
    keyframes: list[Keyframe] = Field(default_factory=list)
    expression: str | None = None
    ownership: Ownership = Ownership.AGENT

    @model_validator(mode="after")
    def require_value(self) -> "AnimatedProperty":
        if self.value is None and not self.keyframes and self.expression is None:
            raise ValueError("property needs a value, keyframe, or expression")
        return self


class Effect(BaseModel):
    id: str
    match_name: str
    properties: list[AnimatedProperty] = Field(default_factory=list)
    ownership: Ownership = Ownership.AGENT


class Asset(BaseModel):
    id: str
    kind: Literal["video", "audio", "image", "data"]
    path: str
    sha256: str | None = None
    ownership: Ownership = Ownership.HUMAN
    source_anchor: Anchor | None = None


class Layer(BaseModel):
    id: str
    name: str
    kind: Literal["text", "shape", "footage", "audio", "null"]
    start: float = Field(default=0, ge=0)
    duration: float = Field(gt=0)
    ownership: Ownership = Ownership.AGENT
    source_anchor: Anchor | None = None
    asset_id: str | None = None
    text: str | None = None
    text_font: str | None = None
    text_size: float | None = Field(default=None, gt=0)
    text_fill: list[float] | None = None
    text_justification: Literal["left", "center", "right"] | None = None
    shape: Literal["rectangle", "ellipse"] | None = None
    size: list[float] | None = None
    fill: list[float] | None = None
    properties: list[AnimatedProperty] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    markers: list[Marker] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "Layer":
        if self.kind in {"footage", "audio"} and not self.asset_id:
            raise ValueError(f"{self.kind} layer requires asset_id")
        if self.kind == "text" and self.text is None:
            raise ValueError("text layer requires text")
        if self.kind != "text" and any(
            value is not None
            for value in (
                self.text_font,
                self.text_size,
                self.text_fill,
                self.text_justification,
            )
        ):
            raise ValueError("text styling is only valid for text layers")
        if self.text_fill and (
            len(self.text_fill) != 3 or any(x < 0 or x > 1 for x in self.text_fill)
        ):
            raise ValueError("text_fill must be RGB values in [0, 1]")
        if self.kind == "shape" and (not self.shape or not self.size or not self.fill):
            raise ValueError("shape layer requires shape, size, and fill")
        if self.fill and (len(self.fill) not in {3, 4} or any(x < 0 or x > 1 for x in self.fill)):
            raise ValueError("fill must be RGB/RGBA values in [0, 1]")
        return self


class Scene(BaseModel):
    id: str
    name: str
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    claim: str
    ownership: Ownership = Ownership.SHARED
    source_anchor: Anchor | None = None
    layers: list[Layer]
    markers: list[Marker] = Field(default_factory=list)


class AEProject(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    title: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0, le=240)
    background: list[float] = Field(default_factory=lambda: [0, 0, 0])
    assets: list[Asset] = Field(default_factory=list)
    scenes: list[Scene]

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> "AEProject":
        records: list[tuple[str, str]] = [("project", self.project_id)]
        records += [("asset", item.id) for item in self.assets]
        for scene in self.scenes:
            records.append(("scene", scene.id))
            records += [("layer", layer.id) for layer in scene.layers]
            records += [("marker", marker.id) for marker in scene.markers]
            for layer in scene.layers:
                records += [("marker", marker.id) for marker in layer.markers]
                records += [("effect", effect.id) for effect in layer.effects]
        seen: dict[str, str] = {}
        for kind, stable_id in records:
            if not ID_PATTERN.fullmatch(stable_id):
                raise ValueError(f"invalid stable ID {stable_id!r}")
            if stable_id in seen:
                raise ValueError(f"duplicate stable ID {stable_id!r}: {seen[stable_id]} and {kind}")
            seen[stable_id] = kind
        assets = {asset.id for asset in self.assets}
        for scene in self.scenes:
            if scene.start + scene.duration > self.duration + 1e-6:
                raise ValueError(f"scene {scene.id} exceeds project duration")
            for layer in scene.layers:
                if layer.start + layer.duration > scene.duration + 1e-6:
                    raise ValueError(f"layer {layer.id} exceeds scene duration")
                if layer.asset_id and layer.asset_id not in assets:
                    raise ValueError(f"layer {layer.id} references missing asset {layer.asset_id}")
        if len(self.background) != 3 or any(x < 0 or x > 1 for x in self.background):
            raise ValueError("background must be RGB values in [0, 1]")
        return self

    @property
    def duration(self) -> float:
        return max((scene.start + scene.duration for scene in self.scenes), default=0)


def load_project(path: str | Path) -> AEProject:
    return AEProject.model_validate_json(Path(path).read_text(encoding="utf-8"))


def canonical_project(project: AEProject) -> dict[str, Any]:
    """Return order-independent semantic data suitable for review and diff."""

    data = project.model_dump(mode="json", exclude_none=True)
    data["assets"] = sorted(data.get("assets", []), key=lambda item: item["id"])
    for scene in data["scenes"]:
        scene["layers"] = sorted(scene.get("layers", []), key=lambda item: item["id"])
        scene["markers"] = sorted(scene.get("markers", []), key=lambda item: item["id"])
        for layer in scene["layers"]:
            layer["markers"] = sorted(layer.get("markers", []), key=lambda item: item["id"])
            layer["effects"] = sorted(layer.get("effects", []), key=lambda item: item["id"])
            layer["properties"] = sorted(
                layer.get("properties", []), key=lambda item: item["match_name"]
            )
    data["scenes"] = sorted(data["scenes"], key=lambda item: item["id"])
    return data


def write_canonical(project: AEProject, output: str | Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(canonical_project(project), indent=2) + "\n", encoding="utf-8")
    return output


def _index_records(data: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    records: dict[str, tuple[str, dict[str, Any]]] = {}
    for asset in data.get("assets", []):
        records[asset["id"]] = (f"assets/{asset['id']}", asset)
    for scene in data.get("scenes", []):
        records[scene["id"]] = (f"scenes/{scene['id']}", scene)
        for marker in scene.get("markers", []):
            records[marker["id"]] = (
                f"scenes/{scene['id']}/markers/{marker['id']}", marker
            )
        for layer in scene.get("layers", []):
            records[layer["id"]] = (f"scenes/{scene['id']}/layers/{layer['id']}", layer)
            for marker in layer.get("markers", []):
                records[marker["id"]] = (
                    f"scenes/{scene['id']}/layers/{layer['id']}/markers/{marker['id']}",
                    marker,
                )
            for effect in layer.get("effects", []):
                records[effect["id"]] = (
                    f"scenes/{scene['id']}/layers/{layer['id']}/effects/{effect['id']}",
                    effect,
                )
    return records


def _leaf_diff(
    before: Any, after: Any, path: str = "", inherited_owner: str = "shared"
) -> list[tuple[str, Any, Any, str]]:
    if isinstance(before, dict) and isinstance(after, dict):
        owner = before.get("ownership", after.get("ownership", inherited_owner))
        changes: list[tuple[str, Any, Any, str]] = []
        for key in sorted(set(before) | set(after)):
            if key in {"layers", "assets", "scenes", "markers", "effects"}:
                continue
            changes += _leaf_diff(before.get(key), after.get(key), f"{path}/{key}", owner)
        return changes
    if isinstance(before, list) and isinstance(after, list):
        # Properties have match names (not stable IDs) and carry their own ownership.
        if all(isinstance(item, dict) and "match_name" in item for item in before + after):
            changes: list[tuple[str, Any, Any, str]] = []
            old_index = {item["match_name"]: item for item in before}
            new_index = {item["match_name"]: item for item in after}
            for name in sorted(set(old_index) | set(new_index)):
                changes += _leaf_diff(
                    old_index.get(name),
                    new_index.get(name),
                    f"{path}/{name}",
                    inherited_owner,
                )
            return changes
    if before != after:
        return [(path, before, after, inherited_owner)]
    return []


def semantic_diff(before: AEProject, after: AEProject) -> dict[str, Any]:
    """Classify stable-ID changes according to the baseline ownership contract."""

    left, right = canonical_project(before), canonical_project(after)
    left_index, right_index = _index_records(left), _index_records(right)
    changes: list[dict[str, Any]] = []
    for stable_id in sorted(set(left_index) | set(right_index)):
        old = left_index.get(stable_id)
        new = right_index.get(stable_id)
        owner = (old or new)[1].get("ownership", "shared")
        record_path = (old or new)[0]
        if old is None or new is None:
            disposition = {
                "agent": "agent_can_apply",
                "human": "preserve_human_edit",
                "shared": "conflict_requires_review",
            }[owner]
            changes.append(
                {
                    "stable_id": stable_id,
                    "path": record_path,
                    "kind": "added" if old is None else "removed",
                    "before": None if old is None else old[1],
                    "after": None if new is None else new[1],
                    "ownership": owner,
                    "disposition": disposition,
                }
            )
            continue
        for leaf_path, old_value, new_value, leaf_owner in _leaf_diff(
            old[1], new[1], record_path, owner
        ):
            disposition = {
                "agent": "agent_can_apply",
                "human": "preserve_human_edit",
                "shared": "conflict_requires_review",
            }[leaf_owner]
            changes.append(
                {
                    "stable_id": stable_id,
                    "path": leaf_path,
                    "kind": "modified",
                    "before": old_value,
                    "after": new_value,
                    "ownership": leaf_owner,
                    "disposition": disposition,
                }
            )
    counts = {name: 0 for name in ("agent_can_apply", "preserve_human_edit", "conflict_requires_review")}
    for change in changes:
        counts[change["disposition"]] += 1
    return {
        "schema_version": "1.0",
        "project_id": before.project_id,
        "change_count": len(changes),
        "summary": counts,
        "safe_to_auto_apply": counts["conflict_requires_review"] == 0,
        "changes": changes,
    }


def write_diff(before: AEProject, after: AEProject, output: str | Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(semantic_diff(before, after), indent=2) + "\n", encoding="utf-8")
    return output


def _jsx_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _resolved_spec(project: AEProject, manifest_dir: Path) -> dict[str, Any]:
    data = canonical_project(project)
    for asset in data["assets"]:
        path = Path(asset["path"])
        if not path.is_absolute():
            path = (manifest_dir / path).resolve()
        asset["resolved_path"] = str(path)
    return data


_JSX_INSPECTION_HELPERS = r'''
  function adwJsonQuote(value) {
    return '"' + String(value)
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\x08/g, "\\b")
      .replace(/\f/g, "\\f")
      .replace(/\n/g, "\\n")
      .replace(/\r/g, "\\r")
      .replace(/\t/g, "\\t")
      .replace(/[\x00-\x1f\u2028\u2029]/g, function (character) {
        var code = character.charCodeAt(0).toString(16);
        return "\\u" + ("0000" + code).slice(-4);
      }) + '"';
  }
  function adwStringify(value, indent) {
    var step = typeof indent === "number" && indent > 0 ? new Array(indent + 1).join(" ") : "";
    var stack = [];
    function encode(current, depth) {
      if (current === null) return "null";
      var kind = typeof current;
      if (kind === "string") return adwJsonQuote(current);
      if (kind === "number") return isFinite(current) ? String(current) : "null";
      if (kind === "boolean") return current ? "true" : "false";
      if (kind === "undefined" || kind === "function") return null;
      for (var s=0; s<stack.length; s++) if (stack[s] === current) throw new Error("Cannot serialize cyclic inspection data");
      stack.push(current);
      var nextIndent = step ? new Array(depth + 2).join(step) : "";
      var currentIndent = step ? new Array(depth + 1).join(step) : "";
      var rows = [];
      if (current instanceof Array) {
        for (var a=0; a<current.length; a++) {
          var encodedItem = encode(current[a], depth + 1);
          rows.push(encodedItem === null ? "null" : encodedItem);
        }
      } else {
        var keys = [];
        for (var key in current) if (Object.prototype.hasOwnProperty.call(current, key)) keys.push(key);
        keys.sort();
        for (var k=0; k<keys.length; k++) {
          var encodedValue = encode(current[keys[k]], depth + 1);
          if (encodedValue !== null) rows.push(adwJsonQuote(keys[k]) + (step ? ": " : ":") + encodedValue);
        }
      }
      stack.pop();
      var open = current instanceof Array ? "[" : "{";
      var close = current instanceof Array ? "]" : "}";
      if (!rows.length) return open + close;
      return step ? open + "\n" + nextIndent + rows.join(",\n" + nextIndent) + "\n" + currentIndent + close : open + rows.join(",") + close;
    }
    return encode(value, 0);
  }
  function simpleValue(value) {
    if (value === null || value === undefined) return null;
    if (typeof value === "number" || typeof value === "string" || typeof value === "boolean") return value;
    if (value instanceof Array) { var array=[]; for (var i=0;i<value.length;i++) array.push(simpleValue(value[i])); return array; }
    try { if (value instanceof TextDocument) return {text:value.text,font:value.font,font_size:value.fontSize,fill_color:simpleValue(value.fillColor),justification:String(value.justification)}; } catch (_) {}
    return String(value);
  }
  function snapshotMarkers(group) {
    var result=[]; if (!group) return result;
    for (var i=1;i<=group.numKeys;i++) { var marker=group.keyValue(i); var parameters={};
      try { parameters=marker.getParameters(); } catch (_) {}
      result.push({time:group.keyTime(i),comment:marker.comment || "",duration:marker.duration || 0,chapter:marker.chapter || "",url:marker.url || "",label:marker.label || 0,parameters:parameters});
    } return result;
  }
  function snapshotProperty(prop, depth) {
    var row={name:prop.name,match_name:prop.matchName,property_type:String(prop.propertyType)};
    if (prop.propertyType === PropertyType.PROPERTY) {
      try { row.value=simpleValue(prop.value); } catch (valueError) { row.value=null; row.value_error=valueError.toString(); }
      row.num_keys=prop.numKeys; row.keyframes=[];
      for (var k=1;k<=prop.numKeys;k++) { var key={time:prop.keyTime(k),value:simpleValue(prop.keyValue(k))};
        try { key.in_interpolation=String(prop.keyInInterpolationType(k));key.out_interpolation=String(prop.keyOutInterpolationType(k)); } catch (_) {}
        row.keyframes.push(key);
      }
      if (prop.canSetExpression) { row.expression=prop.expression || ""; row.expression_enabled=prop.expressionEnabled; try { row.expression_error=prop.expressionError || ""; } catch (_) {} }
    } else if (depth < 6) { row.properties=[]; for (var p=1;p<=prop.numProperties;p++) row.properties.push(snapshotProperty(prop.property(p),depth+1)); }
    return row;
  }
  function snapshotLayer(layer) {
    var sourcePath=null; try { if (layer.source && layer.source.file) sourcePath=layer.source.file.fsName; } catch (_) {}
    var row={index:layer.index,name:layer.name,comment:layer.comment || "",start:layer.startTime,in_point:layer.inPoint,out_point:layer.outPoint,stretch:layer.stretch,locked:layer.locked,enabled:layer.enabled,source_path:sourcePath,markers:snapshotMarkers(layer.property("ADBE Marker")),properties:[]};
    for (var p=1;p<=layer.numProperties;p++) row.properties.push(snapshotProperty(layer.property(p),0));
    return row;
  }
  function snapshotProject(project, projectId) {
    var report={schema_version:"1.0",project_id:projectId || null,ae_version:app.version,project_file:project.file ? project.file.fsName : null,revision:project.revision,expression_engine:project.expressionEngine,bits_per_channel:project.bitsPerChannel,working_space:project.workingSpace,items:[],render_queue:[]};
    for (var i=1;i<=project.numItems;i++) { var item=project.item(i); var row={name:item.name,type:item.typeName,comment:item.comment || ""};
      if (item instanceof FootageItem) { try { row.source_path=item.file ? item.file.fsName : null; } catch (_) {} }
      if (item instanceof CompItem) { row.width=item.width;row.height=item.height;row.pixel_aspect=item.pixelAspect;row.duration=item.duration;row.fps=item.frameRate;row.background=simpleValue(item.bgColor);row.markers=snapshotMarkers(item.markerProperty);row.layers=[];for(var l=1;l<=item.numLayers;l++)row.layers.push(snapshotLayer(item.layer(l))); }
      report.items.push(row);
    }
    for (var q=1;q<=project.renderQueue.numItems;q++) { var rq=project.renderQueue.item(q);var rr={comp:rq.comp.name,status:String(rq.status),render:rq.render,time_span_start:rq.timeSpanStart,time_span_duration:rq.timeSpanDuration,render_templates:rq.templates,output_modules:[]};
      for(var o=1;o<=rq.numOutputModules;o++){var om=rq.outputModule(o);rr.output_modules.push({file:om.file ? om.file.fsName : null,templates:om.templates});} report.render_queue.push(rr);
    }
    return report;
  }
'''


def generate_build_jsx(
    project: AEProject,
    manifest_dir: str | Path,
    project_output: str | Path,
    report_output: str | Path,
) -> str:
    """Generate deterministic ES3-compatible JSX; execution still requires After Effects."""

    spec = _resolved_spec(project, Path(manifest_dir))
    project_output = str(Path(project_output).resolve())
    report_output = str(Path(report_output).resolve())
    return f'''// Generated by academic-design-workflow. Do not hand-edit.
// Requires After Effects ExtendScript and file-write permission.
(function () {{
  var SPEC = {_jsx_literal(spec)};
  var PROJECT_OUTPUT = {_jsx_literal(project_output)};
  var REPORT_OUTPUT = {_jsx_literal(report_output)};
  function tag(id, owner) {{ return "ADW_ID=" + id + ";OWNER=" + owner; }}
  function byId(items, id) {{ for (var i=0; i<items.length; i++) if (items[i].id === id) return items[i]; return null; }}
  function findProperty(group, matchName) {{
    var direct=group.property(matchName); if (direct) return direct;
    for (var i=1;i<=group.numProperties;i++) {{ var child=group.property(i); if(child.matchName===matchName)return child; if(child.propertyType!==PropertyType.PROPERTY){{var nested=findProperty(child,matchName);if(nested)return nested;}} }}
    return null;
  }}
  function setProperty(group, p) {{
    var prop = findProperty(group, p.match_name);
    if (!prop) throw new Error("Missing property " + p.match_name);
    if (p.value !== undefined && p.value !== null) prop.setValue(p.value);
    for (var k=0; k<p.keyframes.length; k++) prop.setValueAtTime(p.keyframes[k].time, p.keyframes[k].value);
    if (p.expression !== undefined && p.expression !== null && prop.canSetExpression) prop.expression = p.expression;
  }}
  function setMarkers(group, markers) {{
    for (var i=0; i<markers.length; i++) {{
      var marker = new MarkerValue(markers[i].comment);
      marker.duration = markers[i].duration;
      marker.setParameters({{ADW_ID: markers[i].id, OWNER: markers[i].ownership}});
      group.setValueAtTime(markers[i].time, marker);
    }}
  }}
  function addLayer(comp, layerSpec, assetItems) {{
    var layer;
    if (layerSpec.kind === "text") {{
      layer = comp.layers.addText(layerSpec.text);
      var sourceText = layer.property("ADBE Text Properties").property("ADBE Text Document");
      var textDocument = sourceText.value;
      if (layerSpec.text_font !== undefined && layerSpec.text_font !== null) textDocument.font = layerSpec.text_font;
      if (layerSpec.text_size !== undefined && layerSpec.text_size !== null) textDocument.fontSize = layerSpec.text_size;
      if (layerSpec.text_fill !== undefined && layerSpec.text_fill !== null) {{ textDocument.applyFill = true; textDocument.fillColor = layerSpec.text_fill; }}
      if (layerSpec.text_justification === "left") textDocument.justification = ParagraphJustification.LEFT_JUSTIFY;
      else if (layerSpec.text_justification === "center") textDocument.justification = ParagraphJustification.CENTER_JUSTIFY;
      else if (layerSpec.text_justification === "right") textDocument.justification = ParagraphJustification.RIGHT_JUSTIFY;
      sourceText.setValue(textDocument);
    }}
    else if (layerSpec.kind === "null") layer = comp.layers.addNull();
    else if (layerSpec.kind === "shape") {{
      layer = comp.layers.addShape();
      var contents = layer.property("ADBE Root Vectors Group");
      var group = contents.addProperty("ADBE Vector Group");
      var vectors = group.property("ADBE Vectors Group");
      var shape = vectors.addProperty(layerSpec.shape === "ellipse" ? "ADBE Vector Shape - Ellipse" : "ADBE Vector Shape - Rect");
      var sizeMatchName = layerSpec.shape === "ellipse" ? "ADBE Vector Ellipse Size" : "ADBE Vector Rect Size";
      var sizeProperty = shape.property(sizeMatchName);
      if (!sizeProperty) throw new Error("Missing AE shape-size property " + sizeMatchName);
      sizeProperty.setValue(layerSpec.size);
      var fill = vectors.addProperty("ADBE Vector Graphic - Fill");
      fill.property("ADBE Vector Fill Color").setValue(layerSpec.fill.slice(0, 3));
      if (layerSpec.fill.length === 4) fill.property("ADBE Vector Fill Opacity").setValue(layerSpec.fill[3] * 100);
    }} else {{
      var item = assetItems[layerSpec.asset_id];
      if (!item) throw new Error("Missing imported asset " + layerSpec.asset_id);
      layer = comp.layers.add(item);
      if (layerSpec.kind === "audio") layer.audioEnabled = true;
    }}
    layer.name = layerSpec.name;
    layer.comment = tag(layerSpec.id, layerSpec.ownership);
    layer.startTime = layerSpec.start;
    layer.inPoint = layerSpec.start;
    layer.outPoint = layerSpec.start + layerSpec.duration;
    for (var p=0; p<layerSpec.properties.length; p++) setProperty(layer, layerSpec.properties[p]);
    for (var e=0; e<layerSpec.effects.length; e++) {{
      var effectSpec = layerSpec.effects[e];
      var effect = layer.property("ADBE Effect Parade").addProperty(effectSpec.match_name);
      effect.name = effectSpec.id;
      for (var ep=0; ep<effectSpec.properties.length; ep++) setProperty(effect, effectSpec.properties[ep]);
    }}
    setMarkers(layer.property("ADBE Marker"), layerSpec.markers);
    return layer;
  }}
{_JSX_INSPECTION_HELPERS}
  function writeReport(project) {{
    var report = snapshotProject(project, SPEC.project_id);
    var file = new File(REPORT_OUTPUT); file.encoding="UTF-8";
    if (!file.open("w")) throw new Error("Cannot open report output: " + file.error);
    file.write(adwStringify(report, 2)); file.close();
  }}
  app.beginUndoGroup("ADW build " + SPEC.project_id);
  try {{
    if (app.project && (app.project.file !== null || app.project.numItems > 0)) throw new Error("Builder requires a blank unsaved project; it will not replace an open project");
    if (!app.project) app.newProject();
    var project = app.project;
    var projectOutputFile = new File(PROJECT_OUTPUT);
    if (projectOutputFile.exists) throw new Error("Refusing to overwrite existing project: " + PROJECT_OUTPUT);
    var markerFolder = project.items.addFolder("__ADW_PROJECT__" + SPEC.project_id);
    markerFolder.comment = tag(SPEC.project_id, "shared");
    var assetItems = {{}};
    for (var a=0; a<SPEC.assets.length; a++) {{
      var asset = SPEC.assets[a]; var file = new File(asset.resolved_path);
      if (!file.exists) throw new Error("Missing asset: " + asset.resolved_path);
      var imported = project.importFile(new ImportOptions(file)); imported.comment = tag(asset.id, asset.ownership); assetItems[asset.id] = imported;
    }}
    var sceneComps = {{}};
    for (var s=0; s<SPEC.scenes.length; s++) {{
      var scene=SPEC.scenes[s];
      var comp=project.items.addComp(scene.name, SPEC.width, SPEC.height, 1, scene.duration, SPEC.fps);
      comp.comment=tag(scene.id, scene.ownership); comp.bgColor=SPEC.background; sceneComps[scene.id]=comp;
      setMarkers(comp.markerProperty, scene.markers);
      for (var l=scene.layers.length-1; l>=0; l--) addLayer(comp, scene.layers[l], assetItems);
    }}
    var main=project.items.addComp(SPEC.title, SPEC.width, SPEC.height, 1, {project.duration}, SPEC.fps);
    main.comment=tag(SPEC.project_id + ".main", "shared"); main.bgColor=SPEC.background;
    for (var m=SPEC.scenes.length-1; m>=0; m--) {{ var sc=SPEC.scenes[m]; var sl=main.layers.add(sceneComps[sc.id]); sl.name=sc.name; sl.comment=tag(sc.id + ".instance", sc.ownership); sl.startTime=sc.start; sl.inPoint=sc.start; sl.outPoint=sc.start+sc.duration; }}
    project.renderQueue.items.add(main);
    writeReport(project);
    project.save(projectOutputFile);
  }} catch (error) {{
    var errorDetail = error.toString();
    try {{ if (error.line !== undefined) errorDetail += " at line " + error.line; }} catch (_) {{}}
    try {{ if (error.fileName) errorDetail += " in " + error.fileName; }} catch (_) {{}}
    alert("ADW build failed: " + errorDetail); throw error;
  }}
  finally {{ app.endUndoGroup(); }}
}})();
'''


def generate_inspect_jsx(report_output: str | Path) -> str:
    """Generate a read-only project inspection script for a human-edited AEP/AEPX."""

    report_output = str(Path(report_output).resolve())
    return f'''// Generated by academic-design-workflow. Inspects the currently open project.
(function () {{
  var OUTPUT = {_jsx_literal(report_output)};
  if (!app.project) throw new Error("Open an After Effects project first");
{_JSX_INSPECTION_HELPERS}
  var project=app.project; var projectId=null;
  for(var i=1;i<=project.numItems;i++){{var item=project.item(i);if(item.name.indexOf("__ADW_PROJECT__")===0){{projectId=item.name.substring(15);break;}}}}
  var report=snapshotProject(project,projectId);
  var file=new File(OUTPUT);file.encoding="UTF-8";if(!file.open("w"))throw new Error("Cannot open report: "+file.error);file.write(adwStringify(report,2));file.close();
}})();
'''


def validate_jsx_static(script: str) -> list[str]:
    """Cheap deterministic guardrails, not a substitute for executing in AE."""

    errors: list[str] = []
    if script.count("{") != script.count("}"):
        errors.append("unbalanced curly braces")
    if script.count("(") != script.count(")"):
        errors.append("unbalanced parentheses")
    for forbidden in ("=>", "const ", "let ", "`"):
        if forbidden in script:
            errors.append(f"non-ES3 token present: {forbidden!r}")
    if not math.isfinite(float(len(script))):
        errors.append("invalid script length")
    return errors
