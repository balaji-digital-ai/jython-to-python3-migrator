"""Connection settings and client factory for the live-server integration test.

The live test migrates a Jython script and then runs the migrated Python 3
output as a container task on a real Digital.ai Release server, to prove the
converted script actually executes (no runtime issues).

By default it targets the local Release server at ``http://localhost:5516``
with credentials ``admin`` / ``admin``. Settings can be overridden from the
pytest command line (see ``tests/conftest.py``) or via environment variables:

* ``RELEASE_URL``
* ``RELEASE_USERNAME``
* ``RELEASE_PASSWORD``
* ``RELEASE_TOKEN`` (personal access token; takes precedence over user/password)

The task's "Run as user" credentials are read separately:

* ``RELEASE_SCRIPT_USER``      (falls back to ``RELEASE_USERNAME``)
* ``RELEASE_SCRIPT_PASSWORD``  (falls back to ``RELEASE_PASSWORD``)
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from com.xebialabs.xlrelease.release_api_client import ReleaseAPIClient

DEFAULT_URL = "http://localhost:5516"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

# The migrated task type, and the release statuses that mean "done" (success or not).
PYTHON_TASK_TYPE = "containerPython.PythonTask"
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "ABORTED"}


@dataclass
class ServerConfig:
    """Resolved connection settings for the integration suite."""

    url: str = DEFAULT_URL
    username: str | None = DEFAULT_USERNAME
    password: str | None = DEFAULT_PASSWORD
    token: str | None = None


config = ServerConfig(
    url=os.environ.get("RELEASE_URL", DEFAULT_URL),
    username=os.environ.get("RELEASE_USERNAME", DEFAULT_USERNAME),
    password=os.environ.get("RELEASE_PASSWORD", DEFAULT_PASSWORD),
    token=os.environ.get("RELEASE_TOKEN") or None,
)


def make_client() -> ReleaseAPIClient:
    """Build a ``ReleaseAPIClient`` from the currently resolved settings."""
    if config.token:
        return ReleaseAPIClient(config.url, personal_access_token=config.token)
    return ReleaseAPIClient(config.url, config.username, config.password)


def script_user() -> tuple[str, str]:
    """Return the (username, password) used as the release's Run-as user.

    Falls back to the primary credentials when the script-specific env vars are
    not set. Without these the migrated script's getCurrent* / get*Variable
    helpers cannot call back into the Release API.
    """
    user = os.environ.get("RELEASE_SCRIPT_USER", config.username or DEFAULT_USERNAME)
    password = os.environ.get("RELEASE_SCRIPT_PASSWORD", config.password or DEFAULT_PASSWORD)
    return user, password


@dataclass
class TaskRunResult:
    """Outcome of running a migrated script as a live container task."""

    release_status: str
    task_status: str | None
    comments: object | None
    finished: bool  # reached a terminal status within the timeout


def _wait_for_terminal(release_api, release_id: str, timeout: float):
    """Poll the release until it reaches a terminal status or ``timeout`` elapses."""
    import time

    deadline = time.monotonic() + timeout
    release = release_api.getRelease(release_id)
    while release.status not in TERMINAL_STATUSES and time.monotonic() < deadline:
        time.sleep(5)
        release = release_api.getRelease(release_id)
    return release


def _find_task_id(release, title: str) -> str:
    """Return the id of the task with ``title`` by walking the release tree."""
    for phase in release.phases or []:
        for task in phase.tasks or []:
            if task.title == title:
                return task.id
    raise AssertionError(f"task {title!r} not found in release {release.id}")


def run_python_script_task(
    *,
    template_api,
    phase_api,
    task_api,
    release_api,
    script: str,
    release_title: str,
    phase_title: str,
    task_title: str,
    timeout: float,
) -> TaskRunResult:
    """Run ``script`` as a live ``containerPython.PythonTask`` and report the outcome.

    Creates a template with the Run-as user (so the script's getCurrent* /
    get*Variable helpers can call back into the API), attaches one Python 3 Script
    task running ``script``, starts the release, waits for a terminal status, and
    returns a :class:`TaskRunResult`. The template and release are always cleaned up
    before returning, even on failure.

    This is the shared engine behind both live tests (a standalone ``.py`` script and
    a script extracted from a migrated template YAML), so they execute identically.
    """
    from com.xebialabs.xlrelease.domain.forms import CreateRelease
    from com.xebialabs.xlrelease.domain.release import Release
    from com.xebialabs.xlrelease.domain.task import Task

    script_username, script_password = script_user()
    template_id = None
    release_id = None
    try:
        start = datetime.now(timezone.utc)
        template = template_api.createTemplate(Release(
            title=f"{release_title} - Template",
            scheduledStartDate=start,
            dueDate=start + timedelta(days=1),
            scriptUsername=script_username,
            scriptUserPassword=script_password,
        ))
        template_id = template.id

        # Rename the default phase, then attach the Python 3 Script task.
        template = template_api.getTemplate(template.id)
        phase = template.phases[0]
        phase.title = phase_title
        phase = phase_api.updatePhase(phase.id, phase)
        task_api.addTask(phase.id, Task(
            title=task_title, type=PYTHON_TASK_TYPE, script=script))

        # Create a release from the template and start it.
        release = release_api.getRelease(
            template_api.create(
                template.id, CreateRelease(releaseTitle=release_title)).id)
        release_id = release.id
        task_id = _find_task_id(release, task_title)
        release_api.start(release_id)

        final = _wait_for_terminal(release_api, release_id, timeout)
        finished = final.status in TERMINAL_STATUSES
        task = task_api.getTask(task_id) if finished else None
        return TaskRunResult(
            release_status=final.status,
            task_status=getattr(task, "status", None),
            comments=getattr(task, "comments", None),
            finished=finished,
        )
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
