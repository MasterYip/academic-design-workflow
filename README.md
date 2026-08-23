# Academic Design Workflow

An independent, theme-first toolkit and Codex skill for keeping paper figures,
project websites, and videos visually coherent. A versioned YAML theme is the
single source of truth for color, opacity, typography, shape grammar, strokes,
spacing, layout, chart encoding, web behavior, and motion.

## Quick start

```bash
python -m pip install -e .
adw validate themes/academic-clean.yaml
adw compile themes/academic-clean.yaml --output generated/academic-clean
adw styleboard themes/rolling-diffusion.yaml --output generated/styleboards/rolling-diffusion
adw visio validate examples/visio/hoffman_policy.scene.json
```

The compiler creates `theme.json`, `theme.css`, and `matplotlib.json`. The
style-board command creates five coordinated SVG/PDF/PNG boards—foundations,
charts, paper framework, website UI, and video composition—plus an overview.

Included themes:

- `academic-clean`: restrained, warm, publication-first technical clarity.
- `rolling-diffusion`: extracted from user-provided rolling-diffusion figures;
  charcoal clipped panels, neutral machinery, and vivid semantic signal colors.
- `hoffman`: a rolling-diffusion derivative with integrated full-width rounded-top
  panel rails plus reusable widget, graph-node, port, and connector patterns.
- `intact`: extracted from user-provided INTACT references; pale blue/blush,
  math-forward paper diagrams plus a dark blue/white/coral presentation identity.

Themes may use `extends` to inherit a complete design contract and override only
intentional differences. The resolved theme is always fully validated.
Themes may also define `paper`, `web`, and `video` variants. Compilation emits a
JSON, CSS, and Matplotlib artifact for every variant alongside the base tokens.

## Principles

- Define semantics before decoration: colors describe roles, not coordinates.
- Preserve one visual grammar across media while adapting density and motion.
- Prefer editable SVG/PDF figures; use raster output for preview or submission.
- Keep data transformations separate from visual styling and record both.
- Treat reference images as evidence for an original system, not assets to copy.

The Codex skill is in `skills/academic-design-workflow/` and contains the SOP
for choosing and reviewing each workflow mode.

## Native Visio co-authoring

The optional native Visio layer provides a versioned semantic scene, offline
validation and stale-safe edit planning, structural VSDX audit/diff, and a
Windows COM bridge that draws native shapes with glued connectors. It never
imports SVG/PDF/raster chart content. See the
[human-agent Visio SOP](docs/visio-human-agent-workflow.md) and the
[Hoffman example](examples/visio/README.md).
