# A Jython (xlrelease.ScriptTask) script that migrates to a *runnable* Python 3
# Script (Container) script: it uses only Tier-1 constructs (Python 2 `print`, the
# free `release` / `phase` reserved objects, and the `releaseVariables` map), so the
# migrated output runs with no TODO or ERROR left to resolve.
#
# Note: a Jython task's output is simply its printed text (rendered as markdown).
# It has no `result` / `result_2` / `result_3` output variables - those belong to
# the Python 3 Script (Container) task - so this script does not set them.
#
# Migrate it with:
#   jython2py3 migrate examples/jython/current_context.py -o examples/python3/current_context.py
print "Release:", release.title, "(", release.status, ")"
print "Phase:", phase.title

# Record who migrated this release, then read it straight back from the map.
releaseVariables["migratedBy"] = "jython2py3"
print "migratedBy =", releaseVariables["migratedBy"]

# List the release's currently active tasks via the predefined releaseApi object.
for activeTask in releaseApi.getActiveTasks(release.id):
    print "active:", activeTask.title
