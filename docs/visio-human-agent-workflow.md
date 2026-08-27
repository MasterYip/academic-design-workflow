# Native Visio human-agent co-authoring

The Visio workflow turns a versioned semantic scene into an original VSDX made
from native Visio shapes, native text, named ports, and glued 1-D connectors. It
does not insert or convert SVG, PDF, EMF, or raster chart content.

Use it when a human needs to move, resize, restyle, or relabel logical diagram
elements in Visio without entering deep imported groups. Keep the declarative
scene and the publication renderer as the reproducible source of truth.

## Prerequisites

- Python 3.10+ is enough for validation, semantic edit planning, JSON Schema,
  VSDX package audit, and semantic diff.
- Native generation and direct VSDX editing require Windows, PowerShell, and an
  installed Microsoft Visio exposing `Visio.InvisibleApp`.
- Direct AxMath equation generation additionally requires registered 32-bit
  `Equation.AxMath` with CLSID
  `{B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28}` and the 32-bit .NET Framework C#
  compiler. The script checks both and fails closed.
- The Visio dependency is optional. Unsupported hosts fail explicitly only when
  `generate` or `edit` is invoked.

## Scene contract

Scene schema `1.0` contains:

- a stable `scene_id`, monotonically increasing `revision`, page coordinate
  space, and physical page size;
- semantic color roles and a font family;
- native shapes with globally unique semantic IDs, roles, geometry, text,
  optional shallow parent IDs, named normalized ports, styles, and validated
  string Shape Data for source provenance or original equation text;
- optional non-overlapping half-open `text_runs` that retain one selectable
  native shape while giving title/detail ranges distinct point sizes and weights;
- optional native rotation for ordinary shapes and text, used for vertical axes
  or diagram vocabulary without introducing groups or foreign artwork;
- native connectors with globally unique IDs, explicit source/target shape and
  port IDs, optional routes, and connector styles.

Scenes may also carry validated string metadata. The bridge stores scene metadata
on the page sheet and per-shape `data` on the corresponding native object. Keys
must be stable semantic identifiers and cannot shadow workflow-reserved rows.

Validation rejects extra fields, duplicate IDs, invalid or out-of-page geometry,
unknown color roles, duplicate/missing ports, dangling endpoints/parents, and
hierarchy cycles. Text runs must be ordered, non-overlapping, and remain within
the native text length. Emit the machine-readable current contract with:

```powershell
adw visio schema --output scene-v1.schema.json
```

## Round trip

The checked-in Hoffman example is deliberately content-specific; the library is
not. Run from the repository root:

```powershell
adw visio validate examples/visio/hoffman_policy.scene.json --json

adw visio generate examples/visio/hoffman_policy.scene.json `
  --output generated/visio/hoffman-policy.vsdx `
  --preview generated/visio/hoffman-policy.png `
  --audit generated/visio/hoffman-policy.audit.json `
  --bridge-record generated/visio/hoffman-policy.bridge.json

adw visio edit generated/visio/hoffman-policy.vsdx `
  examples/visio/hoffman_policy.scene.json `
  examples/visio/hoffman_policy.resize.edit.json `
  --output-scene generated/visio/hoffman-policy.r2.scene.json `
  --output-vsdx generated/visio/hoffman-policy.r2.vsdx `
  --preview generated/visio/hoffman-policy.r2.png `
  --change-record generated/visio/hoffman-policy.r2.change.json `
  --audit generated/visio/hoffman-policy.r2.audit.json `
  --bridge-record generated/visio/hoffman-policy.r2.bridge.json

adw visio diff generated/visio/hoffman-policy.vsdx `
  generated/visio/hoffman-policy.r2.vsdx `
  --output generated/visio/hoffman-policy.r1-r2.diff.json
```

For an offline-only review, use `apply-edits` instead of `edit`:

```powershell
adw visio apply-edits examples/visio/hoffman_policy.scene.json `
  examples/visio/hoffman_policy.resize.edit.json `
  --output-scene generated/visio/hoffman-policy.r2.scene.json `
  --change-record generated/visio/hoffman-policy.r2.change.json
