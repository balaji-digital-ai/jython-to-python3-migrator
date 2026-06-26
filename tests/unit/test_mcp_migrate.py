"""Unit tests for migrating a Release *template object* (jython2py3.mcp.migrate).

These exercise the pure, offline conversion path - the same code the MCP command runs
after pulling a template - so they need neither the `mcp` SDK nor a server.
"""
import pytest

from jython2py3._tasks import JYTHON_TASK_TYPE, PYTHON3_TASK_TYPE
from jython2py3.mcp.migrate import migrate_template_object


def _template() -> dict:
    """A JSON-shaped template (as get_template would return) with nested Jython tasks."""
    return {
        "id": "Applications/Folderabc/Releasedef",
        "title": "Deploy",
        "phases": [
            {
                "title": "Build",
                "tasks": [
                    {
                        "title": "Greet",
                        "type": JYTHON_TASK_TYPE,
                        "script": 'print "Release:", release.title\n'
                        'releaseVariables["migratedBy"] = "jython2py3"\n',
                    },
                    {
                        "title": "A manual task",
                        "type": "xlrelease.Task",
                    },
                    {
                        # A nested/parallel group with another script task inside.
                        "title": "Group",
                        "type": "xlrelease.ParallelGroup",
                        "tasks": [
                            {
                                "title": "Nested",
                                "type": JYTHON_TASK_TYPE,
                                "script": 'for k, v in releaseVariables.iteritems():\n'
                                '    print k\n',
                            }
                        ],
                    },
                ],
            }
        ],
    }


@pytest.mark.unit
def test_both_script_tasks_converted():
    result = migrate_template_object(_template())
    assert result.tasks_converted == 2
    assert result.changed


@pytest.mark.unit
def test_type_swapped_and_script_migrated():
    result = migrate_template_object(_template())
    task = result.template["phases"][0]["tasks"][0]
    assert task["type"] == PYTHON3_TASK_TYPE
    assert 'print("Release:", release.title)' in task["script"]
    assert 'setReleaseVariable("migratedBy", "jython2py3")' in task["script"]
    assert "release = getCurrentRelease()" in task["script"]


@pytest.mark.unit
def test_nested_task_converted():
    result = migrate_template_object(_template())
    nested = result.template["phases"][0]["tasks"][2]["tasks"][0]
    assert nested["type"] == PYTHON3_TASK_TYPE
    assert ".items()" in nested["script"]  # iteritems() -> items()


@pytest.mark.unit
def test_non_script_task_untouched():
    result = migrate_template_object(_template())
    manual = result.template["phases"][0]["tasks"][1]
    assert manual == {"title": "A manual task", "type": "xlrelease.Task"}


@pytest.mark.unit
def test_input_not_mutated():
    original = _template()
    migrate_template_object(original)
    # The source object is deep-copied; the original still holds Jython.
    assert original["phases"][0]["tasks"][0]["type"] == JYTHON_TASK_TYPE
    assert 'print "Release:"' in original["phases"][0]["tasks"][0]["script"]


@pytest.mark.unit
def test_script_task_with_missing_script_is_skipped():
    template = {"type": JYTHON_TASK_TYPE, "title": "no script here"}
    result = migrate_template_object(template)
    assert result.tasks_converted == 0
    assert not result.changed
