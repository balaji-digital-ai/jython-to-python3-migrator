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

from com.xebialabs.xlrelease.release_api_client import ReleaseAPIClient

DEFAULT_URL = "http://localhost:5516"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


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
