# Example 01 - Reserved objects and the release variable map (Tier 1, fully runnable)
#
# Uses only Tier-1 constructs - Python 2 print, the reserved release / phase objects,
# the predefined releaseApi, and the releaseVariables map - so the migrated Python 3
# runs with no TODO or ERROR left.
release = getCurrentRelease()
phase = getCurrentPhase()
print("Release:", release.title, "(", release.status, ")")
print("Phase:", phase.title)

# Write a value, then read it straight back from the release variable map.
setReleaseVariable("migratedBy", "jython2py3")
print("migratedBy =", getReleaseVariable("migratedBy"))

# Conditional writes are still plain sets (each branch becomes setReleaseVariable).
if str(release.status) == "IN_PROGRESS":
    setReleaseVariable("approvalRequired", True)
else:
    setReleaseVariable("approvalRequired", False)

# List the release's active tasks via the predefined releaseApi object.
for activeTask in releaseApi.getActiveTasks(release.id):
    print("active:", activeTask.title)
