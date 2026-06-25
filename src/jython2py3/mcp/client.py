"""A small synchronous client for the Digital.ai Release MCP server (HTTP transport).

The official Release MCP server (Docker image ``xebialabs/dai-release-mcp``) speaks the
Model Context Protocol. When started in ``streamable-http`` (or ``sse``) mode it
listens on an HTTP endpoint - e.g. ``http://localhost:8000/mcp`` - and exposes Release
operations as MCP *tools* (``list_templates``, ``get_template``, ``create_template``,
...). This client connects to that endpoint and calls those tools.

Design notes
------------
* The ``mcp`` Python SDK is an **optional** dependency (the ``mcp`` extra). It is
  imported lazily inside the methods that need it, so importing this module - or
  running the offline test suite - never requires it. A missing SDK raises a clear,
  actionable error only when you actually try to connect.
* The MCP SDK is ``async``; the rest of this CLI is synchronous. Each public method
  therefore runs one connect -> initialize -> call -> close cycle via
  :func:`asyncio.run`, which keeps the surface area synchronous and stateless.
* Tool **results** are normalised: the SDK returns content blocks, from which we
  prefer ``structuredContent`` (structured JSON) and fall back to JSON-decoding the
  first text block. So callers get plain ``dict``/``list`` objects.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

# Default endpoint for a server started with MCP_TRANSPORT=streamable-http on the
# documented MCP_PORT=8000. The "/mcp" path is the SDK's default mount point.
DEFAULT_URL = "http://localhost:8000/mcp"


class ReleaseMCPError(RuntimeError):
    """Raised for any MCP connection / tool-call failure, with a readable message."""


@dataclass
class MCPConfig:
    """Where and how to reach the Release MCP server.

    Values fall back to environment variables so credentials need not appear on the
    command line:

    * ``url``     <- ``RELEASE_MCP_URL``     (default ``http://localhost:8000/mcp``)
    * ``token``   <- ``RELEASE_MCP_TOKEN``   (optional; sent as ``Authorization: Bearer``)
    * ``transport`` <- ``RELEASE_MCP_TRANSPORT`` (``http`` [default] or ``sse``)
    """

    url: str = DEFAULT_URL
    token: str | None = None
    transport: str = "http"  # "http" (streamable-http) or "sse"
    timeout: float = 60.0

    @classmethod
    def from_env(
        cls,
        url: str | None = None,
        token: str | None = None,
        transport: str | None = None,
        timeout: float | None = None,
    ) -> MCPConfig:
        """Build a config from explicit values, falling back to env vars then defaults.

        Explicit arguments (from CLI flags) win over environment variables.
        """
        return cls(
            url=url or os.environ.get("RELEASE_MCP_URL") or DEFAULT_URL,
            token=token or os.environ.get("RELEASE_MCP_TOKEN"),
            transport=(transport or os.environ.get("RELEASE_MCP_TRANSPORT") or "http").lower(),
            timeout=timeout if timeout is not None else 60.0,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


class ReleaseMCPClient:
    """Synchronous facade over the async MCP SDK for the Release MCP server."""

    def __init__(self, config: MCPConfig | None = None) -> None:
        self.config = config or MCPConfig()

    # -- public, synchronous API ------------------------------------------------

    def list_tools(self) -> list[str]:
        """Return the names of every tool the server exposes (useful for discovery)."""
        return self._run(self._list_tools)

    def list_templates(self, **arguments: Any) -> list[dict]:
        """Call the ``list_templates`` tool and return a list of template summaries.

        Any keyword arguments are passed through as the tool's arguments (e.g. a
        folder or title filter, depending on your server version).
        """
        return _as_list(self.call_tool("list_templates", arguments))

    def get_template(self, template_id: str, **arguments: Any) -> dict:
        """Call ``get_template`` and return the full template object as a ``dict``."""
        payload = {"template_id": template_id, **arguments}
        result = self.call_tool("get_template", payload)
        return _as_template(result)

    def create_template(self, template: dict, **arguments: Any) -> Any:
        """Call ``create_template`` to create a new template from ``template``."""
        return self.call_tool("create_template", {"template": template, **arguments})

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an arbitrary MCP tool by name and return its parsed result.

        This is the escape hatch: tool and argument names can vary between Release
        versions, so if a typed wrapper above does not match your server, call the
        tool directly.
        """
        return self._run(lambda session: self._call_tool(session, name, arguments or {}))

    # -- async plumbing ---------------------------------------------------------

    def _run(self, coro_fn: Any) -> Any:
        """Open a session, run ``coro_fn(session)``, and translate SDK errors."""
        try:
            return asyncio.run(self._with_session(coro_fn))
        except ReleaseMCPError:
            raise
        except ImportError as exc:  # the mcp extra is not installed
            raise ReleaseMCPError(
                "The 'mcp' package is required for MCP integration. Install it with "
                "`uv sync --extra mcp` or `pip install \"jython-to-python3-migrator[mcp]\"`."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - present any transport error readably
            raise ReleaseMCPError(
                f"Could not talk to the Release MCP server at {self.config.url}: {exc}"
            ) from exc

    async def _with_session(self, coro_fn: Any) -> Any:
        from mcp import ClientSession

        async with AsyncExitStack() as stack:
            read, write = await self._open_streams(stack)
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            return await coro_fn(session)

    async def _open_streams(self, stack: AsyncExitStack) -> tuple[Any, Any]:
        """Open the configured transport and return its (read, write) streams."""
        headers = self.config.headers
        if self.config.transport == "sse":
            from mcp.client.sse import sse_client

            read, write = await stack.enter_async_context(
                sse_client(self.config.url, headers=headers)
            )
            return read, write
        from mcp.client.streamable_http import streamablehttp_client

        # streamable-http yields a third value (a session-id callback) we don't need.
        read, write, _ = await stack.enter_async_context(
            streamablehttp_client(self.config.url, headers=headers)
        )
        return read, write

    async def _list_tools(self, session: Any) -> list[str]:
        tools = await session.list_tools()
        return [tool.name for tool in tools.tools]

    async def _call_tool(self, session: Any, name: str, arguments: dict[str, Any]) -> Any:
        result = await session.call_tool(name, arguments=arguments)
        return _parse_tool_result(result)


# -- result parsing -------------------------------------------------------------


def _parse_tool_result(result: Any) -> Any:
    """Normalise an SDK ``CallToolResult`` into plain Python data.

    Prefers the structured payload; otherwise JSON-decodes the first text block,
    returning the raw text if it is not JSON. Raises on an error result.
    """
    if getattr(result, "isError", False):
        raise ReleaseMCPError(f"MCP tool returned an error: {_first_text(result) or '(no detail)'}")

    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        # Some servers wrap the value under a single "result"/"data" key.
        if isinstance(structured, dict) and set(structured) <= {"result", "data"}:
            return next(iter(structured.values()))
        return structured

    text = _first_text(result)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _first_text(result: Any) -> str | None:
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            return text
    return None


def _as_list(value: Any) -> list[dict]:
    """Coerce a list-ish tool result into a list of dicts.

    ``list_templates`` may return a bare list or wrap it under a key such as
    ``templates``/``items``/``results``; accept either.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("templates", "items", "results", "data"):
            inner = value.get(key)
            if isinstance(inner, list):
                return inner
        return [value]
    return []


def _as_template(value: Any) -> dict:
    """Coerce a ``get_template`` result into the template ``dict``."""
    if isinstance(value, dict):
        # Unwrap a single ``template``/``data`` envelope if present.
        for key in ("template", "data", "result"):
            inner = value.get(key)
            if isinstance(inner, dict):
                return inner
        return value
    raise ReleaseMCPError(
        f"Expected a template object from get_template, got {type(value).__name__}"
    )
