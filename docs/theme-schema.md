# Theme architecture

The theme is a versioned contract, not a loose collection of colors. Every
downstream renderer validates the same YAML document and consumes semantic tokens.

A theme may declare `extends: another-theme.yaml`. Mappings merge recursively;
lists and scalar values replace their parent values. Cycles are rejected, and the
fully resolved document must satisfy the complete schema.

`variants` provides validated medium-specific overrides such as `paper`, `web`,
and `video`. Semantic role names must remain stable; variants change surface,
contrast, density, or motion treatment. The compiler emits separate JSON, CSS,
and Matplotlib artifacts for every declared variant.

| System | Controls | Cross-media invariant |
|---|---|---|
| `meta` | intent, anti-goals, version | why the system looks and behaves this way |
| `color` | surfaces, text, data, status, opacity ramps | semantic meaning and contrast |
| `typography` | font stacks, math, role scale, line height, casing | hierarchy and voice |
| `shape` | geometry, corners, fill, strokes, dashes, arrows, icons, shadows | object and relationship grammar |
| `spacing` | base unit, scale, density | grouping rhythm |
| `layout` | grids, margins, paper widths, ratios, reading order | composition logic |
| `chart` | axes, lines, markers, uncertainty, legends, integrity | scientific encoding |
| `web` | widths, breakpoints, focus, radius, transitions | responsive interaction |
| `motion` | purpose, easing, timing, reduced motion | temporal behavior |
| `video` | canvas, safe area, captions, scene defaults | delivery composition |

## Semantic use

Use `data_primary` for the primary scientific entity even if its hex value changes.
Do not create names tied to appearance or position. If a new scientific meaning
needs persistent treatment across artifacts, add a role with documented usage.

The opacity scale distinguishes invisible, ghost, subtle, muted, supporting, and
solid layers. Text remains on explicit text colors; opacity is not a substitute for
readable hierarchy. Shape vocabulary combines geometry, fill, opacity, stroke,
corner radius, padding, shadow, and emphasis into reusable objects.

## Compilation

`adw compile` emits the validated theme as JSON, all tokens as CSS variables, and
Matplotlib `rcParams`. Python schematics bind directly to the validated model.
Web and video packages consume compiled tokens rather than re-declaring a style.