```

## Edit request and stale-input safety

Each edit request binds to:

1. `scene_id`;
2. the canonical SHA-256 of the complete base scene;
3. the canonical SHA-256 of every targeted semantic element.

One request may target each ID at most once. Missing, duplicate, stale, and no-op
edits are rejected before Visio starts. Shape edits support position, size, text,
and style patches. Connector edits intentionally support style only; changing
relationships requires an explicit scene revision. The change record lists exact
before/after values and hashes, changed IDs, and all preserved IDs.

The VSDX page stores the scene hash in Shape Data. Direct edits refuse a VSDX
whose stored hash differs from the request's base hash. Existing output paths are
never overwritten.

## Human handoff SOP

1. Agent validates the scene and generates VSDX, preview, bridge record, and
   package audit.
2. Human opens the VSDX, selects blocks by semantic `NameU`/Shape Data, and
   records desired changes by stable ID. The original file remains unchanged.
3. Agent translates accepted changes into a stale-bound edit request and runs
   `apply-edits` or `edit`.
4. Agent reviews the before/after previews, change record, package audit, and
   semantic diff. The audit must retain native shapes, two glue relations per
   connector, unique semantic IDs, and zero foreign/media content.

### Equation method selection

Visio has no native professional math-layout surface. Choose the edit contract
before choosing a renderer:

| Requirement | Method | Honest edit unit |
|---|---|---|
| Simple labels and symbols | Native Unicode Visio text | Shape text |
| Professional math editable through an installed equation editor | AxMath OLE, preferred | AxMath expression |
| Structured Office equation without AxMath | Word/OMML OLE fallback | Embedded Word equation |
| Exact Python/TeX visual match and deterministic regeneration | MathText/TeX path SVG | LaTeX source plus regeneration |

Imported SVG paths are selectable vector geometry, not semantic equation terms.
Do not describe them as native or directly math-editable. Never instantiate the
deprecated `Equation.3` server.

#### Direct AxMath objects

Task 015 established a focus-independent route that does not require manual
AxMath entry or keyboard automation. `scripts/visio/AxMathOleDirect.cs` is
compiled as x86 and creates a genuine `.afx` OLE structured-storage object with
`OleCreate`, a real `IOleClientSite::SaveObject`, Unicode clipboard LaTeX,
`IOleObject::DoVerb(11)`, and `IPersistStorage`. The Visio script embeds that
object with `InsertFromFile(..., visInsertAsEmbed)`.

Generate one standalone object with:

```powershell
scripts/visio/build_axmath_object.ps1 `
  -OutputAfx generated/visio/equation.afx `
  -Latex '\hat{y}_0\in\mathbb{R}^{H\times29}'
```

For a figure, generate the native VSDX first, then overlay equations on stable
semantic carriers using a manifest:

```powershell
scripts/visio/embed_axmath.ps1 `
  -InputVsdx generated/visio/hoffman-policy.vsdx `
  -OutputVsdx generated/visio/hoffman-policy.axmath.vsdx `
  -Manifest examples/visio/hoffman_policy.axmath.json `
  -Record generated/visio/hoffman-policy.axmath.record.json `
  -Preview generated/visio/hoffman-policy.axmath.png

adw visio audit generated/visio/hoffman-policy.axmath.vsdx `
  --allow-axmath-id axmath_state_head `
  --allow-axmath-id axmath_action_head `
  --output generated/visio/hoffman-policy.axmath.audit.json
