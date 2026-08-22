---
name: academic-design-workflow
description: Design or revise a coherent visual system and apply it to academic paper figures, scientific plots, project websites, or paper videos. Use when visual art direction, cross-media consistency, publication-ready figure design, or reusable academic design infrastructure matters.
---

# Academic Design Workflow

Make `theme.yaml` the single source of truth. Do not begin downstream styling
until the visual intent and semantic hierarchy are understood and the theme is
created or selected. Preserve the theme's semantic roles; adapt scale, density,
and motion to the medium without inventing a second visual language.

## Start

1. Inspect the scientific content, target audience, venue, existing assets, and final output constraints.
2. Decide whether to extend an existing theme or create a new theme. Record intended qualities and explicit anti-goals in `meta.intent` and `meta.avoid`.
3. Validate the theme and compile its cross-media tokens with the repository CLI.
4. Create low-cost structural candidates before polishing an important artifact.
5. Implement from tokens and reusable components; avoid isolated magic values.
6. Review the artifact at its actual delivery size and export reproducibly.

Read [references/overall-style-sop.md](references/overall-style-sop.md) whenever
creating or materially changing a theme. Then read only the reference matching
the requested output:

- Paper plots or schematics: [references/paper-figure-sop.md](references/paper-figure-sop.md)
- Project sites or UI: [references/website-sop.md](references/website-sop.md)
- Teasers or paper videos: [references/video-sop.md](references/video-sop.md)
- Reference image to reusable design system: [references/reference-analysis-sop.md](references/reference-analysis-sop.md)

Before delivery, use [references/quality-gates.md](references/quality-gates.md).

## Invariants

- Semantics precede aesthetics: content relationships determine layout and emphasis.
- Use semantic tokens such as `data_primary`, never names such as `blue_box`.
- Encode critical distinctions with shape, label, marker, or line style as well as hue.
- Keep data processing auditable and separate from presentation code.
- Prefer editable SVG/PDF for paper figures; generate raster previews secondarily.
- Do not imitate a reference artifact literally. Extract principles, disclose the reference, and produce an original grammar suited to the user's content.
- If a downstream need is absent from the schema, extend and document the theme first instead of bypassing it locally.
