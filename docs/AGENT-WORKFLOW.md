# Agent workflow — migrate Release templates with an AI harness

This guide describes how to drive the migrator from an **agent harness** (Claude Code,
OpenCode, Copilot, …) instead of by hand. The design principle is a clean split:

> **The agent owns orchestration; the CLI owns the transform.**

The harness already speaks the [Model Context Protocol][mcp], so it connects to the
Release MCP server, picks templates, and plans the migration *itself*. The
deterministic `jython2py3` CLI does only the one thing it is uniquely good at —
converting Jython to Python 3 — and stays completely free of network and transport
concerns. This keeps the converter sharp and avoids re-implementing MCP plumbing,
JSON↔YAML reconciliation, and version-specific result wrangling inside the tool.

```
 ┌─────────────────────────────┐        list_templates / get_template
 │  Agent harness (Claude, …)  │  ───────────────────────────────────────▶  Release MCP server
 │  - speaks MCP natively      │  ◀───────────────────────────────────────  (read-only)
 │  - plans the migration      │             template JSON
 └──────────────┬──────────────┘
                │ saves template.json, then runs:
                ▼
   jython2py3 migrate template.json -o migrated.json --report report.html
                │   (deterministic, offline, no network — the same rules as
                │    the .py and .yaml paths)
                ▼
   migrated.json + report  →  agent surfaces TODO/ERROR markers and a re-import plan
```

