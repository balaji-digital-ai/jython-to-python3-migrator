"""Tier 1: Java import removal (guide section 11)."""
import pytest


@pytest.mark.unit
def test_from_java_import_removed(migrate):
    result = migrate("from java.util import Date\n")
    assert result.todo_count == 1
    # no executable code line survives - only the breadcrumb comment
    code_lines = [
        ln for ln in result.migrated.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    assert code_lines == []
    # the original import text is quoted inside the breadcrumb
    assert "from java.util import Date" in result.migrated


@pytest.mark.unit
def test_plain_import_java_removed(migrate):
    result = migrate("import java.io\n")
    # the executable import is gone; only the breadcrumb comment remains
    lines = [ln for ln in result.migrated.splitlines() if not ln.lstrip().startswith("#")]
    assert all("import java.io" not in ln for ln in lines)


@pytest.mark.unit
def test_javax_import_removed(migrate):
    result = migrate("from javax.crypto import Cipher\n")
    assert result.todo_count == 1


@pytest.mark.unit
def test_non_java_import_untouched(migrate):
    result = migrate("from datetime import datetime\nimport os\n")
    assert "from datetime import datetime" in result.migrated
    assert "import os" in result.migrated
    assert result.todo_count == 0
