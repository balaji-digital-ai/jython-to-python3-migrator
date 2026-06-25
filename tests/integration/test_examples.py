"""End-to-end migration of the bundled example script.

Asserts behaviour (key substrings) rather than an exact byte-for-byte match, so the
test is robust to incidental whitespace while still proving every rule fired.
"""
import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = _ROOT / "examples" / "jython" / "09_deploy_pipeline.py"
GOLDEN = _ROOT / "examples" / "python3" / "09_deploy_pipeline.py"


@pytest.fixture
def migrated(migrate):
    return migrate(EXAMPLE.read_text(encoding="utf-8"))


@pytest.mark.integration
def test_matches_committed_golden(migrated):
    # The committed examples/python3/09_deploy_pipeline.py is a golden file: if a rule
    # changes, this fails until it is regenerated (see docs/ADDING_A_RULE.md).
    assert migrated.migrated == GOLDEN.read_text(encoding="utf-8")


@pytest.mark.integration
def test_output_is_valid_python3(migrated):
    # The whole point: the result must parse as Python 3.
    ast.parse(migrated.migrated)


@pytest.mark.integration
def test_syntax_rules_applied(migrated):
    out = migrated.migrated
    assert 'print("Release:", release.title, "status", release.status)' in out
    assert "print(\"active task:\", t.title)" in out


@pytest.mark.integration
def test_variable_rules_applied(migrated):
    out = migrated.migrated
    assert 'getReleaseVariable("buildNumber")' in out
    assert 'setReleaseVariable("artifactPath", "/builds/%s/app.jar" % build)' in out


@pytest.mark.integration
def test_java_import_removed(migrated):
    assert "from java.util import Date" in migrated.migrated  # only in the breadcrumb
    code_lines = [
        ln for ln in migrated.migrated.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    assert all("import java" not in ln for ln in code_lines)


@pytest.mark.integration
def test_reserved_object_injected(migrated):
    # Tier 1: `release` is used but unbound, so the helper call is injected.
    assert "release = getCurrentRelease()" in migrated.migrated


@pytest.mark.integration
def test_tier2_items_flagged(migrated):
    # Only HttpRequest remains Tier 2: its import + its call are flagged (2 TODOs).
    assert migrated.todo_count == 3  # java-import breadcrumb + HttpRequest import + call
    assert any("HttpRequest" in todo for todo in migrated.todos)
