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
  --report FILE      write a JSON migration report to FILE
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

Instead of exporting a YAML by hand, the migrator can pull a template **directly from a
running Digital.ai Release instance** through the official
[Release MCP server](https://hub.docker.com/r/xebialabs/dai-release-mcp), migrate its
Jython tasks (the same rules as `.py`/`.yaml`), and save the converted template to a file.
It is **read-only against Release** — you create the new template by re-importing that
file, so your original is never touched.

```bash
uv sync --extra mcp                                   # one-time: install the MCP client SDK
export RELEASE_MCP_URL=http://localhost:8000/mcp      # point at your running MCP server

jython2py3 mcp list                                   # list templates (id <tab> title)
jython2py3 mcp migrate <TEMPLATE_ID> -o migrated.json # pull + migrate to a file
# then re-import migrated.json as a NEW template via the Release UI
```

This CLI is the MCP **client**; it never holds your Release credentials — those live on
the MCP server. The full how-to (connecting, listing, migrating, re-importing,
troubleshooting) is in **[`docs/MCP-INTEGRATION.md`](docs/MCP-INTEGRATION.md)**; for the
MCP server itself see the [official docs](https://docs.digital.ai/release/docs/how-to/release-mcp-server).

---

## What it does

Each migration rule is a **fixer**: a pattern to match plus a transformation. Rules
fall into two tiers.

**Tier 1 — auto-transform** (always safe; applied silently):

| Rule | Example |
| ---- | ------- |
| Python 2 → 3 syntax (guide [§10](docs/JYTHON-TO-PYTHON3-MIGRATION.md#10-python-27--python-3-syntax-changes)) | `print x` → `print(x)`, `d.iteritems()` → `d.items()`, `xrange` → `range`, `except E, e:` → `except E as e:` |
| Variable dictionaries (guide [§5](docs/JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions), [§8](docs/JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `releaseVariables["x"]` → `getReleaseVariable("x")`; `… = v` → `setReleaseVariable("x", v)` (also `folder.`/`global.`) |
| Reserved objects (guide [§5](docs/JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions)) | a free `release`/`phase`/`task` → injects `release = getCurrentRelease()` etc. at the top |
| Java imports (guide [§11](docs/JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `from java.util import Calendar` → removed, with a breadcrumb |
| `java.util.Date` → `datetime` (guide [§11](docs/JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `from java.util import Date` → `import datetime`; `Date()` → `datetime.datetime.now(datetime.timezone.utc)` |

**Tier 2 — annotate** (cannot be rewritten safely; left intact with a marker and a
guide reference). Two marker kinds, so you can tell "needs a rewrite" from "cannot
run at all" at a glance:

| Rule | Marker | Why it is not automated |
| ---- | ------ | ----------------------- |
| `HttpRequest` → `requests` (guide [§9](docs/JYTHON-TO-PYTHON3-MIGRATION.md#9-httprequest--httpresponse--requests)) | `# TODO[jython2py3]` | the original usually reads URL/credentials from a shared configuration the container cannot access |
| Variable-map use that is not a plain read/write — augmented assignment, `del`, an unpacking target, `releaseVariables.keys()`, `for k in releaseVariables`, `releaseVariables["x"].foo()` (guide [§8](docs/JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `# TODO[jython2py3]` | only a plain read/write maps to a single `get`/`set` helper; anything else needs a human to choose the getter/setter split |
| Java **usage** — `Calendar.getInstance()`, `Properties()`, `java.util.X` (guide [§11](docs/JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `# ERROR[jython2py3]` | there is no JVM in the container, so every Java class reference raises at runtime; it has no mechanical Python equivalent and must be redesigned |

`# TODO` means *finish the conversion by hand*; `# ERROR` means *this code cannot run
in Python 3 — don't use Java*. The Java **import** lines are removed (a Tier-1
breadcrumb); this rule additionally stamps each **use** of the imported symbol.

Run `jython2py3 migrate <script> --diff` to see both tiers in action, then resolve
the `# TODO[jython2py3]` and `# ERROR[jython2py3]` markers by hand. The CLI summary
counts all three per file — the silent Tier-1 rewrites plus the two marker kinds
(`K auto-transform(s), N TODO(s) to review, M error(s) to fix`) — and `--report`
records the same as `transform_count` / `todo_count` / `error_count` per file.

> **Scope:** the tool migrates the mechanical ~80%. `HttpRequest` rewrites, mapping
> outputs to `result`/`result_2`/`result_3`, and Java-interop redesign remain human
> review steps that the tool *flags* for you. (Note: a **Jython** task outputs
> printed markdown and has *no* `result`/`result_2`/`result_3` variables — those
> belong to the Python 3 **Container** task, so adding them is a deliberate review
> step, not an automatic rewrite.) See
> [the migration guide](docs/JYTHON-TO-PYTHON3-MIGRATION.md) for the rest.

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

## Updating the migration logic

Adding or changing a rule is a localised, testable change — see
[`docs/ADDING_A_RULE.md`](docs/ADDING_A_RULE.md). In short:

1. Add `src/jython2py3/fixers/fix_<name>.py` (a `BaseFix` subclass).
2. Register it in `src/jython2py3/fixers/__init__.py`.
3. Add a unit test (and fixture) under `tests/`.

No other module changes. Each rule is isolated, so one rule cannot break another.

---

## Development

```bash
uv sync --extra dev           # create .venv with dev tools from the lockfile
uv run pytest                 # run all tests (offline; no Release server needed)
uv run pytest -m unit         # fast unit tests only
uv run pytest -m integration  # end-to-end migration tests
uv run ruff check .           # lint
```

The equivalent pip workflow is `pip install -e ".[dev]"` then `pytest` / `ruff
check .`. Every test runs offline — no Release server or API client required — so it
passes on a fresh `uv sync --extra dev`.

Tests live in `tests/unit` (one file per fixer) and `tests/integration`
(whole-script migrations of `examples/`).
