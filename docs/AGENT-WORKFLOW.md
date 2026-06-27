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

## Two modes: triage vs. actual migration

Be explicit about which goal you're pursuing — they use different inputs:

- **Triage (assess the issues).** The agent pulls a template as JSON over MCP
  (`get_template`), runs `migrate template.json`, and reports the counts, diffs, and
  every `# TODO[jython2py3]` / `# ERROR[jython2py3]` marker. This answers *"what will
  this migration involve?"* across your instance. It is **preview only** — the migrated
  JSON has no clean re-import path, and Release is never touched.
- **Actual migration (produce the re-importable template).** Export the original
  template from Release as **Template-as-code → YAML**, run `migrate template.yaml`,
  resolve the markers, then re-import the YAML in the Release UI. YAML is the round-trip
  Release re-imports with full fidelity.

In short: **MCP/JSON is for understanding the issues; the YAML export/import is the real
migration.** The agent triages over MCP, then switches to the downloaded YAML for the
template it hands back — and it **never uploads to Release itself**; re-import is a human
action in the UI.

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

## Per-harness setup

Ready-made config + a skill-equivalent instructions file (each carrying the playbook
below) ship for four harnesses. For each: start the Release MCP server, edit the URL in
the config if it isn't the default `http://localhost:8000/mcp`, enable/approve the
server in the tool, then invoke as shown.

| Tool | MCP config | Instructions file | Invoke |
| ---- | ---------- | ----------------- | ------ |
| **Claude Code** | [`.mcp.json`](../.mcp.json.example) — copy `.mcp.json.example` → `.mcp.json` | [`.claude/skills/migrate-release-template/SKILL.md`](../.claude/skills/migrate-release-template/SKILL.md) | ask "migrate a Release template to Python 3", or `/migrate-release-template` |
| **GitHub Copilot** (VS Code) | [`.vscode/mcp.json`](../.vscode/mcp.json) (`"servers"`, `type: http`) | [`.github/prompts/migrate-release-template.prompt.md`](../.github/prompts/migrate-release-template.prompt.md) | `/migrate-release-template` in Copilot Chat (Agent mode) |
| **Cursor** | [`.cursor/mcp.json`](../.cursor/mcp.json) (`"mcpServers"`) | [`.cursor/rules/migrate-release-template.mdc`](../.cursor/rules/migrate-release-template.mdc) (`alwaysApply: false`) | enable the server, then ask in Agent chat — the rule auto-attaches by description |
| **OpenCode** | [`opencode.json`](../opencode.json) (`mcp.release`, `type: remote`) | [`.opencode/command/migrate-release-template.md`](../.opencode/command/migrate-release-template.md) | `/migrate-release-template "<template>"` |

For any **other** MCP-aware harness, do the same three things by hand:

1. Register the Release MCP server in that tool's MCP configuration.
2. Give the agent the playbook below (paste it, or save it where your harness loads
   project instructions from).
3. Let it drive `uv run jython2py3 migrate <file>.json …` for the deterministic step.

If a harness cannot speak MCP, fall back to the bundled
[`jython2py3 mcp`](MCP-INTEGRATION.md) commands, which carry their own client.

---

## The playbook

### Triage (MCP / JSON) — understand the work

1. **Discover** — call `list_templates`; confirm which template (`id`/`title`) to assess.
2. **Pull** — call `get_template` for that id; save the object verbatim to
   `scratch/<id>.json`. Don't edit it.
3. **Assess** — `jython2py3 migrate scratch/<id>.json --report scratch/<id>.report.html`
   (add `-o … --diff` to inspect the output/diff). **Preview only** — the migrated JSON
   has no clean re-import path; this exists to size up the work.
4. **Review** — read the report; group by task and surface every TODO (needs a human
   rewrite) and ERROR (cannot run as-is), citing [MIGRATION-RULES.md](MIGRATION-RULES.md).
   Report the scope to the user before going further.

### Actual migration (YAML) — produce the template you re-import

5. **Export the original** — ask the user to export the template from Release as
   **Template-as-code → YAML** and point you at the file. (The agent can't export YAML
   over MCP, and YAML is the format Release re-imports with full fidelity.)
6. **Convert** — `jython2py3 migrate template.yaml -o migrated.yaml --report report.html`.
7. **Resolve** — help edit only the `script` bodies in `migrated.yaml` to clear the
   TODO/ERROR markers; keep structure, ids, and other properties untouched.
8. **Upload — ask, don't assume.** Once the markers are resolved, **stop and ask the
   user how to proceed**:
   - **(1) Guide me** — walk them through **Design → Templates → Import** of
     `migrated.yaml` in the Release UI, step by step; or
   - **(2) I'll upload it** — hand over `migrated.yaml` with the import instructions and
     let them do it.
   The agent **never writes to Release itself** — re-import is always a human action in
   the UI (see [MCP-INTEGRATION.md §4](MCP-INTEGRATION.md#4-getting-the-migrated-template-back-into-release)).
   The original template is never modified.

---

## Guardrails

- **Read-only against Release.** Never write a template back through MCP, and never
  upload the migrated template yourself — re-import is always a manual UI action.
- **Ask before uploading.** After the markers are resolved, ask the user how they want
  to upload (guided vs. manual); don't assume.
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

## Verify & troubleshoot

- **Is the CLI runnable?** `uv run jython2py3 --version` (with uv it lives in `.venv`,
  not on PATH — prefix commands with `uv run`).
- **Is the MCP server connected?** Claude Code: the `/mcp` command. Copilot: *MCP: List
  Servers* (Command Palette). Cursor: **Settings → MCP**. OpenCode: it loads on start.
  You should see `release` exposing `list_templates` / `get_template`.
- **Skill / instructions not picked up?** Confirm the tool is rooted in this repo and
  the file is at the path in the table above (e.g. Claude needs
  `.claude/skills/migrate-release-template/SKILL.md`).
- **`error: The 'mcp' package is required…`** only applies to the built-in
  [`jython2py3 mcp`](MCP-INTEGRATION.md) fallback — not this workflow, where the harness
  (not the CLI) talks to MCP.
- **Server unreachable?** Confirm it runs in `streamable-http` mode on the expected port
  and the URL in your config matches; `curl -i http://localhost:8000/mcp` should return
  some HTTP response. More: [MCP-INTEGRATION.md §5](MCP-INTEGRATION.md#5-troubleshooting).

---

## Reference links

- This project's MCP command guide — [MCP-INTEGRATION.md](MCP-INTEGRATION.md)
- The migration rules the converter applies — [MIGRATION-RULES.md](MIGRATION-RULES.md)
- Release MCP server overview — <https://docs.digital.ai/release/docs/how-to/release-mcp-server>
- Model Context Protocol — <https://modelcontextprotocol.io>

[mcp]: https://modelcontextprotocol.io
[mcp-install]: https://docs.digital.ai/release/docs/how-to/release-mcp-server-installation
