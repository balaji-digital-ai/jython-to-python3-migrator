"""Tier 1: rewrite ``java.util.Date`` as the Python 3 ``datetime`` equivalent.

Migration guide section 11. Most Java classes have no Python stand-in, so
``fix_java_usage`` flags them as errors. ``java.util.Date`` is the exception worth
automating - it maps cleanly onto the standard-library ``datetime`` module:

    from java.util import Date          ->  import datetime
    Date()                             ->  datetime.datetime.now(datetime.timezone.utc)
    Date(x.getTime() + ms)             ->  x + datetime.timedelta(milliseconds=ms)

The conversion is *mechanical, not idiomatic* (the millisecond arithmetic above would
read better as ``timedelta(days=7)``), but it runs. This fixer owns the ``Date`` import
line and every ``Date(...)`` call: ``fix_java_imports`` skips a sole
``from java.util import Date`` and ``fix_java_usage`` skips the ``Date`` name, so the
three rules stay disjoint. A ``Date(...)`` shape this fixer does not recognise is left
intact and flagged as an error, so nothing Java is ever silently passed through.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.fixer_util import Call, Name
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms
from fissix.pytree import Leaf, Node

from .._cst import add_error

# The one java.util name this fixer owns; fix_java_imports / fix_java_usage skip it.
JAVA_DATE_NAME = "Date"

_NOW = "datetime.datetime.now"
_UTC = "datetime.timezone.utc"
_TIMEDELTA = "datetime.timedelta"


class FixJavaDate(fixer_base.BaseFix):
    BM_compatible = True

    PATTERN = """
    import_from< 'from' module=any 'import' 'Date' >
    |
    power< 'Date' trailer< '(' inner=any* ')' > >
    """

    def start_tree(self, tree, filename):
        super().start_tree(tree, filename)
        # Only rewrite `Date(...)` when `Date` is the imported java.util class, never a
        # user-defined class that happens to share the name.
        self._date_is_java = any(
            is_java_util_date_import(node)
            for node in tree.pre_order()
            if node.type == syms.import_from
        )

    def transform(self, node, results):
        if node.type == syms.import_from:
            if not is_java_util_date_import(node):
                return None
            return _import_datetime(node.prefix)

        if not self._date_is_java:
            return None

        inner = [n for n in results.get("inner", []) if n.type != token.COMMA]
        if not inner:
            return Call(Name(_NOW), [Name(_UTC)], prefix=node.prefix)
        if len(inner) == 1:
            shifted = _date_from_millis_shift(inner[0], node.prefix)
            if shifted is not None:
                return shifted

        # An unrecognised `Date(...)` shape: don't guess - flag it like any other Java
        # use so it is never silently emitted as undefined `Date(...)`.
        add_error(
            node,
            "don't use Java in Python 3: this `Date(...)` shape has no mechanical "
            "`datetime` equivalent - rewrite it by hand (guide section 11)",
        )
        return None


def is_java_util_date_import(import_from) -> bool:
    """True for exactly ``from java.util import Date`` (sole name, no alias)."""
    if str(import_from.children[1]).strip() != "java.util":
        return False
    names = [
        leaf.value
        for child in import_from.children[3:]
        for leaf in child.leaves()
        if leaf.type == token.NAME and leaf.value != "as"
    ]
    return names == [JAVA_DATE_NAME]


def _import_datetime(prefix: str) -> Node:
    node = Node(syms.import_name, [Name("import"), Name("datetime", prefix=" ")])
    node.prefix = prefix
    return node


def _date_from_millis_shift(arg, prefix: str):
    """``X.getTime() + N`` -> ``X + datetime.timedelta(milliseconds=N)``; else ``None``."""
    if arg.type != syms.arith_expr or len(arg.children) != 3:
        return None
    left, op, right = arg.children
    if op.type != token.PLUS:
        return None
    receiver = _get_time_receiver(left)
    if receiver is None:
        return None

    base = receiver.clone()
    base.prefix = prefix
    millis = right.clone()
    millis.prefix = ""
    keyword = Node(syms.argument, [Name("milliseconds"), Leaf(token.EQUAL, "="), millis])
    delta = Call(Name(_TIMEDELTA), [keyword])
    delta.prefix = " "
    return Node(syms.arith_expr, [base, Leaf(token.PLUS, "+", prefix=" "), delta])


def _get_time_receiver(node):
    """For a ``X.getTime()`` power, return ``X`` (the receiver); else ``None``."""
    if node.type != syms.power or len(node.children) < 3:
        return None
    if not (_is_empty_call(node.children[-1]) and _is_dot_name(node.children[-2], "getTime")):
        return None
    head = node.children[:-2]
    if len(head) == 1:
        return head[0]
    return Node(syms.power, [child.clone() for child in head])


def _is_empty_call(trailer) -> bool:
    return (
        trailer.type == syms.trailer
        and len(trailer.children) == 2
        and trailer.children[0].type == token.LPAR
        and trailer.children[1].type == token.RPAR
    )


def _is_dot_name(trailer, name: str) -> bool:
    return (
        trailer.type == syms.trailer
        and len(trailer.children) == 2
        and trailer.children[0].type == token.DOT
        and trailer.children[1].type == token.NAME
        and trailer.children[1].value == name
    )
