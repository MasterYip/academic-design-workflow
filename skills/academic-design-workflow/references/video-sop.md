# Paper Video SOP

Create a timed scientific argument, not a slideshow. Write one claim per scene:
problem, key insight, mechanism, evidence, and takeaway. Allocate time according
to conceptual difficulty.

Use theme dimensions, safe area, caption system, colors, typography, shape grammar,
and motion curves. Motion should show causality, progression, correspondence, or
focus. Prefer coordinated transforms and short crossfades to unrelated effects.

- Build reusable title, figure, comparison, annotation, result-grid, citation,
  and end-card compositions.
- Keep important text inside safe areas and understandable without audio.
- Animate vector or high-resolution assets; do not upscale small paper bitmaps.
- Use one dominant transition family per sequence.
- Keep captions stable and usually no more than two short lines.
- Include paper identity and destination URL in the end card.

Review muted playback, representative stills, pacing, caption collisions, safe
area, frame rate, resolution, encoded playback, and color shifts.

For After Effects co-authoring, keep a stable-ID semantic manifest outside the
binary AEP. Generate a new project revision through reviewable JSX, mark every
managed comp/layer/marker with its stable ID and owner, and let the human edit an
incremented copy. Before regeneration, compare the human inspection report and
manifest: preserve human-owned fields, require review for shared fields, and only
regenerate agent-owned fields. Never patch a production AEP in place. See
`docs/after-effects-coauthoring.md` for the complete handoff and recovery SOP.

