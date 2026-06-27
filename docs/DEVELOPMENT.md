# Developer guide

How to work on jython2py3 — add or change a migration rule, set up the environment, and run
the tests and linter.

---

## How the engine fits together

The tool is built on [`fissix`](https://pypi.org/project/fissix/), the maintained fork of
`lib2to3`/`2to3`. It parses **both** Python 2 and 3 grammar (Python 3's own `ast`/`libcst`
cannot parse `print x`) and round-trips comments and whitespace, so migrations preserve
formatting. `lib2to3` itself is deprecated and removed in Python 3.13.

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

Each migration rule is one **fixer** — a `BaseFix` subclass that matches a pattern and
either rewrites it (Tier 1) or stamps a marker (Tier 2). See
[MIGRATION-RULES.md](MIGRATION-RULES.md) for the full list of rules in both tiers.

---

## Updating the migration logic

Adding or changing a rule is a localised, testable change. The detailed walk-through is in
[ADDING_A_RULE.md](ADDING_A_RULE.md). In short:

1. Add `src/jython2py3/fixers/fix_<name>.py` (a `BaseFix` subclass).
2. Register it in `src/jython2py3/fixers/__init__.py`.
3. Add a unit test (and fixture) under `tests/`.

No other module changes. Each rule is isolated, so one rule cannot break another.

---

## Development environment

```bash
uv sync --extra dev           # create .venv with dev tools from the lockfile
uv run pytest                 # run all tests (offline; no Release server needed)
uv run pytest -m unit         # fast unit tests only
uv run pytest -m integration  # end-to-end migration tests
uv run ruff check .           # lint
```

The equivalent pip workflow is `pip install -e ".[dev]"` then `pytest` / `ruff check .`.

Every test runs offline — no Release server or API client required — so it passes on a fresh
`uv sync --extra dev`.

---

## Test layout

| Location | What it covers |
| -------- | -------------- |
| `tests/unit` | one file per fixer — a focused before/after for each rule |
| `tests/integration` | whole-script migrations of `examples/` (golden-file comparison) |

The integration goldens are the committed `examples/python3/` outputs; regenerate them with
`jython2py3 migrate examples/jython/ -o examples/python3/` after an intended rule change, and
review the diff.

---

## Related docs

- [ADDING_A_RULE.md](ADDING_A_RULE.md) — step-by-step for writing a new fixer
- [MIGRATION-RULES.md](MIGRATION-RULES.md) — every rule in both tiers
- [JYTHON-TO-PYTHON3-MIGRATION.md](JYTHON-TO-PYTHON3-MIGRATION.md) — the language-level migration guide
