# Example 01 - Reserved objects and the release variable map (Tier 1, fully runnable)
#
# A Jython (xlrelease.ScriptTask) script that migrates to a *runnable* Python 3
# Script (Container) script. It uses only Tier-1 constructs - Python 2 `print`, the
# free `release` / `phase` reserved objects, the predefined `releaseApi` object, and
# the `releaseVariables` map - so the migrated output runs with no TODO or ERROR left.
#
# Note: a Jython task's output is simply its printed text (rendered as markdown). It
# has no `result` / `result_2` / `result_3` output variables - those belong to the
# Python 3 Script (Container) task - so this script does not set them.
release = getCurrentRelease()
phase = getCurrentPhase()
print("Release:", release.title, "(", release.status, ")")
print("Phase:", phase.title)

# A plain write, then a plain read straight back from the release variable map.
setReleaseVariable("migratedBy", "jython2py3")
print("migratedBy =", getReleaseVariable("migratedBy"))

# Conditional writes are still plain sets - each branch becomes setReleaseVariable(...).
if release.status == "IN_PROGRESS":
    setReleaseVariable("approvalRequired", True)
else:
    setReleaseVariable("approvalRequired", False)

# List the release's currently active tasks via the predefined releaseApi object.
for activeTask in releaseApi.getActiveTasks(release.id):
    print("active:", activeTask.title)
