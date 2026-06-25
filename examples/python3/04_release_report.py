# Example 04 - Reading and updating a release through the API objects (Tier 1, runnable)
#
# A reporting/maintenance task built entirely on the predefined API objects
# (`releaseApi`, `phaseApi`, `taskApi`, `searchApi`) and reserved objects. Everything
# here is Tier 1 - the Python 2 `print` statements and `releaseVariables` accesses are
# rewritten and the API objects pass through unchanged - so the output runs as-is.
release = getCurrentRelease()
print("Release Summary")

print("Release Name : %s" % release.title)
print("Status       : %s" % release.status)

# Validate inputs up front; `raise` is unchanged from Python 2 to 3.
environment = getReleaseVariable("environment")
if environment not in ["DEV", "QA", "PROD"]:
    raise Exception("Invalid environment: %s" % environment)

# Walk every phase and its tasks, tallying completion.
completed = 0
pending = 0
for phase in phaseApi.getPhases(release.id):
    for task in taskApi.getTasks(phase.id):
        print("%s : %s" % (task.title, task.status))
        if task.status == "COMPLETED":
            completed += 1
        else:
            pending += 1

# Find specific tasks by title and annotate them - a task mutation plus a write-back.
for deployTask in searchApi.searchTasksByTitle("Deploy"):
    deployTask.description = "Verified by automation"
    taskApi.updateTask(deployTask)

# Store the tallies back as release variables (plain sets -> setReleaseVariable).
setReleaseVariable("completedTasks", completed)
setReleaseVariable("pendingTasks", pending)

# Output properties of the surrounding task. These migrate unchanged as plain
# variables; in a Python 3 Container task they map to its result output properties.
result = "SUCCESS"
result_2 = "%d completed" % completed
result_3 = "%d pending" % pending
print("Done:", result)
