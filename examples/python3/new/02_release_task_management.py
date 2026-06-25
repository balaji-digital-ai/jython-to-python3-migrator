# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

# Jython Script Task Sample
release = getCurrentRelease()
tasks = releaseApi.getActiveTasks(release.id)

print("Active Tasks")

for task in tasks:
    print("%s : %s" % (task.title, task.status))

    if task.title == "Deploy":
        task.description = "Deployment verified by automation"
        taskApi.updateTask(task)