Compared with the built-in [`jython2py3 mcp …`](MCP-INTEGRATION.md) commands (which
talk to the server through the tool's own bundled client), this workflow hands the MCP
side to the harness. The CLI's job shrinks to a single transport-free primitive:
**migrate a template object that is already on disk.**

---

## The deterministic primitive

The converter accepts a Release **template object saved as JSON** as a first-class
input, alongside standalone scripts and Template-as-code YAML:

```bash
jython2py3 migrate template.json -o migrated.json     # convert a pulled template
jython2py3 migrate template.json --diff               # preview, write nothing
jython2py3 migrate template.json -o out.json --report report.html   # + a report
```

It finds **every** `xlrelease.ScriptTask` at any depth (phases, parallel groups,
nested sub-tasks), migrates each script body with the exact same rules as the `.py` and
`.yaml` paths, swaps each converted task's `type` to `containerPython.PythonTask`, and
leaves everything else byte-for-byte intact. `# TODO[jython2py3]` / `# ERROR[jython2py3]`
markers land as comments inside the migrated scripts, and the `--report` counts and
lists them. This is pure and offline — no MCP extra, no server required — so an agent
can call it in a tight loop.

> A `.json` input is treated as a template object only when you name the file (or match
> it with a glob). Directory scans still pick up `*.py` / `*.yaml` / `*.yml` only, so
> pointing the tool at a folder never slurps unrelated JSON.

---

## Prerequisites

1. **A running Release MCP server** in `streamable-http` mode, reachable at e.g.
   `http://localhost:8000/mcp`, pointed at your Release instance. See the official
   [installation guide][mcp-install]. Release credentials live on the **server**, not
   in the harness.
2. **The migrator installed and runnable.** With uv, run it as `uv run jython2py3 …`
   from the repo root (the command lives in `.venv`, not on PATH). No `mcp` extra is
   needed for this workflow — the harness, not the CLI, talks to the server.
3. **The harness configured to reach the MCP server** (see per-harness notes below).

---

## Claude Code

Two files make this turnkey:

- **`.mcp.json`** registers the Release MCP server so Claude calls `list_templates` /
  `get_template` as native tools. Copy the bundled template and adjust the URL:

  ```bash
  cp .mcp.json.example .mcp.json
  # optionally: export RELEASE_MCP_URL=http://your-host:8000/mcp
  ```

  Reload Claude Code so it picks up the server (you'll be asked to approve it).

- **The `migrate-release-template` skill** (`.claude/skills/migrate-release-template/`)
  encodes the playbook below. Ask Claude to "migrate a Release template to Python 3"
  (or name a template) and it runs the skill.

---

## Other harnesses (OpenCode, Copilot, …)

Nothing about the workflow is Claude-specific. Ready-made config + a skill-equivalent
instructions file (each carrying the playbook below) ships for three common harnesses:

| Tool | MCP config | Instructions file | Invoke |
| ---- | ---------- | ----------------- | ------ |
| **GitHub Copilot** (VS Code) | [`.vscode/mcp.json`](../.vscode/mcp.json) (`"servers"`, `type: http`) | [`.github/prompts/migrate-release-template.prompt.md`](../.github/prompts/migrate-release-template.prompt.md) | `/migrate-release-template` in Copilot Chat (Agent mode) |
| **Cursor** | [`.cursor/mcp.json`](../.cursor/mcp.json) (`"mcpServers"`) | [`.cursor/rules/migrate-release-template.mdc`](../.cursor/rules/migrate-release-template.mdc) (`alwaysApply: false`) | enable the server, then ask in Agent chat — the rule auto-attaches by description |
| **OpenCode** | [`opencode.json`](../opencode.json) (`mcp.release`, `type: remote`) | [`.opencode/command/migrate-release-template.md`](../.opencode/command/migrate-release-template.md) | `/migrate-release-template "<template>"` |

For each: start the Release MCP server, edit the URL in the config if it isn't the
default `http://localhost:8000/mcp`, enable/approve the server in the tool, then invoke
as above. For any **other** MCP-aware harness, do the same three things by hand:

1. Register the Release MCP server in that tool's MCP configuration.
2. Give the agent the playbook below (paste it, or save it where your harness loads
   project instructions from).
3. Let it drive `uv run jython2py3 migrate <file>.json …` for the deterministic step.

If a harness cannot speak MCP, fall back to the bundled
[`jython2py3 mcp`](MCP-INTEGRATION.md) commands, which carry their own client.

---

## The playbook

1. **Discover** — call `list_templates`; confirm which template (`id`/`title`) to migrate.
2. **Pull** — call `get_template` for that id; save the object verbatim to a working
   file (`scratch/<id>.json`). Don't edit it.
3. **Convert** — `jython2py3 migrate scratch/<id>.json -o scratch/<id>.migrated.json
   --report scratch/<id>.report.html` (use `--diff` for a no-write preview).
4. **Review** — read the report; group by task and surface every TODO (needs a human
   rewrite) and ERROR (cannot run as-is), citing [MIGRATION-RULES.md](MIGRATION-RULES.md).
5. **Resolve (optional)** — help edit only the `script` bodies in the migrated JSON to
   clear markers; keep structure, ids, and other properties untouched.
6. **Re-import** — the MCP path is read-only, so recreate the template in Release via
   the Template-as-code YAML import described in [MCP-INTEGRATION.md §4](MCP-INTEGRATION.md#4-getting-the-migrated-template-back-into-release).
   The original template is never modified.

---

## Guardrails

- **Read-only against Release.** Never write a template back through MCP.
- **The converter is authoritative.** Don't hand-rewrite Jython or "fix" code the tool
  flagged with a marker — surface the marker instead.
- **Minimal diffs.** Only the task `type` and migrated `script` should change.

---

## Distilling skills

Treat the first runs as an experiment: see where the harness needs help (tool
discovery, nested-task navigation, marker triage, re-import). Fold whatever works into
the skill / playbook so the next run is one prompt. The Claude skill in
`.claude/skills/migrate-release-template/` is exactly this — a frozen, repeatable
version of the playbook above.

---

## Reference links

- This project's MCP command guide — [MCP-INTEGRATION.md](MCP-INTEGRATION.md)
- The migration rules the converter applies — [MIGRATION-RULES.md](MIGRATION-RULES.md)
- Release MCP server overview — <https://docs.digital.ai/release/docs/how-to/release-mcp-server>
- Model Context Protocol — <https://modelcontextprotocol.io>

[mcp]: https://modelcontextprotocol.io
[mcp-install]: https://docs.digital.ai/release/docs/how-to/release-mcp-server-installation
