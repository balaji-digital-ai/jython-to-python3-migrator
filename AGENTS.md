# AGENTS.md

Guidance for AI agents (Claude Code and any other tool) working in this repository.
This is the single source of truth; `CLAUDE.md` imports it.

Deterministic, rule-based source-to-source migrator: Digital.ai Release **Jython
(Python 2) scripts → Python 3 Script (Container)**. Built on `fissix` (the maintained
`lib2to3` fork) because it parses *both* Python 2 and 3 and round-trips comments.

## Mental model: two tiers
Every rule is a `fissix` fixer and falls into one of two tiers — this is the core idea:
- **Tier 1 (auto-transform):** safe, silent rewrites (e.g. `print x`→`print(x)`,
  `releaseVariables["x"]`→`getReleaseVariable("x")`, reserved-object injection).
- **Tier 2 (annotate):** cannot be rewritten safely, so the code is left intact and
  flagged with a comment — `# TODO[jython2py3]` (finish by hand) or
  `# ERROR[jython2py3]` (cannot run in Python 3, e.g. a Java class).
The migrated output **must always be valid Python 3** (markers are comments).

## Where things live
- `src/jython2py3/engine.py` — the `Migrator` (wraps `RefactoringTool`); pure, no I/O.
- `src/jython2py3/cli.py` — argparse CLI, file/dir handling, summary + JSON report.
- `src/jython2py3/yaml_migrate.py` — Template-as-code YAML path (converts only
  `xlrelease.ScriptTask` → `containerPython.PythonTask`, in place, via ruamel).
- `src/jython2py3/fixers/` — **one fixer per rule**; `_cst.py` has shared CST helpers
  (`add_todo` / `add_error`).
- `docs/JYTHON-TO-PYTHON3-MIGRATION.md` — **the spec / source of truth** for rules.
  Cite its section number in each fixer docstring and TODO message.

## Adding/changing a rule (see docs/ADDING_A_RULE.md)
1. Add `src/jython2py3/fixers/fix_<name>.py` (a `BaseFix` subclass).
2. Register it in `src/jython2py3/fixers/__init__.py` (`CUSTOM_FIXERS`).
3. Add a unit test under `tests/unit/` (one file per fixer).
4. **Regenerate the goldens and update the EXPECTED tables** (see below).

## Golden-file workflow — do this after ANY rule change
Examples are golden-tested byte-for-byte. Never hand-edit a golden; regenerate:
```bash
jython2py3 migrate examples/jython/ -o examples/python3/
jython2py3 migrate examples/templates/jython/ -o examples/templates/python3/
```
Then keep the expectation tables in sync (tests fail loudly if you forget):
- `tests/integration/test_example_goldens.py` → `EXPECTED` = per-file (TODO, ERROR).
- `tests/integration/test_template_yaml.py` → `EXPECTED` = per-template tasks_converted.
- Example inputs use **numbered, descriptive** names (`01_reserved_objects.py` …);
  `examples/jython/*.py` → `examples/python3/*.py`, templates `jython/` → `python3/`.

## Dev / test
- `uv sync --extra dev` then `uv run pytest` (or `-m unit` / `-m integration`).
- `uv run ruff check .` — `examples/` is excluded (the inputs are Python 2).
- The whole suite is **offline** — no Release server or API client. Don't add live/
  network tests. Python 3.9+ (`requires-python` in `pyproject.toml`); the tool is
  OS-agnostic and must keep running identically on Windows and Linux.

## Gotchas
- The migrator preserves comments, so an example's header comments flow into its
  golden — edit the example, then regenerate.
- A fixer matches but may decline to act; the engine counts a transform only when the
  tree actually changes (see `engine._counting`).
- Treat goldens as generated artifacts, not source.
