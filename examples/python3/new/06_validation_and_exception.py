# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

task = getCurrentTask()
owner = getReleaseVariable("owner")
environment = getReleaseVariable("environment")

if owner == "":
    raise Exception("Owner is mandatory")

if environment not in ["DEV", "QA", "PROD"]:
    raise Exception("Invalid environment")

task.description = "Validated by Jython Script"
taskApi.updateTask(task)

print("Validation completed successfully")
