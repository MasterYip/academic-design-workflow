# Overall Style SOP

Use this reference to create or materially revise the cross-media design system.

## Design brief and semantics

Capture audience, contribution, venue, media, final dimensions, printing limits,
existing identity, and accessibility constraints. Describe the desired voice with
three specific qualities and three anti-goals. List recurring meanings before
choosing colors: primary method, observations, actions, baselines, uncertainty,
success, warning, failure, neutral structure, and focal contribution.

## Total style definition

Complete all theme systems; a palette alone is not a complete theme.

- Color: surfaces, text contrast, semantic accents, data palettes, named opacity.
- Typography: font stacks, role sizes, weights, line height, casing, math fallback.
- Shapes: geometry, corners, fill, stroke hierarchy, dashes, connectors,
  arrowheads, padding, icons, and shadows.
- Spacing/layout: base unit, density, grids, aspect ratios, margins, reading order.
- Charts: axes, grid, lines, markers, uncertainty, legend, and integrity rules.
- Web: breakpoints, focus behavior, component radii, and state transitions.
- Motion/video: transition families, timing, easing, safe area, and captions.

Opacity is structural: low alpha for contextual regions and uncertainty, medium
alpha for supporting layers, and solid color for focal marks. Do not lower text
opacity to make it quiet; use a readable secondary text color.

## Proof and version

Render palette roles, typography, shapes, connectors, a plot, a schematic, and
representative web/video frames. Evaluate at delivery size and in grayscale.
Revise the theme instead of patching the proof. Validate YAML, compile all token
targets, and increment the theme version for visual breaking changes.

