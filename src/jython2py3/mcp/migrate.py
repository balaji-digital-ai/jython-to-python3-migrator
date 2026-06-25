"""Convert the Jython script tasks inside a Release *template object*.

The MCP server returns a template as JSON, which the client decodes to a plain
``dict``. This module migrates that object **in place** using the exact same
:class:`~jython2py3.engine.Migrator` (and therefore the exact same rule set) used for
standalone ``.py`` scripts and template-as-code YAML - so a template converted via
MCP is identical to the same template converted from a YAML export.

It is deliberately free of any MCP/network code: it takes a ``dict`` in and returns a
new ``dict`` out, which makes it trivial to unit-test offline.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .._tasks import PYTHON3_TASK_TYPE, iter_script_tasks
from ..engine import Migrator


@dataclass
class TemplateMigrationResult:
    """Outcome of migrating a single template object pulled over MCP."""

    template: dict  # the converted template (a deep copy; the input is never mutated)
    todos: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    transforms: int = 0  # Tier-1 auto-rewrites across all converted task scripts
    tasks_converted: int = 0

    @property
    def changed(self) -> bool:
        return self.tasks_converted > 0


def migrate_template_object(
    template: dict, migrator: Migrator | None = None
) -> TemplateMigrationResult:
    """Convert every Jython ``xlrelease.ScriptTask`` in ``template`` to a Python 3 task.

    ``template`` is a JSON-decoded Release template object (as returned by the MCP
    ``get_template`` tool). The input is **not** mutated - the result carries a deep
    copy with each Jython task's ``script`` migrated and its ``type`` swapped to
    ``containerPython.PythonTask``. Tasks of any other type are left untouched.

    ``migrator`` is reused if given (constructing one compiles the fixer set, so a
    caller converting many templates should share a single instance).
    """
    migrator = migrator or Migrator()
    converted_template = copy.deepcopy(template)

    todos: list[str] = []
    errors: list[str] = []
    transforms = 0
    converted = 0

    for task in iter_script_tasks(converted_template):
        script = task.get("script")
        if not isinstance(script, str):
            continue  # a ScriptTask with a non-string (or missing) script: leave it
        result = migrator.migrate(script)
        task["script"] = result.migrated
        task["type"] = PYTHON3_TASK_TYPE
        todos.extend(result.todos)
        errors.extend(result.errors)
        transforms += result.transforms
        converted += 1

    return TemplateMigrationResult(
        template=converted_template,
        todos=todos,
        errors=errors,
        transforms=transforms,
        tasks_converted=converted,
    )
