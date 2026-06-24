"""The migration engine: a thin wrapper around ``fissix.RefactoringTool``.

It assembles two groups of fixers and runs them in a single pass:

1. The stock ``fissix`` Python 2 -> 3 fixers (``print`` statement, ``except``,
   ``iteritems``, ``xrange``, ``unicode`` ...). These cover migration-guide section 10.
2. The Release-specific fixers in :mod:`jython2py3.fixers`.

The engine is pure Python and does no I/O, so it behaves identically on Windows and
Linux. File reading/writing and path handling live in :mod:`jython2py3.cli`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fissix import refactor

from . import ERROR_MARKER, TODO_MARKER
from .fixers import CUSTOM_FIXERS

# Stock fixers that change behaviour rather than just syntax, or are stylistic. We
# exclude them to mirror the conservative default behaviour of the ``2to3`` tool.
_BUILTIN_DENYLIST = {
    "fissix.fixes.fix_idioms",   # opinionated rewrites (e.g. type(x) == type(y))
    "fissix.fixes.fix_ws_comma",  # cosmetic whitespace-after-comma changes
}


def _builtin_fixers() -> list[str]:
    """All stock ``fissix`` Python 2 -> 3 fixers, minus the denylisted ones."""
    names = refactor.get_fixers_from_package("fissix.fixes")
    return [name for name in names if name not in _BUILTIN_DENYLIST]


@dataclass
class MigrationResult:
    """Outcome of migrating a single script."""

    original: str
    migrated: str
    todos: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.migrated != self.original

    @property
    def todo_count(self) -> int:
        return len(self.todos)

    @property
    def error_count(self) -> int:
        return len(self.errors)


class Migrator:
    """Reusable migrator. Construct once, call :meth:`migrate` per script."""

    def __init__(self) -> None:
        fixer_names = _builtin_fixers() + list(CUSTOM_FIXERS)
        # fissix logs a warning for every file without a trailing newline; we add one
        # ourselves below, so quiet the logger to keep CLI output clean.
        logging.getLogger("RefactoringTool").setLevel(logging.ERROR)
        self._tool = refactor.RefactoringTool(fixer_names)

    def migrate(self, source: str) -> MigrationResult:
        """Migrate Jython ``source`` and return the Python 3 result.

        The transformation preserves comments and (most) formatting because fissix
        works on a concrete syntax tree, not text.
        """
        # fissix requires a trailing newline to parse the final statement; remember
        # whether the caller had one so we can restore the original shape.
        had_trailing_newline = source.endswith("\n")
        to_parse = source if had_trailing_newline else source + "\n"

        tree = self._tool.refactor_string(to_parse, name="<script>")
        migrated = str(tree)

        if not had_trailing_newline and migrated.endswith("\n"):
            migrated = migrated[:-1]

        todos = [
            line.strip()
            for line in migrated.splitlines()
            if TODO_MARKER in line
        ]
        errors = [
            line.strip()
            for line in migrated.splitlines()
            if ERROR_MARKER in line
        ]
        return MigrationResult(
            original=source, migrated=migrated, todos=todos, errors=errors)
