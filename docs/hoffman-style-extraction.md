# Hoffman style extraction

The `hoffman` theme is an original derivative of `rolling-diffusion`. It uses
user-supplied technical diagrams and the Hoffman website demo only to identify
reusable visual principles; it does not reproduce a reference's scientific
content or composition. Reference provenance remains external to this repository.

Version 3 retains the version 2 paper grammar and adds an explicit website
language: a full-bleed near-black media hero followed by compact light academic
sections. This is a web-variant extension, not a dark-theme replacement for paper
figures.

## Website evidence

The visual audit used `HoffMan WebTpl.mp4`, sampled at three-second intervals
from 0 to 24 seconds. The supplied file is 1920 x 1080, about 25.03 seconds long,
and has SHA-256
`73E54D26F81080F3B95323C45C2EC1DDB58E0577DD5392709EB25248C2515446`.
The current `hoffman.github.io` implementation at commit `e88b303` was inspected
only to confirm exact token values already visible in the rendered demo.

The audit found two deliberately coordinated modes rather than one uniformly
dark site:

- The opening hero is a spatially stable, full-bleed robot-video field. White and
  quiet-gray typography occupies a protected reading zone; orange marks the main
  command; muted blue and burgundy preserve state/action semantics.
- Subsequent method and evidence sections return to the pale academic canvas,
  charcoal integrated rails, thin orange rules, compact type, and dense alignment
  used by paper figures.
- Navigation changes contrast at the dark/light boundary instead of floating in
  a permanently dark shell.
- Entry motion is restrained and directional, while semantic animation follows
  established signal rails. Reduced motion uses a crossfade.

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
- The `web` variant adds `hero_deep`, `hero_mid`, an inverse text ladder, a
  readable dark-surface blue, and quiet inverse borders. These roles are scoped to
  web so paper output continues to resolve the original pale canvas.
- `hero_field`, `hero_media`, primary/quiet hero buttons, and state/core/action
  signal shapes encode the dark opening. `phase_tab_active` carries the compact
  square editorial rhythm after the hero.
- Web layout uses a 1420 px content width, 1080/820/520 px responsive boundaries,
  and restrained 4/12/24 px radii. The deliberate entry duration is 560 ms and
  ordinary updates remain 220 ms.

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

The website proof now demonstrates the dark-media/light-editorial boundary while
the foundations proof remains an academic component board. The theme does not
transfer marketing copy, decorative card grids, or dark surfaces into paper
figures.

Generate the complete proof with:

```bash
adw validate themes/hoffman.yaml
adw compile themes/hoffman.yaml --output generated/hoffman
adw styleboard themes/hoffman.yaml --output generated/styleboards/hoffman
```
