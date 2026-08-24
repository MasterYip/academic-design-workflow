# After Effects human-agent co-authoring

This workflow treats After Effects as the authoritative editor and renderer, not
as a binary file format to reverse engineer. The version-controlled source is a
small semantic JSON manifest. `adw` validates it, emits reviewable ExtendScript
(`.jsx`), and compares stable-ID revisions. After Effects executes the JSX to
create a normal binary `.aep`; the human edits a copied revision and runs a
read-only inspector before the next agent pass.

## Why this boundary

- `.aep` is binary and has no supported external mutation API.
- `.aepx` is XML, but Adobe says it contains hexadecimal binary sections, exposes
  only selected strings, and should be an intermediate copy rather than the
  primary project. Limit direct AEPX automation to names, comments, markers, and
  footage/proxy paths, and validate every result in the target AE version.
- ExtendScript is Adobe's supported project DOM. It can create project items,
  compositions, footage, text, shape and null layers, properties, keyframes,
  expressions, effects, markers, and render-queue items.
- `afterfx -r script.jsx` runs a JSX in an existing AE instance. `aerender` renders
  a project/render queue; it is not a general project-authoring API.
- JSON/CSV/TSV/mgJSON footage and expressions are useful for replaceable data,
  captions, chart values, and narration timing. They do not replace the project
  structure.
- `.mogrt` is a packaged, deliberately constrained interface for exposed controls.
  It is useful downstream in Premiere, but not as the canonical full AE project.

The source bridge was initially implemented offline, then qualified natively in
Adobe After Effects 2020 `17.0.4x59` on Windows through an immutable agent,
proxy-human, and reconciled-agent AEP cycle plus a full-duration `aerender` pass.
Offline tests still do not replace target-workstation qualification: fonts,
effects, templates, codecs, permissions, and version conversion remain local.

## AE 2020 compatibility baseline

The core bridge was subsequently qualified against Adobe After Effects 2020
`17.0.4x59` on Windows. That runtime does not provide a global `JSON` object, so
generated builders and inspectors include an ES3-compatible deterministic JSON
serializer. Rectangle and ellipse construction uses the legacy match names
`ADBE Vector Rect Size` and `ADBE Vector Ellipse Size`. The inspector also records
a `value_error` instead of aborting when AE exposes a `PropertyValueType.NO_VALUE`
leaf such as a gradient or outer-glow placeholder.

Text layers support the optional manifest fields `text_font`, `text_size`,
`text_fill`, and `text_justification` (`left`, `center`, or `right`). These map to
the native `TextDocument` and remain ordinary editable AE text. Font availability
and substitution still require inspection in the target workstation.

## Semantic contract

Every project, scene, layer, marker, effect, and asset has a stable lowercase ID.
Generated AE items carry `ADW_ID=<id>;OWNER=<owner>` in their comment fields;
marker parameters carry the same identity. Never infer identity from display name
or layer index. Paper anchors record source file, semantic locator, and optional
revision. Assets can record a SHA-256 digest and stay outside Git.

Ownership is explicit:

| Owner | Meaning | Merge action |
|---|---|---|
| `agent` | Reproducible generated timing/style | Agent may regenerate after checking the diff |
| `human` | Editorial composition, bezier work, plugin tuning | Preserve; agent proposes rather than overwrites |
| `shared` | Claim text, scene boundary, citation | Any divergence is a review conflict |

Properties can override their layer's ownership. This allows the agent to own a
caption fade while the human owns its position. Canonicalization sorts records by
stable ID so panel ordering and JSON serialization do not produce false changes.

## Commands

```bash
adw ae validate examples/after-effects/paper-video.json
adw ae preflight examples/after-effects/paper-video.json \
  --project-output build/paper-video.agent-r001.aep \
  --report-output build/paper-video.agent-r001.ae-report.json \
  --json-output build/paper-video.agent-r001.preflight.json
adw ae normalize examples/after-effects/paper-video.json --output build/paper-video.normalized.json
adw ae generate examples/after-effects/paper-video.json \
  --output build/paper-video.build.jsx \
  --project-output build/paper-video.agent-r001.aep \
  --report-output build/paper-video.agent-r001.ae-report.json
adw ae inspect-script --output build/inspect-current.jsx \
  --report-output build/paper-video.human-r001.ae-report.json
adw ae diff examples/after-effects/paper-video.json \
  examples/after-effects/paper-video-human-edit.json \
  --output build/human-edit.semantic-diff.json
adw ae script-command --afterfx "C:/path/to/AfterFX.exe" \
  --script build/paper-video.build.jsx
adw ae render-command build/paper-video.agent-r001.aep \
  --aerender "C:/path/to/aerender.exe" \
  --comp "HoffMan paper video" \
  --render-settings "Draft Settings" \
  --output-module "Review AVI" \
  --output build/paper-video.agent-r001.preview.avi
```

