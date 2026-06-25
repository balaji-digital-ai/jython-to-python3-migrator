# Jython Script Task Sample
tasks = releaseApi.getActiveTasks(release.id)

print "Active Tasks"

for task in tasks:
    print "%s : %s" % (task.title, task.status)

    if task.title == "Deploy":
        task.description = "Deployment verified by automation"
        taskApi.updateTask(task)
