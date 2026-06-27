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
  INPUT              files, directories (searched for *.py / *.yaml / *.yml), or glob patterns

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

## What it does

Each rule is a **fixer** that the tool applies in one of two tiers:

- **Tier 1 — auto-transform:** safe, mechanical rewrites done silently (Python 2 → 3
  syntax, variable dictionaries, reserved objects, Java imports, `Date` → `datetime`).
- **Tier 2 — annotate:** things that can't be rewritten safely are left intact and
  flagged with a marker — `# TODO[jython2py3]` (*finish by hand*) or `# ERROR[jython2py3]`
  (*can't run in Python 3 — redesign*).

Run `jython2py3 migrate <script> --diff` to see both tiers, then resolve the markers by
hand. The CLI summary (and `--report`) counts all three:
`K auto-transform(s), N TODO(s) to review, M error(s) to fix`.

The tool migrates the mechanical ~80% and flags the rest for human review.

**Full rule-by-rule reference:** see **[`docs/MIGRATION-RULES.md`](docs/MIGRATION-RULES.md)**
— every Tier 1 and Tier 2 rule with examples and the reasoning behind each marker.

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

Want to add or change a migration rule, or run the tests and linter? The quick start:

```bash
uv sync --extra dev           # create .venv with dev tools from the lockfile
uv run pytest                 # run all tests (offline; no Release server needed)
uv run ruff check .           # lint
```

Adding a rule is a localised, isolated change — a new fixer under
`src/jython2py3/fixers/` plus a unit test, with no other module changes.

See **[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)** for the full developer guide —
the engine architecture, updating the migration logic, the dev environment, and the
test layout. The step-by-step for writing a fixer is in
[`docs/ADDING_A_RULE.md`](docs/ADDING_A_RULE.md).
