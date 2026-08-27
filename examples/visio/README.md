# HoffMan native Visio example

`hoffman_policy.scene.json` demonstrates the generic scene contract with Hoffman
colors, state/action semantics, a focal decoder, and a sampling chain.
`hoffman_policy.resize.edit.json` is bound to that exact revision and demonstrates
a safe move, resize, text, and style edit of `condition_encoder`.

See [the full co-authoring SOP](../../docs/visio-human-agent-workflow.md) for
generation, edit, audit, diff, safety, and recovery commands.

`hoffman_policy.axmath.json` is a small optional equation-overlay example. Run
it only after generating the native VSDX and only on a Windows host with AxMath
registered. It preserves the native carriers and adds audited AxMath children;
it is not required for ordinary native-Visio diagrams.
