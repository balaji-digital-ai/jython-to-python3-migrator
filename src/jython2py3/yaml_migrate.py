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

from dataclasses import dataclass, field
from io import StringIO

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from ._tasks import JYTHON_TASK_TYPE, PYTHON3_TASK_TYPE, iter_script_tasks
from .engine import Migrator

# Re-exported for callers/tests that import the task-type constants from this module.
__all__ = ["JYTHON_TASK_TYPE", "PYTHON3_TASK_TYPE", "YamlMigrationResult", "migrate_yaml"]


@dataclass
class YamlMigrationResult:
    """Outcome of migrating a single template-as-code YAML document."""

    original: str
    migrated: str
    todos: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    transforms: int = 0  # Tier-1 auto-rewrites across all converted task scripts
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
    transforms = 0
    converted = 0

    for task in iter_script_tasks(data):
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
        transforms += result.transforms
        converted += 1

    buffer = StringIO()
    yaml.dump(data, buffer)

    return YamlMigrationResult(
        original=source,
        migrated=buffer.getvalue(),
        todos=todos,
        errors=errors,
        transforms=transforms,
        tasks_converted=converted,
    )
