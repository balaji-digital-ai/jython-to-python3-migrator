"""Stock fissix Python 2 -> 3 fixers wired through the engine (guide section 10)."""
import pytest


@pytest.mark.unit
def test_print_statement(migrate):
    result = migrate('print "Hello", name\n')
    assert result.migrated == 'print("Hello", name)\n'


@pytest.mark.unit
def test_except_clause(migrate):
    result = migrate("try:\n    pass\nexcept Exception, e:\n    pass\n")
    assert "except Exception as e:" in result.migrated


@pytest.mark.unit
def test_dict_iteritems(migrate):
    result = migrate("for k, v in d.iteritems():\n    pass\n")
    assert "d.items()" in result.migrated
    assert "iteritems" not in result.migrated


@pytest.mark.unit
def test_has_key(migrate):
    result = migrate('d.has_key("k")\n')
    assert '"k" in d' in result.migrated


@pytest.mark.unit
def test_xrange(migrate):
    result = migrate("for i in xrange(10):\n    pass\n")
    assert "range(10)" in result.migrated
    assert "xrange" not in result.migrated


@pytest.mark.unit
def test_already_python3_is_untouched(migrate):
    # Genuinely inert Python 3 (no constructs any fixer rewrites). Note: a multi-arg
    # print() is intentionally avoided - under assumed-Py2 input it reads as printing
    # a tuple, which fix_print correctly rewraps.
    source = "x = 1\nvalues = [i * 2 for i in range(3)]\ntotal = sum(values) + x\n"
    result = migrate(source)
    assert not result.changed


@pytest.mark.unit
def test_dict_view_wrapped_in_list_for_safety(migrate):
    # Stock fix_dict preserves Python 2 list semantics by wrapping views in list().
    result = migrate("items = d.items()\n")
    assert "list(d.items())" in result.migrated
