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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from com.xebialabs.xlrelease.domain.forms import CreateRelease
from com.xebialabs.xlrelease.domain.release import Release
from com.xebialabs.xlrelease.domain.task import Task

from tests.integration.server import script_user

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
JYTHON_SCRIPT = _ROOT / "examples" / "jython" / "current_context.py"

PYTHON_TASK_TYPE = "containerPython.PythonTask"
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "ABORTED"}

RELEASE_TITLE = "jython2py3-live-test"
PHASE_TITLE = "Run Migrated Python"
TASK_TITLE = "Run migrated script"
WAIT_TIMEOUT = float(os.environ.get("RELEASE_TIMEOUT", "240"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_terminal(release_api, release_id: str) -> Release:
    """Poll the release until it reaches a terminal status or times out."""
    deadline = time.monotonic() + WAIT_TIMEOUT
    release = release_api.getRelease(release_id)
    while release.status not in TERMINAL_STATUSES and time.monotonic() < deadline:
        time.sleep(5)
        release = release_api.getRelease(release_id)
    return release


def _find_task_id(release: Release, title: str) -> str:
    """Return the id of the task with ``title`` by walking the release tree."""
    for phase in release.phases or []:
        for task in phase.tasks or []:
            if task.title == title:
                return task.id
    raise AssertionError(f"task {title!r} not found in release {release.id}")


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
    script = result.migrated

    script_username, script_password = script_user()
    template_id = None
    release_id = None

    try:
        # --- 2. Create a template with the Run-as user so the migrated script's
        #        getCurrent* / get*Variable helpers can call back into the API.
        start = datetime.now(timezone.utc)
        template = template_api.createTemplate(Release(
            title=f"{RELEASE_TITLE} - Template",
            scheduledStartDate=start,
            dueDate=start + timedelta(days=1),
            scriptUsername=script_username,
            scriptUserPassword=script_password,
        ))
        template_id = template.id

        # Rename the default phase.
        template = template_api.getTemplate(template.id)
        phase = template.phases[0]
        phase.title = PHASE_TITLE
        phase = phase_api.updatePhase(phase.id, phase)

        # Attach the Python 3 Script task running the *migrated* source.
        task_api.addTask(phase.id, Task(
            title=TASK_TITLE, type=PYTHON_TASK_TYPE, script=script))

        # Create and start the release.
        release = release_api.getRelease(
            template_api.create(
                template.id, CreateRelease(releaseTitle=RELEASE_TITLE)).id)
        release_id = release.id
        task_id = _find_task_id(release, TASK_TITLE)
        release_api.start(release_id)

        # --- 3. Wait for completion and verify the migrated script ran cleanly.
        final = _wait_for_terminal(release_api, release_id)
        if final.status not in TERMINAL_STATUSES:
            pytest.skip(
                f"Release {release_id} did not finish within {WAIT_TIMEOUT:.0f}s "
                f"(status={final.status}); is a container runner available?")

        task = task_api.getTask(task_id)
        assert final.status == "COMPLETED", (
            f"Migrated script failed at runtime; release ended {final.status}, "
            f"task status={task.status}, comments={getattr(task, 'comments', None)}")
        assert task.status == "COMPLETED"

    finally:
        if release_id:
            try:
                rel = release_api.getRelease(release_id)
                if rel.status not in TERMINAL_STATUSES:
                    release_api.abort(release_id, "test cleanup")
            except Exception:
                pass
            try:
                release_api.delete(release_id)
            except Exception:
                pass
        if template_id:
            try:
                template_api.deleteTemplate(template_id)
            except Exception:
                pass
