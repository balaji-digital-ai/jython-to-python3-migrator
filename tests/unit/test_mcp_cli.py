"""CLI behaviour for the `mcp` command group, driven by a fake MCP client.

We monkeypatch jython2py3.cli._build_client so nothing connects to a real server -
the focus is the CLI wiring (listing, migrate-to-file, --push, --report), not the
transport, which is parsing-tested in test_mcp_client.py.
"""
import json

import pytest

from jython2py3._tasks import JYTHON_TASK_TYPE, PYTHON3_TASK_TYPE
from jython2py3.cli import main


def _template() -> dict:
    return {
        "id": "Folder/Release1",
        "title": "Deploy",
        "phases": [
            {
                "title": "Build",
                "tasks": [
                    {
                        "title": "Greet",
                        "type": JYTHON_TASK_TYPE,
                        "script": 'print "hi", release.title\n',
                    }
                ],
            }
        ],
    }


class FakeClient:
    def __init__(self):
        self.created: list[dict] = []

    def list_tools(self):
        return ["get_template", "list_templates", "create_template"]

    def list_templates(self, **_):
        return [{"id": "Folder/Release1", "title": "Deploy"}]

    def get_template(self, template_id, **_):
        assert template_id == "Folder/Release1"
        return _template()

    def create_template(self, template, **_):
        self.created.append(template)
        return {"id": "Folder/Release2", "title": template.get("title")}


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("jython2py3.cli._build_client", lambda args: client)
    return client


@pytest.mark.unit
def test_mcp_list_templates(fake_client, capsys):
    code = main(["mcp", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Folder/Release1" in out
    assert "Deploy" in out


@pytest.mark.unit
def test_mcp_list_tools(fake_client, capsys):
    code = main(["mcp", "list", "--tools"])
    assert code == 0
    out = capsys.readouterr().out
    assert "get_template" in out


@pytest.mark.unit
def test_mcp_migrate_to_file(fake_client, tmp_path, capsys):
    dest = tmp_path / "migrated.json"
    code = main(["mcp", "migrate", "Folder/Release1", "-o", str(dest)])
    assert code == 0

    migrated = json.loads(dest.read_text(encoding="utf-8"))
    task = migrated["phases"][0]["tasks"][0]
    assert task["type"] == PYTHON3_TASK_TYPE
    assert 'print("hi", release.title)' in task["script"]
    # Nothing was pushed without --push.
    assert fake_client.created == []


@pytest.mark.unit
def test_mcp_migrate_stdout(fake_client, capsys):
    code = main(["mcp", "migrate", "Folder/Release1"])
    assert code == 0
    out = capsys.readouterr().out
    assert PYTHON3_TASK_TYPE in out


@pytest.mark.unit
def test_mcp_migrate_push_creates_new_template(fake_client, capsys):
    code = main(["mcp", "migrate", "Folder/Release1", "--push"])
    assert code == 0
    assert len(fake_client.created) == 1
    pushed = fake_client.created[0]
    # A fresh template: original id stripped, title marked, script migrated.
    assert "id" not in pushed
    assert pushed["title"] == "Deploy (migrated to Python 3)"
    assert pushed["phases"][0]["tasks"][0]["type"] == PYTHON3_TASK_TYPE


@pytest.mark.unit
def test_mcp_migrate_push_custom_title(fake_client):
    main(["mcp", "migrate", "Folder/Release1", "--push", "--push-title", "Deploy v2"])
    assert fake_client.created[0]["title"] == "Deploy v2"


@pytest.mark.unit
def test_mcp_migrate_report(fake_client, tmp_path):
    report = tmp_path / "report.json"
    main(["mcp", "migrate", "Folder/Release1", "--report", str(report)])
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["files"][0]["tasks_converted"] == 1
    assert data["tool"] == "jython2py3"
