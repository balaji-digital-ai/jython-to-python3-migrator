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
| Python 2 → 3 syntax (guide [§10](docs/JYTHON-TO-PYTHON3-MIGRATION.md#10-python-27--python-3-syntax-changes)) | `print x` → `print(x)`, `d.iteritems()` → `d.items()`, `xrange` → `range`, `except E, e:` → `except E as e:` |
| Variable dictionaries (guide [§5](docs/JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions), [§8](docs/JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `releaseVariables["x"]` → `getReleaseVariable("x")`; `… = v` → `setReleaseVariable("x", v)` (also `folder.`/`global.`) |
| Reserved objects (guide [§5](docs/JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions)) | a free `release`/`phase`/`task` → injects `release = getCurrentRelease()` etc. at the top |
| Java imports (guide [§11](docs/JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `from java.util import Date` → removed, with a breadcrumb |

**Tier 2 — annotate** (cannot be rewritten safely; left intact with a marker and a
guide reference). Two marker kinds, so you can tell "needs a rewrite" from "cannot
run at all" at a glance:

| Rule | Marker | Why it is not automated |
| ---- | ------ | ----------------------- |
| `HttpRequest` → `requests` (guide [§9](docs/JYTHON-TO-PYTHON3-MIGRATION.md#9-httprequest--httpresponse--requests)) | `# TODO[jython2py3]` | the original usually reads URL/credentials from a shared configuration the container cannot access |
| Variable-map use that is not a plain read/write — augmented assignment, `del`, an unpacking target, `releaseVariables.keys()`, `for k in releaseVariables`, `releaseVariables["x"].foo()` (guide [§8](docs/JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `# TODO[jython2py3]` | only a plain read/write maps to a single `get`/`set` helper; anything else needs a human to choose the getter/setter split |
| Java **usage** — `Date()`, `Calendar.getInstance()`, `java.util.X` (guide [§11](docs/JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `# ERROR[jython2py3]` | there is no JVM in the container, so every Java class reference raises at runtime; it has no mechanical Python equivalent and must be redesigned |

`# TODO` means *finish the conversion by hand*; `# ERROR` means *this code cannot run
in Python 3 — don't use Java*. The Java **import** lines are removed (a Tier-1
breadcrumb); this rule additionally stamps each **use** of the imported symbol.

Run `jython2py3 migrate <script> --diff` to see both tiers in action, then resolve
the `# TODO[jython2py3]` and `# ERROR[jython2py3]` markers by hand. The CLI summary
reports both counts (`N TODO(s) to review, M error(s) to fix`).

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
different slice of the rule set:

| Example | Demonstrates | Result |
| ------- | ------------ | ------ |
| [`current_context`](examples/jython/current_context.py) | `print`, free `release`/`phase`, the `releaseVariables` map, a `releaseApi` call | **runs as-is** — 0 TODO / 0 ERROR |
| [`orchestrate_release`](examples/jython/orchestrate_release.py) | the API flow: `templateApi.createTemplate` → `phaseApi.addPhase` → `taskApi.addTask` → `templateApi.create` → `releaseApi.start` | **runs as-is** — API imports pass through unchanged |
| [`variable_map`](examples/jython/variable_map.py) | release/folder/global maps, a Map (dict) value, an augmented assignment and a whole-map iteration (TODOs), a `java.util.HashMap` (ERROR) | 3 TODO / 1 ERROR |
| [`java_datetime_report`](examples/jython/java_datetime_report.py) | heavy Java date/time use — every reference flagged "don't use Java in Python 3" | 2 TODO / 5 ERROR |
| [`http_health_check`](examples/jython/http_health_check.py) | `HttpRequest` → `requests` (TODO) alongside a `java.net.URL` (ERROR) | 3 TODO / 1 ERROR |
| [`deploy`](examples/jython/deploy.py) | a compact mix of syntax, variable and import rules | 3 TODO / 0 ERROR |

The two "runs as-is" examples are the ones safe to drop straight into a Python 3
Script (Container) task; the others print a checklist of markers to resolve first.

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
uv run pytest                 # run all tests (the live test self-skips with no server)
uv run pytest -m unit         # fast unit tests only
uv run pytest -m integration  # end-to-end migration tests
uv run ruff check .           # lint
```

The equivalent pip workflow is `pip install -e ".[dev]"` then `pytest` / `ruff
check .`. A plain test run needs no Release server and no Release API client — the
live test self-skips — so it passes offline on a fresh `uv sync --extra dev`.

Tests live in `tests/unit` (one file per fixer) and `tests/integration`
(whole-script migrations of `examples/`).

### Live-server test (migrate **and run**)

`tests/integration/test_live_migration.py` goes one step further than the offline
tests: it migrates `examples/jython/current_context.py` and then **executes the
migrated Python 3** as a `containerPython.PythonTask` on a real Digital.ai Release
server, proving the converted script has no migration *or* runtime issues.

It needs the Release API client (Python 3.10+) and a running server with a container
runner:

```bash
uv sync --extra dev --extra integration    # adds the Release API client

# run the live test (defaults to http://localhost:5516, admin/admin)
uv run pytest tests/integration/test_live_migration.py -v
```

The test **skips automatically** when no server is reachable, so a plain `pytest`
run still passes offline.

Point it at another server with CLI options or environment variables:

| Option | Env var | Default |
| ------ | ------- | ------- |
| `--release-url` | `RELEASE_URL` | `http://localhost:5516` |
| `--release-username` | `RELEASE_USERNAME` | `admin` |
| `--release-password` | `RELEASE_PASSWORD` | `admin` |
| `--release-token` | `RELEASE_TOKEN` | _(overrides user/password)_ |

The container task calls back into the API as the release's **"Run as user"**.
Those credentials default to the primary ones but can be set separately via
`RELEASE_SCRIPT_USER` / `RELEASE_SCRIPT_PASSWORD` — without a valid run-as user the
migrated script's `getCurrent*` / `get*Variable` helpers fail with a "Cannot
connect to Release API" error.

```bash
uv run pytest tests/integration/test_live_migration.py \
  --release-url https://release.example.com \
  --release-token "$MY_PAT" -v
```
