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
python examples/paper-figures/styleboard.py
```

The compiler creates `theme.json`, `theme.css`, and `matplotlib.json`. The
example creates SVG, PDF, and PNG previews using the same validated theme.

## Principles

- Define semantics before decoration: colors describe roles, not coordinates.
- Preserve one visual grammar across media while adapting density and motion.
- Prefer editable SVG/PDF figures; use raster output for preview or submission.
- Keep data transformations separate from visual styling and record both.
- Treat reference images as evidence for an original system, not assets to copy.

The Codex skill is in `skills/academic-design-workflow/` and contains the SOP
for choosing and reviewing each workflow mode.

