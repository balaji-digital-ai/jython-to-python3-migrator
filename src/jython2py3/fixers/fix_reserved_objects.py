"""Tier 1: inject the helper calls for Jython reserved objects.

Migration guide section 5. Jython binds ``release`` / ``phase`` / ``task`` directly
into the script namespace; Python 3 Script does not. The guide's canonical output
adds the matching helper call near the top:

    release = getCurrentRelease()   # (and/or getCurrentPhase() / getCurrentTask())

This rule reproduces that. It detects *free* uses (a reserved name that is read but
never assigned/imported/defined in the script) and injects ``name = getCurrentX()``
at the top of the module body, after any leading docstring.

The check is intentionally conservative: it never injects for a name the script
already binds, so re-running on migrated code is a no-op.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.fixer_util import Assign, Call, Name, Newline
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms
from fissix.pytree import Node

# reserved object -> the helper function that now provides it
_HELPERS = {
    "release": "getCurrentRelease",
    "phase": "getCurrentPhase",
    "task": "getCurrentTask",
}


class FixReservedObjects(fixer_base.BaseFix):
    # Match the whole module once and reason about it as a unit. Disable the
    # bottom-matcher optimisation, which targets interior-node patterns.
    BM_compatible = False
    PATTERN = "file_input< any* >"

    def transform(self, node, results):
        loaded: set[str] = set()
        bound: set[str] = set()
        for leaf in node.leaves():
            if leaf.type != token.NAME or leaf.value not in _HELPERS:
                continue
            if self._is_attribute_or_keyword(leaf):
                continue
            if self._is_binding(leaf):
                bound.add(leaf.value)
            else:
                loaded.add(leaf.value)

        free = [name for name in _HELPERS if name in loaded and name not in bound]
        if not free:
            return None

        new_statements = [
            Node(syms.simple_stmt, [Assign(Name(name), Call(Name(_HELPERS[name]))), Newline()])
            for name in free
        ]

        # Insert after a leading module docstring, if present.
        insert_at = 0
        children = node.children
        if (
            children
            and children[0].type == syms.simple_stmt
            and children[0].children
            and children[0].children[0].type == token.STRING
        ):
            insert_at = 1

        existing = node.children[insert_at]
        # Keep any leading comments/blank lines above the injected block, and make
        # sure the first injected statement starts on its own line.
        lead = existing.prefix
        if lead and not lead.endswith("\n"):
            lead += "\n"
        new_statements[0].prefix = lead
        existing.prefix = ""
        for offset, statement in enumerate(new_statements):
            node.insert_child(insert_at + offset, statement)
        return None

    @staticmethod
    def _is_attribute_or_keyword(leaf) -> bool:
        """True for ``foo.release`` (attribute) or ``f(release=1)`` (keyword arg) -
        neither is a use of the reserved object itself."""
        prev = leaf.prev_sibling
        if prev is not None and prev.type == token.DOT:
            return True
        nxt = leaf.next_sibling
        if (
            leaf.parent is not None
            and leaf.parent.type == syms.argument
            and prev is None
            and nxt is not None
            and nxt.type == token.EQUAL
        ):
            return True
        return False

    @staticmethod
    def _is_binding(leaf) -> bool:
        """True if this occurrence *defines* the name (assignment, def/class, import,
        ``as`` alias, ``for`` target, or parameter)."""
        parent = leaf.parent
        if parent is None:
            return False

        prev = leaf.prev_sibling
        if prev is not None and prev.type == token.NAME and prev.value in {
            "def",
            "class",
            "as",
            "import",
        }:
            return True

        # `name = ...` or `name += ...` at statement level
        if (
            parent.type == syms.expr_stmt
            and parent.children
            and parent.children[0] is leaf
            and len(parent.children) > 1
            and parent.children[1].type in (token.EQUAL, syms.augassign)
        ):
            return True

        # `for name in ...` (a for-statement) or `... for name in ...` (a
        # comprehension's `comp_for`). In both, the target sits before the `in`
        # keyword. A comprehension variable is locally scoped in Python 3, so a name
        # like `release` used only as a comprehension target is not the reserved
        # object and must not trigger an injection.
        if parent.type in (syms.for_stmt, syms.comp_for):
            children = parent.children
            try:
                in_index = next(
                    i
                    for i, child in enumerate(children)
                    if child.type == token.NAME and child.value == "in"
                )
                if children.index(leaf) < in_index:
                    return True
            except (StopIteration, ValueError):
                pass

        # inside an import statement or a parameter list, anywhere above
        ancestor = parent
        while ancestor is not None:
            if ancestor.type in (
                syms.import_from,
                syms.import_name,
                syms.parameters,
                syms.typedargslist,
                syms.varargslist,
            ):
                return True
            ancestor = ancestor.parent
        return False
