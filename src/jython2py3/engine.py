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
    transforms: int = 0  # Tier-1 auto-rewrites applied (annotations excluded)

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
        # Per-migrate() tally of how many rules fired; see _instrument_fixers.
        self._applications = 0
        self._instrument_fixers()

    def _instrument_fixers(self) -> None:
        """Wrap every fixer's ``transform`` so we can count rule applications.

        A fixer may ``match`` a node yet decide not to rewrite it (returning ``None``
        and touching nothing), so counting every ``transform`` call would over-count.
        A real application shows up in one of two ways: the fixer **returns a new node**
        (fissix splices it in afterwards), or it **edits the tree in place** and returns
        ``None`` (a node replaced, a prefix annotated). The wrapper detects the first via
        the return value and the second via the tree's ``was_changed`` flag, which fissix
        sets through :meth:`Base.changed` on any in-place edit. This covers the stock and
        custom fixers uniformly without each one threading a counter through its logic.
        """
        for fixer in self._tool.pre_order + self._tool.post_order:
            fixer.transform = self._counting(fixer.transform)

    def _counting(self, transform):
        def wrapper(node, results):
            root = node
            while root.parent is not None:
                root = root.parent
            was_changed = root.was_changed
            root.was_changed = False
            try:
                new = transform(node, results)
            finally:
                edited_in_place = root.was_changed
                # Keep the tree's overall changed flag intact for fissix.
                root.was_changed = was_changed or edited_in_place
            if new is not None or edited_in_place:
                self._applications += 1
            return new

        return wrapper

    def migrate(self, source: str) -> MigrationResult:
        """Migrate Jython ``source`` and return the Python 3 result.

        The transformation preserves comments and (most) formatting because fissix
        works on a concrete syntax tree, not text.
        """
        # fissix requires a trailing newline to parse the final statement; remember
        # whether the caller had one so we can restore the original shape.
        had_trailing_newline = source.endswith("\n")
        to_parse = source if had_trailing_newline else source + "\n"

        self._applications = 0
        tree = self._tool.refactor_string(to_parse, name="<script>")
        migrated = str(tree)
        applications = self._applications

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
        # Tier-1 transforms are the rule applications that were *not* annotations.
        # Each annotation (a Tier-2 rule) emits exactly one marker line, so removing
        # the marker-line counts from the total isolates the silent auto-rewrites.
        transforms = max(0, applications - len(todos) - len(errors))
        return MigrationResult(
            original=source, migrated=migrated, todos=todos, errors=errors,
            transforms=transforms)
