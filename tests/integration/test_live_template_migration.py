"""Live end-to-end test for **template-as-code YAML** migration.

Sibling to ``test_live_migration.py``. Where that test migrates a standalone ``.py``
script, this one starts from a Release *YAML: Template as code* export
(``examples/templates/jython_template.yaml``), migrates it with the real
:func:`~jython2py3.yaml_migrate.migrate_yaml`, extracts the Python 3 script from the
converted ``containerPython.PythonTask``, and **runs that script** on a live
Digital.ai Release server. It proves the YAML conversion produces a task whose script
has no migration *or* runtime issues.

The suite self-skips when the Release server is not reachable (the session-scoped
``client`` fixture in conftest.py) or the ``[integration]`` extra is not installed, so
a normal offline ``pytest`` run still passes.

See ``test_live_migration.py`` and ``tests/integration/server.py`` for the shared
configuration and the Run-as user the container task calls back as.
"""

import ast
import os
from pathlib import Path

import pytest

# The Release API client is an optional ([integration]) dependency; skip the whole
# module at collection time when it is absent so a plain offline `pytest` still passes.
pytest.importorskip(
    "com.xebialabs.xlrelease.release_api_client",
    reason="Release API client not installed; install .[integration] to run the live test",
)

from ruamel.yaml import YAML  # noqa: E402

from jython2py3.yaml_migrate import (  # noqa: E402
    JYTHON_TASK_TYPE,
    PYTHON3_TASK_TYPE,
    migrate_yaml,
)
from tests.integration.server import run_python_script_task  # noqa: E402

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
JYTHON_TEMPLATE = _ROOT / "examples" / "templates" / "jython_template.yaml"

RELEASE_TITLE = "jython2py3-live-template-test"
PHASE_TITLE = "Run Migrated Template Task"
TASK_TITLE = "Run migrated template script"
WAIT_TIMEOUT = float(os.environ.get("RELEASE_TIMEOUT", "240"))


def _first_task_script(migrated_yaml: str) -> str:
    """Extract the converted Python 3 task's script from the migrated template YAML."""
    data = YAML().load(migrated_yaml)
    task = data["spec"][0]["phases"][0]["tasks"][0]
    assert task["type"] == PYTHON3_TASK_TYPE, (
        f"expected the task type to be swapped to {PYTHON3_TASK_TYPE}, got {task['type']}")
    return str(task["script"])


def test_migrated_template_task_runs_end_to_end(
    release_api, template_api, phase_api, task_api
):
    """Migrate the template YAML, then run its converted Python 3 task on a live server.

    Two layers of verification:
      1. Migration: exactly one ``xlrelease.ScriptTask`` is converted to a
         ``containerPython.PythonTask``, with no leftover ``# TODO`` / ``# ERROR``
         markers, and the extracted script is valid Python 3.
      2. Runtime: that extracted script runs to COMPLETED in a container task, proving
         the YAML-migrated task works end to end (the rewritten getCurrent* /
         get*/setReleaseVariable helpers and the releaseApi call back into the server).
    """
    # --- 1. Migrate the template YAML and confirm a clean conversion.
    result = migrate_yaml(JYTHON_TEMPLATE.read_text(encoding="utf-8"))
    assert result.changed, "expected the template task to be converted"
    assert result.tasks_converted == 1, (
        f"expected exactly one task converted, got {result.tasks_converted}")
    assert JYTHON_TASK_TYPE not in result.migrated
    assert not result.todos, f"converted task still has TODOs to resolve: {result.todos}"
    assert not result.errors, f"converted task still has errors to fix: {result.errors}"

    script = _first_task_script(result.migrated)
    ast.parse(script)  # the extracted script must be valid Python 3

    # --- 2. Run the extracted script as a live container task and verify it completes.
    run = run_python_script_task(
        template_api=template_api,
        phase_api=phase_api,
        task_api=task_api,
        release_api=release_api,
        script=script,
        release_title=RELEASE_TITLE,
        phase_title=PHASE_TITLE,
        task_title=TASK_TITLE,
        timeout=WAIT_TIMEOUT,
    )
    if not run.finished:
        pytest.skip(
            f"Release did not finish within {WAIT_TIMEOUT:.0f}s "
            f"(status={run.release_status}); is a container runner available?")
    assert run.release_status == "COMPLETED", (
        f"Migrated template task failed at runtime; release ended {run.release_status}, "
        f"task status={run.task_status}, comments={run.comments}")
    assert run.task_status == "COMPLETED"
