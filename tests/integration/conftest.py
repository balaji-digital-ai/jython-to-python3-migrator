"""Fixtures for the live-server integration test.

Provides a session-scoped :class:`ReleaseAPIClient` (skipping the live test when
the Release server cannot be reached) and one session-scoped API fixture per
wrapper the live test uses.

These fixtures are only needed by ``test_live_migration.py``. The Release API
client is imported lazily *inside* each fixture (never at module import time) so
that collecting this directory's offline tests (``test_example_goldens.py``,
``test_examples.py``) does not require the ``[integration]`` extra to be
installed. A plain ``pytest`` run therefore still passes with only ``[dev]``.
"""

import pytest


@pytest.fixture(scope="session")
def client():
    """A Release API client for the whole test session.

    Skips the live integration test when the Release API client is not installed
    or the Release server is not reachable, so the offline migration tests still
    pass with no server (and no client) present.
    """
    try:
        from com.xebialabs.xlrelease.api.v1.settings_api import SettingsApi

        from tests.integration.server import make_client
    except ImportError as exc:
        pytest.skip(f"Release API client not installed ({exc}); install .[integration]")

    c = make_client()
    try:
        SettingsApi(c).getInstanceInformation()
    except Exception as exc:
        pytest.skip(f"Release server not reachable: {exc}")
    yield c
    c.close()


@pytest.fixture(scope="session")
def settings_api(client):
    from com.xebialabs.xlrelease.api.v1.settings_api import SettingsApi

    return SettingsApi(client)


@pytest.fixture(scope="session")
def release_api(client):
    from com.xebialabs.xlrelease.api.v1.release_api import ReleaseApi

    return ReleaseApi(client)


@pytest.fixture(scope="session")
def phase_api(client):
    from com.xebialabs.xlrelease.api.v1.phase_api import PhaseApi

    return PhaseApi(client)


@pytest.fixture(scope="session")
def task_api(client):
    from com.xebialabs.xlrelease.api.v1.task_api import TaskApi

    return TaskApi(client)


@pytest.fixture(scope="session")
def template_api(client):
    from com.xebialabs.xlrelease.api.v1.template_api import TemplateApi

    return TemplateApi(client)


@pytest.fixture(scope="session")
def server_version(settings_api):
    info = settings_api.getInstanceInformation()
    return info.get("version")
