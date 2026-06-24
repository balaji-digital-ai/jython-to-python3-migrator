"""Tier 1: variable-dictionary rewrites (guide sections 5 and 8)."""
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
