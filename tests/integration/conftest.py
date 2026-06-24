"""Fixtures for the live-server integration test.

Provides a session-scoped :class:`ReleaseAPIClient` (skipping the live test when
the Release server cannot be reached) and one session-scoped API fixture per
wrapper the live test uses.

These fixtures are only needed by ``test_live_migration.py``; the offline
example-migration tests (``test_examples.py``) do not import them.
"""

import pytest
from com.xebialabs.xlrelease.api.v1.phase_api import PhaseApi
from com.xebialabs.xlrelease.api.v1.release_api import ReleaseApi
from com.xebialabs.xlrelease.api.v1.settings_api import SettingsApi
from com.xebialabs.xlrelease.api.v1.task_api import TaskApi
from com.xebialabs.xlrelease.api.v1.template_api import TemplateApi

from tests.integration.server import make_client


@pytest.fixture(scope="session")
def client():
    """A Release API client for the whole test session.

    Skips the live integration test when the Release server is not reachable, so
    the offline migration tests still pass with no server running.
    """
    c = make_client()
    try:
        SettingsApi(c).getInstanceInformation()
    except Exception as exc:
        pytest.skip(f"Release server not reachable: {exc}")
    yield c
    c.close()


@pytest.fixture(scope="session")
def settings_api(client):
    return SettingsApi(client)


@pytest.fixture(scope="session")
def release_api(client):
    return ReleaseApi(client)


@pytest.fixture(scope="session")
def phase_api(client):
    return PhaseApi(client)


@pytest.fixture(scope="session")
def task_api(client):
    return TaskApi(client)


@pytest.fixture(scope="session")
def template_api(client):
    return TemplateApi(client)


@pytest.fixture(scope="session")
def server_version(settings_api):
    info = settings_api.getInstanceInformation()
    return info.get("version")
