# Hoffman style extraction

The `hoffman` theme is an original derivative of `rolling-diffusion`. It uses the
user-supplied technical diagram only to identify reusable visual principles; it
does not reproduce the diagram's scientific content, labels, or composition. The
reference's license and original provenance were not provided.

## Observations

- Large light-gray panel bodies establish the primary reading stages.
- A charcoal title rail spans each panel and visually belongs to its container.
- The title rail has rounded top corners and square lower corners, so it reads as
  the top of the panel rather than a detached badge or clipped trapezoid.
- Compact rounded widgets, explicit ports, and black directed connectors make
  local data flow legible. A small warm accent identifies focal computation.
- Shape, enclosure, labels, and line style carry meaning in addition to color.

## Hoffman adaptations

- `panel_container` and `panel_header` form one reusable panel pattern. The header
  uses `rounded_top_rectangle`, spans the container width, and shares its top
  radius; the panel renderer owns their alignment.
- `widget` and `widget_focal` cover compact observation/action or status controls.
- `graph_group`, `graph_node`, `graph_node_focal`, and `graph_port` define graph
  containment, computation, emphasis, and interfaces without artifact-local
  colors.
- `graph_flow`, `graph_feedback`, and `graph_guide` distinguish forward flow,
  feedback, and non-causal alignment using solid, dashed, and dotted strokes.
- The inherited muted-blue/orange/burgundy signal roles remain restrained against
  a predominantly neutral field. Focal state uses both an orange boundary and a
  stronger component role, so emphasis survives grayscale.

## Usage

Use `panel(...)` for integrated titled stages and semantic shape names with
`styled_shape(...)` for widgets and graph elements. Use `arrow(...)` with the
graph stroke names for relationship types. Keep bounds in layout code and all
visual constants in the theme.

```python
panel(ax, theme, (0, 0, 6, 4), "Data processing", label="a")
styled_shape(ax, theme, (0.7, 1.1, 1.8, 0.8), style="graph_node", title="Encode")
arrow(ax, theme, (2.5, 1.5), (3.4, 1.5), style="graph_flow")
```

Generate the complete proof with:

```bash
adw validate themes/hoffman.yaml
adw compile themes/hoffman.yaml --output generated/hoffman
adw styleboard themes/hoffman.yaml --output generated/styleboards/hoffman
```
