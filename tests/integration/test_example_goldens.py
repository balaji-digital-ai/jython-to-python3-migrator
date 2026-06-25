"""Golden-file coverage for every bundled example.

For each ``examples/jython/<name>.py`` the migrated output must match the committed
``examples/python3/<name>.py`` byte for byte, parse as Python 3, and carry exactly
the documented number of ``# TODO`` / ``# ERROR`` annotations. If a rule changes,
these fail until the goldens are regenerated:

    jython2py3 migrate examples/jython/ -o examples/python3/

(see docs/ADDING_A_RULE.md).
"""
import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
JYTHON_DIR = _ROOT / "examples" / "jython"
PYTHON3_DIR = _ROOT / "examples" / "python3"

# name -> (expected TODO count, expected ERROR count). Keeping the numbers here makes
# each example's "what should the reader still fix?" contract explicit and tested.
EXPECTED = {
    "01_reserved_objects.py": (0, 0),       # reserved objects + API + vars; fully runnable
    "02_python2_syntax.py": (0, 0),         # pure Python 2 -> 3 syntax pass; runs as-is
    "03_release_orchestration.py": (0, 0),  # API create flow; API imports pass through
    "04_release_report.py": (0, 0),         # read/update via API objects; fully runnable
    "05_release_variables.py": (3, 1),      # java-import + aug-assign + map iteration; HashMap use
    "06_variable_edge_cases.py": (3, 0),    # method-call + .keys() + del on a variable map
    "07_http_request.py": (3, 1),           # HttpRequest (import+call) + java import; java URL use
    "08_java_interop.py": (9, 13),          # nine java imports; thirteen Java uses
    "09_deploy_pipeline.py": (3, 0),        # java-import breadcrumb + HttpRequest (import+call)
}

EXAMPLES = sorted(p.name for p in JYTHON_DIR.glob("*.py"))


@pytest.mark.integration
def test_every_jython_example_has_a_golden_and_expectation():
    # Guard against adding a Jython example but forgetting its golden / expected counts.
    assert set(EXAMPLES) == set(EXPECTED), "examples and EXPECTED are out of sync"
    for name in EXAMPLES:
        assert (PYTHON3_DIR / name).exists(), f"missing golden for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", EXAMPLES)
def test_example_matches_committed_golden(migrate, name):
    migrated = migrate((JYTHON_DIR / name).read_text(encoding="utf-8"))
    golden = (PYTHON3_DIR / name).read_text(encoding="utf-8")
    assert migrated.migrated == golden


@pytest.mark.integration
@pytest.mark.parametrize("name", EXAMPLES)
def test_example_output_is_valid_python3(migrate, name):
    # Annotations are comments, so even the Java/HttpRequest examples must still parse;
    # they fail at *runtime*, not at import, which is exactly what the markers flag.
    migrated = migrate((JYTHON_DIR / name).read_text(encoding="utf-8"))
    ast.parse(migrated.migrated)


@pytest.mark.integration
@pytest.mark.parametrize("name, counts", EXPECTED.items())
def test_example_annotation_counts(migrate, name, counts):
    expected_todos, expected_errors = counts
    migrated = migrate((JYTHON_DIR / name).read_text(encoding="utf-8"))
    assert migrated.todo_count == expected_todos, migrated.todos
    assert migrated.error_count == expected_errors, migrated.errors
