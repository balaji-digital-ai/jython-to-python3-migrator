"""Tier 2: Java *usage* is flagged as an error (guide section 11).

``fix_java_imports`` drops the import line; this rule flags the places that still
reference the now-undefined Java symbol, because there is no mechanical Python
equivalent to substitute.
"""
import ast

import pytest

from jython2py3 import ERROR_MARKER


@pytest.mark.unit
def test_imported_name_used_is_flagged(migrate):
    result = migrate("from java.util import Date\nnow = Date()\n")
    assert result.error_count == 1
    assert any("Date" in e for e in result.errors)
    # the offending line is left intact (we never silently delete code)
    assert "now = Date()" in result.migrated
    # and it carries an ERROR marker, distinct from a TODO
    assert ERROR_MARKER in result.migrated


@pytest.mark.unit
def test_aliased_import_uses_alias(migrate):
    result = migrate(
        "from java.text import SimpleDateFormat as SDF\nfmt = SDF('yyyy')\n")
    assert result.error_count == 1
    # the flagged symbol is the local alias actually used, not the original
    assert any("`SDF`" in e for e in result.errors)


@pytest.mark.unit
def test_fully_qualified_reference_is_flagged(migrate):
    result = migrate("stamp = java.lang.System.currentTimeMillis()\n")
    assert result.error_count == 1
    assert any("java.lang.System" in e for e in result.errors)


@pytest.mark.unit
def test_multiple_usages_each_flagged(migrate):
    src = (
        "from java.util import Date, Calendar\n"
        "now = Date()\n"
        "cal = Calendar.getInstance()\n"
    )
    result = migrate(src)
    assert result.error_count == 2


@pytest.mark.unit
def test_import_line_itself_is_not_double_flagged(migrate):
    # The import is handled by fix_java_imports (a TODO breadcrumb); the usage rule
    # must not also stamp an ERROR on the import line.
    result = migrate("from java.util import Date\n")  # imported but never used
    assert result.error_count == 0
    assert result.todo_count == 1


@pytest.mark.unit
def test_attribute_named_like_java_symbol_is_safe(migrate):
    # `obj.Date` is a member access on a local object, not the Java class.
    result = migrate("from java.util import Date\nx = obj.Date\n")
    assert result.error_count == 0


@pytest.mark.unit
def test_non_java_code_has_no_errors(migrate):
    result = migrate("from datetime import datetime\nnow = datetime.now()\n")
    assert result.error_count == 0


@pytest.mark.unit
def test_error_inside_indented_block_keeps_valid_indentation(migrate):
    # Annotating the *first* statement of a block must not dedent it: the indentation
    # of that line lives in the preceding INDENT token, not the statement prefix.
    result = migrate("from java.util import Date\nif True:\n    now = Date()\n")
    assert result.error_count == 1
    assert "    now = Date()" in result.migrated  # still indented under the `if`
    ast.parse(result.migrated)  # the whole module must still parse
