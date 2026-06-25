# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

release = getCurrentRelease()
print("Release Summary")

print("Release Name : %s" % release.title)
print("Status       : %s" % release.status)

phases = phaseApi.getPhases(release.id)

completed = 0
pending = 0

for phase in phases:
    tasks = taskApi.getTasks(phase.id)

    for task in tasks:
        print("%s : %s" % (task.title, task.status))
        if task.status == "COMPLETED":
            completed += 1
        else:
            pending += 1

setReleaseVariable("completedTasks", completed)
setReleaseVariable("pendingTasks", pending)
