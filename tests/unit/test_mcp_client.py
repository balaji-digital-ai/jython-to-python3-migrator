"""Unit tests for the MCP client's result-parsing helpers and config.

These cover the pure, synchronous parts of jython2py3.mcp.client - no network and no
`mcp` SDK required. The async transport is exercised end-to-end only via the CLI test
with a fake client (test_mcp_cli.py).
"""
import pytest

from jython2py3.mcp.client import (
    DEFAULT_URL,
    MCPConfig,
    ReleaseMCPError,
    _as_list,
    _as_template,
    _parse_tool_result,
)


class _Block:
    """Stand-in for an SDK TextContent block."""

    def __init__(self, text):
        self.text = text


class _Result:
    """Stand-in for an SDK CallToolResult."""

    def __init__(self, content=None, structuredContent=None, isError=False):
        self.content = content or []
        self.structuredContent = structuredContent
        self.isError = isError


@pytest.mark.unit
def test_parse_prefers_structured_content():
    result = _Result(structuredContent={"id": "R1", "title": "Deploy"})
    assert _parse_tool_result(result) == {"id": "R1", "title": "Deploy"}


@pytest.mark.unit
def test_parse_unwraps_single_result_envelope():
    result = _Result(structuredContent={"result": [{"id": "R1"}]})
    assert _parse_tool_result(result) == [{"id": "R1"}]


@pytest.mark.unit
def test_parse_decodes_json_text_block():
    result = _Result(content=[_Block('{"id": "R1"}')])
    assert _parse_tool_result(result) == {"id": "R1"}


@pytest.mark.unit
def test_parse_returns_raw_text_when_not_json():
    result = _Result(content=[_Block("plain text")])
    assert _parse_tool_result(result) == "plain text"


@pytest.mark.unit
def test_parse_raises_on_error_result():
    result = _Result(content=[_Block("boom")], isError=True)
    with pytest.raises(ReleaseMCPError, match="boom"):
        _parse_tool_result(result)


@pytest.mark.unit
@pytest.mark.parametrize("key", ["templates", "items", "results", "data"])
def test_as_list_unwraps_known_keys(key):
    assert _as_list({key: [{"id": "R1"}]}) == [{"id": "R1"}]


@pytest.mark.unit
def test_as_list_passes_through_bare_list():
    assert _as_list([{"id": "R1"}]) == [{"id": "R1"}]


@pytest.mark.unit
def test_as_template_unwraps_envelope():
    assert _as_template({"template": {"id": "R1"}}) == {"id": "R1"}


@pytest.mark.unit
def test_as_template_rejects_non_dict():
    with pytest.raises(ReleaseMCPError):
        _as_template(["not", "a", "template"])


@pytest.mark.unit
def test_config_from_env_defaults(monkeypatch):
    for var in ("RELEASE_MCP_URL", "RELEASE_MCP_TOKEN", "RELEASE_MCP_TRANSPORT"):
        monkeypatch.delenv(var, raising=False)
    config = MCPConfig.from_env()
    assert config.url == DEFAULT_URL
    assert config.token is None
    assert config.transport == "http"
    assert config.headers == {}


@pytest.mark.unit
def test_config_explicit_beats_env(monkeypatch):
    monkeypatch.setenv("RELEASE_MCP_URL", "http://env:8000/mcp")
    config = MCPConfig.from_env(url="http://flag:9000/mcp", token="t0ken")
    assert config.url == "http://flag:9000/mcp"
    assert config.headers == {"Authorization": "Bearer t0ken"}
