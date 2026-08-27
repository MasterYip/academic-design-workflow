# Native Visio Co-authoring SOP

Read the repository's complete
[`docs/visio-human-agent-workflow.md`](../../../docs/visio-human-agent-workflow.md)
before generating or modifying a VSDX.

## Required workflow

1. Keep the theme and publication renderer as visual truth. Represent the chart
   as a versioned semantic scene with stable `NameU`/Shape Data IDs.
2. Draw blocks, text, ports, and glued 1-D connectors as native Visio objects.
   Imported SVG/PDF/raster artwork is not native semantic editing.
3. Validate the scene offline, generate to a new VSDX path, then retain the
   bridge record, package audit, and preview.
4. Bind automated revisions to scene and targeted-element hashes. Never infer a
   two-way source update from arbitrary unrecorded canvas changes.
5. Compare layout, font, text overflow, alignment, connector glue, and foreign
   package content against the canonical preview before handoff.

## Equations

Choose the edit unit explicitly:

- Native Unicode text for simple symbols.
- AxMath OLE for professional equations that must remain editable in an
  installed equation editor. Use `build_axmath_object.ps1` and
  `embed_axmath.ps1`; retain exact source/display LaTeX Shape Data and audit the
  exact AxMath CLSID allowlist.
- Word/OMML OLE when structured Office Math is required and AxMath is absent.
- MathText/TeX SVG only when LaTeX regeneration, not direct term editing in
  Visio, is the accepted contract.

Never use `Equation.3`, SendKeys, focus-dependent UI automation, or a PNG as an
editable equation. AxMath is a narrow foreign-object exception: one genuine OLE
embedding and one EMF cache per declared semantic ID. Other foreign content
must still fail audit.

## Process and durability safety

Inventory Visio/AxMath/Office PIDs before launch. Create a separate owned
automation instance, use only that instance, close normally, and verify all
unowned process sets are unchanged. Never attach to, repurpose, or terminate a
human's open canvas.

Write immutable revision paths. A visible unsaved canvas is not a deliverable.
Save, close, reopen, render, hash, and audit the exact VSDX that will be handed
to the human. Preserve the source VSDX and record all semantic additions and
unrelated drift checks.