```

Each replacement keeps the native carrier, adds a named equation child, and
records `SemanticID`, `ParentSemanticID`, `SourceText`, `DisplayLatex`,
`AxMathProgID`, and `AxMathCLSID`. `pin_x`/`pin_y` default to the carrier center;
positive `max_width` and `max_height` bound aspect-preserving scale. AxMath
renders monochrome and Visio stores one OLE embedding plus one EMF presentation
cache per object. AxMath must be installed to edit the expression later.

The AxMath audit exception is exact, not a blanket permission for foreign data.
It requires the declared semantic IDs and metadata, genuine compound-file roots
with the AxMath CLSID, one `ForeignData`, one embedding, and one EMF cache per
equation. Every undeclared foreign shape, embedding, image, or group still fails.

#### Structured Office Math fallback

When AxMath is unavailable but structured editability is required, generate a
small `Word.Document.12` DOCX containing OMML and use
`scripts/visio/embed_office_math.ps1`. Call `audit_vsdx(...,
allowed_office_math_semantic_ids=(...))` or repeat CLI option
`--allow-office-math-id`. Record the exact LaTeX source alongside OMML. Word OLE
can have slower shutdown and weaker cached rendering, so use bounded waits and
report delayed normal closure rather than terminating a process.
5. Accepted geometry is back-ported to the canonical scene/publication source.
   Do not treat arbitrary unrecorded VSDX manipulation as automatic round trip.

## Safety and recovery

The bridge creates a separate invisible Visio automation instance, records the
process IDs that appeared after creation, calls normal COM `Quit()`, and verifies
that only its owned process has closed. It never kills processes. If an owned
instance cannot close normally, the command stops and reports the condition; a
human decides recovery. Do not attach to or terminate an existing Visio process.

Equation automation applies the same ownership rule to Visio, AxMath, Word, and
PowerPoint. Inventory process IDs before launch, operate only the newly created
instance, call normal close/quit, wait within a declared bound, and require the
before/after unowned process sets to match. Do not use `GetActiveObject`, reuse an
open human canvas, send keystrokes to the foreground, or terminate a process.

Always write to a new VSDX path. After embedding equations, save, close, reopen,
export a preview, and compare package/semantic audits to the baseline. An open
unsaved Visio canvas is not evidence that a durable VSDX exists; the output path,
checksum, reopened preview, and audit are the handoff evidence.

Generation/edit errors leave the input scene and VSDX untouched. Remove or rename
partial task-owned outputs only after inspection, then retry with a new output
path. Package `audit` and `diff` are read-only and never launch Visio.

## Known limitations

- Visio-native Unicode math remains editable but does not match a TeX renderer's
  italic metrics and spacing.
- AxMath objects require the installed AxMath OLE server for semantic edits,
  render monochrome, and add one embedding and EMF cache per equation.
- Connector routing and arrowheads can differ modestly from Matplotlib/SVG.
- Generation orders native objects as canvas, panel fills, connectors, then
  ordinary content so causal routes remain visible without crossing block text.
- Compound widgets are represented as shallow semantic children, not a general
  constraint solver or automatic two-way VSDX-to-Python reconstruction.
- The bridge currently supports rectangles, rounded rectangles, ellipses, text,
  and orthogonal/polyline connectors. Extend the versioned contract deliberately
  for additional native vocabulary shapes.

## Microsoft API basis

The bridge uses documented native APIs: [`Page.DrawRectangle`](https://learn.microsoft.com/en-us/office/vba/api/visio.page.drawrectangle),
[`Page.DrawOval`](https://learn.microsoft.com/en-us/office/vba/api/visio.page.drawoval),
[`InvisibleApp.ConnectorToolDataObject`](https://learn.microsoft.com/en-us/office/vba/api/visio.invisibleapp.connectortooldataobject),
[`Cell.GlueTo`](https://learn.microsoft.com/en-us/office/vba/api/visio.cell.glueto),
[`Shape.AddNamedRow`](https://learn.microsoft.com/en-us/office/vba/api/visio.shape.addnamedrow),
and stable [`Shape.NameU`](https://learn.microsoft.com/en-us/office/vba/api/visio.shape.nameu).
The read-only auditor follows Microsoft's documented
[VSDX Open Packaging/XML format](https://learn.microsoft.com/en-us/office/client-developer/visio/introduction-to-the-visio-file-formatvsdx).
