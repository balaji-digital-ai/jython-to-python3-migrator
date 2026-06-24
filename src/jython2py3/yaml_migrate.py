"""Migrate Jython script tasks embedded in a Release *template-as-code* YAML.

The Release UI's **YAML: Template as code** export embeds each Jython
``xlrelease.ScriptTask`` body as a literal block scalar under ``script:``. This
module reuses the very same :class:`~jython2py3.engine.Migrator` used for standalone
``.py`` scripts: it walks the YAML document, migrates every ``xlrelease.ScriptTask``
script *in place*, and swaps that task's ``type`` to ``containerPython.PythonTask``.

Everything else in the document - key order, comments, block-scalar style, anchors
and custom tags such as ``!value`` - is preserved, because we use ``ruamel.yaml`` in
round-trip mode and only ever touch the two keys we change (``script`` and ``type``)
on the tasks we convert. Tasks of any other type are left exactly as they were.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from io import StringIO

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from .engine import Migrator

# The Jython script task we convert, and the Python 3 Script (Container) task it
# becomes. Both task types expose the script under the same `script` input property,
# so converting a task is a type swap plus an in-place migration of the script body.
JYTHON_TASK_TYPE = "xlrelease.ScriptTask"
PYTHON3_TASK_TYPE = "containerPython.PythonTask"


@dataclass
class YamlMigrationResult:
    """Outcome of migrating a single template-as-code YAML document."""

    original: str
    migrated: str
    todos: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tasks_converted: int = 0

    @property
    def changed(self) -> bool:
        return self.migrated != self.original


def _new_yaml() -> YAML:
    """A round-trip YAML configured to match the Release export's layout.

    Round-trip mode preserves comments, key order and custom tags. The indent and
    a wide line width keep untouched content byte-stable, so a converted template's
    only diff is the tasks we actually changed.
    """
    yaml = YAML()  # round-trip (typ="rt") is the default
    yaml.preserve_quotes = True
    yaml.width = 4096  # never line-wrap existing scalars
    yaml.indent(mapping=2, sequence=2, offset=0)  # matches the "Template as code" export
    return yaml


def migrate_yaml(source: str, migrator: Migrator | None = None) -> YamlMigrationResult:
    """Convert every Jython ``xlrelease.ScriptTask`` in ``source`` to a Python 3 task.

    ``migrator`` is reused if given (constructing one compiles the fixer set, so a
    caller migrating many files should share a single instance).
    """
    migrator = migrator or Migrator()
    yaml = _new_yaml()
    data = yaml.load(source)

    todos: list[str] = []
    errors: list[str] = []
    converted = 0

    for task in _iter_script_tasks(data):
        script = task.get("script")
        if not isinstance(script, str):
            continue  # a ScriptTask with a non-string (or missing) script: leave it
        result = migrator.migrate(str(script))
        # LiteralScalarString re-emits as a `|` block scalar; with no trailing newline
        # ruamel writes `|-`, matching how the export wrote the Jython body.
        task["script"] = LiteralScalarString(result.migrated)
        task["type"] = PYTHON3_TASK_TYPE
        todos.extend(result.todos)
        errors.extend(result.errors)
        converted += 1

    buffer = StringIO()
    yaml.dump(data, buffer)

    return YamlMigrationResult(
        original=source,
        migrated=buffer.getvalue(),
        todos=todos,
        errors=errors,
        tasks_converted=converted,
    )


def _iter_script_tasks(node: object) -> Iterator[dict]:
    """Yield every mapping that is an ``xlrelease.ScriptTask`` carrying a ``script``,
    anywhere in the document (templates -> phases -> tasks, including nested subtasks).

    The walk is structural, not schema-aware, so it works regardless of how deeply a
    task is nested (gates, parallel groups, sub-releases, ...).
    """
    if isinstance(node, dict):
        if node.get("type") == JYTHON_TASK_TYPE and "script" in node:
            yield node
        for value in node.values():
            yield from _iter_script_tasks(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _iter_script_tasks(item)
