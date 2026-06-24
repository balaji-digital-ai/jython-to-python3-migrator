"""Tier 2: flag plain Java *usage* with an error comment (migration guide section 11).

``fix_java_imports`` removes the ``java.*`` / ``javax.*`` *import* lines, but the
symbols they introduced are still referenced further down the script:

    from java.util import Date
    now = Date()                      # <- this still says `Date()`

In the Python 3 container there is no JVM, so every such reference raises at runtime
(``NameError`` for an imported symbol, ``ModuleNotFoundError`` for a fully-qualified
path). Unlike an ``HttpRequest`` call there is no mechanical Python equivalent to
swap in - the author has to redesign the code - so this is flagged as an **error**,
not a TODO:

    # ERROR[jython2py3] don't use Java in Python 3: `Date()` ...
    now = Date()

Two shapes are caught:

* a name imported from ``java.*`` / ``javax.*`` and then used (``Date()``), and
* a fully-qualified reference written inline (``java.util.Date()``).

The import lines themselves are left to ``fix_java_imports``; they are skipped here.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms

from .._cst import add_error, enclosing_statement

_JAVA_ROOTS = {"java", "javax"}

_IMPORT_TYPES = (syms.import_from, syms.import_name)


class FixJavaUsage(fixer_base.BaseFix):
    # Reason about the whole module at once: the names to flag come from the import
    # statements, so a single interior node is not enough context.
    BM_compatible = False
    PATTERN = "file_input< any* >"

    def start_tree(self, tree, filename):
        super().start_tree(tree, filename)
        # Collect the local names introduced by `from java.* import A, B as C`. We do
        # this once up front, while the imports are still present (fix_java_imports
        # removes them later in the same pass).
        self._java_names: set[str] = set()
        for node in tree.pre_order():
            if node.type == syms.import_from and _is_java_module(node):
                self._java_names.update(_imported_names(node))

    def transform(self, node, results):
        for leaf in list(node.leaves()):
            if leaf.type != token.NAME or _in_import(leaf):
                continue

            # 1. A fully-qualified reference: `java.util.Date(...)`.
            if leaf.value in _JAVA_ROOTS and _is_qualified_head(leaf):
                stmt = enclosing_statement(leaf)
                add_error(stmt, _message(_qualified_text(leaf)))
                continue

            # 2. A name imported from java.* and used here (not an attribute access
            #    like `obj.Date`, and not the import binding itself).
            if (
                leaf.value in self._java_names
                and not _is_attribute(leaf)
                and not _is_binding(leaf)
            ):
                stmt = enclosing_statement(leaf)
                add_error(stmt, _message(leaf.value))
        return None


def _message(symbol: str) -> str:
    return (
        f"don't use Java in Python 3: `{symbol}` is a JVM class that the container "
        f"cannot load - replace it with a Python 3 equivalent (guide section 11)"
    )


def _is_java_module(import_from) -> bool:
    """True for `from java...`/`from javax...` import statements."""
    # children: 'from' <module> 'import' ...
    module = import_from.children[1]
    first = next((lf for lf in module.leaves() if lf.type == token.NAME), None)
    return first is not None and first.value in _JAVA_ROOTS


def _imported_names(import_from) -> set[str]:
    """The local names bound by an `from java.x import ...` (honouring `as` aliases)."""
    names: set[str] = set()
    # The import target is everything after the 'import' keyword.
    after_import = import_from.children[3:]
    leaves = [lf for node in after_import for lf in node.leaves()]
    i = 0
    while i < len(leaves):
        leaf = leaves[i]
        if leaf.type == token.NAME and leaf.value != "as":
            nxt = leaves[i + 1] if i + 1 < len(leaves) else None
            if nxt is not None and nxt.type == token.NAME and nxt.value == "as":
                names.add(leaves[i + 2].value)  # `X as Y` binds Y
                i += 3
                continue
            names.add(leaf.value)
        i += 1
    # `from java.x import *` binds nothing we can name; ignore the star.
    names.discard("*")
    return names


def _in_import(leaf) -> bool:
    ancestor = leaf.parent
    while ancestor is not None:
        if ancestor.type in _IMPORT_TYPES:
            return True
        ancestor = ancestor.parent
    return False


def _is_attribute(leaf) -> bool:
    """True for the `Date` in `obj.Date` (a member access, not the imported name)."""
    prev = leaf.prev_sibling
    return prev is not None and prev.type == token.DOT


def _is_qualified_head(leaf) -> bool:
    """True if `leaf` (`java`/`javax`) heads an attribute chain, e.g. `java.util.X`."""
    return not _is_attribute(leaf) and _is_dot_trailer(leaf.next_sibling)


def _qualified_text(leaf) -> str:
    """Render the dotted path headed by `leaf`, e.g. `java.util.Date`, for the message."""
    parts = [leaf.value]
    sibling = leaf.next_sibling
    while _is_dot_trailer(sibling):
        parts.append(sibling.children[1].value)
        sibling = sibling.next_sibling
    return ".".join(parts)


def _is_dot_trailer(node) -> bool:
    """True for a ``.name`` trailer node, e.g. the ``.util`` in ``java.util``."""
    return (
        node is not None
        and node.type == syms.trailer
        and node.children[0].type == token.DOT
    )


def _is_binding(leaf) -> bool:
    """True if this occurrence defines the name (assignment target, def/class, `as`)."""
    parent = leaf.parent
    if parent is None:
        return False
    prev = leaf.prev_sibling
    if prev is not None and prev.type == token.NAME and prev.value in {"def", "class", "as"}:
        return True
    if (
        parent.type == syms.expr_stmt
        and parent.children
        and parent.children[0] is leaf
        and len(parent.children) > 1
        and parent.children[1].type in (token.EQUAL, syms.augassign)
    ):
        return True
    return False
