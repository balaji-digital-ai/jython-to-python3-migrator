---
name: migrate-release-template
description: >-
  Migrate Digital.ai Release Jython script tasks to Python 3 Script (Container)
  end-to-end: discover templates on a running Release instance via the Release MCP
  server, pull one, convert its Jython with the deterministic `jython2py3` CLI,
  surface the TODO/ERROR markers that need a human, and produce a re-import plan.
  Use when the user asks to migrate, convert, or port a Release template (or its
  Jython/ScriptTask automation) to Python 3, or mentions the Release MCP server in
  that context.
---

# Migrate a Release template (Jython → Python 3)

You orchestrate; a deterministic CLI does the actual code transform. **Never rewrite
Jython by hand** — the `jython2py3` tool is the single source of truth for the
mechanical conversion (it parses a concrete syntax tree, preserves comments, and is
fully tested). Your job is discovery, running the tool, interpreting its output, and
planning the re-import.

## Division of labor

- **You (the agent):** speak MCP, pick the template, save it, run the CLI, read the
  report, explain TODO/ERROR markers, and lay out the re-import steps.
- **The `jython2py3` CLI:** the deterministic, offline transform. It takes a Release
  template JSON (or a `.py` / `.yaml`) and converts every `xlrelease.ScriptTask` to a
  `containerPython.PythonTask`, migrating the script body and leaving everything else
  untouched.
- **The Release MCP server:** read-only access to the Release instance. It is never
  written to from here.

## Prerequisites (check, don't assume)

1. **MCP server reachable.** The `release` MCP server (from `.mcp.json`) must be
   connected. If its tools (`list_templates`, `get_template`) aren't available, tell
   the user to copy `.mcp.json.example` → `.mcp.json`, start the Release MCP server in
   `streamable-http` mode, set `RELEASE_MCP_URL` if it isn't the default
   `http://localhost:8000/mcp`, and reload. Do not fall back to guessing.
2. **CLI runnable.** Use `uv run jython2py3 …` from the repo root (the command is
   installed into `.venv`, not on PATH). Confirm with `uv run jython2py3 --version`.

## Workflow

1. **Discover.** Call the `list_templates` MCP tool. Show the user the `id`/`title`
   list and confirm which template to migrate. If they already named one, look it up.
2. **Pull.** Call `get_template` for the chosen id. Save the returned object verbatim
   to a working file, e.g. `scratch/<safe-id>.json`. Do **not** edit it.
3. **Convert (deterministic).** Run the CLI on that file and write a report:

   ```bash
   uv run jython2py3 migrate scratch/<safe-id>.json -o scratch/<safe-id>.migrated.json --report scratch/<safe-id>.report.html
   ```

   Use `--diff` first if the user wants a preview without writing anything.
4. **Review.** Read the report (and the migrated JSON). Summarize per task:
   - tasks converted and silent Tier-1 transforms (already correct — no action),
   - every `# TODO[jython2py3]` marker (needs a human rewrite; cite the rule), and
   - every `# ERROR[jython2py3]` marker (cannot run as-is — must be resolved).
   Group by task title so the user knows exactly where to look. The rules and their
   guide references are in `docs/MIGRATION-RULES.md`.
5. **Resolve (optional).** If the user wants, help edit the `script` bodies in the
   migrated JSON to clear TODO/ERROR markers. Edit only script text; never change
   structure, ids, or other task properties.
6. **Re-import plan.** The MCP path is read-only, so explain how to get the result
   back into Release. The fidelity-preserving route is the Template-as-code YAML
   import (see `docs/MCP-INTEGRATION.md` §4): export the template as YAML from the
   Release UI, run `uv run jython2py3 migrate template.yaml -o migrated.yaml`, then
   **Design → Templates → Import** the migrated YAML as a new template. The original
   is never modified.

## Guardrails

- Read-only against Release. Never write a template back via MCP.
- The converter is deterministic and authoritative — do not re-implement or "improve"
  its rules by hand, and do not silently fix code it flagged with a marker; surface
  the marker to the user.
- Preserve everything except the task `type` and migrated `script`. If you edit the
  migrated JSON, keep the diff minimal.
- Treat `scratch/` (or the session scratchpad) as the place for pulled/migrated files;
  don't litter the repo.
- If `list_templates`/`get_template` shapes differ on this Release version, inspect the
  actual JSON and adapt — the CLI's template walk is structural and tolerant, but you
  must hand it the real template object.

## Multi-template runs

For "migrate everything" requests: list templates, confirm scope with the user, then
loop steps 2–4 per template, and present one consolidated report (counts per template
plus the full TODO/ERROR list). Convert with a single CLI invocation per file so each
template gets its own report artifact.
