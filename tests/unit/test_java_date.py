"""Tier 1: java.util.Date -> datetime (guide section 11).

Unlike other Java classes (flagged as errors by fix_java_usage), Date has a clean
stdlib equivalent, so it is auto-converted. This rule owns the `Date` import line and
every `Date(...)` call; fix_java_imports / fix_java_usage skip Date so the rules stay
disjoint.
"""
import ast

import pytest


@pytest.mark.unit
def test_import_becomes_datetime(migrate):
    result = migrate("from java.util import Date\n")
    assert "import datetime" in result.migrated
    assert result.todo_count == 0  # not dropped with a breadcrumb like other java imports
    assert result.error_count == 0


@pytest.mark.unit
def test_no_arg_date_is_now(migrate):
    result = migrate("from java.util import Date\nnow = Date()\n")
    assert "now = datetime.datetime.now(datetime.timezone.utc)" in result.migrated
    assert result.error_count == 0
    ast.parse(result.migrated)


@pytest.mark.unit
def test_gettime_shift_becomes_timedelta(migrate):
    result = migrate(
        "from java.util import Date\n"
        "due = Date(start.getTime() + 7 * 24 * 60 * 60 * 1000)\n"
    )
    assert (
        "due = start + datetime.timedelta(milliseconds=7 * 24 * 60 * 60 * 1000)"
        in result.migrated
    )
    assert result.error_count == 0
    ast.parse(result.migrated)


@pytest.mark.unit
def test_unrecognised_date_shape_is_flagged(migrate):
    # A constructor shape with no mechanical datetime equivalent is left intact + flagged,
    # never silently emitted as an undefined `Date(...)`.
    result = migrate("from java.util import Date\nd = Date(2024, 0, 1)\n")
    assert result.error_count == 1
    assert "d = Date(2024, 0, 1)" in result.migrated


@pytest.mark.unit
def test_user_defined_date_is_untouched(migrate):
    # `Date` not imported from java.util is not our class; leave it (and add no datetime).
    result = migrate("from mypkg import Date\nx = Date()\n")
    assert "x = Date()" in result.migrated
    assert result.error_count == 0
    assert "datetime" not in result.migrated


@pytest.mark.unit
def test_attribute_named_date_is_untouched(migrate):
    # `obj.Date()` is a method call on a local object, not the java.util.Date constructor.
    result = migrate("from java.util import Date\nx = obj.Date()\n")
    assert "obj.Date()" in result.migrated
    assert result.error_count == 0
