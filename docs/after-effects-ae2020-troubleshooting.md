# After Effects 2020 native troubleshooting

This guide generalizes issues reproduced while qualifying the source-first bridge
in Adobe After Effects 2020 `17.0.4x59` on Windows. Keep the exact failing JSX,
line/file diagnostic, AE build, AEP/input hashes, process inventory, render command,
and raw log whenever a new workstation diverges.

## Fast decision tree

```text
AE 2020 executable not found?
  -> Check HKLM\SOFTWARE\Adobe\After Effects\17.0 InstallPath and shortcuts.
  -> Do not substitute another major version for a 2020 gate.

Builder stops before making items?
  -> "JSON is undefined": regenerate with the ES3 serializer; do not call JSON.stringify.
  -> report/output permission: enable the scripting file-write preference and use fresh paths.
  -> existing/open project: start with one blank unsaved task-owned project.

Builder stops while making shapes?
  -> Null shape size: use ADBE Vector Rect Size / ADBE Vector Ellipse Size.

Builder/inspector stops while snapshotting properties?
  -> PropertyValueType.NO_VALUE: use the guarded inspector and retain value_error.

Inspection or reconciliation is unsafe?
  -> Verify the source AEP SHA-256 and fresh output path with adw ae preflight.
  -> Treat human-owned changes as preserve, shared changes as conflicts.

Render dimensions/fps differ from the comp?
  -> Read the actual output-module warning and probe the rendered media.
  -> Use a validated installed template; do not call a coerced review file a master.

Unexpected Adobe process remains?
  -> Compare with the pre-launch PID set.
  -> Close only the task-owned process normally; never terminate an unrelated PID.
```

## Reproduced AE 2020 constraints

| Symptom | Cause | Safe response |
|---|---|---|
| `"JSON" is undefined` | AE 2020 ExtendScript does not expose a global `JSON` object | Regenerate with the deterministic ES3 `adwStringify` helper. |
| `TypeError: null is not an object` on shape size | Generic `ADBE Vector Shape Size` does not resolve for native rectangles/ellipses | Use `ADBE Vector Rect Size` or `ADBE Vector Ellipse Size` and fail explicitly if absent. |
| Reading an outer-glow/gradient leaf throws `PropertyValueType.NO_VALUE` | Some property leaves have no readable value | Catch the read, set `value: null`, retain `value_error`, and continue inspection. |
| File write is denied | **Allow Scripts to Write Files and Access Network** is disabled, or the output is not writable | Enable the preference for the controlled run, use a new output, then restore the preference if desired. Generated builders preflight report writes before project mutation. |
| JSX failure gives little context | Legacy errors otherwise show only a message | Retain `error.line` and `error.fileName`; archive the exact generated JSX. |
| Inspector output already exists | Immutable evidence would be overwritten | Use a new revision/report path. Generated scripts now refuse overwrites. |

## Revision and asset safety

Run `adw ae preflight` before launching AE. It verifies linked files, declared
SHA-256 values, fresh project/report outputs, and optionally a source AEP hash.
Never infer identity from layer order or names; compare stable IDs and ownership.
Never edit r001 in place to obtain r002. If AE saves the AEP but a later evidence
write fails, preserve and hash that partial result, correct the evidence path or
permission, inspect it read-only, and continue under a new revision name.

Generated `script-command` and `render-command` output JSON argv arrays. Execute
them without a shell when automating. Inventory Adobe processes before and after;
`AfterFX.exe -r` may use an existing instance, so process ownership must be
established independently of the command return.

## Render-template and log constraints

`aerender` uses installed localized render/output-module templates. A template may
coerce requested scale, pixel aspect, codec, or fps—for example a 960x540 review
request can become 720x480/29.97 under a DV NTSC module. Always preserve the raw
log and probe the resulting media. Treat a coerced file as review-only. Select a
known installed master template or configure the render queue interactively for
production output.

Localized `aerender` output can be mojibake in a mismatched terminal code page.
Do not rely only on translated text parsing. Record argv, executable hash/version,
exit code, start/end, frame count, output hash, and structured `ffprobe` metadata.
Do not use `-continueOnMissingFootage` for an acceptance render.

## Developer checks

Node 18 may reject `node --check file.jsx` with `ERR_UNKNOWN_FILE_EXTENSION`.
Pipe the file through standard input instead:

```powershell
Get-Content -LiteralPath build.jsx -Raw | node --check
```

When running the repository without installation, set `PYTHONPATH` to `src` before
pytest. A missing optional `ruff` executable is a tooling availability note; do
not install it during a locked native qualification unless authorized.

## Known residuals

- Linked raster figures are editable as AE layers but their internal diagram
  elements are not native AE shapes.
- The generic inspector walks a deep property tree and can emit large JSON on
  complex projects. Profile before raising its recursion depth.
- A preflight write cannot make project/report saving transactional. If the final
  report write fails after `project.save`, recover the saved AEP as described above.
- Output existence checks cannot discover every numbered image-sequence member;
  use a fresh render directory for sequences.
- Fonts, plugins, effects, codecs, color profiles, and localized template names
  remain workstation-specific native gates.
