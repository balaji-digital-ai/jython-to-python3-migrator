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

**Triage (MCP/JSON) — understand the work:**

1. **Discover** — call the `list_templates` MCP tool; show the `id`/`title` list and
   confirm which template (or use the one given in $ARGUMENTS).
2. **Pull** — call `get_template` for that id; save the object verbatim to
   `scratch/<id>.json`. Do not edit it.
3. **Assess** — run
   `uv run jython2py3 migrate scratch/<id>.json --report scratch/<id>.report.html`
   (add `-o … --diff` to inspect output). Preview only — the JSON has no clean re-import
   path; this just sizes up the work.
4. **Review** — read the report; group by task and surface every `# TODO[jython2py3]`
   (needs a human rewrite) and `# ERROR[jython2py3]` (cannot run as-is), citing
   `docs/MIGRATION-RULES.md`. Report the scope before continuing.

**Actual migration (YAML) — produce the re-importable template:**

5. **Export the original** — ask the user to export the template from Release as
   **Template-as-code → YAML** and point you at the file (YAML can't be pulled over MCP).
6. **Convert** — `uv run jython2py3 migrate template.yaml -o migrated.yaml --report report.html`.
7. **Resolve** — edit only the `script` bodies in `migrated.yaml` to clear markers; keep
   structure, ids, and other properties untouched.
8. **Upload — ask, don't assume** — when markers are cleared, stop and ask how to upload:
   (1) walk the user through **Design → Templates → Import** of `migrated.yaml` in the
   Release UI, or (2) hand over `migrated.yaml` and let them import it. See
   `docs/MCP-INTEGRATION.md` §4.

## Guardrails

- Read-only against Release — never write a template back via MCP, and never upload the
  migrated template yourself; re-import is always a manual UI action by the user.
- After resolving markers, **ask the user how they want to upload** (guided vs. manual).
- The CLI is authoritative — don't hand-rewrite Jython or "fix" flagged code; surface
  the marker instead.
- Only the task `type` and migrated `script` should change.

Full design and per-harness notes: `docs/AGENT-WORKFLOW.md`.
