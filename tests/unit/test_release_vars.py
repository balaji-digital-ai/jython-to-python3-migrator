"""Tier 1: variable-dictionary rewrites (guide sections 5 and 8)."""
import ast

import pytest


@pytest.mark.unit
def test_release_variable_read(migrate):
    result = migrate('x = releaseVariables["buildNumber"]\n')
    assert 'getReleaseVariable("buildNumber")' in result.migrated
    assert "releaseVariables[" not in result.migrated


@pytest.mark.unit
def test_release_variable_write_literal(migrate):
    result = migrate('releaseVariables["deployTarget"] = "production"\n')
    assert result.migrated == 'setReleaseVariable("deployTarget", "production")\n'


@pytest.mark.unit
def test_release_variable_write_expression(migrate):
    result = migrate('releaseVariables["artifactPath"] = "/b/%s" % build\n')
    assert result.migrated == 'setReleaseVariable("artifactPath", "/b/%s" % build)\n'


@pytest.mark.unit
def test_folder_and_global_scopes(migrate):
    result = migrate(
        'a = folderVariables["folder.team"]\n'
        'globalVariables["global.env"] = "prod"\n'
    )
    assert 'getFolderVariable("folder.team")' in result.migrated
    assert 'setGlobalVariable("global.env", "prod")' in result.migrated


@pytest.mark.unit
def test_read_inside_call_preserves_context(migrate):
    result = migrate('print(getReleaseVariable, releaseVariables["x"])\n')
    assert 'getReleaseVariable("x")' in result.migrated


@pytest.mark.unit
def test_indentation_preserved_in_block(migrate):
    source = 'if True:\n    releaseVariables["x"] = 1\n'
    result = migrate(source)
    assert '    setReleaseVariable("x", 1)\n' in result.migrated


@pytest.mark.unit
def test_augmented_assignment_is_flagged_not_rewritten(migrate):
    result = migrate('releaseVariables["count"] += 1\n')
    # left as-is (cannot be a single setter call) but flagged for review
    assert "releaseVariables" in result.migrated
    assert result.todo_count == 1


@pytest.mark.unit
def test_nested_read_inside_write_is_rewritten(migrate):
    # Both sides are rewritten: the value is a read, the target is a write.
    result = migrate('releaseVariables["a"] = releaseVariables["b"]\n')
    assert result.migrated == (
        'setReleaseVariable("a", getReleaseVariable("b"))\n')


@pytest.mark.unit
def test_subscript_key_is_a_read_not_a_target(migrate):
    # `releaseVariables["x"]` here is the *key* of another subscript on the LHS, so it
    # is a read, not the assignment target - it must become a getter.
    result = migrate('data[releaseVariables["x"]] = 1\n')
    assert result.migrated == 'data[getReleaseVariable("x")] = 1\n'


@pytest.mark.unit
@pytest.mark.parametrize(
    "source",
    [
        'releaseVariables["x"], y = 1, 2\n',       # bare tuple target
        '[releaseVariables["x"], y] = data\n',     # list target
        '(releaseVariables["x"], y) = data\n',     # parenthesised tuple target
    ],
)
def test_unpacking_target_is_flagged_not_broken(migrate, source):
    # A dict subscript used as a tuple/list unpacking target is a *write*. Emitting a
    # getter there would be a call on the left of `=` (invalid Python), so the rule
    # must flag it instead - and never produce code that fails to parse.
    result = migrate(source)
    assert result.todo_count == 1
    assert "tuple/list unpacking" in result.todos[0]
    # the offending line is left intact (we never silently emit broken code)
    assert "releaseVariables[" in result.migrated
    ast.parse(result.migrated)  # must still be valid Python 3


@pytest.mark.unit
def test_unpacking_on_right_hand_side_stays_a_read(migrate):
    # The subscript is on the value side of the assignment, so it is a read.
    result = migrate('x = releaseVariables["a"], y\n')
    assert result.migrated == 'x = getReleaseVariable("a"), y\n'
