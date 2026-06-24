"""Golden-file coverage for the bundled template-as-code example.

``examples/templates/jython_template.yaml`` migrates to the committed
``examples/templates/python3_template.yaml`` byte for byte (regenerate it with
``jython2py3 migrate examples/templates/jython_template.yaml -o
examples/templates/python3_template.yaml``), and the migrated document must remain
valid YAML with the task type swapped and the script body migrated.
"""
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
JYTHON_TEMPLATE = _ROOT / "examples" / "templates" / "jython_template.yaml"
PYTHON3_TEMPLATE = _ROOT / "examples" / "templates" / "python3_template.yaml"


@pytest.mark.integration
def test_template_matches_committed_golden():
    migrated = migrate_yaml(JYTHON_TEMPLATE.read_text(encoding="utf-8"))
    golden = PYTHON3_TEMPLATE.read_text(encoding="utf-8")
    assert migrated.migrated == golden


@pytest.mark.integration
def test_golden_is_valid_yaml_with_python3_task():
    golden = PYTHON3_TEMPLATE.read_text(encoding="utf-8")
    data = YAML().load(golden)
    task = data["spec"][0]["phases"][0]["tasks"][0]
    assert task["type"] == PYTHON3_TASK_TYPE
    assert JYTHON_TASK_TYPE not in golden
    assert "getCurrentRelease()" in task["script"]


@pytest.mark.integration
def test_cli_converts_template(tmp_path):
    dest = tmp_path / "out.yaml"
    code = main(["migrate", str(JYTHON_TEMPLATE), "-o", str(dest)])
    assert code == 0
    assert dest.read_text(encoding="utf-8") == \
        PYTHON3_TEMPLATE.read_text(encoding="utf-8")
