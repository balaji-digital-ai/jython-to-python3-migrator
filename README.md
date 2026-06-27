# jython2py3 — Jython → Python 3 Script migrator

A deterministic, **rule-based source-to-source migrator** that converts Digital.ai
Release **Jython Script** automation (`xlrelease.ScriptTask`) into **Python 3 Script
(Container)** scripts (`containerPython.PythonTask`).

It automates the mechanical parts of the bundled
[Jython → Python 3 migration guide](docs/JYTHON-TO-PYTHON3-MIGRATION.md) and
**flags** the parts that need a human decision — it never silently emits code that might
be wrong.

* Pure Python, **runs identically on Windows and Linux**.
* Preserves comments and formatting (it works on a syntax tree, not text).
* One file in, one file out — or whole directories at once.

---

## Install & run (clone-and-run)

This is a [uv](https://docs.astral.sh/uv/) project. With uv installed:

```bash
git clone <repo-url> jython-to-python3-migrator
cd jython-to-python3-migrator

# create the environment from the lockfile, then run the tool inside it
uv sync
uv run jython2py3 migrate path/to/script.py -o migrated/script.py
```

`uv sync` creates `.venv/` and installs the pinned dependencies; `uv run` executes
inside it, so there is nothing to activate.

Prefer pip? It is a standard PEP 621 package:

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install .
jython2py3 migrate path/to/script.py -o migrated/script.py
```

---

## Usage

```text
usage: jython2py3 migrate [-h] [-o PATH] [--in-place] [--backup] [--dry-run]
                          [--diff] [--report FILE] [--header]
                          INPUT [INPUT ...]

positional arguments:
  INPUT              files (.py script, .yaml/.yml or .json Release template),
                     directories (searched for *.py / *.yaml / *.yml), or glob patterns

options:
  -h, --help         show this help message and exit
  -o, --output PATH  output file (single input) or directory (mirrors input layout)
  --in-place         overwrite the input files in place
  --backup           with --in-place, keep the original as <file>.bak
  --dry-run          do not write anything; only report what would change
  --diff             print a unified diff for each changed file
  --report FILE      write a migration report to FILE (HTML if it ends in .html/.htm, else JSON)
  --header           prepend a '# Migrated from Jython by jython2py3' header to each script
```

Inputs may be files, directories (searched recursively for `*.py`, `*.yaml` and
`*.yml`), or glob patterns (expanded in-process, so they work on Windows too).

### Examples

```bash
jython2py3 migrate script.py                        # preview migrated source on stdout
jython2py3 migrate script.py -o out.py              # write one file
jython2py3 migrate scripts/ -o migrated/            # mirror a directory tree
jython2py3 migrate scripts/ --in-place --backup     # overwrite, keeping *.bak originals
jython2py3 migrate "scripts/*.py" --dry-run --diff  # preview changes, write nothing
jython2py3 migrate scripts/ -o migrated/ --report report.json   # + JSON report
jython2py3 migrate scripts/ -o migrated/ --report report.html   # + styled HTML report
jython2py3 migrate scripts/ -o migrated/ --header   # stamp each output file
jython2py3 migrate template.yaml -o migrated.yaml   # a Template-as-code export
jython2py3 migrate template.json -o migrated.json   # a Release template object (e.g. pulled over MCP)
```

---

## Template-as-code YAML

Release's **YAML: Template as code** view exports a whole template, embedding each
Jython task's script as a literal block scalar. Point the migrator at that `.yaml`
(or `.yml`) file and it converts the template **in place**: every
`xlrelease.ScriptTask` becomes a `containerPython.PythonTask` (both share the same
`script` property) and its script body is migrated with the exact same rules used for
standalone `.py` files. Everything else — key order, comments, the `|-` block style,
anchors and secret `!value` tags — is preserved, so the only diff is the task type
and the migrated script.

```bash
jython2py3 migrate template.yaml -o template.python3.yaml
jython2py3 migrate template.yaml --diff      # preview the change first
```

```diff
     - name: New task
-      type: xlrelease.ScriptTask
+      type: containerPython.PythonTask
       script: |-
-        print "Release:", release.title
-        releaseVariables["migratedBy"] = "jython2py3"
+        release = getCurrentRelease()
+        print("Release:", release.title)
+        setReleaseVariable("migratedBy", "jython2py3")
```

The summary reports how many tasks were converted, plus the usual TODO/ERROR counts
(the markers land as comments inside the migrated `script:` block). Re-import the
file via the same Template-as-code view. A worked example is in
[`examples/templates/`](examples/templates/). Only tasks whose type is exactly
`xlrelease.ScriptTask` are converted; every other task is left untouched.

---

## Pull templates straight from Release (MCP)

Instead of exporting a YAML file by hand, the migrator can pull a template **directly
from a running Digital.ai Release instance** via the official
[Release MCP server](https://hub.docker.com/r/xebialabs/dai-release-mcp), then preview or
migrate its Jython tasks. It is **read-only** — your originals in Release are never touched.

```bash
uv sync --extra mcp                              # one-time: install the MCP client SDK
export RELEASE_MCP_URL=http://localhost:8000/mcp # point at your MCP server

jython2py3 mcp list                              # list templates
jython2py3 mcp migrate <TEMPLATE_ID> --diff      # preview what would change
```

Full setup, auth, and re-import notes: **[`docs/MCP-INTEGRATION.md`](docs/MCP-INTEGRATION.md)**.

---

## For agents (Claude Code, OpenCode, Copilot)

You can let an **AI agent harness** run the whole migration for you. The split is
clean: the **agent owns orchestration** (it speaks MCP, lists templates, picks one,
plans the work) and the **CLI owns the transform** (deterministic Jython → Python 3).
The agent never re-implements the conversion, and the converter never grows network
code.

The harness connects to the Release MCP server itself, pulls a template as JSON, and
hands that file to the transport-free converter:

```bash
# the agent pulls the template via MCP, saves it, then runs:
jython2py3 migrate template.json -o migrated.json --report report.html
```

`migrate` accepts a Release **template object saved as JSON** as a first-class input —
the same in-place conversion as the YAML export, with no MCP extra or server needed —
so an agent can call it in a loop, read the report, surface the
`# TODO[jython2py3]` / `# ERROR[jython2py3]` markers, and lay out the re-import.

For **Claude Code**, two files make it turnkey:

- copy [`.mcp.json.example`](.mcp.json.example) → `.mcp.json` to register the Release
  MCP server, and
- the [`migrate-release-template`](.claude/skills/migrate-release-template/SKILL.md)
  skill encodes the playbook — just ask Claude to "migrate a Release template to
  Python 3".

### Other harnesses

The same workflow ships ready-made for other MCP-aware tools — each pairs an MCP server
config with a skill-equivalent instructions file carrying the full playbook:

| Tool | MCP config | Instructions | Invoke |
| ---- | ---------- | ------------ | ------ |
| **GitHub Copilot** (VS Code) | [`.vscode/mcp.json`](.vscode/mcp.json) | [`.github/prompts/migrate-release-template.prompt.md`](.github/prompts/migrate-release-template.prompt.md) | `/migrate-release-template` in Copilot Chat (Agent mode) |
| **Cursor** | [`.cursor/mcp.json`](.cursor/mcp.json) | [`.cursor/rules/migrate-release-template.mdc`](.cursor/rules/migrate-release-template.mdc) | enable the server, then ask in Agent chat (rule auto-attaches) |
| **OpenCode** | [`opencode.json`](opencode.json) | [`.opencode/command/migrate-release-template.md`](.opencode/command/migrate-release-template.md) | `/migrate-release-template "<template>"` |

Start the Release MCP server first, edit the URL in the config if it isn't the default
`http://localhost:8000/mcp`, and enable/approve the server in your tool.

How it works, the per-harness setup, and the full playbook and guardrails:
**[`docs/AGENT-WORKFLOW.md`](docs/AGENT-WORKFLOW.md)**.

---

## What it does

Safe rewrites are applied automatically; anything that can't be migrated safely is flagged for review — every rule, with examples, is in **[`docs/MIGRATION-RULES.md`](docs/MIGRATION-RULES.md)**.

---

## Examples

`examples/jython/<name>.py` is the input; `examples/python3/<name>.py` is the
committed migrated output (a golden file, regenerated with
`jython2py3 migrate examples/jython/ -o examples/python3/`). Each one targets a
different slice of the rule set — from scripts that **run as-is** to ones that mix
in `# TODO` / `# ERROR` markers to resolve.

See **[`docs/examples.md`](docs/examples.md)** for a detailed walk-through of every
example — the Python scripts and the Template-as-code YAML — with the exact rules
each one exercises and annotated before/after diffs.

---

## How it works

```
Jython source (Python 2 syntax)
        │
        ▼  fissix parses Python 2 & 3 → concrete syntax tree (keeps comments)
        │
        ▼  RefactoringTool applies fixers:
        │     • stock fissix fixers  → Python 2 → 3 syntax
        │     • jython2py3 fixers    → rewrite (Tier 1) or annotate (Tier 2)
        ▼
Python 3 source + `# TODO[jython2py3]` / `# ERROR[jython2py3]` markers
```

The engine is [`fissix`](https://pypi.org/project/fissix/), the maintained fork of
`lib2to3`/`2to3`. It is the right base because it parses **both** Python 2 and 3
grammar (Python 3's own `ast`/`libcst` cannot parse `print x`) and round-trips
comments and whitespace. `lib2to3` itself is deprecated and removed in Python 3.13.

---

## Development

Adding a rule, dev environment setup, and running the tests — see **[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)**.
