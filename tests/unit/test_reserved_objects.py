"""Tier 1: reserved objects release/phase/task are injected when free (guide section 5)."""
import pytest


@pytest.mark.unit
def test_free_release_is_injected(migrate):
    result = migrate("title = release.title\n")
    assert "release = getCurrentRelease()" in result.migrated
    assert "title = release.title" in result.migrated
    # it is a real assignment, not a TODO comment
    assert result.todo_count == 0


@pytest.mark.unit
def test_injected_before_first_use(migrate):
    result = migrate("title = release.title\n")
    lines = [ln for ln in result.migrated.splitlines() if ln.strip()]
    assert lines[0] == "release = getCurrentRelease()"


@pytest.mark.unit
def test_docstring_kept_above_injection(migrate):
    result = migrate('"""Module doc."""\ntitle = release.title\n')
    lines = [ln for ln in result.migrated.splitlines() if ln.strip()]
    assert lines[0] == '"""Module doc."""'
    assert lines[1] == "release = getCurrentRelease()"


@pytest.mark.unit
def test_multiple_reserved_objects_injected(migrate):
    result = migrate("a = release.title\nb = task.id\n")
    assert "release = getCurrentRelease()" in result.migrated
    assert "task = getCurrentTask()" in result.migrated
    assert "getCurrentPhase" not in result.migrated  # phase was never used


@pytest.mark.unit
def test_already_bound_is_not_reinjected(migrate):
    # the name is already defined, so it must not be injected again (idempotent rule)
    result = migrate("release = getCurrentRelease()\ntitle = release.title\n")
    assert result.migrated.count("release = getCurrentRelease()") == 1


@pytest.mark.unit
def test_attribute_named_release_is_not_injected(migrate):
    result = migrate("name = deployment.release\n")
    assert "getCurrentRelease" not in result.migrated


@pytest.mark.unit
def test_comprehension_loopvar_named_release_is_not_injected(migrate):
    # A comprehension variable is locally scoped in Python 3, so `release` here is the
    # loop variable, not the reserved object - injecting a helper call would be wrong.
    result = migrate("xs = [release for release in items]\n")
    assert "getCurrentRelease" not in result.migrated


@pytest.mark.unit
def test_dict_comprehension_loopvar_named_phase_is_not_injected(migrate):
    result = migrate("xs = {p: 1 for phase in items}\n")
    assert "getCurrentPhase" not in result.migrated


@pytest.mark.unit
def test_free_use_still_injected_despite_unrelated_comprehension(migrate):
    # `task` is genuinely free; the comprehension over `phase` must not suppress it.
    result = migrate("t = task.id\nxs = [phase for phase in items]\n")
    assert "task = getCurrentTask()" in result.migrated
    assert "getCurrentPhase" not in result.migrated
