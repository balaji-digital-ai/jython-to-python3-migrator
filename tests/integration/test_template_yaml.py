"""Golden-file coverage for the bundled template-as-code examples.

Each ``examples/templates/jython/<name>.yaml`` migrates to the committed
``examples/templates/python3/<name>.yaml`` byte for byte (regenerate them with
``jython2py3 migrate examples/templates/jython/ -o examples/templates/python3/``).

The migrator must convert **only** ``xlrelease.ScriptTask`` tasks - swapping the type
to ``containerPython.PythonTask`` and migrating the embedded script - and leave every
other task untouched: manual/gate/notification tasks, tasks that are *already*
``containerPython.PythonTask``, the group wrappers, and non-script fields such as a
task ``description`` (even when it contains Python-2-looking prose).
"""
import re
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from jython2py3.cli import main
from jython2py3.yaml_migrate import (
    JYTHON_TASK_TYPE,
    PYTHON3_TASK_TYPE,
    migrate_yaml,
)

_ROOT = Path(__file__).resolve().parents[2]
JYTHON_DIR = _ROOT / "examples" / "templates" / "jython"
PYTHON3_DIR = _ROOT / "examples" / "templates" / "python3"

# name -> number of `xlrelease.ScriptTask` tasks the template should convert.
EXPECTED = {
    "01_mixed_task_types.yaml": 1,   # one script task beside manual/gate/python tasks
    "02_release_pipeline.yaml": 2,   # a script task in each of two phases
    "03_nested_tasks.yaml": 2,       # a nested (grouped) script task + a top-level one
}

TEMPLATES = sorted(p.name for p in JYTHON_DIR.glob("*.yaml"))


def _other_task_types(source: str) -> set[str]:
    """Every ``type:`` value in the document except the script/python task types -
    i.e. the tasks (and conditions) the migrator must leave completely alone."""
    types = set(re.findall(r"type:\s*(\S+)", source))
    types.discard(JYTHON_TASK_TYPE)
    types.discard(PYTHON3_TASK_TYPE)
    return types


@pytest.mark.integration
def test_every_template_has_a_golden_and_expectation():
    # Guard against adding a template but forgetting its golden / expected count.
    assert set(TEMPLATES) == set(EXPECTED), "templates and EXPECTED are out of sync"
    for name in TEMPLATES:
        assert (PYTHON3_DIR / name).exists(), f"missing golden for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", TEMPLATES)
def test_template_matches_committed_golden(name):
    migrated = migrate_yaml((JYTHON_DIR / name).read_text(encoding="utf-8"))
    golden = (PYTHON3_DIR / name).read_text(encoding="utf-8")
    assert migrated.migrated == golden


@pytest.mark.integration
@pytest.mark.parametrize("name", TEMPLATES)
def test_golden_is_valid_yaml(name):
    YAML().load((PYTHON3_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.parametrize("name, converted", EXPECTED.items())
def test_only_script_tasks_convert(name, converted):
    source = (JYTHON_DIR / name).read_text(encoding="utf-8")
    result = migrate_yaml(source)

    # Exactly the `xlrelease.ScriptTask` tasks were converted, and none remain.
    assert result.tasks_converted == converted
    assert source.count(f"type: {JYTHON_TASK_TYPE}") == converted
    assert JYTHON_TASK_TYPE not in result.migrated

    # Every other task/condition type is preserved with the same count - the migrator
    # touched nothing but the script tasks.
    for other_type in _other_task_types(source):
        assert source.count(f"type: {other_type}") \
            == result.migrated.count(f"type: {other_type}"), other_type


@pytest.mark.integration
def test_non_script_content_is_not_migrated():
    # The manual task's description in 01 holds Python-2 `print "..."` *prose*. Because
    # the task is not a ScriptTask, the migrator must leave it byte-for-byte: it must
    # NOT be rewritten to `print(...)`.
    result = migrate_yaml((JYTHON_DIR / "01_mixed_task_types.yaml").read_text("utf-8"))
    assert 'print "this is not migrated"' in result.migrated
    assert 'print("this is not migrated")' not in result.migrated
    # The task that was already a containerPython.PythonTask is left exactly as-is.
    assert 'print("already migrated")' in result.migrated


@pytest.mark.integration
def test_nested_script_task_is_converted():
    # A ScriptTask nested inside a ParallelGroup is found by the structural walk.
    result = migrate_yaml((JYTHON_DIR / "03_nested_tasks.yaml").read_text("utf-8"))
    data = YAML().load(result.migrated)
    group = data["spec"][0]["phases"][0]["tasks"][0]
    assert group["type"] == "xlrelease.ParallelGroup"  # the wrapper is untouched
    nested = group["tasks"][0]
    assert nested["type"] == PYTHON3_TASK_TYPE
    assert "getCurrentRelease()" in nested["script"]


@pytest.mark.integration
def test_cli_converts_template_directory(tmp_path):
    out = tmp_path / "python3"
    code = main(["migrate", str(JYTHON_DIR), "-o", str(out)])
    assert code == 0
    for name in TEMPLATES:
        assert (out / name).read_text("utf-8") == (PYTHON3_DIR / name).read_text("utf-8")
