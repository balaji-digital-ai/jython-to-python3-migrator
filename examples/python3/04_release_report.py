# Example 04 - Reading and updating a release through the API objects (Tier 1, runnable)
#
# A reporting/maintenance task built on the reserved release object and the predefined
# taskApi. All Tier 1, so the output runs as-is after migration.
release = getCurrentRelease()
print("Release Summary")

print("Release Name : %s" % release.title)
print("Status       : %s" % release.status)

# Seed a sample input, then validate it; raise is unchanged from Python 2 to 3.
setReleaseVariable("environment", "QA")
environment = getReleaseVariable("environment")
if environment not in ["DEV", "QA", "PROD"]:
    raise Exception("Invalid environment: %s" % environment)

# Walk every phase and its tasks: tally completion and annotate "Deploy" tasks.
completed = 0
pending = 0
for phase in release.getPhases():
    for task in phase.getTasks():
        print("%s : %s" % (task.title, task.status))
        if str(task.status) == "COMPLETED":
            completed += 1
        else:
            pending += 1
        if "Deploy" in task.title:
            task.description = "Verified by automation"
            taskApi.updateTask(task)

# Store the tallies back as release variables (plain sets -> setReleaseVariable).
setReleaseVariable("completedTasks", completed)
setReleaseVariable("pendingTasks", pending)

# Plain result variables; in a Python 3 Container task these map to its outputs.
result = "SUCCESS"
result_2 = "%d completed" % completed
result_3 = "%d pending" % pending
print("Done:", result)
