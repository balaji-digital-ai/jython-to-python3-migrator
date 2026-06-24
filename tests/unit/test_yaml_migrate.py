"""Unit tests for the template-as-code YAML migrator (jython2py3.yaml_migrate)."""
import pytest

from jython2py3.yaml_migrate import (
    JYTHON_TASK_TYPE,
    PYTHON3_TASK_TYPE,
    migrate_yaml,
)

# A minimal "Template as code" export with a single Jython script task.
TEMPLATE = """\
apiVersion: xl-release/v1
kind: Templates
metadata:
  home: Test
spec:
- template: two
  phases:
  - phase: New Phase
    tasks:
    - name: New task
      type: xlrelease.ScriptTask
      script: |-
        print "Release:", release.title
        releaseVariables["migratedBy"] = "jython2py3"
  scriptUsername: admin
  scriptUserPassword: !value "xlrelease_Release_two_scriptUserPassword"
"""


@pytest.mark.unit
def test_task_type_is_swapped():
    result = migrate_yaml(TEMPLATE)
    assert result.tasks_converted == 1
    assert f"type: {PYTHON3_TASK_TYPE}" in result.migrated
    assert f"type: {JYTHON_TASK_TYPE}" not in result.migrated


@pytest.mark.unit
def test_script_body_is_migrated():
    result = migrate_yaml(TEMPLATE)
    assert "release = getCurrentRelease()" in result.migrated
    assert 'print("Release:", release.title)' in result.migrated
    assert 'setReleaseVariable("migratedBy", "jython2py3")' in result.migrated


@pytest.mark.unit
def test_block_scalar_style_preserved():
    # The script stays a literal block scalar (`|-`), not a folded or quoted string.
    result = migrate_yaml(TEMPLATE)
    assert "script: |-" in result.migrated


@pytest.mark.unit
def test_value_tag_and_other_keys_preserved():
    result = migrate_yaml(TEMPLATE)
    # The secret reference (a custom `!value` tag) and surrounding keys are untouched.
    assert 'scriptUserPassword: !value "xlrelease_Release_two_scriptUserPassword"' \
        in result.migrated
    assert "scriptUsername: admin" in result.migrated
    assert "home: Test" in result.migrated


@pytest.mark.unit
def test_non_script_tasks_are_untouched():
    template = """\
spec:
- template: t
  phases:
  - phase: P
    tasks:
    - name: Manual
      type: xlrelease.Task
    - name: Gate
      type: xlrelease.GateTask
"""
    result = migrate_yaml(template)
    assert result.tasks_converted == 0
    assert not result.changed
    assert result.migrated == template


@pytest.mark.unit
def test_multiple_and_nested_script_tasks_all_convert():
    template = """\
spec:
- template: t
  phases:
  - phase: P
    tasks:
    - name: First
      type: xlrelease.ScriptTask
      script: |-
        print "one"
    - name: Group
      type: xlrelease.ParallelGroup
      tasks:
      - name: Nested
        type: xlrelease.ScriptTask
        script: |-
          print "two"
"""
    result = migrate_yaml(template)
    assert result.tasks_converted == 2
    assert f"type: {JYTHON_TASK_TYPE}" not in result.migrated
    assert 'print("one")' in result.migrated
    assert 'print("two")' in result.migrated


@pytest.mark.unit
def test_todos_and_errors_are_aggregated():
    template = """\
spec:
- template: t
  phases:
  - phase: P
    tasks:
    - name: Java
      type: xlrelease.ScriptTask
      script: |-
        from java.util import Date
        now = Date()
"""
    result = migrate_yaml(template)
    assert result.tasks_converted == 1
    assert result.errors  # Date() is flagged as a Java-usage ERROR
    assert any("Date" in err for err in result.errors)
