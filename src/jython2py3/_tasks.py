"""Shared helpers for locating Jython script tasks inside a Release template.

A Release template is a nested structure - phases -> tasks -> (gates, parallel
groups, sub-tasks) -> tasks - and a Jython ``xlrelease.ScriptTask`` can sit at any
depth. Both the *template-as-code* YAML path (:mod:`jython2py3.yaml_migrate`) and
the MCP path (:mod:`jython2py3.mcp.migrate`) need to find every such task and convert
it to a ``containerPython.PythonTask``.

The walk here is purely *structural* (recurse through ``dict`` and ``list`` nodes,
matching on the ``type``/``script`` keys). That is deliberate: it works unchanged for
a ``ruamel.yaml`` round-trip document **and** for a plain ``dict`` decoded from the
MCP server's JSON, so a single converter serves both transports.
"""
from __future__ import annotations

from collections.abc import Iterator

# The Jython script task we convert, and the Python 3 Script (Container) task it
# becomes. Both task types expose the script under the same ``script`` input
# property, so converting a task is a ``type`` swap plus an in-place migration of the
# script body.
JYTHON_TASK_TYPE = "xlrelease.ScriptTask"
PYTHON3_TASK_TYPE = "containerPython.PythonTask"


def iter_script_tasks(node: object) -> Iterator[dict]:
    """Yield every mapping that is an ``xlrelease.ScriptTask`` carrying a ``script``,
    anywhere in ``node`` (templates -> phases -> tasks, including nested subtasks).

    The walk is structural, not schema-aware, so it works regardless of how deeply a
    task is nested (gates, parallel groups, sub-releases, ...) and regardless of
    whether ``node`` is a YAML document or a JSON-decoded ``dict``.
    """
    if isinstance(node, dict):
        if node.get("type") == JYTHON_TASK_TYPE and "script" in node:
            yield node
        for value in node.values():
            yield from iter_script_tasks(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from iter_script_tasks(item)
