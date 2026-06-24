# Changelog

All notable changes to this project are documented here. The version aligns with the
Digital.ai Release migration guide it targets, so users can pin to a known ruleset.

## [Unreleased]

### Fixed
- A `releaseVariables[...]` (or `folder`/`global`) subscript used as a **tuple/list
  unpacking target** (e.g. `releaseVariables["x"], y = a, b`) is no longer rewritten
  to a getter on the left of `=` — which produced code that fails to parse. It is now
  left intact and flagged with a `# TODO[jython2py3]` to use the setter explicitly
  (§8). The migrator never silently emits invalid Python.
- **Leftover variable-map references are now flagged** instead of silently passed
  through. A use that is not a plain read/write — `releaseVariables.keys()`,
  `for k in releaseVariables`, a chained `releaseVariables["x"].foo()` — left a bare
  `releaseVariables` name that does not exist in the container (a runtime `NameError`).
  A new `fix_release_var_refs` rule stamps each with a `# TODO[jython2py3]` (§8).
- **Tier-2 annotations no longer break indentation** when the flagged statement is the
  first/only statement in an indented block (`if:`, `for:`, `def:` …). The comment was
  inserted with no indent, dedenting the statement and producing invalid Python; the
  indent is now read from the block's `INDENT` token. Affected every `# TODO` / `#
  ERROR` inside a block.
- A comprehension/loop variable named `release` / `phase` / `task`
  (`[release for release in items]`) no longer triggers a spurious
  `release = getCurrentRelease()` injection — comprehension targets are recognised as
  local bindings.
- Offline `pytest` no longer fails at collection when the optional `[integration]`
  Release API client is not installed: `tests/integration/conftest.py` imports the
  client lazily and `test_live_migration.py` self-skips via `importorskip`. A plain
  `pytest` with only `[dev]` installed now passes, as the README documents.
- Corrected the `[integration]` dependency from the non-existent `release-api-client`
  to the published `digitalai-release-api-client` (gated to Python ≥ 3.10, which that
  client requires).

### Added
- **Template-as-code YAML migration.** Pointing the CLI at a Release *YAML: Template
  as code* export (`.yaml`/`.yml`) now converts every embedded
  `xlrelease.ScriptTask` to a `containerPython.PythonTask` (both share the `script`
  property) and migrates the script body with the existing ruleset. Powered by
  `ruamel.yaml` round-trip parsing, so key order, comments, the `|-` block style,
  anchors and secret `!value` tags are preserved — the only diff is the task type and
  the migrated script. Directories are searched for `*.yaml`/`*.yml` alongside `*.py`,
  the summary/JSON report gains a per-file `tasks_converted` count, and a worked
  example lives in `examples/templates/`.
- Adopted [uv](https://docs.astral.sh/uv/): a committed `uv.lock`, uv-based developer
  and CI workflows. `pip install .` / `pip install -e ".[dev]"` still work.
- GitHub Actions workflow (`.github/workflows/python-test.yml`) running lint + tests
  on a Windows + Linux × Python 3.9/3.12 matrix (via uv), matching the documented CI
  claim.

### Changed
- `xlrelease.*` imports (e.g. `from xlrelease.HttpRequest import HttpRequest`) are now
  **removed** with a breadcrumb instead of left in place — they cannot load in the
  container. The `HttpRequest(...)` call is still flagged in place for a manual
  `requests` rewrite (§9). Consistent with the `java.*` import rule.
- Reserved objects `release` / `phase` / `task` are now **injected** as
  `release = getCurrentRelease()` (etc.) at the top of the module when used but
  unbound — promoted from a Tier-2 annotation to a Tier-1 transform, matching the
  migration guide's canonical output (§5). Idempotent: never re-injects a name the
  script already binds.
- Bundled the migration guide as `docs/JYTHON-TO-PYTHON3-MIGRATION.md` and pointed
  the README/docstrings at the local copy.

## [0.1.0] - 2026-06-24

Initial release.

### Added
- Rule-based migration engine built on `fissix` (parses Python 2 & 3, preserves
  comments).
- Tier 1 (auto-transform) rules:
  - Stock Python 2 → 3 syntax fixers (guide §10).
  - `releaseVariables` / `folderVariables` / `globalVariables` subscript reads and
    assignments → helper calls (guide §5, §8).
  - `java.*` / `javax.*` import removal with a breadcrumb comment (guide §11).
- Tier 2 (annotate) rules:
  - `HttpRequest` import and usage flagged for a `requests` rewrite (guide §9).
  - Reserved objects `release` / `phase` / `task` flagged when used but unbound
    (guide §5).
- `jython2py3 migrate` CLI: file/directory/glob inputs, `-o`, `--in-place`,
  `--backup`, `--dry-run`, `--diff`, `--report`.
- Unit tests per fixer, integration test over `examples/`, and a Windows + Linux CI
  matrix.
