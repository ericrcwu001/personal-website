# Project Showcase Idea Bank

Status: Working idea bank only. No project showcase has been designed or assigned.

## Governing decisions

- Every project-to-format assignment is **TBD** until Eric reviews it.
- Do not infer that Eric created a project merely because its repository exists locally.
- Only add a project after its ownership and portfolio relevance are verified.
- CES appears last in any future project ordering until Eric's contribution is finished.
- Homepage previews should eventually be lightweight. Heavier interaction belongs on project detail pages.
- Signal Ledger is not part of the portfolio inventory. It was incorrectly inferred from a local README and must not be reintroduced unless Eric explicitly confirms it.

## Showcase patterns worth keeping

### Click-through walkthrough

A short, guided sequence of real product screens. The visitor clicks hotspots to advance through a task without needing an account or backend.

Useful tools: [Arcade](https://www.arcade.so/), [Supademo](https://supademo.com/)

### Self-hosted DOM replay

Record actual DOM changes and replay them inside the site. This can stay crisp at different screen sizes and can be scrubbed like a timeline.

Useful tool: [rrweb](https://www.rrweb.io/)

### Guided real demo

Load a safe, isolated version of the real application and guide the visitor through it with contextual steps. This is interactive, not a recording.

Useful tool: [Driver.js](https://driverjs.com/)

### Short cinematic motion poster

A 10-20 second polished loop that communicates the product's core behavior through camera movement, real interface footage, captions, and soundless motion.

Useful tool: [Screen Studio](https://www.screen.studio/)

### Programmatic product video

A video assembled from real screenshots, screen captures, data, and repeatable motion templates. This is useful when multiple aspect ratios or updated versions are needed.

Useful tool: [Remotion](https://www.remotion.dev/)

### Terminal replay

An authentic, controllable terminal session for developer tools, model workflows, infrastructure, or command-line interfaces.

Useful tool: [asciinema-player](https://docs.asciinema.org/manual/player/)

### Interactive architecture explorer

Let the visitor explore the components, data flow, agents, services, or model pipeline. Clicking a node can reveal the design decision and evidence behind it.

Useful tool: [React Flow](https://reactflow.dev/)

### Before-and-after comparison

A draggable comparison for outputs where the improvement is visible, such as image processing, reconstruction, model correction, interface redesign, or data cleaning.

Useful tool: [React Compare Slider](https://react-compare-slider.vercel.app/)

### Live isolated widget

Expose one small, safe part of a project instead of the entire application. The interaction should make sense without setup, credentials, or private data.

Useful tool: [Sandpack](https://sandpack.codesandbox.io/) for browser-runnable code experiences

### Timeline or run replay

Reconstruct how a system behaved over time: inputs arrive, a model or agent acts, tests run, failures surface, and the final output is produced. The visitor can pause and inspect any stage.

Potential implementation: a custom React timeline using sanitized real run artifacts

### Evidence or result explorer

Let the visitor change a benchmark slice, failure class, threshold, or case and see the associated result. This is especially valuable when evaluation is itself part of the project contribution.

Potential implementation: a small custom React visualization backed by a static, sanitized result bundle

## Assignment matrix

This deliberately contains no project names yet.

| Verified project | Homepage preview | Detail-page showcase | Evidence to feature | Status |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | Unassigned |

## Questions to answer before assigning formats

For each verified project:

1. What is the single behavior a visitor should remember?
2. Is the strongest proof visual behavior, technical architecture, measured results, or a real user workflow?
3. Can a safe demo run without credentials, private data, costly inference, or fragile infrastructure?
4. What real artifacts already exist: source, screenshots, recordings, evaluations, diagrams, or run logs?
5. What must be explained by Eric, and what can the visitor understand by interacting?

## Deferred work

- Verify the complete project inventory from GitHub and local repositories.
- Decide project order and hierarchy.
- Assign one primary showcase pattern to each project.
- Define the light homepage preview and the richer detail-page version separately.
- Plan capture sessions or demo rebuilds only after the assignments are approved.
