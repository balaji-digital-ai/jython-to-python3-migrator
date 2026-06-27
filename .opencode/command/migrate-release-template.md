---
description: Migrate a Release template's Jython tasks to Python 3 (Container)
---

# Migrate a Release template (Jython → Python 3)

Migrate the Release template identified by: $ARGUMENTS
(if empty, list templates first and ask which one).

You orchestrate; the `jython2py3` CLI does the actual code transform. **Never rewrite
Jython by hand** — the CLI is the authoritative, deterministic converter.

Requires the `release` MCP server (`opencode.json`) connected, and the migrator
runnable as `uv run jython2py3 …` from the repo root (it lives in `.venv`, not on PATH).

## Workflow

1. **Discover** — call the `list_templates` MCP tool; show the `id`/`title` list and
   confirm which template to migrate (or use the one given in $ARGUMENTS).
2. **Pull** — call `get_template` for that id; save the returned object verbatim to a
   working file (`scratch/<id>.json`). Do not edit it.
3. **Convert** — run:
   `uv run jython2py3 migrate scratch/<id>.json -o scratch/<id>.migrated.json --report scratch/<id>.report.html`
   (use `--diff` for a no-write preview).
4. **Review** — read the report; group by task and surface every `# TODO[jython2py3]`
   (needs a human rewrite) and `# ERROR[jython2py3]` (cannot run as-is), citing
   `docs/MIGRATION-RULES.md`.
5. **Resolve (optional)** — edit only the `script` bodies in the migrated JSON to clear
   markers; keep structure, ids, and other properties untouched.
6. **Re-import** — the MCP path is read-only, so recreate the template in Release via
   the Template-as-code YAML import in `docs/MCP-INTEGRATION.md` §4. The original is
   never modified.

## Guardrails

- Read-only against Release — never write a template back via MCP.
- The CLI is authoritative — don't hand-rewrite Jython or "fix" flagged code; surface
  the marker instead.
- Only the task `type` and migrated `script` should change.

Full design and per-harness notes: `docs/AGENT-WORKFLOW.md`.
