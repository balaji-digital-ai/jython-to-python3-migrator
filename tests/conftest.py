"""Shared pytest fixtures.

The migrator builds a fissix grammar + fixer set, which is mildly expensive, so it
is constructed once per test session and reused.
"""
import pytest

from jython2py3.engine import Migrator


@pytest.fixture(scope="session")
def _migrator() -> Migrator:
    return Migrator()


@pytest.fixture
def migrate(_migrator):
    """Return a function that migrates a source string and returns the result."""
    def _run(source: str):
        return _migrator.migrate(source)

    return _run
