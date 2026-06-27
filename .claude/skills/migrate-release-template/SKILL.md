---
name: migrate-release-template
description: >-
  Migrate Digital.ai Release Jython script tasks to Python 3 Script (Container)
  end-to-end: discover templates on a running Release instance via the Release MCP
  server, pull one, convert its Jython with the deterministic `jython2py3` CLI,
  surface the TODO/ERROR markers that need a human, then guide re-import (pulling the
  JSON over MCP is triage-only; the real re-import is via the Template-as-code YAML, and
  the agent always asks the user before any upload). Use when the user asks to migrate,
  convert, or port a Release template (or its Jython/ScriptTask automation) to Python 3,
  or mentions the Release MCP server in that context.
---

# Migrate a Release template (Jython → Python 3)

You orchestrate; a deterministic CLI does the actual code transform. **Never rewrite
Jython by hand** — the `jython2py3` tool is the single source of truth for the
mechanical conversion (it parses a concrete syntax tree, preserves comments, and is
fully tested). Your job is discovery, running the tool, interpreting its output, and
guiding re-import — pausing to ask the user before any upload (you never write to
Release yourself).

There are **two modes**, with different inputs: **triage** pulls the template as JSON
over MCP to size up the work (preview only, no re-import); **actual migration** runs on
the **Template-as-code YAML** the user exports from Release, because YAML is what
re-imports with full fidelity.

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

### Triage (MCP / JSON) — size up the work

1. **Discover.** Call the `list_templates` MCP tool. Show the user the `id`/`title`
   list and confirm which template to assess. If they already named one, look it up.
2. **Pull.** Call `get_template` for the chosen id. Save the returned object verbatim
   to a working file, e.g. `scratch/<safe-id>.json`. Do **not** edit it.
3. **Assess (deterministic).** Run the CLI on that file to produce a report:

   ```bash
   uv run jython2py3 migrate scratch/<safe-id>.json --report scratch/<safe-id>.report.html
   ```

   Add `-o scratch/<safe-id>.migrated.json` and/or `--diff` to inspect the output. This
   is **preview only** — the migrated JSON has no clean re-import path; it exists to tell
   you the scope and the issues.
4. **Review.** Read the report. Summarize per task:
   - tasks converted and silent Tier-1 transforms (already correct — no action),
   - every `# TODO[jython2py3]` marker (needs a human rewrite; cite the rule), and
   - every `# ERROR[jython2py3]` marker (cannot run as-is — must be resolved).
   Group by task title and report the scope to the user before going further. The rules
   and their guide references are in `docs/MIGRATION-RULES.md`.

### Actual migration (YAML) — produce the template to re-import

5. **Export the original.** Ask the user to export the template from Release as
   **Template-as-code → YAML** and point you at the file. You can't export YAML over
   MCP, and YAML is the format Release re-imports with full fidelity.
6. **Convert.** Run:

   ```bash
   uv run jython2py3 migrate template.yaml -o migrated.yaml --report report.html
   ```

7. **Resolve.** If the user wants, help edit the `script` bodies in `migrated.yaml` to
   clear TODO/ERROR markers. Edit only script text; never change structure, ids, or
   other task properties.
8. **Upload — ask, don't assume.** Once the markers are resolved, **stop and ask the
   user how to proceed**:
   - **(1) Guide me** — walk them through **Design → Templates → Import** of
     `migrated.yaml` in the Release UI, step by step; or
   - **(2) I'll upload it** — hand over `migrated.yaml` with the import instructions.
   Never write to Release yourself — re-import is always a manual UI action (see
   `docs/MCP-INTEGRATION.md` §4). The original is never modified.

## Guardrails

- Read-only against Release. Never write a template back via MCP, and never upload the
  migrated template yourself — re-import is always a manual UI action by the user.
- After resolving markers, **ask the user how they want to upload** (guided vs. manual)
  rather than assuming.
- The converter is deterministic and authoritative — do not re-implement or "improve"
  its rules by hand, and do not silently fix code it flagged with a marker; surface
  the marker to the user.
- Preserve everything except the task `type` and migrated `script`. If you edit the
  migrated file, keep the diff minimal.
- Treat `scratch/` (or the session scratchpad) as the place for pulled/migrated files;
  don't litter the repo.
- If `list_templates`/`get_template` shapes differ on this Release version, inspect the
  actual JSON and adapt — the CLI's template walk is structural and tolerant, but you
  must hand it the real template object.

## Multi-template runs

For "migrate everything" requests: list templates, confirm scope with the user, then
loop the **triage** steps (1–4) per template and present one consolidated report (counts
per template plus the full TODO/ERROR list) so the user can prioritize. Do the **actual
migration** (YAML export → convert → resolve → upload checkpoint) per template, one at a
time, so each gets its own reviewed artifact and explicit upload decision.
