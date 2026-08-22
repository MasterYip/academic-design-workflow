# Hoffman style extraction

The `hoffman` theme is an original derivative of `rolling-diffusion`. It uses the
user-supplied technical diagram only to identify reusable visual principles; it
does not reproduce the diagram's scientific content, labels, or composition. The
reference's license and original provenance were not provided.

Version 2 introduces the compound widget/node grammar and layered data-store
silhouette; this is a deliberate visual breaking change from the simpler first proof.

## Observations

- Large light-gray panel bodies establish the primary reading stages.
- A charcoal title rail spans each panel and visually belongs to its container.
- The title rail has rounded top corners and square lower corners, so it reads as
  the top of the panel rather than a detached badge or clipped trapezoid.
- Compact rounded widgets, explicit ports, and black directed connectors make
  local data flow legible. A small warm accent identifies focal computation.
- Data stores use a stacked-cylinder silhouette with repeated top contours, while
  long charcoal rounded rails name collection or process stages.
- Dense examples are composed as one readable system, not a mosaic of unrelated
  component cards.
- Shape, enclosure, labels, and line style carry meaning in addition to color.

## Hoffman adaptations

- `panel_container` and `panel_header` form one reusable panel pattern. The header
  uses `rounded_top_rectangle`, spans the container width, and shares its top
  radius; the panel renderer owns their alignment.
- `semantic_row(...)` composes `widget_row`, quiet segments, and one active segment
  into observation/noise or state/action patterns with hierarchy beyond a plain box.
- `compound_node(...)` composes node enclosure, internal title band, detail line,
  semantic badge, and labeled input/output ports. Focal nodes combine the warm
  boundary with a distinct output port rather than relying on hue alone.
- `graph_group`, `graph_node`, `graph_node_focal`, and `graph_port` define graph
  containment, computation, emphasis, and interfaces without artifact-local
  colors.
- Hoffman overrides `dataset` with the reusable `layered_cylinder` geometry; the
  generic cylinder used by other themes remains unchanged. `process_bar` provides
  a long charcoal rounded stage rail with theme-resolved inverse text.
- `graph_flow`, `graph_feedback`, and `graph_guide` distinguish forward flow,
  feedback, and non-causal alignment using solid, dashed, and dotted strokes.
- Primary, secondary, and hairline strokes use deliberately separated weights;
  corners and padding tighten as elements move from panels to groups to widgets.
- The inherited muted-blue/orange/burgundy signal roles remain restrained against
  a predominantly neutral field. Focal state uses both an orange boundary and a
  stronger component role, so emphasis survives grayscale.

## Usage

Use `panel(...)` for integrated titled stages, `semantic_row(...)` for segmented
state widgets, and `compound_node(...)` for graph computation. Use `arrow(...)`
with the graph stroke names for relationship types. Keep bounds in layout code
and all visual constants in the theme.

```python
panel(ax, theme, (0, 0, 6, 4), "Data processing", label="a")
semantic_row(ax, theme, (0.5, 2.4, 2.6, 0.6), ("Observation", "Noise"))
compound_node(ax, theme, (3.7, 1.7, 1.8, 1.2), title="Encode",
              detail="normalize · embed", badge="STATE")
styled_shape(ax, theme, (0.5, 0.6, 5.0, 0.5), style="process_bar",
             title="PROCESS STAGE")
```

The revised foundations proof follows the installed frontend art-direction skill
only at the composition level: one dominant miniature system, restrained accent,
and hierarchy driven by scale, spacing, alignment, and contrast. Landing-page
hero, marketing copy, motion, and generic card patterns are intentionally not
transferred into this academic component board.

Generate the complete proof with:

```bash
adw validate themes/hoffman.yaml
adw compile themes/hoffman.yaml --output generated/hoffman
adw styleboard themes/hoffman.yaml --output generated/styleboards/hoffman
```
