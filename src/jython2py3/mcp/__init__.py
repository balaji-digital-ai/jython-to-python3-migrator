"""MCP integration for the Jython -> Python 3 migrator.

This subpackage lets the migrator pull Release **templates** straight from a running
Digital.ai Release instance through the official
`Release MCP server <https://hub.docker.com/r/xebialabs/dai-release-mcp>`_, convert
the Jython script tasks they contain, and (optionally) push the converted copy back.

Two pieces, kept apart on purpose:

* :mod:`jython2py3.mcp.migrate` - pure, offline conversion of a template *object*
  (a JSON-decoded ``dict``). No network, no extra dependencies; fully unit-tested.
* :mod:`jython2py3.mcp.client` - the thin MCP client that talks HTTP to the server.
  It imports the optional ``mcp`` SDK lazily, so the rest of the package (and its
  test suite) keeps working with no MCP dependency installed.

Install the client dependency with the ``mcp`` extra::

    uv sync --extra mcp        # or:  pip install ".[mcp]"
"""
from __future__ import annotations

from .migrate import TemplateMigrationResult, migrate_template_object

__all__ = ["TemplateMigrationResult", "migrate_template_object"]
