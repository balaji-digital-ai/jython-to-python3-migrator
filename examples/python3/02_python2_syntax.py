# Example 02 - Python 2 -> 3 syntax rules (guide section 10, Tier 1, runnable)
#
# Focused on the constructs the stock fissix fixers rewrite - print statements,
# print-to-stderr, old-style `except E, e:`, the dict `iter*()` / `has_key()` methods,
# `xrange()` and the `<>` operator - so the migrated golden shows the breadth of the
# syntax pass. Everything here is Tier 1, so the output runs as-is with no TODO or
# ERROR left to resolve.
import sys

results = {"passed": 5, "failed": 2, "skipped": 1}

# Old-style print statements, including printing to stderr.
print("Test run summary")
if results["failed"] != 0:
    print("There were failures", file=sys.stderr)

# `iteritems()` / `iterkeys()` and `has_key()` are gone in Python 3.
for name, count in results.items():
    print(name, "->", count)

for name in results.keys():
    if name in results:
        print("have result for", name)

# `xrange()` is just `range()` in Python 3; old-style `except E, e:` becomes `as`.
total = 0
try:
    for i in range(len(results)):
        total = total + i
except KeyError as err:
    print("lookup failed:", err)

print("Total index sum:", total)
