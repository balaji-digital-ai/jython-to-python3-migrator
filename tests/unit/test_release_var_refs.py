"""Tier 2 safety net: leftover variable-map references are flagged (guide section 8).

``fix_release_vars`` rewrites the plain read/write shapes; any *other* use of the
``releaseVariables`` / ``folderVariables`` / ``globalVariables`` maps has no
getter/setter equivalent and would raise ``NameError`` in the container, so it is
left intact and flagged for a manual rewrite.
"""
import ast

import pytest


@pytest.mark.unit
def test_iterating_the_map_is_flagged(migrate):
    result = migrate("for k in releaseVariables:\n    print(k)\n")
    assert result.todo_count == 1
    assert "releaseVariables" in result.todos[0]
    assert "for k in releaseVariables:" in result.migrated  # left intact
    ast.parse(result.migrated)


@pytest.mark.unit
def test_map_method_call_is_flagged(migrate):
    result = migrate("names = releaseVariables.keys()\n")
    assert result.todo_count == 1
    assert "releaseVariables" in result.todos[0]


@pytest.mark.unit
def test_subscript_chained_with_access_is_flagged(migrate):
    # A read chained with further access (`["x"].strip()`) is not the plain subscript
    # fix_release_vars rewrites, so it is flagged rather than silently passed through.
    result = migrate('value = releaseVariables["x"].strip()\n')
    assert result.todo_count == 1
    assert 'releaseVariables["x"].strip()' in result.migrated


@pytest.mark.unit
def test_folder_and_global_leftovers_are_flagged(migrate):
    result = migrate("for k in folderVariables:\n    v = globalVariables.get(k)\n")
    assert result.todo_count == 2
    assert any("folderVariables" in t for t in result.todos)
    assert any("globalVariables" in t for t in result.todos)
    ast.parse(result.migrated)


@pytest.mark.unit
def test_plain_read_is_not_flagged_as_leftover(migrate):
    # The clean read is rewritten by fix_release_vars; the leftover rule must keep off
    # it (no double handling, no spurious TODO).
    result = migrate('x = releaseVariables["a"]\n')
    assert result.todo_count == 0
    assert 'getReleaseVariable("a")' in result.migrated


@pytest.mark.unit
def test_plain_write_is_not_flagged_as_leftover(migrate):
    result = migrate('releaseVariables["a"] = 1\n')
    assert result.todo_count == 0
    assert result.migrated == 'setReleaseVariable("a", 1)\n'


@pytest.mark.unit
def test_flagged_variants_are_not_double_stamped(migrate):
    # del / augmented / unpacking are flagged once by fix_release_vars; the leftover
    # rule must not add a second TODO to the same statement.
    for source in (
        'del releaseVariables["x"]\n',
        'releaseVariables["c"] += 1\n',
        'releaseVariables["x"], y = 1, 2\n',
    ):
        result = migrate(source)
        assert result.todo_count == 1, (source, result.todos)


@pytest.mark.unit
def test_attribute_named_like_the_map_is_safe(migrate):
    # `obj.releaseVariables` is a member access, not the reserved map.
    result = migrate("x = obj.releaseVariables\n")
    assert result.todo_count == 0


@pytest.mark.unit
def test_rebinding_the_name_is_not_flagged(migrate):
    # The author shadows the name with their own dict; it is no longer the map.
    result = migrate("releaseVariables = {}\n")
    assert result.todo_count == 0
