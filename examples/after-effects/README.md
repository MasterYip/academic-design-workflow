# Native AE co-authoring example

`paper-video.json` is the agent manifest and `paper-video-human-edit.json` is a
controlled editor revision. They demonstrate stable IDs, nested ownership, paper
anchors, native text/shape properties, and a shared-text conflict.

Use a fresh ignored `build/` directory and immutable output names:

```bash
adw ae preflight examples/after-effects/paper-video.json \
  --project-output build/paper-video.agent-r001.aep \
  --report-output build/paper-video.agent-r001.report.json \
  --json-output build/paper-video.agent-r001.preflight.json
adw ae generate examples/after-effects/paper-video.json \
  --output build/paper-video.agent-r001.build.jsx \
  --project-output build/paper-video.agent-r001.aep \
  --report-output build/paper-video.agent-r001.report.json
```

After AE creates r001, hash it. Copy it to a new human/proxy-human revision,
inspect that copy into a new JSON path, encode accepted human-owned changes in the
next manifest, and stop on shared conflicts. Generate r003 rather than overwriting
r001 or r002. Use `adw ae script-command` and `adw ae render-command` to obtain
shell-free argv lists for an orchestration layer; these commands never launch or
terminate Adobe processes.

The reusable library contains no HoffMan scene layout. Project-specific content,
footage, animation, and claim text belong in a manifest/example/demo layer.
