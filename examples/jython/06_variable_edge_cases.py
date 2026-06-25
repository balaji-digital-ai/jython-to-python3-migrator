# Example 06 - Variable-map access patterns that need a manual rewrite (guide section 8)
#
# Mixes Tier-1 rewrites (reserved task object, a plain releaseVariables read) with
# Tier-2 shapes that have no getter/setter form - a method call on a looked-up value,
# .keys() enumeration, and a del - which are left intact and flagged TODO.

# Tier 1: the reserved task object gets its helper injected at the top.
print "Cleaning up after task:", task.title

# Seed the variables this example reads so it runs standalone.
releaseVariables["buildNumber"] = "42"
releaseVariables["artifacts"] = ["app-1.0.jar"]
releaseVariables["scratchValue"] = "temp"

# Tier 1: a plain read becomes getReleaseVariable("buildNumber").
buildNumber = releaseVariables["buildNumber"]

# Tier 2 TODO: a method call on a looked-up value is more than a plain read.
releaseVariables["artifacts"].append(buildNumber)

# Tier 2 TODO: enumerating the keys has no getter/setter form.
for name in releaseVariables.keys():
    print "configured variable:", name

# Tier 2 TODO: deleting a variable is neither a get nor a set.
del releaseVariables["scratchValue"]

print "Cleanup complete for build", buildNumber
