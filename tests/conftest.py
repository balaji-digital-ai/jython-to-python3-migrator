"""Shared pytest fixtures and command-line options.

The migrator builds a fissix grammar + fixer set, which is mildly expensive, so it
is constructed once per test session and reused.

The ``--release-*`` options below point the live-server integration test
(``tests/integration/test_live_migration.py``) at a Release server other than
the local default (http://localhost:5516, admin/admin). They are parsed here so
the offline tests never import the Release API client.
"""
import pytest

from jython2py3.engine import Migrator

# Defaults are duplicated here (rather than imported from tests.integration.server)
# so collecting the offline unit tests never imports the Release API client.
_DEFAULT_URL = "http://localhost:5516"
_DEFAULT_USERNAME = "admin"


def pytest_addoption(parser):
    group = parser.getgroup("release", "Digital.ai Release integration test options")
    group.addoption(
        "--release-url",
        action="store",
        default=None,
        help=f"Base URL of the Release server (default: {_DEFAULT_URL})",
    )
    group.addoption(
        "--release-username",
        action="store",
        default=None,
        help=f"Username for basic authentication (default: {_DEFAULT_USERNAME})",
    )
    group.addoption(
        "--release-password",
        action="store",
        default=None,
        help="Password for basic authentication (default: admin)",
    )
    group.addoption(
        "--release-token",
        action="store",
        default=None,
        help="Personal access token; overrides username/password when provided",
    )


def pytest_configure(config):
    # Apply CLI overrides to the live-server connection settings. Imported lazily
    # so offline runs (and machines without the client installed) are unaffected.
    if not any(
        config.getoption(opt)
        for opt in ("--release-url", "--release-username",
                    "--release-password", "--release-token")
    ):
        return

    from tests.integration import server

    url = config.getoption("--release-url")
    if url:
        server.config.url = url
    username = config.getoption("--release-username")
    if username:
        server.config.username = username
    password = config.getoption("--release-password")
    if password:
        server.config.password = password
    token = config.getoption("--release-token")
    if token:
        server.config.token = token


@pytest.fixture(scope="session")
def _migrator() -> Migrator:
    return Migrator()


@pytest.fixture
def migrate(_migrator):
    """Return a function that migrates a source string and returns the result."""
    def _run(source: str):
        return _migrator.migrate(source)

    return _run
