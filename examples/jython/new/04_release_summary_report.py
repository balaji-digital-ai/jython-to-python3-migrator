print "Release Summary"

print "Release Name : %s" % release.title
print "Status       : %s" % release.status

phases = phaseApi.getPhases(release.id)

completed = 0
pending = 0

for phase in phases:
    tasks = taskApi.getTasks(phase.id)

    for task in tasks:
        print "%s : %s" % (task.title, task.status)
        if task.status == "COMPLETED":
            completed += 1
        else:
            pending += 1

releaseVariables["completedTasks"] = completed
releaseVariables["pendingTasks"] = pending
