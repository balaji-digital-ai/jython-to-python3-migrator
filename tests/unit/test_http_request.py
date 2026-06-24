"""HttpRequest handling: import removed, call flagged in place (guide section 9)."""
import pytest


@pytest.mark.unit
def test_xlrelease_import_removed(migrate):
    result = migrate("from xlrelease.HttpRequest import HttpRequest\n")
    assert result.todo_count == 1
    # the dead xlrelease import is gone (only the breadcrumb comment remains)
    code_lines = [
        ln for ln in result.migrated.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    assert code_lines == []
    # the original import text is quoted inside the breadcrumb
    assert "from xlrelease.HttpRequest import HttpRequest" in result.migrated


@pytest.mark.unit
def test_httprequest_call_flagged_in_place(migrate):
    source = 'response = HttpRequest({"url": "https://x"}).get("/health")\n'
    result = migrate(source)
    assert result.todo_count == 1
    # original call preserved (not guessed at)
    assert 'response = HttpRequest({"url": "https://x"}).get("/health")' in result.migrated


@pytest.mark.unit
def test_non_xlrelease_import_untouched(migrate):
    result = migrate("import requests\nfrom foo import HttpRequest\n")
    assert "import requests" in result.migrated
    assert "from foo import HttpRequest" in result.migrated
    assert result.todo_count == 0


@pytest.mark.unit
def test_no_httprequest_means_no_flag(migrate):
    result = migrate("import requests\nrequests.get('https://x', timeout=30)\n")
    assert result.todo_count == 0
