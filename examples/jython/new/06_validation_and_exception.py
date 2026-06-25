owner = releaseVariables["owner"]
environment = releaseVariables["environment"]

if owner == "":
    raise Exception("Owner is mandatory")

if environment not in ["DEV", "QA", "PROD"]:
    raise Exception("Invalid environment")

task.description = "Validated by Jython Script"
taskApi.updateTask(task)

print "Validation completed successfully"
