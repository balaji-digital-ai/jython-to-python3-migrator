# A task-cleanup Jython (xlrelease.ScriptTask) script. It mixes a Tier-1 rewrite - the
# free `task` reserved object becomes `task = getCurrentTask()`, and a plain variable
# read becomes `getReleaseVariable(...)` - with the Tier-2 variable-map shapes that have
# no single getter/setter form: a method call on a looked-up value, enumerating the map
# with `.keys()`, and a `del`. Those three are left intact and flagged with a TODO
# marker for a manual rewrite (guide section 8).
#
# Migrate it with:
#   jython2py3 migrate examples/jython/task_cleanup.py -o examples/python3/task_cleanup.py

# Tier 1: a free `task` reserved object gets its helper injected at the top.
print "Cleaning up after task:", task.title

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
