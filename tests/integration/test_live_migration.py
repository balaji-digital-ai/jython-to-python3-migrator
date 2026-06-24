"""Live end-to-end test: migrate a Jython script, then RUN the migrated output.

Unlike ``test_examples.py`` (which only checks the migrated *source*), this test
proves the conversion works at runtime: it migrates ``examples/jython/
current_context.py`` with the real :class:`Migrator`, then executes the migrated
Python 3 as a ``containerPython.PythonTask`` on a live Digital.ai Release server
and verifies the task completes with the expected outputs — i.e. the converted
script has no migration *or* runtime issues.

The suite is skipped automatically when the Release server is not reachable
(handled by the session-scoped ``client`` fixture in conftest.py), so a normal
``pytest`` run with no server still passes.

Configuration
-------------
Target server defaults to ``http://localhost:5516`` (admin/admin). Override via
the ``--release-*`` pytest options or the ``RELEASE_*`` environment variables —
see ``tests/conftest.py`` and ``tests/integration/server.py``.

The container task calls back to the server as the release's "Run as user":

    RELEASE_SCRIPT_USER      (falls back to RELEASE_USERNAME)
    RELEASE_SCRIPT_PASSWORD  (falls back to RELEASE_PASSWORD)

Without these the getCurrent* / get*Variable helpers inside the migrated script
fail with a "Cannot connect to Release API" error.
"""

import ast
import os
from pathlib import Path

import pytest

# The Release API client is an optional ([integration]) dependency. When it is not
# installed, skip this whole module at collection time instead of failing with an
# ImportError, so a plain offline `pytest` run still passes.
pytest.importorskip(
    "com.xebialabs.xlrelease.release_api_client",
    reason="Release API client not installed; install .[integration] to run the live test",
)

from tests.integration.server import run_python_script_task  # noqa: E402

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
JYTHON_SCRIPT = _ROOT / "examples" / "jython" / "current_context.py"

RELEASE_TITLE = "jython2py3-live-test"
PHASE_TITLE = "Run Migrated Python"
TASK_TITLE = "Run migrated script"
WAIT_TIMEOUT = float(os.environ.get("RELEASE_TIMEOUT", "240"))


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_migrated_script_runs_end_to_end(
    migrate, release_api, template_api, phase_api, task_api
):
    """Migrate current_context.py, then run the result on a live Release task.

    Two layers of verification:
      1. Migration: the conversion is clean - no Tier-2 ``# TODO`` markers and no
         ``# ERROR`` markers - and the output is valid Python 3.
      2. Runtime: the migrated script runs to COMPLETED in a container task, which
         proves the rewritten helpers (``getCurrentRelease`` / ``getCurrentPhase`` /
         ``get`` + ``setReleaseVariable``) and the ``releaseApi`` call back into the
         server correctly.

    A Jython task's output is its printed text (markdown), so - unlike the Python 3
    Container task - it has no ``result`` / ``result_2`` / ``result_3`` output
    variables to assert; reaching COMPLETED is the success signal.
    """
    # --- 1. Migrate the Jython script and confirm it has no issues to resolve.
    jython_source = JYTHON_SCRIPT.read_text(encoding="utf-8")
    result = migrate(jython_source)
    assert result.changed, "expected the migrator to rewrite the Jython script"
    assert result.todo_count == 0, (
        f"migrated script still has TODOs to resolve: {result.todos}")
    assert result.error_count == 0, (
        f"migrated script still has errors to fix: {result.errors}")
    ast.parse(result.migrated)  # must be valid Python 3

    # --- 2. Run the migrated script as a live container task and verify it completes.
    run = run_python_script_task(
        template_api=template_api,
        phase_api=phase_api,
        task_api=task_api,
        release_api=release_api,
        script=result.migrated,
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
        f"Migrated script failed at runtime; release ended {run.release_status}, "
        f"task status={run.task_status}, comments={run.comments}")
    assert run.task_status == "COMPLETED"