`preflight` hashes every linked asset, checks any declared asset digest, and
refuses existing project/report outputs. For a derived revision, also pass
`--source-project` and `--source-sha256`; a stale source hash, same input/output
path, or existing output fails closed. `script-command` and `render-command`
emit JSON argv arrays for shell-free execution. They do not launch or terminate
Adobe processes. The render command never adds `-continueOnMissingFootage`.

Generated project files, footage, renders, caches, and reports belong in an
ignored build/artifact directory. Commit only manifests, scripts when useful for
audit, compact reports, and selected review stills.

## Required application-side verification

1. Record AE version/build, OS, expression engine, fonts, installed effects, and
   render/output-module template names. Copy the entire bundle; do not open the
   only production AEP.
2. Run `adw ae preflight`. Preserve its JSON and the source AEP hash. Do not
   proceed if an asset is missing/mismatched, the source hash is stale, or an
   output path already exists.
3. In **Preferences > Scripting & Expressions**, temporarily allow scripts to
   write files. Keep network access unused. Generated AE 2020 scripts probe a new
   report path before project mutation and emit an actionable permission error.
4. Inventory `AfterFX`/`aerender` processes. Start at most one task-owned AE
   instance, then run the builder using **File > Scripts > Run Script
   File**, or `AfterFX.exe -r <absolute-builder.jsx>` against that open instance.
5. Confirm all expected `ADW_ID` tags, scene durations, layer in/out points,
   markers, expressions, footage links, fonts, effects, color management, and the
   queued master composition. Save as `*.agent-rNNN.aep`; never overwrite input.
6. Render one first/middle/last frame per scene and a low-resolution full preview.
   Run the inspector JSX and archive its JSON alongside the project checksum.
7. Human editor uses **Increment and Save**, changes only the copied revision,
   and notes intentional plugin/font/substitution decisions in markers or the
   handoff manifest. Lock approved human-owned layers when practical.
8. Run the inspector again to a new report path. Prove the AEP checksum is
   unchanged before/after inspection. Review a semantic report plus contact sheet and video.
   Shared conflicts require an explicit choice. Preserve human-owned changes.
9. After acceptance, update the semantic manifest rather than patching the binary
   AEP. Generate a new `agent-rNNN+1` copy and repeat the smoke render.
10. Close only the task-owned instance through normal AE/script/window behavior.
    Re-inventory processes and preserve every pre-existing PID.

## Recovery and conflict policy

- Keep immutable manifest, AEP/AEPX copy, inspection JSON, render, and asset
  checksum sets for both sides of every handoff.
- Use AE's **Collect Files** for an exchange bundle and verify paths after moving.
  Relink only in a derived copy. Fail closed on missing footage or digest mismatch.
- Missing fonts/plugins, disabled expressions, unknown effects, version upgrades,
  output-template differences, or color-profile changes block automatic merge.
- Do not run two writers against one AEP. An OS lock file is advisory; the durable
  rule is one owner and one immutable revision per handoff.
- A successful `project.save()` followed by a report-write failure is a partial
  success, not permission to rerun against the same output. Hash the saved AEP,
  inspect it into a fresh report path after correcting the scripting preference,
  and continue with a new immutable revision name.
- AE can save a copy for the previous major release, but unsupported newer
  features may be ignored. The receiving version must perform the smoke render.
- Use AEPX only for inspection or narrow metadata/path changes. Convert the result
  to AEP in AE and compare an inspection report before accepting it.

## Viewing and agent inspection

The human reviews the native AE timeline, Graph Editor, render queue, and RAM
preview. The agent reviews the semantic manifest/diff, AE inspection JSON, asset
checksums, missing-dependency report, representative PNG contact sheet, captions
with timecodes, waveform/transcript references, and an encoded preview. These
views complement one another: JSON cannot prove pixels, and a render cannot prove
stable identity or ownership.

## AE 2020 troubleshooting

See [AE 2020 troubleshooting](after-effects-ae2020-troubleshooting.md) for the
validated symptoms and decision tree covering absent global `JSON`, legacy shape
match names, `PropertyValueType.NO_VALUE`, file-write preferences, output
overwrites/stale hashes, renderer template coercion, localized logs, and owned
process cleanup.

## Known limits

The first builder covers the structural core, basic text styling, and generic
match-name properties; advanced text layout, masks, cameras/lights, complex vector
paths, specialized effect parameters, interpolation/easing, render templates, and
color management require explicit schema additions and a tested AE fixture. The
inspector reports items, stable tags, timing, locks, source paths, property trees,
keyframes, expressions, and effects; very large projects still require profiling
and may need an explicit inspection allowlist.
