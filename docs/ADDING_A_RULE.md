# Adding or changing a migration rule

Every migration rule is a self-contained [`fissix`](https://pypi.org/project/fissix/)
fixer. This is the only file you touch to evolve the migration logic, which is what
keeps the engine maintainable.

## 1. Decide the tier

* **Tier 1 (auto-transform)** — the rewrite is unambiguous and always correct.
  Return the replacement node from `transform`.
* **Tier 2 (annotate)** — the rewrite needs human judgement. Call
  `add_todo(node, "...")` from `jython2py3._cst` and return `None`. Reference the
  relevant migration-guide section in the message.

When in doubt, prefer Tier 2. The tool's contract is: *never silently emit code that
might be wrong.*

## 2. Write the fixer

Create `src/jython2py3/fixers/fix_<name>.py`:

```python
from fissix import fixer_base
from fissix.fixer_util import Call, Name

class FixExample(fixer_base.BaseFix):
    BM_compatible = True

    # A fissix grammar pattern. Capture sub-nodes with `name=...`.
    PATTERN = """
    power< 'oldName' trailer< '(' args=any* ')' > >
    """

    def transform(self, node, results):
        # results["args"] holds the captured nodes
        return Call(Name("newName"), [results["args"][0].clone()], prefix=node.prefix)
```

Useful helpers:

* `fissix.fixer_util`: `Call`, `Name`, `Comma`, `Assign`, `Newline`, `BlankLine`.
* `jython2py3._cst`: `add_todo(node, message)` (Tier 2 comments), `enclosing_statement`,
  `is_name`.

Tips:

* Patterns match the **concrete syntax tree**, not text, so comments and strings are
  never matched by accident.
* To rewrite a whole statement (e.g. an assignment), navigate to `node.parent` and
  `replace()` it; remember to `remove()` a child before reparenting it.
* Preserve `node.prefix` on the replacement so indentation/leading comments survive.

## 3. Register it

Append the dotted path to `CUSTOM_FIXERS` in
`src/jython2py3/fixers/__init__.py`.

## 4. Test it

Add `tests/unit/test_<name>.py` using the `migrate` fixture:

```python
import pytest

@pytest.mark.unit
def test_example(migrate):
    result = migrate("oldName(1)\n")
    assert "newName(1)" in result.migrated
```

Run `pytest -m unit`. For broader coverage, extend `examples/jython/deploy.py` and
the integration assertions in `tests/integration/test_examples.py`.

## 5. Reference the spec

Cite the [migration guide](JYTHON-TO-PYTHON3-MIGRATION.md) section in the fixer
docstring and the TODO message so the tool and the documentation cannot drift apart.
The guide's Quick Reference table is effectively the test matrix.
