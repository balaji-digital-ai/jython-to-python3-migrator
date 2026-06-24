# jython2py3 — Jython → Python 3 Script migrator

A deterministic, **rule-based source-to-source migrator** that converts Digital.ai
Release **Jython Script** automation (`xlrelease.ScriptTask`) into **Python 3 Script
(Container)** scripts (`containerPython.PythonTask`).

It automates the mechanical parts of the bundled
[Jython → Python 3 migration guide](docs/JYTHON-TO-PYTHON3-MIGRATION.md) (also published
[online](https://docs.digital.ai/release/docs/next/how-to/container-python3-plugin)) and
**flags** the parts that need a human decision — it never silently emits code that might
be wrong.

* Pure Python, **runs identically on Windows and Linux**.
* Preserves comments and formatting (it works on a syntax tree, not text).
* One file in, one file out — or whole directories at once.

---

## Install & run (clone-and-run)

```bash
git clone <repo-url> jython-to-python3-migrator
cd jython-to-python3-migrator

# create an isolated environment and install the tool
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install .

# migrate
jython2py3 migrate path/to/script.py -o migrated/script.py
```

No-install alternative from a clone: `pip install fissix` then
`python -m jython2py3 migrate ...`.

---

## Usage

```bash
jython2py3 migrate script.py                  # preview migrated source on stdout
jython2py3 migrate script.py -o out.py        # write one file
jython2py3 migrate scripts/ -o migrated/      # mirror a directory tree
jython2py3 migrate scripts/ --in-place --backup
jython2py3 migrate "scripts/*.py" --dry-run --diff
jython2py3 migrate scripts/ -o migrated/ --report report.json
```

| Option | Effect |
| ------ | ------ |
| `-o, --output PATH` | output file (single input) or directory (mirrors layout) |
| `--in-place` | overwrite the inputs (`--backup` keeps `<file>.bak`) |
| `--dry-run` | report what would change; write nothing |
| `--diff` | print a unified diff per changed file |
| `--report FILE` | write a JSON migration report (CI-friendly) |

Inputs may be files, directories (searched recursively for `*.py`), or glob
patterns (expanded in-process, so they work on Windows too).

---

## What it does

Each migration rule is a **fixer**: a pattern to match plus a transformation. Rules
fall into two tiers.

**Tier 1 — auto-transform** (always safe; applied silently):

| Rule | Example |
| ---- | ------- |
| Python 2 → 3 syntax (guide §10) | `print x` → `print(x)`, `d.iteritems()` → `d.items()`, `xrange` → `range`, `except E, e:` → `except E as e:` |
| Variable dictionaries (guide §5, §8) | `releaseVariables["x"]` → `getReleaseVariable("x")`; `… = v` → `setReleaseVariable("x", v)` (also `folder.`/`global.`) |
| Reserved objects (guide §5) | a free `release`/`phase`/`task` → injects `release = getCurrentRelease()` etc. at the top |
| Java imports (guide §11) | `from java.util import Date` → removed, with a breadcrumb |

**Tier 2 — annotate** (cannot be rewritten safely; left intact with a
`# TODO[jython2py3]` marker and a guide reference):

| Rule | Why it is not automated |
| ---- | ----------------------- |
| `HttpRequest` → `requests` (guide §9) | the original usually reads URL/credentials from a shared configuration the container cannot access |

Run `jython2py3 migrate <script> --diff` to see both tiers in action, then resolve
the `# TODO[jython2py3]` markers by hand.

> **Scope:** the tool migrates the mechanical ~80%. `HttpRequest` rewrites, mapping
> outputs to `result`/`result_2`/`result_3`, and Java-interop redesign remain human
> review steps that the tool *flags* for you. See
> [the migration guide](docs/JYTHON-TO-PYTHON3-MIGRATION.md) for the rest.

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
Python 3 source + `# TODO[jython2py3]` markers
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
pip install -e ".[dev]"
pytest                 # run all tests
pytest -m unit         # fast unit tests only
ruff check .           # lint
```

Tests live in `tests/unit` (one file per fixer) and `tests/integration`
(whole-script migrations of `examples/`).
