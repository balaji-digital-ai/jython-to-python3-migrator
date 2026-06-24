# Changelog

All notable changes to this project are documented here. The version aligns with the
Digital.ai Release migration guide it targets, so users can pin to a known ruleset.

## [Unreleased]

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
