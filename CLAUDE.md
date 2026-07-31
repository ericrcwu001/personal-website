# Personal_Website

## Higgsfield: use the MCP server, not the CLI

Higgsfield is wired up as an **MCP server** (`.mcp.json` → `higgsfield`, enabled in
`.claude/settings.local.json`). Use its `mcp__higgsfield__*` tools for all
Higgsfield work — image/video/audio/3D generation, workflows, websites, games.

The `@higgsfield/cli` package has been **removed** from this repo. There is no
`higgsfield` on `PATH` and `npx higgsfield` will not resolve locally. Do not
install it or shell out to it; if a command seems to need the CLI, the MCP
server has an equivalent tool.

Entry points, all via MCP:

- Generation → `generate_image`, `generate_video`, `generate_audio`, `generate_3d`
  (unsure which model? `models_explore` with `action: 'recommend'` first)
- Edits on an existing asset → `upscale_image` / `upscale_video`,
  `outpaint_image`, `reframe`, `remove_background`, `motion_control`
- Multi-step video briefs (explainer, ad, UGC, podcast) →
  `get_workflow_instructions` with no argument to list the catalog, then again
  with the matching workflow name
- Websites → `get_website_creation_instructions` first, then `create_website`,
  `website_repo_access`, `deploy_website`
- Games → `get_game_creation_instructions` first, then `deploy_game`
- Local files as input → `media_upload_widget` (remote MCP tools cannot read
  Claude chat attachments)

The CLI-based `higgsfield-*` skills are no longer hooked into `.claude/skills/`.
Their source is still on disk at `.agents/skills/` (tracked by
`skills-lock.json`) if the CLI path ever needs restoring, but their instructions
are written against the CLI and should not be followed as-is.
